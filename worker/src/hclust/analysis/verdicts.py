"""Verdicts for every state of a campaign, from the database (doc/Plan.md, 2.2 and Phase 5).

The reference energy of a state is its lowest CCSD(T) single point (level L2) on a structure
that is
- a minimum at the level that optimized it (the L2 job's parent: L1 or L1M opt+freq), and
- not an unbound anion (neither the parent's nor the reference's HOMO says so).
Thermal corrections come from the parent's frequencies. The point group and the symmetry
number of the rotational entropy come from hclust.analysis.symmetry (0.05 Å tolerance), not
ORCA, whose detection is too strict for optimized structures (Plan, Phase 1).

Two steps, so that a server can cache the expensive one:
- load(): everything the database says, independent of T and p (plain data, no session);
- evaluate(): thermochemistry, asymptotes and verdicts at any T and p (milliseconds).
"""

from dataclasses import dataclass, field
from typing import Literal

from sqlmodel import Session, delete, select

from hclust.analysis.fragments import Asymptotes, StateEnergy, Verdict, judge
from hclust.analysis.shape import shape_class
from hclust.analysis.symmetry import point_group
from hclust.analysis.thermo import rrho
from hclust.db import Campaign, Job, JobResult, JobStatus, StateRow, Structure, VerdictRow
from hclust.geometry import Geometry
from hclust.species import State
from hclust.structures import DISSOCIATION_CUTOFF, composition, is_dissociated

REFERENCE_LEVEL = "L2"
GEOMETRY_LEVELS = ("L1", "L1V", "L1b", "L1M")
PROTON = Geometry.hydrogens([[0.0, 0.0, 0.0]], "H+")
EnergySource = Literal["reference", "geometry"]


@dataclass(frozen=True)
class Reference:
    """A CCSD(T) single point on a minimum, with what its geometry job knows about it."""

    ref_job_id: int
    structure_id: int
    energy: float  # CCSD(T), Eh
    geometry_level: str  # L1 or L1M
    geometry_energy: float  # the geometry level's own energy at this structure
    geometry: Geometry
    frequencies: tuple[float, ...] | None
    point_group: str
    symmetry_number: int
    homo: float | None  # HF orbitals of the reference
    lumo: float | None
    s2: float | None


@dataclass(frozen=True)
class StateData:
    """One state as loaded from the database: its references, lowest CCSD(T) first."""

    state_id: int
    state: State
    references: tuple[Reference, ...]
    has_intact: bool  # some geometry-level result did not fall apart
    all_unbound: bool  # every flagged geometry-level result is an unbound anion
    has_minimum: bool  # some intact geometry-level result is a minimum
    # Lowest energy of any intact result per geometry level, minimum or not: decides which
    # multiplicity is a species' ground state even when that state has no reference.
    lowest_energy: dict[str, float] = field(default_factory=dict)


@dataclass
class StateAnalysis:
    state_id: int
    state: State
    verdict: Verdict
    best: StateEnergy | None = None
    reference: Reference | None = None
    d: dict[str, tuple[float, str] | None] = field(default_factory=dict)  # quantity -> (D, channel)
    n_candidates: int = 0
    spin_gap: float | None = None
    detachment: float | None = None
    ionization: float | None = None

    @property
    def geometry(self) -> Geometry | None:
        return self.reference.geometry if self.reference else None

    @property
    def point_group(self) -> str | None:
        return self.reference.point_group if self.reference else None

    @property
    def spin_contaminated(self) -> bool | None:
        s2 = self.reference.s2 if self.reference else None
        s = (self.state.mult - 1) / 2
        if s2 is None or s == 0:
            return None
        return abs(s2 - s * (s + 1)) > 0.1 * s * (s + 1)


def analyze(
    session: Session, campaign_name: str, temperature: float = 298.15, pressure: float = 1.0,
) -> list[StateAnalysis]:
    return evaluate(load(session, campaign_name), temperature, pressure)


def load(session: Session, campaign_name: str) -> list[StateData]:
    campaign = session.exec(select(Campaign).where(Campaign.name == campaign_name)).one()
    cutoff = campaign.spec.get("dissociation_cutoff", DISSOCIATION_CUTOFF)
    jobs = {j.id: j for j in session.exec(select(Job).where(Job.campaign_id == campaign.id)).all()}
    results = {
        r.job_id: r for r in session.exec(select(JobResult).where(JobResult.job_id.in_(list(jobs))))
    }
    geometries = _Geometries(session)
    states = {s.id: s for s in session.exec(select(StateRow)).all()}

    by_state: dict[int, list[Job]] = {}
    for job in jobs.values():
        by_state.setdefault(job.state_id, []).append(job)

    data = []
    for state_id, state_jobs in by_state.items():
        state = states[state_id].to_state()
        references = []
        for job in state_jobs:
            if job.level != REFERENCE_LEVEL or job.status != JobStatus.DONE or job.parent_id is None:
                continue
            result, parent = results.get(job.id), jobs.get(job.parent_id)
            parent_result = results.get(job.parent_id)
            if result is None or parent_result is None or result.unbound or parent_result.unbound:
                continue
            if state.m > 1 and parent_result.n_imag != 0:
                continue
            geometry = geometries[result.final_structure_id]
            group, sigma = point_group(geometry)
            references.append(Reference(
                ref_job_id=job.id, structure_id=result.final_structure_id, energy=result.energy,
                geometry_level=parent.level, geometry_energy=parent_result.energy,
                geometry=geometry,
                frequencies=tuple(parent_result.frequencies) if parent_result.frequencies else None,
                point_group=group, symmetry_number=sigma,
                homo=result.homo, lumo=result.lumo, s2=result.s2,
            ))
        evidence = [
            r for j in state_jobs
            if j.level in GEOMETRY_LEVELS and (r := results.get(j.id)) is not None
        ]
        intact = [r for r in evidence if not is_dissociated(geometries[r.final_structure_id], cutoff)]
        flagged = [r.unbound for r in evidence if r.unbound is not None]
        lowest: dict[str, float] = {}
        for r in intact:
            level = jobs[r.job_id].level
            lowest[level] = min(lowest.get(level, r.energy), r.energy)
        data.append(StateData(
            state_id, state, tuple(sorted(references, key=lambda r: r.energy)),
            has_intact=bool(intact), all_unbound=bool(flagged) and all(flagged),
            has_minimum=any(r.n_imag == 0 for r in intact), lowest_energy=lowest,
        ))
    return sorted(data, key=lambda d: d.state)


