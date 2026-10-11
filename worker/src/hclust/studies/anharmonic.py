"""Anharmonic zero-point energy (VPT2) of H5+ and its fragments H3+ and H2, at RI-MP2.

Harmonic ZPE decides 'bound with ZPE' for the floppy ion clusters (Phase 5); this checks
how much anharmonicity moves D0(H5+ -> H3+ + H2). Two steps:
1. a tight re-optimization with a numerical Hessian (RI-MP2 has no analytic one);
2. Hessians at +-dq along every normal mode -> cubic and semi-quartic force field -> VPT2
   (hclust.analysis.vpt2, formulas checked against exact model diagonalization).
"""

from collections.abc import Callable

from sqlmodel import Session

from hclust.analysis.shape import is_linear, masses
from hclust.analysis.verdicts import StateAnalysis
from hclust.analysis.vpt2 import HARTREE_TO_CM, default_steps, force_field, normal_modes, vpt2
from hclust.engines.orca import OrcaJob, Task
from hclust.geometry import Geometry
from hclust.levels import LEVELS
from hclust.studies.base import run_jobs

STUDY = "anharmonic"
SPECIES = ("H2 (1)", "H3+ (1)", "H5+ (1)")
CHANNELS = [("H5+ (1)", ("H3+ (1)", "H2 (1)"))]
TIGHT = "%geom\n  TolE 1e-8\n  TolRMSG 2e-6\n  TolMaxG 5e-6\nend"
CM_TO_EV = 1 / 8065.543937


def run(session: Session, campaign: str, analyses: list[StateAnalysis], workers: int,
        log: Callable[[str], None]) -> list[dict]:
    level = LEVELS["L1M"]
    chosen = {a.state.label: a for a in analyses if a.state.label in SPECIES and a.reference}
    opt_jobs = {
        label: OrcaJob(a.state, a.reference.geometry, level, Task.OPTFREQ, maxcore_mb=500, blocks=(TIGHT,))
        for label, a in chosen.items()
    }
    study = f"{STUDY}@{campaign}"
    optimized = run_jobs(session, study, opt_jobs, workers=workers, log=log)

    displaced, setup = {}, {}
    for label in [s for s in SPECIES if s in optimized]:  # report in SPECIES order
        result = optimized[label]
        if not result.ok or result.hessian is None:
            log(f"{label}: no reference Hessian ({result.error})")
            continue
        g = result.geometry
        modes = normal_modes(g.symbols, g.coords, result.hessian, masses(g))
        steps = default_steps(modes.omega)
        setup[label] = (g, modes, steps, result.hessian)
        for k in range(len(modes.omega)):
            for sign in (1, -1):
                shifted = Geometry(g.symbols, g.coords + modes.displacement(k, sign * steps[k]))
                displaced[f"{label}|{k}|{sign:+d}"] = OrcaJob(
                    chosen[label].state, shifted, level, Task.FREQ, maxcore_mb=500
                )
    hessians = run_jobs(session, study, displaced, workers=workers, log=log)

    rows, zpe = [], {}
    for label, (g, modes, steps, h0) in setup.items():
        n = len(modes.omega)
        if any(not hessians[f"{label}|{k}|{s:+d}"].ok for k in range(n) for s in (1, -1)):
            log(f"{label}: some displaced Hessians failed")
            continue
        h = {(k, s): hessians[f"{label}|{k}|{s:+d}"].hessian for k in range(n) for s in (1, -1)}
        cubic, quartic = force_field(modes, h, h0, steps)
        if is_linear(g):
            result = vpt2(modes.omega, cubic, quartic)  # no Watson/Coriolis terms for linear tops
        else:
            b, zeta = modes.rotational_constants_and_zeta()
            result = vpt2(modes.omega, cubic, quartic, b, zeta)
        zpe[label] = result
        rows.append({
            "species": label,
            "harmonic_cm": round(result.harmonic, 1),
            "vpt2_cm": round(result.zpe, 1),
            "correction_cm": round(result.correction, 1),
            "g0_cm": round(result.g0, 1),
            "rotation_cm": round(result.rotation + result.coriolis, 1),
            "frequencies_cm": [round(float(w), 1) for w in modes.omega],
        })

    by_label = {a.state.label: a for a in analyses}
    for parent, fragments in CHANNELS:
        if parent not in zpe or any(f not in zpe for f in fragments):
            continue
        delta = sum(zpe[f].correction for f in fragments) - zpe[parent].correction  # cm-1
        a = by_label[parent]
        d0 = a.d["E0"][0] * HARTREE_TO_CM if a.d.get("E0") else None
        rows.append({
            "species": f"D0({parent} -> {' + '.join(fragments)})",
            "harmonic_cm": None if d0 is None else round(d0, 1),
            "vpt2_cm": None if d0 is None else round(d0 + delta, 1),
            "correction_cm": round(delta, 1),
            "g0_cm": None, "rotation_cm": None, "frequencies_cm": None,
            "harmonic_ev": None if d0 is None else round(d0 * CM_TO_EV, 4),
            "vpt2_ev": None if d0 is None else round((d0 + delta) * CM_TO_EV, 4),
        })
    return rows

