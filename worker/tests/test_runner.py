"""Runner logic with a scripted fake ORCA: DAG progression, retries, resumability."""

import numpy as np
import pytest
from sqlmodel import Session, select

from hclust.campaign import CampaignSpec
from hclust.db import Attempt, Job, JobResult, Structure, get_engine
from hclust.engines import orca
from hclust.engines.orca import OrcaJob, Task
from hclust.geometry import Geometry
from hclust.results import Result
from hclust.runner import MAX_ATTEMPTS, Runner, plan


@pytest.fixture(autouse=True)
def fixed_version(monkeypatch):
    monkeypatch.setattr(orca, "orca_version", lambda: "6.1.1")


@pytest.fixture
def session(tmp_path):
    with Session(get_engine(tmp_path / "test.sqlite")) as s:
        yield s


def make_spec(m=(1, 2), charges=(0,), n_mult=1) -> CampaignSpec:
    return CampaignSpec.model_validate({
        "name": "t",
        "species": {"m": list(m), "charges": list(charges), "n_mult": n_mult},
        "seeds": [{"generator": "chain", "params": {"spacing": 0.8}}],
        "stages": [
            {"name": "pre", "level": "L0", "task": "opt"},
            {"name": "opt", "level": "L1", "task": "optfreq", "from": "pre"},
            {"name": "ref", "level": "L2", "task": "sp", "from": "opt", "when": "minimum"},
        ],
    })


def ok(job: OrcaJob, freqs=None, energy=-1.0) -> Result:
    """A successful result; optimizations shrink the geometry so that outputs are traceable."""
    g = job.geometry
    task = job.effective_task
    if task.optimizes:
        g = Geometry(g.symbols, g.coords * 0.9)
    result = Result(status="ok", energy=energy, geometry=g)
    if task.has_freq:
        n_vib = max(3 * len(g) - 5, 1)
        result.frequencies = np.array(freqs if freqs is not None else [1000.0] * n_vib)
        modes = np.zeros((len(result.frequencies), len(g), 3))
        modes[:, :, 0] = 1.0  # every mode moves all atoms along +x
        result.modes = modes
    return result


class FakeOrca:
    """Records calls; `script(job, n_call_for_this_hash)` decides the result."""

    def __init__(self, script=None):
        self.calls: list[OrcaJob] = []
        self.script = script or (lambda job, n: ok(job))

    def __call__(self, job: OrcaJob, timeout_s: float) -> Result:
        self.calls.append(job)
        return self.script(job, len(self.calls))


def run(session, spec, fake, workers=1):
    return Runner(session, spec, execute=fake, workers=workers, log=lambda _: None).run()


def jobs(session):
    return session.exec(select(Job).order_by(Job.id)).all()


def test_plan_is_idempotent(session):
    spec = make_spec(m=(1, 3), charges=(-1, 0, 1), n_mult=2)
    plan(session, spec)
    first = [(j.state_id, j.stage, j.input_structure_id) for j in jobs(session)]
    plan(session, spec)
    assert [(j.state_id, j.stage, j.input_structure_id) for j in jobs(session)] == first
    assert len(first) == len(spec.species.states())


def test_dag_runs_to_completion(session):
    fake = FakeOrca()
    counts = run(session, make_spec(), fake)
    # H (single atom) and H2: three stages each.
    assert counts == {"pending": 0, "running": 0, "done": 6, "failed": 0}
    by_stage = {(j.state_id, j.stage): j for j in jobs(session)}
    for (state_id, stage), job in by_stage.items():
        if stage == "pre":
            continue
        parent = session.get(Job, job.parent_id)
        # Each stage starts from its parent's final structure.
        assert job.input_structure_id == session.get(JobResult, parent.id).final_structure_id
    # The H2 L1 job saw the L0-optimized (shrunk) geometry.
    h2_opt = next(c for c in fake.calls if c.level.name == "L1" and len(c.geometry) == 2)
    assert h2_opt.geometry.distances()[0] == pytest.approx(0.8 * 0.9)


