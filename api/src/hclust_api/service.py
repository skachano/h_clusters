"""Read side of the API: cached campaign data and the computations behind each endpoint.

load() (database, ~1.5 s for the baseline) is cached per campaign until the database
changes; evaluate() at a given T and p takes milliseconds and is cached too, so the
conditions slider of the web app only pays for new (T, p) pairs.
"""

from collections import Counter, OrderedDict, defaultdict
from pathlib import Path
from threading import Lock

import numpy as np
from sqlalchemy import func
from sqlmodel import Session, select

from hclust.analysis.fragments import Asymptotes, StateEnergy, Verdict, species_label
from hclust.analysis.shape import radius_of_gyration, shape_class
from hclust.analysis.thermo import rrho
from hclust.analysis.verdicts import PROTON, StateAnalysis, StateData, evaluate, load
from hclust.db import Attempt, Campaign, Job, JobResult, StateRow, Structure
from hclust.structures import composition
from hclust.units import HARTREE_TO_EV

from hclust_api import schemas

QUANTITY_KEY = {"d_e": "E", "d_0": "E0", "d_h": "H", "d_g": "G"}
JOB_FILES = ("job.inp", "job.out", "job.property.json", "job.xyz", "job_trj.xyz")
GEOMETRY_LEVEL_ORDER = ("L1M", "L1", "L1V", "L1b")  # which energies rank multiplicities


def ev(x: float | None) -> float | None:
    return None if x is None else x * HARTREE_TO_EV


class Store:
    """Per-process cache keyed by a cheap fingerprint of the database contents."""

    MAX_EVALUATIONS = 256

    def __init__(self, engine):
        self.engine = engine
        self._lock = Lock()
        self._loaded: dict[str, tuple[tuple, list[StateData]]] = {}
        self._evaluated: OrderedDict[tuple, list[StateAnalysis]] = OrderedDict()

    def version(self, session: Session) -> tuple:
        jobs = session.exec(select(func.count(Job.id), func.max(Job.updated_at))).one()
        results = session.exec(select(func.count(JobResult.job_id))).one()
        return (*jobs, results)

    def data(self, session: Session, campaign: str) -> tuple[tuple, list[StateData]]:
        version = self.version(session)
        with self._lock:
            cached = self._loaded.get(campaign)
            if cached is None or cached[0] != version:
                cached = (version, load(session, campaign))
                self._loaded[campaign] = cached
        return cached

    def analyses(
        self, session: Session, campaign: str, temperature: float, pressure: float,
        geometry_level: str | None = None, energy: str = "reference",
    ) -> list[StateAnalysis]:
        version, data = self.data(session, campaign)
        key = (campaign, version, round(temperature, 6), round(pressure, 9), geometry_level, energy)
        with self._lock:
            if key in self._evaluated:
                self._evaluated.move_to_end(key)
                return self._evaluated[key]
        analyses = evaluate(data, temperature, pressure, geometry_level, energy)
        with self._lock:
            self._evaluated[key] = analyses
            while len(self._evaluated) > self.MAX_EVALUATIONS:
                self._evaluated.popitem(last=False)
        return analyses


# --------------------------------------------------------------------------- campaigns


def campaigns(session: Session) -> list[schemas.CampaignOut]:
    out = []
    for c in session.exec(select(Campaign).order_by(Campaign.id)).all():
        n_jobs, n_states = session.exec(
            select(func.count(Job.id), func.count(func.distinct(Job.state_id))).where(Job.campaign_id == c.id)
        ).one()
        out.append(schemas.CampaignOut(name=c.name, n_states=n_states, n_jobs=n_jobs))
    return out


def campaign_exists(session: Session, name: str) -> bool:
    return session.exec(select(Campaign).where(Campaign.name == name)).first() is not None


# --------------------------------------------------------------------------- states


def brief(a: StateAnalysis) -> schemas.StateBrief:
    d = {q: ev(v[0]) if v else None for q, v in a.d.items()}
    ref = a.reference
    return schemas.StateBrief(
        m=a.state.m, charge=a.state.charge, mult=a.state.mult, label=a.state.label,
        verdict=a.verdict.value, d_e=d.get("E"), d_0=d.get("E0"), d_h=d.get("H"), d_g=d.get("G"),
        channel=a.d["E"][1] if a.d.get("E") else None,
        channel_g=a.d["G"][1] if a.d.get("G") else None,
        spin_gap=ev(a.spin_gap),
        structure_id=ref.structure_id if ref else None,
        point_group=a.point_group,
        shape=shape_class(ref.geometry) if ref else None,
        composition=composition(ref.geometry) if ref else None,
    )


