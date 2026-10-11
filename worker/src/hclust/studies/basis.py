"""Basis-set limit (L4) and CCSD(T) geometries (L3) for the small clusters.

L4: CCSD(T) extrapolated to the complete basis set from aVTZ and aVQZ at every best
structure with m <= 5, and D_e recomputed with those energies (all fragments of an m <= 5
cluster are themselves m <= 5). How far is aug-cc-pVTZ from the limit?

L3: CCSD(T)/aVTZ optimization (numerical gradients) of H2, H3+ and both H5+ structures, the
C2v H3+·H2 minimum and the proton-shared D2d structure, to recheck the 0.13 kcal/mol ordering
of Phase 3 on CCSD(T) geometries instead of MP2/DFT ones.
"""

from sqlmodel import Session

from hclust.analysis.fragments import Asymptotes, StateEnergy
from hclust.analysis.verdicts import StateAnalysis, load
from hclust.engines.orca import OrcaJob, Task
from hclust.levels import LEVELS
from hclust.studies.base import run_jobs
from hclust.units import HARTREE_TO_CM, HARTREE_TO_EV, HARTREE_TO_KCAL

STUDY = "basis"
MAX_M = 5
L3_STATES = ("H2 (1)", "H3+ (1)", "H5+ (1)")


def run(session: Session, campaign: str, analyses: list[StateAnalysis], workers: int, log) -> list[dict]:
    study = f"{STUDY}@{campaign}"
    small = [a for a in analyses if a.best is not None and a.state.m <= MAX_M]
    cbs_jobs = {
        a.state.label: OrcaJob(a.state, a.reference.geometry, LEVELS["L4"], Task.SP, maxcore_mb=1000)
        for a in small
    }
    l3_jobs = {}
    for a in analyses:
        if a.state.label not in L3_STATES or a.reference is None:
            continue
        l3_jobs[f"{a.state.label}|opt"] = OrcaJob(a.state, a.reference.geometry, LEVELS["L2"], Task.OPT, maxcore_mb=1000)
        if a.state.label == "H5+ (1)":
            refs = next(d.references for d in load(session, campaign) if d.state_id == a.state_id)
            d2d = next((r for r in refs if r.point_group == "D2d"), None)
            if d2d is not None:
                l3_jobs["H5+ (1)|D2d|opt"] = OrcaJob(a.state, d2d.geometry, LEVELS["L2"], Task.OPT, maxcore_mb=1000)
                l3_jobs["H5+ (1)|D2d|sp"] = OrcaJob(a.state, d2d.geometry, LEVELS["L2"], Task.SP, maxcore_mb=1000)
    results = run_jobs(session, study, cbs_jobs | l3_jobs, workers=workers, log=log)

    rows = []
    # L4: D_e at aVTZ and at the CBS limit, from the same structures
    cbs = {k: r.energy for k, r in results.items() if k in cbs_jobs and r.ok}
    tz_states = [a.best for a in small]
    cbs_states = [StateEnergy(a.state.m, a.state.charge, a.state.mult, cbs[a.state.label])
                  for a in small if a.state.label in cbs]
    proton = StateEnergy(1, 1, 1, 0.0)
    tz, lim = Asymptotes(tz_states + [proton]), Asymptotes(cbs_states + [proton])
    for a, s in zip(small, tz_states):
        if a.state.label not in cbs:
            continue
        d_tz = tz.dissociation(StateEnergy(s.m, s.charge, s.mult, s.energy), "E")
        d_cbs = lim.dissociation(StateEnergy(s.m, s.charge, s.mult, cbs[a.state.label]), "E")
        if d_tz is None or d_cbs is None:
            continue
        rows.append({
            "item": a.state.label, "channel": d_cbs[1],
            "avtz": round(d_tz[0] * HARTREE_TO_EV, 4), "cbs": round(d_cbs[0] * HARTREE_TO_EV, 4),
            "change": round((d_cbs[0] - d_tz[0]) * HARTREE_TO_EV, 4), "unit": "eV (D_e)",
        })
    # L3: CCSD(T) geometries: bond lengths before and after, and how far the energy drops
    def shortest(g) -> str:
        return ", ".join(f"{d:.4f}" for d in g.distances()[:3])

    for key, r in results.items():
        if key not in l3_jobs or not key.endswith("|opt") or not r.ok:
            continue
        label = key.split("|")[0]
        a = next(x for x in analyses if x.state.label == label)
        start = results.get(key.replace("|opt", "|sp")) if "D2d" in key else a.best
        start_geometry = l3_jobs[key].geometry
        rows.append({
            "item": key, "channel": "shortest H–H distances (Å): start → CCSD(T) geometry",
            "avtz": shortest(start_geometry), "cbs": shortest(r.geometry),
            "change": None if start is None or start.energy is None
            else round((r.energy - start.energy) * HARTREE_TO_CM, 1),
            "unit": "Å; change: CCSD(T) energy lowering on relaxing, cm⁻¹",
        })
    c2v, d2d_opt, d2d_sp = (results.get(k) for k in ("H5+ (1)|opt", "H5+ (1)|D2d|opt", "H5+ (1)|D2d|sp"))
    h5 = next((x for x in analyses if x.state.label == "H5+ (1)"), None)
    if c2v and d2d_opt and c2v.ok and d2d_opt.ok and h5 is not None:
        rows.append({
            "item": "H5+ D2d - C2v", "channel": "proton-shared minus H3+·H2",
            "avtz": round((d2d_sp.energy - h5.best.energy) * HARTREE_TO_KCAL, 3) if d2d_sp and d2d_sp.ok else None,
            "cbs": round((d2d_opt.energy - c2v.energy) * HARTREE_TO_KCAL, 3), "change": None,
            "unit": "kcal/mol: at MP2/DFT geometries, at CCSD(T) geometries",
        })
    return rows

