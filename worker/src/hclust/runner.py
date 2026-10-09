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
from hclust.db import (
    TERMINAL, Attempt, Campaign, Candidate, Job, JobResult, JobStatus, StateRow, Structure, _now,
)
from hclust.engines.orca import OrcaJob, Task, allow_runs, kill_all, run_orca
from hclust.geometry import Geometry
from hclust.levels import LEVELS
from hclust.results import Result
from hclust.structures import GENERATORS, composition, is_dissociated, same_structure
from hclust.units import HARTREE_TO_KCAL

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

    generated: dict[tuple[int, int], list[Geometry]] = {}  # (seed index, m) -> geometries
    for state in spec.species.states():
        row = _state_row(session, state)
        for i, seed in enumerate(spec.seeds):
            if (i, state.m) not in generated:
                generated[i, state.m] = GENERATORS[seed.generator](state.m, **seed.params)
            for geometry in generated[i, state.m]:
                structure = _structure(session, row.id, f"seed:{seed.generator}", geometry)
                _job(session, campaign, row.id, spec.seed_stage(seed), structure.id, parent_id=None)
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
        self._expand()
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
        jobs = self._jobs()
        return {s.value: sum(j.status == s for j in jobs) for s in JobStatus}

    def _jobs(self, *conditions) -> list[Job]:
        return self.session.exec(
            select(Job).where(Job.campaign_id == self.campaign.id, *conditions)
        ).all()

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
        elif result.error_kind == "opt" and self._dissociated(result.geometry):
            job.status = JobStatus.DISSOCIATED
        else:
            job.status = JobStatus.FAILED
        job.updated_at = _now()
        self.session.add(job)
        self.session.commit()
        self._log_outcome(job, result, elapsed, action)
        if job.status in TERMINAL:
            self._maybe_select(job.state_id)

    def _dissociated(self, geometry: Geometry | None) -> bool:
        return geometry is not None and is_dissociated(geometry, self.spec.dissociation_cutoff)

    def _next_action(self, job: Job, result: Result) -> str | None:
        """Retry playbook (doc/Plan.md, 3.5). None means the job reached a final state.

        Fragments drifting apart are a result, not a failure: they are never retried.
        """
        if job.attempts >= MAX_ATTEMPTS or self._dissociated(result.geometry):
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
        stage = self.spec.stage(job.stage)
        if result.ensemble is not None:
            ensemble = result.ensemble[: stage.max_outputs]
            outputs = [_structure(self.session, job.state_id, job.stage, g, job.id).id for g in ensemble]
        elif Task(job.task).optimizes or Task(job.task) is Task.GOAT:
            outputs = [_structure(self.session, job.state_id, job.stage, result.geometry, job.id).id]
        else:
            outputs = [job.start_structure_id]
        self.session.merge(JobResult(
            job_id=job.id, energy=result.energy, final_structure_id=outputs[0],
            s2=result.s2, homo=result.homo, lumo=result.lumo,
            mulliken_charges=result.mulliken_charges,
            frequencies=None if result.frequencies is None else result.frequencies.tolist(),
            modes=None if result.modes is None else result.modes.tolist(),
            thermo=result.thermo, n_imag=result.n_imag,
            point_group=result.point_group, symmetry_number=result.symmetry_number,
            opt_converged=result.opt_converged, orca_version=result.orca_version,
        ))
        self.session.flush()
        self._spawn_children(job)

    def _spawn_children(self, job: Job) -> None:
        """Create the jobs of every ORCA stage that continues from this finished job (idempotent)."""
        result = self.session.get(JobResult, job.id)
        stage = self.spec.stage(job.stage)
        if Task(job.task) is Task.GOAT:
            outputs = [s.id for s in self.session.exec(
                select(Structure)
                .where(Structure.parent_job_id == job.id, Structure.origin == job.stage)
                .order_by(Structure.id)
            ).all()][: stage.max_outputs]
        else:
            outputs = [result.final_structure_id]
        single_atom = self.session.get(StateRow, job.state_id).m == 1  # trivially a minimum
        for child in self.spec.children(job.stage):
            if child.is_select or (child.when == "minimum" and not (single_atom or result.n_imag == 0)):
                continue
            for structure_id in outputs:
                _job(self.session, self.campaign, job.state_id, child, structure_id, parent_id=job.id)

    def _expand(self) -> None:
        """Create jobs for stages added to the campaign after their parents had finished."""
        for job in self._jobs(Job.status == JobStatus.DONE):
            self._spawn_children(job)
        self.session.commit()
        for state_id in {j.state_id for j in self._jobs()}:
            self._maybe_select(state_id)

    # ----------------------------------------------------------------------- selection

    def _maybe_select(self, state_id: int) -> None:
        """Run each select stage for this state once all jobs that can feed it have finished."""
        for stage in self.spec.stages:
            if not stage.is_select:
                continue
            if self._selected(stage.name, state_id):
                self._spawn_from_selection(stage, state_id)
                continue
            upstream = self._jobs(
                Job.state_id == state_id, Job.stage.in_(self.spec.upstream(stage.from_[0]))
            )
            if upstream and all(j.status in TERMINAL for j in upstream):
                done = [j for j in upstream if j.stage == stage.from_[0] and j.status == JobStatus.DONE]
                if done:
                    self._select(stage, state_id, done)

    def _spawn_from_selection(self, stage: StageSpec, state_id: int) -> None:
        chosen = self.session.exec(
            select(Candidate).where(
                Candidate.campaign_id == self.campaign.id, Candidate.stage == stage.name,
                Candidate.state_id == state_id, Candidate.selected == True,  # noqa: E712
            )
        ).all()
        for candidate in chosen:
            for child in self.spec.children(stage.name):
                _job(self.session, self.campaign, state_id, child, candidate.structure_id,
                     parent_id=candidate.job_id)
        self.session.commit()

    def _selected(self, stage: str, state_id: int) -> bool:
        return self.session.exec(
            select(Candidate).where(
                Candidate.campaign_id == self.campaign.id, Candidate.stage == stage,
                Candidate.state_id == state_id,
            )
        ).first() is not None

    def _select(self, stage: StageSpec, state_id: int, jobs: list[Job]) -> None:
        params = stage.select
        candidates: list[tuple[Candidate, Geometry]] = []
        for job in jobs:
            result = self.session.get(JobResult, job.id)
            geometry = Geometry.from_xyz(self.session.get(Structure, result.final_structure_id).xyz)
            candidate = Candidate(
                campaign_id=self.campaign.id, stage=stage.name, state_id=state_id, job_id=job.id,
                structure_id=result.final_structure_id, energy=result.energy,
                source=self.session.get(Structure, job.input_structure_id).origin,
                composition=composition(geometry), dissociated=self._dissociated(geometry),
            )
            self.session.add(candidate)
            candidates.append((candidate, geometry))
        self.session.flush()

        unique: list[tuple[Candidate, Geometry]] = []
        for candidate, geometry in sorted(candidates, key=lambda c: c[0].energy):
            if candidate.dissociated:
                continue
            twin = next((
                u for u, g in unique
                if abs(candidate.energy - u.energy) * HARTREE_TO_KCAL < params.dedup_energy_kcal
                and same_structure(geometry, g, params.dedup_distance)
            ), None)
            if twin is None:
                unique.append((candidate, geometry))
            else:
                candidate.duplicate_of = twin.id

        for rank, (candidate, _) in enumerate(unique):
            gap = (candidate.energy - unique[0][0].energy) * HARTREE_TO_KCAL
            candidate.rank = rank
            candidate.selected = rank < params.max_per_state and gap <= params.energy_window_kcal
        self.session.commit()
        self._spawn_from_selection(stage, state_id)

        label = self.session.get(StateRow, state_id).to_state().label
        n_dissociated = sum(c.dissociated for c, _ in candidates)
        n_selected = sum(c.selected for c, _ in unique)
        self.log(
            f"select {label:<10} {stage.name}: {len(candidates)} structures, "
            f"{n_dissociated} dissociated, {len(unique)} unique, {n_selected} promoted"
        )

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


def displace_along_imaginary_mode(result: Result, sign: int = 1) -> Geometry:
    """Push a saddle point downhill along its most imaginary mode."""
    mode = result.modes[int(np.argmin(result.frequencies))]
    mode = mode / np.linalg.norm(mode, axis=1).max()
    geometry = result.geometry
    return Geometry(geometry.symbols, geometry.coords + sign * DISPLACEMENT * mode)