def ground_states(analyses: list[StateAnalysis], data: list[StateData]) -> dict[tuple[int, int], StateAnalysis]:
    """The lowest-energy multiplicity of each species.

    Ranked by the geometry level's lowest intact energy (minimum or not), so that a species
    whose ground multiplicity has no minimum (H10 singlet) still shows that multiplicity.
    """
    by_id = {d.state_id: d for d in data}
    species: dict[tuple[int, int], list[StateAnalysis]] = defaultdict(list)
    for a in analyses:
        species[(a.state.m, a.state.charge)].append(a)
    ground = {}
    for key, states in species.items():
        for level in GEOMETRY_LEVEL_ORDER:
            ranked = [a for a in states if level in by_id[a.state_id].lowest_energy]
            if len(ranked) == len(states) or (ranked and level == GEOMETRY_LEVEL_ORDER[-1]):
                ground[key] = min(ranked, key=lambda a: by_id[a.state_id].lowest_energy[level])
                break
        else:
            with_best = [a for a in states if a.best is not None]
            ground[key] = (min(with_best, key=lambda a: a.best.energy) if with_best
                           else max(states, key=lambda a: list(Verdict).index(a.verdict)))
    return ground


def grid(store: Store, session: Session, campaign: str, temperature: float, pressure: float,
         quantity: schemas.Quantity) -> schemas.GridOut:
    analyses = store.analyses(session, campaign, temperature, pressure)
    _, data = store.data(session, campaign)
    ground = ground_states(analyses, data)
    cells = []
    for (m, charge), g in sorted(ground.items()):
        states = sorted((a for a in analyses if (a.state.m, a.state.charge) == (m, charge)),
                        key=lambda a: a.state.mult)
        value = ev(g.d[QUANTITY_KEY[quantity]][0]) if g.d.get(QUANTITY_KEY[quantity]) else None
        cells.append(schemas.GridCell(
            m=m, charge=charge, species=species_label(m, charge), ground=brief(g), value=value,
            survives=None if value is None else value > 0, states=[brief(a) for a in states],
        ))
    return schemas.GridOut(campaign=campaign, temperature=temperature, pressure=pressure,
                           quantity=quantity, cells=cells)


def state_detail(store: Store, session: Session, campaign: str, m: int, charge: int, mult: int,
                 temperature: float, pressure: float) -> schemas.StateDetail | None:
    analyses = store.analyses(session, campaign, temperature, pressure)
    _, data = store.data(session, campaign)
    a = next((x for x in analyses if (x.state.m, x.state.charge, x.state.mult) == (m, charge, mult)), None)
    if a is None:
        return None
    d = next(x for x in data if x.state_id == a.state_id)
    ref = a.reference
    channels = []
    if a.best is not None:
        bests = [x.best for x in analyses if x.best is not None]
        if not any((b.m, b.charge) == (1, 1) for b in bests):
            bests.append(StateEnergy(1, 1, 1, 0.0, rrho(PROTON, None, 1, 1, temperature, pressure)))
        asym = Asymptotes(bests)
        limits = {q: dict(asym.channel_limits((m, charge), mult, q)) for q in ("E", "E0", "G")}
        for split, limit in sorted(limits["E"].items(), key=lambda kv: kv[1].value):
            def dq(q):
                lim = limits[q].get(split)
                own = a.best.value(q)
                return ev(lim.value - own) if lim is not None and own is not None else None
            channels.append(schemas.ChannelOut(split=split, limit=limit.label,
                                               d_e=dq("E"), d_0=dq("E0"), d_g=dq("G")))
    isomers = [
        schemas.IsomerOut(
            structure_id=r.structure_id, ref_job_id=r.ref_job_id, geometry_level=r.geometry_level,
            energy=r.energy, relative=ev(r.energy - d.references[0].energy),
            point_group=r.point_group, shape=shape_class(r.geometry), composition=composition(r.geometry),
        ) for r in d.references
    ]
    same_species = sorted((x for x in analyses if (x.state.m, x.state.charge) == (m, charge)),
                          key=lambda x: x.state.mult)
    thermo = a.best.thermo if a.best else None
    return schemas.StateDetail(
        **brief(a).model_dump(), campaign=campaign, temperature=temperature, pressure=pressure,
        energy=a.best.energy if a.best else None, zpe=thermo.zpe if thermo else None,
        geometry_level=ref.geometry_level if ref else None,
        xyz=ref.geometry.to_xyz() if ref else None,
        homo=ev(ref.homo) if ref else None, lumo=ev(ref.lumo) if ref else None,
        gap=ev(ref.lumo - ref.homo) if ref and ref.homo is not None and ref.lumo is not None else None,
        s2=ref.s2 if ref else None, spin_contaminated=a.spin_contaminated,
        detachment=ev(a.detachment), ionization=ev(a.ionization),
        radius_of_gyration=radius_of_gyration(ref.geometry) if ref else None,
        channels=channels, isomers=isomers, multiplicities=[brief(x) for x in same_species],
    )


