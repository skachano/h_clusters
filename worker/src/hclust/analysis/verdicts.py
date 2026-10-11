"""Verdicts for every state of a campaign, from the database (doc/Plan.md, 2.2 and Phase 5).

The reference energy of a state is its lowest CCSD(T) single point (level L2) on a structure
that is
- a minimum at the level that optimized it (the L2 job's parent: L1 or L1M opt+freq), and
- not an unbound anion (neither the parent's nor the reference's HOMO says so).
Thermal corrections come from the parent's frequencies. The point group and the symmetry
number of the rotational entropy come from hclust.analysis.symmetry (0.05 Å tolerance), not
ORCA, whose detection is too strict for optimized structures (Plan, Phase 1).
"""

from dataclasses import dataclass, field

from sqlmodel import Session, delete, select

from hclust.analysis.fragments import Asymptotes, StateEnergy, Verdict, judge
from hclust.analysis.shape import shape_class
from hclust.analysis.symmetry import point_group
from hclust.analysis.thermo import rrho
from hclust.db import Campaign, Job, JobResult, JobStatus, StateRow, Structure, VerdictRow
from hclust.geometry import Geometry
from hclust.structures import DISSOCIATION_CUTOFF, composition, is_dissociated

REFERENCE_LEVEL = "L2"
GEOMETRY_LEVELS = ("L1", "L1V", "L1b", "L1M")
PROTON = Geometry.hydrogens([[0.0, 0.0, 0.0]], "H+")


@dataclass
class StateAnalysis:
    state: StateRow
    verdict: Verdict
    best: StateEnergy | None = None
    d: dict[str, tuple[float, str] | None] = field(default_factory=dict)  # quantity -> (D, channel)
    ref_job: Job | None = None
    ref_result: JobResult | None = None
    parent_job: Job | None = None
    parent_result: JobResult | None = None
    geometry: Geometry | None = None
    point_group: str | None = None
    n_candidates: int = 0
    spin_gap: float | None = None
    detachment: float | None = None
    ionization: float | None = None

    @property
    def spin_contaminated(self) -> bool | None:
        s2 = self.ref_result.s2 if self.ref_result else None
        s = (self.state.mult - 1) / 2
        if s2 is None or s == 0:
            return None
        return abs(s2 - s * (s + 1)) > 0.1 * s * (s + 1)


def analyze(
    session: Session, campaign_name: str, temperature: float = 298.15, pressure: float = 1.0,
) -> list[StateAnalysis]:
    campaign = session.exec(select(Campaign).where(Campaign.name == campaign_name)).one()
    jobs = session.exec(select(Job).where(Job.campaign_id == campaign.id)).all()
    states = {s.id: s for s in session.exec(select(StateRow)).all()}
    by_state: dict[int, list[Job]] = {}
    for job in jobs:
        by_state.setdefault(job.state_id, []).append(job)

    analyses = [
        _best_reference(session, states[sid], state_jobs, temperature, pressure)
        for sid, state_jobs in by_state.items()
    ]
    proton = StateEnergy(1, 1, 1, 0.0, rrho(PROTON, None, 1, 1, temperature, pressure))
    bests = [a.best for a in analyses if a.best is not None]
    if not any((b.m, b.charge) == (1, 1) for b in bests):
        bests.append(proton)
    asymptotes = Asymptotes(bests)

    for a in analyses:
        s = a.state
        if a.best is not None:
            a.d = {q: asymptotes.dissociation(a.best, q) for q in ("E", "E0", "H", "G")}
            same = [b.energy for b in bests if (b.m, b.charge) == (s.m, s.charge)]
            a.spin_gap = a.best.energy - min(same)
            if s.charge == -1 and (n := asymptotes.lowest_with_electron((s.m, 0), s.mult)):
                a.detachment = n.value - a.best.energy
            if s.charge <= 0 and (c := asymptotes.lowest_with_electron((s.m, s.charge + 1), s.mult)):
                a.ionization = c.value - a.best.energy
        cutoff = campaign.spec.get("dissociation_cutoff", DISSOCIATION_CUTOFF)
        a.verdict = _verdict(session, a, by_state[s.id], cutoff)
    return sorted(analyses, key=lambda a: (a.state.m, a.state.charge, a.state.mult))


