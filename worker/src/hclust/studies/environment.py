"""Shared machinery for studies that recompute D_e in a changed environment (field, solvent).

For each chosen state and every fragment of its lowest gas-phase channel, optimize at ωB97X-D4
in each environment, then D_e(env) = sum E(fragments, env) - E(state, env). The geometry level
is DFT (analytic gradients in a field or continuum); the *shift* of D_e with the environment is
the result, which can be added to the CCSD(T) gas-phase D_e.
"""

from collections.abc import Callable

from sqlmodel import Session

from hclust.analysis.verdicts import StateAnalysis
from hclust.engines.orca import OrcaJob, Task
from hclust.levels import LEVELS
from hclust.species import State
from hclust.studies.base import run_jobs
from hclust.studies.counterpoise import parse_part
from hclust.units import HARTREE_TO_EV


def fragments_of(a: StateAnalysis) -> list[State] | None:
    parts = [parse_part(p) for p in a.d["E"][1].split(" + ")] if a.d.get("E") else None
    if not parts or any(p is None for p in parts) or any(m - q == 0 for m, q, _ in parts):
        return None  # electron detachment or a bare proton: no environment-free reference
    return [State(m, q, mult) for m, q, mult in parts]


def run_environments(
    session: Session, study: str, analyses: list[StateAnalysis], labels: tuple[str, ...],
    environments: dict[str, tuple[tuple[str, ...], tuple[str, ...]]], workers: int,
    log: Callable[[str], None], orient: Callable | None = None,
) -> tuple[dict, dict]:
    """environments: name -> (extra keywords, input blocks). Returns (energies, channels).

    Every fragment must have its own best structure (H, H-, H2, H3+, ... all do).
    """
    level = LEVELS["L1"]
    by_label = {a.state.label: a for a in analyses}
    channels: dict[str, list[State]] = {}
    needed: dict[str, StateAnalysis] = {}
    for label in labels:
        a = by_label.get(label)
        frags = fragments_of(a) if a is not None and a.reference is not None else None
        missing = [f.label for f in frags or [] if by_label.get(f.label) is None or by_label[f.label].reference is None]
        if frags is None or missing:
            log(f"{label}: skipped ({'fragments without structure: ' + ', '.join(missing) if missing else 'no usable channel'})")
            continue
        channels[label] = frags
        needed[label] = a
        needed.update({f.label: by_label[f.label] for f in frags})
    jobs = {}
    for name, (keywords, blocks) in environments.items():
        for label, a in needed.items():
            geometry = orient(a.reference.geometry) if orient else a.reference.geometry
            jobs[f"{label}|{name}"] = OrcaJob(
                a.state, geometry, level, Task.OPT, maxcore_mb=500,
                extra_keywords=keywords, blocks=blocks,
            )
    results = run_jobs(session, study, jobs, workers=workers, log=log)
    energies = {k: (r.energy if r.ok else None) for k, r in results.items()}
    return energies, channels


def d_e_table(energies: dict, channels: dict, environments) -> list[dict]:
    rows = []
    for label, frags in channels.items():
        row = {"state": label, "channel": " + ".join(f.label for f in frags)}
        for name in environments:
            e = energies.get(f"{label}|{name}")
            parts = [energies.get(f"{f.label}|{name}") for f in frags]
            row[name] = None if e is None or None in parts else round((sum(parts) - e) * HARTREE_TO_EV, 4)
        rows.append(row)
    return rows
