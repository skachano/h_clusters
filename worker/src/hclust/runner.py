"""Campaign orchestrator: plans the stage DAG into the database and runs it with a pool.

A single process owns the database. ORCA jobs run in a thread pool: each thread just
waits on an external ORCA process, so threads are enough. The run is resumable:
finished jobs are never redone, interrupted ones go back to the queue, and
run_orca's content-addressed cache turns re-runs of finished-on-disk jobs into
a parse.
"""

import time
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait

import numpy as np
from sqlmodel import Session, select

from hclust.campaign import CampaignSpec, StageSpec
from hclust.db import Attempt, Campaign, Job, JobResult, JobStatus, StateRow, Structure, _now
from hclust.engines.orca import OrcaJob, Task, allow_runs, kill_all, run_orca
from hclust.geometry import Geometry
from hclust.levels import LEVELS
from hclust.results import Result
from hclust.structures import GENERATORS

MAX_ATTEMPTS = 3
# Keywords added on the 1st and 2nd retry after an SCF convergence failure.
SCF_LADDER = (("SlowConv",), ("VerySlowConv",))
# Largest atomic displacement (Angstrom) when pushing a saddle point downhill.
DISPLACEMENT = 0.1

Execute = Callable[[OrcaJob, float], Result]


def execute_orca(job: OrcaJob, timeout_s: float) -> Result:
    return run_orca(job, timeout_s=timeout_s)


# --------------------------------------------------------------------------- planning


def plan(session: Session, spec: CampaignSpec) -> Campaign:
    """Insert the campaign, its states, seed structures and root jobs. Idempotent."""
    campaign = session.exec(select(Campaign).where(Campaign.name == spec.name)).first()
    if campaign is None:
        campaign = Campaign(name=spec.name, spec={})
    campaign.spec = spec.model_dump(mode="json", by_alias=True)
    session.add(campaign)
    session.flush()

    for state in spec.species.states():
        row = _state_row(session, state)
        for seed in spec.seeds:
            for geometry in GENERATORS[seed.generator](state.m, **seed.params):
                structure = _structure(session, row.id, f"seed:{seed.generator}", geometry)
                _job(session, campaign, row.id, spec.root, structure.id, parent_id=None)
    session.commit()
    return campaign


def _state_row(session: Session, state) -> StateRow:
    row = session.exec(
        select(StateRow).where(
            StateRow.m == state.m, StateRow.charge == state.charge, StateRow.mult == state.mult
        )
    ).first()
    if row is None:
        row = StateRow(m=state.m, charge=state.charge, mult=state.mult, n_electrons=state.n_electrons)
        session.add(row)
        session.flush()
    return row


def _structure(
    session: Session, state_id: int, origin: str, geometry: Geometry, parent_job_id: int | None = None
) -> Structure:
    xyz = geometry.to_xyz()
    row = session.exec(
        select(Structure).where(
            Structure.state_id == state_id, Structure.origin == origin,
            Structure.parent_job_id == parent_job_id, Structure.xyz == xyz,
        )
    ).first()
    if row is None:
        row = Structure(state_id=state_id, origin=origin, parent_job_id=parent_job_id, xyz=xyz)
        session.add(row)
        session.flush()
    return row


def _job(
    session: Session, campaign: Campaign, state_id: int, stage: StageSpec,
    structure_id: int, parent_id: int | None,
) -> Job:
    job = session.exec(
        select(Job).where(
            Job.campaign_id == campaign.id, Job.stage == stage.name,
            Job.input_structure_id == structure_id,
        )
    ).first()
    if job is None:
        job = Job(
            campaign_id=campaign.id, state_id=state_id, stage=stage.name, level=stage.level,
            task=stage.task, parent_id=parent_id,
            input_structure_id=structure_id, start_structure_id=structure_id,
        )
        session.add(job)
        session.flush()
    return job


# --------------------------------------------------------------------------- running


