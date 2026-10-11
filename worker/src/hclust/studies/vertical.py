"""Vertical detachment (anions) and vertical ionization (neutrals) energies.

CCSD(T)/aug-cc-pVTZ of the species with one electron fewer, at the best structure of the
state, for each spin that couples with the removed electron. Vertical minus adiabatic is
the relaxation energy of the product. Phase 5 left VDEs out because these single points had
not been run.
"""

from hclust.analysis.fragments import couples
from hclust.analysis.verdicts import StateAnalysis
from hclust.engines.orca import OrcaJob, Task
from hclust.levels import LEVELS
from hclust.species import State, allowed_multiplicities
from hclust.units import HARTREE_TO_EV

STUDY = "vertical"


def build(analyses: list[StateAnalysis], maxcore_mb: int = 500) -> dict[str, OrcaJob]:
    jobs = {}
    for a in analyses:
        s, ref = a.state, a.reference
        if ref is None or s.charge not in (-1, 0) or s.m - (s.charge + 1) == 0:
            continue  # H atom -> H+ is the bare proton: E = 0, no job
        q = s.charge + 1
        for mult in allowed_multiplicities(s.m - q):
            if couples(mult, 2, s.mult):
                jobs[f"{s.label}|{q:+d}|{mult}"] = OrcaJob(
                    State(s.m, q, mult), ref.geometry, LEVELS["L2"], Task.SP, maxcore_mb=maxcore_mb
                )
    return jobs


def report(analyses: list[StateAnalysis], energies: dict[str, float | None]) -> list[dict]:
    rows = []
    for a in analyses:
        s = a.state
        if a.best is None or s.charge not in (-1, 0):
            continue
        targets = {k: e for k, e in energies.items() if k.startswith(f"{s.label}|") and e is not None}
        if s.m == 1 and s.charge == 0:
            targets = {"H+": 0.0}
        if not targets:
            continue
        key, e = min(targets.items(), key=lambda kv: kv[1])
        vertical = (e - a.best.energy) * HARTREE_TO_EV
        adiabatic = a.detachment if s.charge == -1 else a.ionization
        rows.append({
            "state": s.label,
            "kind": "VDE" if s.charge == -1 else "VIE",
            "vertical_ev": round(vertical, 4),
            "adiabatic_ev": None if adiabatic is None else round(adiabatic * HARTREE_TO_EV, 4),
            "to_mult": key.split("|")[-1] if "|" in key else "1",
            "verdict": a.verdict.value,
        })
    return rows