def store(session: Session, campaign_name: str, analyses: list[StateAnalysis]) -> None:
    """Replace the campaign's verdict rows."""
    campaign = session.exec(select(Campaign).where(Campaign.name == campaign_name)).one()
    session.exec(delete(VerdictRow).where(VerdictRow.campaign_id == campaign.id))
    for a in analyses:
        d = {q: (v[0] if v else None) for q, v in a.d.items()}
        thermo = a.best.thermo if a.best else None
        session.add(VerdictRow(
            campaign_id=campaign.id, state_id=a.state.id, verdict=a.verdict.value,
            temperature=thermo.temperature if thermo else 298.15,
            pressure=thermo.pressure if thermo else 1.0,
            ref_job_id=a.ref_job.id if a.ref_job else None,
            structure_id=a.ref_result.final_structure_id if a.ref_result else None,
            geometry_level=a.parent_job.level if a.parent_job else None,
            energy=a.best.energy if a.best else None,
            zpe=thermo.zpe if thermo else None,
            d_e=d.get("E"), d_0=d.get("E0"), d_h=d.get("H"), d_g=d.get("G"),
            channel=a.d["E"][1] if a.d.get("E") else None,
            channel_g=a.d["G"][1] if a.d.get("G") else None,
            spin_gap=a.spin_gap, detachment=a.detachment, ionization=a.ionization,
            homo=a.ref_result.homo if a.ref_result else None,
            s2=a.ref_result.s2 if a.ref_result else None,
            spin_contaminated=a.spin_contaminated,
            point_group=a.point_group,
            shape=shape_class(a.geometry) if a.geometry else None,
            composition=composition(a.geometry) if a.geometry else None,
            n_candidates=a.n_candidates,
        ))
    session.commit()


def _best_reference(
    session: Session, state: StateRow, jobs: list[Job], temperature: float, pressure: float,
) -> StateAnalysis:
    analysis = StateAnalysis(state, Verdict.DISSOCIATES)
    for job in jobs:
        if job.level != REFERENCE_LEVEL or job.status != JobStatus.DONE or job.parent_id is None:
            continue
        result = session.get(JobResult, job.id)
        parent = session.get(Job, job.parent_id)
        parent_result = session.get(JobResult, parent.id)
        if result is None or parent_result is None or result.unbound or parent_result.unbound:
            continue
        if state.m > 1 and parent_result.n_imag != 0:
            continue
        analysis.n_candidates += 1
        if analysis.best is not None and result.energy >= analysis.best.energy:
            continue
        geometry = Geometry.from_xyz(session.get(Structure, result.final_structure_id).xyz)
        group, sigma = point_group(geometry)
        thermo = rrho(geometry, parent_result.frequencies, state.mult, sigma, temperature, pressure)
        analysis.best = StateEnergy(state.m, state.charge, state.mult, result.energy, thermo)
        analysis.ref_job, analysis.ref_result = job, result
        analysis.parent_job, analysis.parent_result = parent, parent_result
        analysis.geometry, analysis.point_group = geometry, group
    return analysis


def _verdict(session: Session, a: StateAnalysis, jobs: list[Job], cutoff: float) -> Verdict:
    """judge() with the evidence of the geometry levels for states without a reference.

    An anion is unbound when every flagged result says so, even if the loose electron then let
    the cluster drift apart (the electron is the cause).
    """
    results = [
        r for j in jobs
        if j.level in GEOMETRY_LEVELS and (r := session.get(JobResult, j.id)) is not None
    ]
    intact = [
        r for r in results
        if not is_dissociated(Geometry.from_xyz(session.get(Structure, r.final_structure_id).xyz), cutoff)
    ]
    flagged = [r.unbound for r in results if r.unbound is not None]
    d_e = a.d["E"][0] if a.d.get("E") else None
    d_0 = a.d["E0"][0] if a.d.get("E0") else None
    return judge(
        a.best, d_e, d_0, m=a.state.m, charge=a.state.charge,
        has_intact=bool(intact), all_unbound=bool(flagged) and all(flagged),
        has_minimum=any(r.n_imag == 0 for r in intact),
    )
