"""Bond orders of every stored structure: how much of a bond each H-H contact is.

The campaign's outputs only print Mayer orders above 0.1, and for RI-MP2 and CCSD(T) jobs
from the Hartree-Fock density. Here one ωB97X-D4/def2-TZVPPD single point per structure
prints the overlap, density and spin-density matrices, and Mayer orders down to 0.001.

The drawn index is the Wiberg index in the Löwdin-orthogonalized basis, computed here as
B_AB = 2 sum_{mu in A, nu in B} (Pa~_{mu nu}^2 + Pb~_{mu nu}^2), with Pa~ = S^1/2 Pa S^1/2 for
the alpha density and Pb~ for beta (closed shell: D~^2 with D the total density). For UKS the
block ORCA titles DENSITY holds the alpha density (its trace is N_alpha) and SPIN DENSITY is
alpha - beta, so beta = DENSITY - SPIN DENSITY. ORCA's own Löwdin bond orders
omit the spin-density term, which halves one-electron bonds (H2+: 0.25 instead of 0.5);
for closed shells the two agree (H3+: 4/9 each). Mayer orders, with the same open-shell
formula but in the non-orthogonal basis, are kept for comparison: with this diffuse basis
they are noisier and can dip below zero.

Per atom, from the same output: Löwdin charge and spin population, Mayer's total valence
VA and free valence FA (bonding capacity left: ~1 on an atom carrying an unpaired electron).
"""

from collections.abc import Callable

from sqlmodel import Session

from hclust.analysis.verdicts import StateAnalysis, load
from hclust.engines.orca import OrcaJob, Task
from hclust.levels import LEVELS
import numpy as np

from hclust.parse import atom_populations, bond_orders, printed_matrix
from hclust.results import Result
from hclust.structures import BOND_CUTOFF, fragments
from hclust.studies.base import run_jobs

STUDY = "bonds"
METHOD = "ωB97X-D4/def2-TZVPPD"
THRESHOLD = 0.001
BLOCKS = (
    "%output\n  Print[P_Overlap] 1\n  Print[P_Density] 1\n  Print[P_SpinDensity] 1\n  Print[P_BondOrder_M] 1\nend",
    f"%method\n  MAYER_BONDORDERTHRESH {THRESHOLD}\nend",
)


def key(structure_id: int) -> str:
    return f"structure {structure_id}"


def data(result: Result, n_electrons: int) -> dict | None:
    out = result.workdir / "job.out" if result.workdir else None
    if out is None or not out.exists():
        return None
    text = out.read_text()
    overlap, density = printed_matrix(text, "OVERLAP MATRIX"), printed_matrix(text, "DENSITY")
    if overlap is None or density is None or result.geometry is None:
        return None
    loewdin = loewdin_bond_orders(overlap, density, printed_matrix(text, "SPIN DENSITY"),
                                  len(result.geometry), n_electrons)
    mayer = bond_orders(text).get("mayer", [])
    return {
        "loewdin": [[i, j, round(v, 4)] for i, j, v in loewdin if v >= THRESHOLD],
        "mayer": [[i, j, round(v, 4)] for i, j, v in mayer],
        "atoms": [{k: None if v is None else round(v, 4) for k, v in a.items()}
                  for a in atom_populations(text) or []],
    }


def loewdin_bond_orders(overlap: np.ndarray, density: np.ndarray, spin: np.ndarray | None,
                        n_atoms: int, n_electrons: int) -> list[tuple[int, int, float]]:
    """Open-shell Wiberg index in the Löwdin basis for every atom pair (i < j).

    `density` is the total density (closed shell) or ORCA's UKS alpha density, told apart by
    its trace; `spin` = alpha - beta. Assumes every atom carries the same number of basis
    functions, in atom order (all H).
    """
    n = len(overlap)
    if n % n_atoms:
        raise ValueError(f"{n} basis functions do not split evenly over {n_atoms} atoms")
    count = float(np.sum(density * overlap))
    if spin is None:
        alpha = beta = density / 2
    elif abs(count - n_electrons) < 0.01:  # total density
        alpha, beta = (density + spin) / 2, (density - spin) / 2
    else:  # ORCA's UKS print: alpha density
        alpha, beta = density, density - spin
    for p, label in ((alpha, "alpha"), (beta, "beta")):
        if np.sum(p * overlap) < -0.01:
            raise ValueError(f"negative {label} electron count: densities misread")
    if abs(np.sum((alpha + beta) * overlap) - n_electrons) > 0.01:
        raise ValueError(f"densities hold {np.sum((alpha + beta) * overlap):.3f} electrons, not {n_electrons}")
    w, v = np.linalg.eigh(overlap)
    half = (v * np.sqrt(w)) @ v.T
    squares = 2 * ((half @ alpha @ half) ** 2 + (half @ beta @ half) ** 2)
    per = n // n_atoms
    blocks = squares.reshape(n_atoms, per, n_atoms, per).sum(axis=(1, 3))
    return [(i, j, float(blocks[i, j])) for i in range(n_atoms) for j in range(i + 1, n_atoms)]


def run(session: Session, campaign: str, analyses: list[StateAnalysis], workers: int,
        log: Callable[[str], None]) -> list[dict]:
    jobs, owners = {}, {}
    for d in load(session, campaign):
        for r in d.references:
            k = key(r.structure_id)
            if k not in jobs:
                jobs[k] = OrcaJob(d.state, r.geometry, LEVELS["L1"], Task.SP, maxcore_mb=500, blocks=BLOCKS)
                owners[k] = d.state.label
    electrons = {k: j.state.n_electrons for k, j in jobs.items()}
    results = run_jobs(session, f"{STUDY}@{campaign}", jobs, workers=workers, log=log,
                       data=lambda k, r: data(r, electrons[k]))

    rows = []
    for a in analyses:
        if a.reference is None:
            continue
        r = results.get(key(a.reference.structure_id))
        orders = data(r, a.state.n_electrons) if r is not None and r.ok else None
        if not orders or "loewdin" not in orders:
            continue
        rows.append({"state": a.state.label, "structure_id": a.reference.structure_id,
                     **summary(a.reference.geometry, orders["loewdin"])})
    return rows


def summary(geometry, loewdin: list) -> dict:
    """Weakest bond inside a unit (H-H < 1.15 Å) and strongest link between units."""
    unit = {i: n for n, f in enumerate(fragments(geometry, BOND_CUTOFF)) for i in f}
    inside = [v for i, j, v in loewdin if unit[i] == unit[j]]
    between = [v for i, j, v in loewdin if unit[i] != unit[j]]
    return {
        "units": len(set(unit.values())),
        "weakest_in_unit": min(inside) if inside else None,
        "strongest_in_unit": max(inside) if inside else None,
        "strongest_link": max(between) if between else None,
    }