def evaluate(
    data: list[StateData], temperature: float = 298.15, pressure: float = 1.0,
    geometry_level: str | None = None, energy: EnergySource = "reference",
) -> list[StateAnalysis]:
    """Verdicts at (T, p). `geometry_level` keeps only structures optimized at that level;
    `energy="geometry"` uses that level's own energies instead of CCSD(T) (for benchmarks)."""
    analyses = []
    for d in data:
        refs = [r for r in d.references if geometry_level in (None, r.geometry_level)]
        a = StateAnalysis(d.state_id, d.state, Verdict.DISSOCIATES, n_candidates=len(refs))
        if refs:
            key = (lambda r: r.energy) if energy == "reference" else (lambda r: r.geometry_energy)
            ref = min(refs, key=key)
            s = d.state
            thermo = rrho(ref.geometry, ref.frequencies, s.mult, ref.symmetry_number, temperature, pressure)
            a.reference = ref
            a.best = StateEnergy(s.m, s.charge, s.mult, key(ref), thermo)
        analyses.append(a)

    bests = [a.best for a in analyses if a.best is not None]
    if not any((b.m, b.charge) == (1, 1) for b in bests):
        bests.append(StateEnergy(1, 1, 1, 0.0, rrho(PROTON, None, 1, 1, temperature, pressure)))
    asymptotes = Asymptotes(bests)

    for a, d in zip(analyses, data):
        s = a.state
        if a.best is not None:
            a.d = {q: asymptotes.dissociation(a.best, q) for q in ("E", "E0", "H", "G")}
            a.spin_gap = a.best.energy - min(b.energy for b in bests if (b.m, b.charge) == (s.m, s.charge))
            if s.charge == -1 and (n := asymptotes.lowest_with_electron((s.m, 0), s.mult)):
                a.detachment = n.value - a.best.energy
            if s.charge <= 0 and (c := asymptotes.lowest_with_electron((s.m, s.charge + 1), s.mult)):
                a.ionization = c.value - a.best.energy
        d_e = a.d["E"][0] if a.d.get("E") else None
        d_0 = a.d["E0"][0] if a.d.get("E0") else None
        # An anion is unbound when every flagged result says so, even if the loose electron
        # then let the cluster drift apart (the electron is the cause).
        a.verdict = judge(
            a.best, d_e, d_0, m=s.m, charge=s.charge,
            has_intact=d.has_intact, all_unbound=d.all_unbound, has_minimum=d.has_minimum,
        )
    return analyses


def store(session: Session, campaign_name: str, analyses: list[StateAnalysis]) -> None:
    """Replace the campaign's verdict rows."""
    campaign = session.exec(select(Campaign).where(Campaign.name == campaign_name)).one()
    session.exec(delete(VerdictRow).where(VerdictRow.campaign_id == campaign.id))
    for a in analyses:
        d = {q: (v[0] if v else None) for q, v in a.d.items()}
        thermo = a.best.thermo if a.best else None
        ref = a.reference
        session.add(VerdictRow(
            campaign_id=campaign.id, state_id=a.state_id, verdict=a.verdict.value,
            temperature=thermo.temperature if thermo else 298.15,
            pressure=thermo.pressure if thermo else 1.0,
            ref_job_id=ref.ref_job_id if ref else None,
            structure_id=ref.structure_id if ref else None,
            geometry_level=ref.geometry_level if ref else None,
            energy=a.best.energy if a.best else None,
            zpe=thermo.zpe if thermo else None,
            d_e=d.get("E"), d_0=d.get("E0"), d_h=d.get("H"), d_g=d.get("G"),
            channel=a.d["E"][1] if a.d.get("E") else None,
            channel_g=a.d["G"][1] if a.d.get("G") else None,
            spin_gap=a.spin_gap, detachment=a.detachment, ionization=a.ionization,
            homo=ref.homo if ref else None, s2=ref.s2 if ref else None,
            spin_contaminated=a.spin_contaminated, point_group=a.point_group,
            shape=shape_class(ref.geometry) if ref else None,
            composition=composition(ref.geometry) if ref else None,
            n_candidates=a.n_candidates,
        ))
    session.commit()


class _Geometries(dict):
    """Structure id -> Geometry, loaded on first use."""

    def __init__(self, session: Session):
        super().__init__()
        self.session = session

    def __missing__(self, structure_id: int) -> Geometry:
        g = Geometry.from_xyz(self.session.get(Structure, structure_id).xyz)
        self[structure_id] = g
        return g
