"""Counterpoise (Boys-Bernardi) correction of the weakest-channel D_e of complexes.

The complex is split into the fragments of its lowest channel (e.g. H3+ + H2 for H5+,
H4 + H for H5), each fragment borrowing the basis functions of the others inside the
complex. That basis-set superposition error is

    BSSE = sum over fragments f of  E(f, own basis) - E(f, basis of the whole complex),

both at the complex geometry, and D_e(CP) = D_e - BSSE. Covalent clusters (H3+, H2), whose
fragments are not separate units, are not corrected.
"""

import re

from hclust.analysis.verdicts import StateAnalysis
from hclust.engines.orca import OrcaJob, Task
from hclust.geometry import Geometry
from hclust.levels import LEVELS
from hclust.species import State, allowed_multiplicities
from hclust.structures import BOND_CUTOFF, fragments
from hclust.units import HARTREE_TO_EV

STUDY = "counterpoise"
PART = re.compile(r"^H(\d*)([+-]?)(?:\((\d+)\))?$")


def parse_part(label: str) -> tuple[int, int, int] | None:
    """'H3+' -> (3, 1, 1); 'H2(3)' -> (2, 0, 3); 'e-' -> None."""
    m = PART.match(label.strip())
    if not m:
        return None
    size = int(m[1] or 1)
    charge = {"": 0, "+": 1, "-": -1}[m[2]]
    mult = int(m[3]) if m[3] else allowed_multiplicities(size - charge)[0]
    return size, charge, mult


def units_of(a: StateAnalysis) -> list[tuple[list[int], int, int]] | None:
    """Atoms, charge and multiplicity of each fragment of the lowest channel, or None.

    The channel's fragments are built from the complex's bonded units (< 1.15 Å): a charged
    or odd-sized fragment needs its core unit (H3 for H3+(H2)k, a lone H for H-(H2)k and
    H(H2)k), then H2 units are handed out nearest-first, so a departing H2 is the most
    loosely bound one. None when the units cannot form the fragments (H2+(H2)2 has no H3
    unit) or the channel detaches an electron.
    """
    if a.reference is None or not a.d.get("E"):
        return None
    parts = [parse_part(p) for p in a.d["E"][1].split(" + ")]
    if any(p is None for p in parts) or len(parts) < 2:
        return None
    g = a.reference.geometry
    units = fragments(g, BOND_CUTOFF)
    if any(len(u) > 3 for u in units):
        return None
    centre = lambda atoms: g.coords[atoms].mean(axis=0)  # noqa: E731
    pool = {tuple(u): len(u) for u in units}
    plan: list[list[int]] = [[] for _ in parts]

    def take(size: int, near: list[int] | None, farthest: bool = False) -> list[int] | None:
        options = [u for u, n in pool.items() if n == size]
        if not options:
            return None
        if near:
            options.sort(key=lambda u: float(((centre(list(u)) - centre(near)) ** 2).sum()))
        else:  # no core: the most loosely bound first, i.e. farthest from the cluster centre
            mid = g.coords.mean(axis=0)
            options.sort(key=lambda u: -float(((centre(list(u)) - mid) ** 2).sum()))
        u = options[-1] if farthest else options[0]
        del pool[u]
        return list(u)

    # cores first: H3 for odd cations, H for odd neutrals and anions
    for i, (size, charge, _) in enumerate(parts):
        if size % 2 == 1:
            core = take(3 if charge == 1 else 1, None)
            if core is None:
                return None
            plan[i] = core
    # then H2 units: fragments with a core take their nearest; the rest the loosest first
    order = sorted(range(len(parts)), key=lambda i: (not plan[i], parts[i][0]))
    for i in order:
        while len(plan[i]) < parts[i][0]:
            unit = take(2, plan[i] or None)
            if unit is None:
                return None
            plan[i] += unit
    if pool or any(len(p) != part[0] for p, part in zip(plan, parts)):
        return None
    return [(sorted(atoms), charge, mult) for atoms, (_, charge, mult) in zip(plan, parts)]


def build(analyses: list[StateAnalysis], maxcore_mb: int = 500) -> dict[str, OrcaJob]:
    jobs = {}
    level = LEVELS["L2"]
    for a in analyses:
        plan = units_of(a)
        if plan is None:
            continue
        g = a.reference.geometry
        for i, (atoms, charge, mult) in enumerate(plan):
            if len(atoms) - charge == 0:
                continue  # a bare proton has no electrons, so no BSSE
            state = State(len(atoms), charge, mult)
            own = Geometry(tuple("H" for _ in atoms), g.coords[atoms])
            ghosts = tuple(j for j in range(len(g)) if j not in atoms)
            base = f"{a.state.label}|{i}|{'.'.join(map(str, atoms))}"
            jobs[f"{base}|own"] = OrcaJob(state, own, level, Task.SP, maxcore_mb=maxcore_mb)
            jobs[f"{base}|ghost"] = OrcaJob(state, g, level, Task.SP, maxcore_mb=maxcore_mb, ghosts=ghosts)
    return jobs


def report(analyses: list[StateAnalysis], energies: dict[str, float | None]) -> list[dict]:
    rows = []
    for a in analyses:
        keys = [k for k in energies if k.startswith(f"{a.state.label}|")]
        if not keys:
            continue
        bsse, complete = 0.0, True
        for k in {k.rsplit("|", 1)[0] for k in keys}:
            own, ghost = energies.get(f"{k}|own"), energies.get(f"{k}|ghost")
            if own is None or ghost is None:
                complete = False
                continue
            bsse += own - ghost
        if not complete:
            continue
        d_e = a.d["E"][0]
        d_0 = a.d["E0"][0] if a.d.get("E0") else None
        rows.append({
            "state": a.state.label,
            "channel": a.d["E"][1],
            "d_e_ev": round(d_e * HARTREE_TO_EV, 4),
            "bsse_ev": round(bsse * HARTREE_TO_EV, 4),
            "d_e_cp_ev": round((d_e - bsse) * HARTREE_TO_EV, 4),
            "d_0_cp_ev": None if d_0 is None else round((d_0 - bsse) * HARTREE_TO_EV, 4),
            "bound_after_cp": d_e - bsse > 0,
        })
    return rows