# --------------------------------------------------------------------------- structures


def structure_xyz(session: Session, structure_id: int) -> str | None:
    s = session.get(Structure, structure_id)
    return None if s is None else s.xyz


def modes(session: Session, structure_id: int) -> schemas.ModesOut | None:
    """Normal modes of the frequency job that produced this structure."""
    row = session.exec(
        select(JobResult, Job).join(Job, Job.id == JobResult.job_id)
        .where(JobResult.final_structure_id == structure_id, JobResult.frequencies.is_not(None))
        .order_by(Job.id)
    ).first()
    if row is None or not row[0].frequencies or row[0].modes is None:
        return None
    result, job = row
    return schemas.ModesOut(
        structure_id=structure_id, job_id=job.id, level=job.level,
        xyz=session.get(Structure, structure_id).xyz,
        frequencies=result.frequencies, modes=result.modes,
    )


# --------------------------------------------------------------------------- trends


TREND_UNITS = {
    "binding_per_atom": "eV/atom", "d_e": "eV", "d_0": "eV", "d_g": "eV",
    "second_difference": "eV", "gap": "eV",
}


def trends(store: Store, session: Session, campaign: str, quantity: schemas.TrendQuantity,
           temperature: float, pressure: float) -> schemas.TrendsOut:
    analyses = store.analyses(session, campaign, temperature, pressure)
    _, data = store.data(session, campaign)
    ground = ground_states(analyses, data)
    energy = {k: a.best.energy for k, a in ground.items() if a.best is not None}
    energy.setdefault((1, 1), 0.0)  # bare proton
    series = []
    for charge in (-1, 0, 1):
        points = []
        for m in range(1, 11):
            g = ground.get((m, charge))
            value = None
            if g is not None and g.best is not None:
                if quantity == "binding_per_atom" and (1, 0) in energy:
                    carrier = {-1: energy.get((1, -1)), 0: energy[(1, 0)], 1: 0.0}[charge]
                    if carrier is not None:
                        atoms = (m - 1) * energy[(1, 0)] + carrier
                        value = ev(atoms - g.best.energy) / m
                elif quantity in ("d_e", "d_0", "d_g"):
                    v = g.d.get(QUANTITY_KEY[quantity])
                    value = ev(v[0]) if v else None
                elif quantity == "second_difference":
                    up, down = energy.get((m + 1, charge)), energy.get((m - 1, charge))
                    if up is not None and down is not None:
                        value = ev(up + down - 2 * g.best.energy)
                elif quantity == "gap" and g.reference and g.reference.homo is not None and g.reference.lumo is not None:
                    value = ev(g.reference.lumo - g.reference.homo)
            points.append(schemas.TrendPoint(m=m, value=value, label=g.state.label if g else None))
        series.append(schemas.TrendSeries(charge=charge, points=points))
    return schemas.TrendsOut(campaign=campaign, quantity=quantity, unit=TREND_UNITS[quantity],
                             temperature=temperature, pressure=pressure, series=series)


# --------------------------------------------------------------------------- benchmark