class Runner:
    def __init__(
        self, session: Session, spec: CampaignSpec, execute: Execute = execute_orca,
        workers: int | None = None, log: Callable[[str], None] = print,
    ):
        self.session = session
        self.spec = spec
        self.execute = execute
        self.workers = workers or spec.resources.workers
        self.log = log
        self.campaign = plan(session, spec)

    def run(self) -> dict[str, int]:
        """Run until no job is pending or running; return job counts by status."""
        self._recover()
        allow_runs()
        in_flight: dict[Future, int] = {}
        with ThreadPoolExecutor(self.workers) as pool:
            try:
                while True:
                    while len(in_flight) < self.workers and (job := self._next_pending()):
                        in_flight[self._submit(pool, job)] = job.id
                    if not in_flight:
                        break
                    finished, _ = wait(in_flight, return_when=FIRST_COMPLETED)
                    for future in finished:
                        result, elapsed = future.result()
                        job_id = in_flight.pop(future)
                        self._record(self.session.get(Job, job_id), result, elapsed)
            except KeyboardInterrupt:
                kill_all()
                pool.shutdown(wait=True, cancel_futures=True)
                self._requeue(in_flight.values())
                self.log(f"interrupted: {len(in_flight)} running job(s) returned to the queue")
                raise
        return self.counts()

    def counts(self) -> dict[str, int]:
        jobs = self.session.exec(select(Job).where(Job.campaign_id == self.campaign.id)).all()
        return {s.value: sum(j.status == s for j in jobs) for s in JobStatus}

    def _recover(self) -> None:
        """Jobs left 'running' by a killed orchestrator go back to the queue."""
        stale = self.session.exec(
            select(Job).where(Job.campaign_id == self.campaign.id, Job.status == JobStatus.RUNNING)
        ).all()
        self._requeue(j.id for j in stale)
        if stale:
            self.log(f"recovered {len(stale)} job(s) left running by a previous run")

    def _requeue(self, job_ids) -> None:
        for job_id in job_ids:
            job = self.session.get(Job, job_id)
            job.status, job.updated_at = JobStatus.PENDING, _now()
            self.session.add(job)
        self.session.commit()

    def _next_pending(self) -> Job | None:
        return self.session.exec(
            select(Job)
            .where(Job.campaign_id == self.campaign.id, Job.status == JobStatus.PENDING)
            .order_by(Job.id)
        ).first()

    def _submit(self, pool: ThreadPoolExecutor, job: Job) -> Future:
        orca_job = self.orca_job(job)
        job.status, job.hash, job.updated_at = JobStatus.RUNNING, orca_job.hash, _now()
        self.session.add(job)
        self.session.commit()
        timeout_s = self.spec.resources.timeout_min * 60
        return pool.submit(_timed, self.execute, orca_job, timeout_s)

    def orca_job(self, job: Job) -> OrcaJob:
        state = self.session.get(StateRow, job.state_id).to_state()
        geometry = Geometry.from_xyz(self.session.get(Structure, job.start_structure_id).xyz)
        return OrcaJob(
            state, geometry, LEVELS[job.level], Task(job.task),
            self.spec.resources.maxcore_mb, tuple(job.modifiers),
        )

    # ----------------------------------------------------------------------- outcomes

    def _record(self, job: Job, result: Result, elapsed: float) -> None:
        job.attempts += 1
        action = self._next_action(job, result)
        self.session.add(Attempt(
            job_id=job.id, n=job.attempts, hash=job.hash, modifiers=list(job.modifiers),
            start_structure_id=job.start_structure_id,
            status=result.status, error=result.error, error_kind=result.error_kind,
            action=action, cached=result.cached, wall_s=result.wall_time_s,
        ))
        job.error, job.error_kind, job.wall_s = result.error, result.error_kind, result.wall_time_s

        if action is not None:
            self._prepare_retry(job, result, action)
            job.status = JobStatus.PENDING
        elif result.ok:
            job.status = JobStatus.DONE
            self._store_result(job, result)
        else:
            job.status = JobStatus.FAILED
        job.updated_at = _now()
        self.session.add(job)
        self.session.commit()
        self._log_outcome(job, result, elapsed, action)

    def _next_action(self, job: Job, result: Result) -> str | None:
        """Retry playbook (doc/Plan.md, 3.5). None means the job reached a final state."""
        if job.attempts >= MAX_ATTEMPTS:
            return None
        if result.ok:
            return "displace" if result.n_imag else None
        if result.error_kind == "scf" and job.attempts <= len(SCF_LADDER):
            return "scf"
        if result.error_kind == "opt" and result.geometry is not None:
            return "restart"
        return None

    def _prepare_retry(self, job: Job, result: Result, action: str) -> None:
        if action == "scf":
            job.modifiers = list(SCF_LADDER[job.attempts - 1])
            return
        geometry = result.geometry
        if action == "displace":
            geometry = displace_along_imaginary_mode(result, sign=(-1) ** (job.attempts + 1))
        structure = _structure(self.session, job.state_id, f"{job.stage}:{action}", geometry, job.id)
        job.start_structure_id = structure.id

    def _store_result(self, job: Job, result: Result) -> None:
        if Task(job.task).optimizes:
            final_id = _structure(self.session, job.state_id, job.stage, result.geometry, job.id).id
        else:
            final_id = job.start_structure_id
        self.session.merge(JobResult(
            job_id=job.id, energy=result.energy, final_structure_id=final_id,
            s2=result.s2, homo=result.homo, lumo=result.lumo,
            mulliken_charges=result.mulliken_charges,
            frequencies=None if result.frequencies is None else result.frequencies.tolist(),
            modes=None if result.modes is None else result.modes.tolist(),
            thermo=result.thermo, n_imag=result.n_imag,
            point_group=result.point_group, symmetry_number=result.symmetry_number,
            opt_converged=result.opt_converged, orca_version=result.orca_version,
        ))
        for child in self.spec.children(job.stage):
            if child.when == "minimum" and not _is_minimum(result):
                continue
            _job(self.session, self.campaign, job.state_id, child, final_id, parent_id=job.id)

    def _log_outcome(self, job: Job, result: Result, elapsed: float, action: str | None) -> None:
        counts = self.counts()
        total = sum(counts.values())
        finished = counts["done"] + counts["failed"]
        state = self.session.get(StateRow, job.state_id).to_state()
        outcome = f"retry ({action})" if action else str(job.status)
        if job.status == JobStatus.DONE and result.n_imag:
            outcome += f", saddle point ({result.n_imag} imaginary)"
        if not result.ok:
            outcome += f": {result.error}"
        source = "cached" if result.cached else f"{elapsed:.1f} s"
        self.log(
            f"[{finished:4d}/{total:4d}] {state.label:<10} {job.stage:<6} "
            f"#{job.attempts} {outcome} ({source})"
        )


def _timed(execute: Execute, job: OrcaJob, timeout_s: float) -> tuple[Result, float]:
    start = time.monotonic()
    result = execute(job, timeout_s)
    return result, time.monotonic() - start


def _is_minimum(result: Result) -> bool:
    """A lone atom has no vibrations and is trivially a minimum."""
    if result.geometry is not None and len(result.geometry) == 1:
        return True
    return bool(result.is_minimum)


def displace_along_imaginary_mode(result: Result, sign: int = 1) -> Geometry:
    """Push a saddle point downhill along its most imaginary mode."""
    mode = result.modes[int(np.argmin(result.frequencies))]
    mode = mode / np.linalg.norm(mode, axis=1).max()
    geometry = result.geometry
    return Geometry(geometry.symbols, geometry.coords + sign * DISPLACEMENT * mode)