def test_scf_failure_climbs_the_ladder(session):
    def script(job, n):
        if "VerySlowConv" in job.extra_keywords:
            return ok(job)
        return Result(status="failed", error="SCF NOT CONVERGED", error_kind="scf")

    run(session, make_spec(m=(1, 1)), FakeOrca(script))
    pre = jobs(session)[0]
    assert pre.status == "done" and pre.attempts == 3
    assert pre.modifiers == ["VerySlowConv"]
    attempts = session.exec(select(Attempt).where(Attempt.job_id == pre.id).order_by(Attempt.n)).all()
    assert [a.modifiers for a in attempts] == [[], ["SlowConv"], ["VerySlowConv"]]
    assert [a.action for a in attempts] == ["scf", "scf", None]


def test_unconverged_opt_restarts_from_last_geometry(session):
    seen = []

    def script(job, n):
        seen.append(job.geometry.distances()[0])
        if job.level.name == "L0" and len(seen) == 1:
            last = Geometry(job.geometry.symbols, job.geometry.coords * 1.1)
            return Result(status="failed", error_kind="opt", error="not converged", geometry=last)
        return ok(job)

    run(session, make_spec(m=(2, 2)), FakeOrca(script))
    assert seen[1] == pytest.approx(0.8 * 1.1)
    assert all(j.status == "done" for j in jobs(session))


def test_saddle_point_is_displaced_then_given_up(session):
    def script(job, n):
        if job.effective_task.has_freq:
            return ok(job, freqs=[-500.0])  # stays a saddle point forever
        return ok(job)

    run(session, make_spec(m=(2, 2)), FakeOrca(script))
    opt = next(j for j in jobs(session) if j.stage == "opt")
    assert opt.status == "done" and opt.attempts == MAX_ATTEMPTS
    assert session.get(JobResult, opt.id).n_imag == 1
    # Displacements alternate in sign along the imaginary mode (+x), by 0.1 A.
    starts = session.exec(
        select(Structure).where(Structure.origin == "opt:displace").order_by(Structure.id)
    ).all()
    assert len(starts) == 2
    # Not a minimum: the L2 stage (when: minimum) is never created.
    assert not any(j.stage == "ref" for j in jobs(session))


def test_unrecoverable_failure_stops_the_branch(session):
    def script(job, n):
        if job.level.name == "L1":
            return Result(status="failed", error="boom", error_kind="other")
        return ok(job)

    counts = run(session, make_spec(m=(2, 2)), FakeOrca(script))
    assert counts["failed"] == 1 and counts["done"] == 1
    assert jobs(session)[1].attempts == 1


def test_interrupted_run_resumes_without_redoing_work(session):
    spec = make_spec(m=(1, 3), charges=(0, 1), n_mult=1)

    def interrupt_on_third(job, n):
        if n == 3:
            raise KeyboardInterrupt
        return ok(job)

    first = FakeOrca(interrupt_on_third)
    with pytest.raises(KeyboardInterrupt):
        run(session, spec, first)
    done_before = {j.id for j in jobs(session) if j.status == "done"}
    assert len(done_before) == 2
    assert not any(j.status == "running" for j in jobs(session))

    second = FakeOrca()
    counts = run(session, spec, second)
    assert counts["done"] == len(jobs(session)) and counts["failed"] == 0
    rerun = {c.hash for c in second.calls}
    assert rerun.isdisjoint({j.hash for j in jobs(session) if j.id in done_before})
    # The interrupted job (call 3) is run again, the two finished ones are not.
    assert first.calls[2].hash in rerun


def test_jobs_left_running_by_a_crash_are_recovered(session):
    spec = make_spec(m=(1, 1))
    plan(session, spec)
    job = jobs(session)[0]
    job.status = "running"
    session.add(job)
    session.commit()
    counts = run(session, spec, FakeOrca())
    assert counts["running"] == 0 and counts["done"] == 3