def benchmark(store: Store, session: Session, campaign: str, test: str) -> schemas.BenchmarkOut:
    """D_e at the test level's own energies against CCSD(T), on the same structures."""
    reference = store.analyses(session, campaign, 298.15, 1.0, test, "reference")
    tested = store.analyses(session, campaign, 298.15, 1.0, test, "geometry")
    points = []
    for r, t in zip(reference, tested):
        if r.d.get("E") and t.d.get("E"):
            points.append(schemas.BenchmarkPoint(
                label=r.state.label, m=r.state.m, charge=r.state.charge, mult=r.state.mult,
                reference=ev(r.d["E"][0]), test=ev(t.d["E"][0]),
            ))
    errors = np.array([p.test - p.reference for p in points])
    return schemas.BenchmarkOut(
        campaign=campaign, test=test, reference="L2", n=len(points),
        mae=float(np.abs(errors).mean()) if len(errors) else None,
        max_abs=float(np.abs(errors).max()) if len(errors) else None, points=points,
    )


# --------------------------------------------------------------------------- jobs


def jobs_summary(session: Session, campaign: str) -> schemas.JobsSummaryOut:
    c = session.exec(select(Campaign).where(Campaign.name == campaign)).one()
    jobs = session.exec(select(Job).where(Job.campaign_id == c.id)).all()
    states = {s.id: s.to_state().label for s in session.exec(select(StateRow)).all()}
    walls: dict[int, list[float]] = defaultdict(list)
    for attempt in session.exec(
        select(Attempt).join(Job, Job.id == Attempt.job_id).where(Job.campaign_id == c.id)
    ).all():
        if not attempt.cached and attempt.wall_s is not None:
            walls[attempt.job_id].append(attempt.wall_s)

    by_stage: dict[str, list[Job]] = defaultdict(list)
    for job in jobs:
        by_stage[job.stage].append(job)
    edges = [float(x) for x in np.logspace(0, 5, 21)]  # 1 s ... 1e5 s
    stages = []
    for stage, stage_jobs in by_stage.items():
        times = [w for j in stage_jobs for w in walls.get(j.id, [])]
        counts, _ = np.histogram(times, bins=edges)
        stages.append(schemas.StageSummary(
            stage=stage, level=stage_jobs[0].level, counts=dict(Counter(j.status for j in stage_jobs)),
            retried=sum(j.attempts > 1 for j in stage_jobs), cpu_hours=sum(times) / 3600,
            wall_median_s=float(np.median(times)) if times else None,
            histogram_edges_s=edges, histogram_counts=[int(x) for x in counts],
        ))
    stages.sort(key=lambda s: min(j.id for j in by_stage[s.stage]))
    failures = [
        schemas.FailureOut(job_id=j.id, label=states[j.state_id], stage=j.stage, status=j.status,
                           error_kind=j.error_kind, error=j.error, attempts=j.attempts)
        for j in jobs if j.status == "failed"
    ]
    return schemas.JobsSummaryOut(campaign=campaign, counts=dict(Counter(j.status for j in jobs)),
                                  stages=stages, failures=failures)


def job_detail(session: Session, job_id: int, jobs_root: Path) -> schemas.JobOut | None:
    job = session.get(Job, job_id)
    if job is None:
        return None
    attempts = session.exec(select(Attempt).where(Attempt.job_id == job_id).order_by(Attempt.n)).all()
    directory = jobs_root / (job.hash or "")
    return schemas.JobOut(
        id=job.id, campaign=session.get(Campaign, job.campaign_id).name,
        label=session.get(StateRow, job.state_id).to_state().label,
        stage=job.stage, level=job.level, task=job.task, status=job.status, attempts=job.attempts,
        hash=job.hash, parent_id=job.parent_id, input_structure_id=job.input_structure_id,
        error_kind=job.error_kind, error=job.error, wall_s=job.wall_s,
        files=[f for f in JOB_FILES if job.hash and (directory / f).is_file()],
        history=[schemas.AttemptOut(
            n=t.n, hash=t.hash, modifiers=t.modifiers, status=t.status, error_kind=t.error_kind,
            error=t.error, action=t.action, cached=t.cached, wall_s=t.wall_s,
        ) for t in attempts],
    )


def job_file(session: Session, job_id: int, name: str, jobs_root: Path) -> Path | None:
    job = session.get(Job, job_id)
    if job is None or not job.hash or name not in JOB_FILES:
        return None
    path = jobs_root / job.hash / name
    return path if path.is_file() else None
