"""Quantum nuclear motion of the neutral van der Waals clusters H3...H9 by diffusion Monte Carlo.

The campaign calls them "bound" (D_e > 0) but not "bound with ZPE": the harmonic zero-point
energy of the soft intermolecular modes exceeds the well depth. Harmonic ZPE is poor for such
floppy motion, so this study solves the nuclear problem properly (analysis/dmc.py) on a
potential built from our own CCSD(T):

1. CCSD(T)/aug-cc-pVTZ, counterpoise-corrected interaction energies, scanned in R for
   H2-H2 and H-H2 with H2 rigid at its vibrationally averaged bond length (<r>_0 = 0.7668 Å).
2. Isotropic averages: para-H2 in J = 0 is spherical. H2-H2 over the four standard
   orientations, V00 = (V_L + 4 V_T + 2 V_H + 2 V_X) / 9 (exact for the P2 anisotropy);
   H-H2 over the angle with 3-point Gauss-Legendre in cos(theta) (exact up to P4).
3. DMC of (H2)_k and (H2)_k·H as pair sums, k = 1-4; D0 per channel from the DMC energies.
   The dimers are also solved exactly (radial equation) as a check of the DMC.

What the model leaves out: H2 anisotropy beyond the average (ortho-H2, J = 1), three-body
forces, and H2 vibration (decoupled: 4400 cm-1). The lone H atom is spherical (2S).
"""

from collections.abc import Callable
from itertools import combinations

import numpy as np
from sqlmodel import Session

from hclust.analysis.dmc import (
    BOHR_PER_ANGSTROM, MASS_H, MASS_H2, PairPotential, dmc, radial_ground_state,
)
from hclust.analysis.verdicts import StateAnalysis
from hclust.engines.orca import OrcaJob, Task
from hclust.geometry import Geometry
from hclust.levels import LEVELS
from hclust.species import State
from hclust.structures import BOND_CUTOFF, fragments
from hclust.studies.base import run_jobs
from hclust.units import HARTREE_TO_EV

STUDY = "dmc"
R_H2 = 0.7668  # Å, <r> in the vibrational ground state of H2
DISTANCES = [round(2.0 + 0.1 * i, 2) for i in range(27)] + [5.0, 5.5, 6.0, 7.0, 8.0, 10.0]  # Å
# H2-H2: orientation of (A, B) with B on +z; weights of the isotropic average
H2H2 = {"L": ((0, 0, 1), (0, 0, 1), 1), "T": ((0, 0, 1), (1, 0, 0), 4),
        "H": ((1, 0, 0), (1, 0, 0), 2), "X": ((1, 0, 0), (0, 1, 0), 2)}
# H-H2: cos(theta) nodes and weights of 3-point Gauss-Legendre on [0, 1]
COS_THETA = [(0.5 - np.sqrt(15) / 10, 5 / 18), (0.5, 8 / 18), (0.5 + np.sqrt(15) / 10, 5 / 18)]
BLOCKS = ("%mdci\n  STol 1e-7\nend",)
KEYWORDS = ("VeryTightSCF",)
CLUSTERS = [(1, 1), (2, 0), (2, 1), (3, 0), (3, 1), (4, 0), (4, 1)]  # (H2 units, H atoms)
MEV = HARTREE_TO_EV * 1000
# The well depths are uncertain by ~10 % (aVTZ, isotropic averaging), so every cluster is also
# solved on a potential 10 % shallower: "bound" must survive it, else "at threshold".
SCALES = (1.0, 0.9)


def _scaled(pot, scale):
    return pot if scale == 1.0 else (lambda r: scale * pot(r))


def _bound(r: dict) -> bool:
    if r["exact"]:
        return r["d0"] > 0
    return r["d0"] > 3 * r["err"] and r["growth"] < 1.15


def label(k: int, a: int) -> str:
    return f"H{2 * k + a} ({2 if a else 1})"


def formula(k: int, a: int) -> str:
    n = 2 * k + a
    return "H" if n == 1 else f"H{n}"


def _h2(center, u) -> list[list[float]]:
    c, u = np.asarray(center, float), np.asarray(u, float) / np.linalg.norm(u)
    return [list(c - u * R_H2 / 2), list(c + u * R_H2 / 2)]


def scan_jobs() -> dict[str, OrcaJob]:
    """Dimer and both monomers in the dimer basis (counterpoise), per geometry."""
    level, jobs = LEVELS["L2"], {}

    def add(key, coords, state, ghosts=()):
        # a lone H atom is run as HF (exact for one electron); a %mdci block would still
        # start the coupled-cluster module, which stops: "number of pairs (0)"
        blocks = BLOCKS if state.n_electrons >= 2 else ()
        jobs[key] = OrcaJob(state, Geometry.hydrogens(coords), level, Task.SP, maxcore_mb=1000,
                            extra_keywords=KEYWORDS, blocks=blocks, ghosts=ghosts)

    for r in DISTANCES:
        for name, (ua, ub, _) in H2H2.items():
            coords = _h2((0, 0, 0), ua) + _h2((0, 0, r), ub)
            add(f"HH|{name}|{r:.2f}|AB", coords, State(4, 0, 1))
            add(f"HH|{name}|{r:.2f}|A", coords, State(2, 0, 1), (2, 3))
            add(f"HH|{name}|{r:.2f}|B", coords, State(2, 0, 1), (0, 1))
        for i, (c, _) in enumerate(COS_THETA):
            coords = _h2((0, 0, 0), (np.sqrt(1 - c * c), 0, c)) + [[0, 0, r]]
            add(f"H|{i}|{r:.2f}|AB", coords, State(3, 0, 2))
            add(f"H|{i}|{r:.2f}|A", coords, State(2, 0, 1), (2,))
            add(f"H|{i}|{r:.2f}|B", coords, State(1, 0, 2), (0, 1))
    return jobs


def interaction(energies: dict[str, float | None], prefix: str) -> float | None:
    parts = [energies.get(f"{prefix}|{p}") for p in ("AB", "A", "B")]
    return None if None in parts else parts[0] - parts[1] - parts[2]


def averaged_curves(energies: dict[str, float | None]) -> dict[str, list[tuple[float, float]]]:
    """Isotropic interaction energy (Eh) against R (Å), for 'H2-H2' and 'H-H2'."""
    curves = {"H2-H2": [], "H-H2": []}
    for r in DISTANCES:
        hh = [interaction(energies, f"HH|{n}|{r:.2f}") for n in H2H2]
        if None not in hh:
            curves["H2-H2"].append((r, sum(w * v for (_, _, w), v in zip(H2H2.values(), hh)) / 9))
        h = [interaction(energies, f"H|{i}|{r:.2f}") for i in range(len(COS_THETA))]
        if None not in h:
            curves["H-H2"].append((r, sum(w * v for (_, w), v in zip(COS_THETA, h))))
    return curves


def potentials(curves) -> dict[str, PairPotential]:
    return {name: PairPotential(np.array([r for r, _ in pts]) * BOHR_PER_ANGSTROM, np.array([v for _, v in pts]))
            for name, pts in curves.items()}


def start_geometry(k: int, a: int, analyses: list[StateAnalysis]) -> np.ndarray:
    """Unit centres (bohr) of the campaign's best structure of that cluster, H2 units first;
    a compact guess if the structure does not split into k H2 units and a H atoms."""
    a_state = next((x for x in analyses if x.state.label == label(k, a) and x.reference), None)
    if a_state is not None:
        g = a_state.reference.geometry
        units = fragments(g, BOND_CUTOFF)
        h2 = [g.coords[u].mean(axis=0) for u in units if len(u) == 2]
        h = [g.coords[u[0]] for u in units if len(u) == 1]
        if len(h2) == k and len(h) == a:
            return np.array(h2 + h) * BOHR_PER_ANGSTROM
    pts = [np.array([3.4 * np.cos(2 * np.pi * i / max(k + a, 1)), 3.4 * np.sin(2 * np.pi * i / max(k + a, 1)), 0])
           for i in range(k + a)]
    return np.array(pts) * BOHR_PER_ANGSTROM


def classical_minimum(masses_kind: list[str], pots: dict[str, PairPotential], start: np.ndarray) -> float:
    """Lowest pair-sum energy (Eh) reached by gradient descent from `start` (the model's D_e)."""
    pair = [(i, j, pots["H2-H2" if masses_kind[i] == masses_kind[j] == "H2" else "H-H2"])
            for i, j in combinations(range(len(start)), 2)]

    def energy(x):
        return sum(float(p(np.array([np.linalg.norm(x[i] - x[j])]))[0]) for i, j, p in pair)

    x, e, step = start.copy(), energy(start), 0.2
    for _ in range(3000):
        grad = np.zeros_like(x)
        for idx in np.ndindex(x.shape):
            d = np.zeros_like(x)
            d[idx] = 1e-3
            grad[idx] = (energy(x + d) - energy(x - d)) / 2e-3
        trial = x - step * grad / (np.abs(grad).max() + 1e-300)
        e_trial = energy(trial)
        if e_trial < e:
            x, e, step = trial, e_trial, min(step * 1.2, 0.5)
        else:
            step *= 0.5
            if step < 1e-5:
                break
    return e


def run(session: Session, campaign: str, analyses: list[StateAnalysis], workers: int,
        log: Callable[[str], None], walkers: int = 2000, dt: float = 10.0, steps: int = 150000,
        equilibration: int = 30000) -> list[dict]:
    """dt = 10 au: halving it from 20 lowered cluster energies by 3-4 % (0.015-0.04 meV), the
    time-step bias; D0 differences, from runs at the same dt, are affected less."""
    results = run_jobs(session, f"{STUDY}@{campaign}", scan_jobs(), workers=workers, log=log)
    energies = {k: (r.energy if r.ok else None) for k, r in results.items()}
    curves = averaged_curves(energies)
    pots = potentials(curves)
    for name, pts in curves.items():  # the potential itself, for the record (also in study_result)
        log(f"{name} isotropic V (meV): " + ", ".join(f"{r:g} Å {v * MEV:+.3f}" for r, v in pts))
    for name, pot in pots.items():
        r_min, v_min = pot.minimum()
        log(f"{name}: isotropic well {v_min * MEV:.3f} meV at {r_min / BOHR_PER_ANGSTROM:.2f} Å, "
            f"C6 = {pot.tail[0]:.2f} Eh bohr^6")

    by_label = {x.state.label: x for x in analyses}
    energy = {SCALES[0]: {(1, 0): (0.0, 0.0), (0, 1): (0.0, 0.0)}, SCALES[1]: {(1, 0): (0.0, 0.0), (0, 1): (0.0, 0.0)}}
    classical: dict[tuple[int, int], float] = {(1, 0): 0.0, (0, 1): 0.0}
    rows = []
    for k, a in CLUSTERS:
        kinds = ["H2"] * k + ["H"] * a
        masses = [MASS_H2] * k + [MASS_H] * a
        start = start_geometry(k, a, analyses)
        classical[(k, a)] = classical_minimum(kinds, pots, start)
        channels = [((k - 1, a), "H2")] + ([((k, 0), "H")] if a else [])
        result = {}
        for scale in SCALES:  # the full potential, and one 10 % shallower: is the answer robust?
            pair = {(i, j): _scaled(pots["H2-H2" if kinds[i] == kinds[j] == "H2" else "H-H2"], scale)
                    for i, j in combinations(range(k + a), 2)}
            res = dmc(masses, pair, start, walkers=walkers, dt=dt, steps=steps, equilibration=equilibration,
                      seed=k * 10 + a)
            # fragments at the same dt and scale, so the time-step bias largely cancels in D0
            energy[scale][(k, a)] = (res.energy, res.error)
            d0 = min(((energy[scale][f][0] - res.energy, np.hypot(energy[scale][f][1], res.error), f"{formula(*f)} + {p}")
                      for f, p in channels), key=lambda c: c[0])
            if k + a == 2:  # dimers: the exact radial solution decides; DMC is the check
                mu = masses[0] * masses[1] / (masses[0] + masses[1])
                e, size = radial_ground_state(pair[(0, 1)], mu, r_min=3.0, r_max=600, n=20000)
                result[scale] = {"d0": -e, "err": 0.0, "exact_r": size, "spread": res.size,
                                 "growth": res.size_growth, "exact": True, "dmc": d0[0], "channel": d0[2]}
            else:
                result[scale] = {"d0": d0[0], "err": d0[1], "spread": res.size, "growth": res.size_growth,
                                 "exact": False, "channel": d0[2]}
            log(f"  {label(k, a)} x{scale}: E_DMC = {res.energy * MEV:.4f} ± {res.error * MEV:.4f} meV, "
                f"D0 = {d0[0] * MEV:.4f} ± {d0[1] * MEV:.4f} meV ({d0[2]}), size "
                f"{res.size / BOHR_PER_ANGSTROM:.2f} Å (growth {res.size_growth:.2f})")
        full, shallow = result[SCALES[0]], result[SCALES[1]]
        verdict = ("bound" if _bound(full) and _bound(shallow) else
                   "threshold" if _bound(full) else "unbound")
        x = by_label.get(label(k, a))
        rows.append({
            "state": label(k, a),
            "channel": full.get("channel", f"{formula(*channels[0][0])} + {channels[0][1]}"),
            "d_e_ccsdt_mev": None if x is None or not x.d.get("E") else round(x.d["E"][0] * MEV, 2),
            "d_e_model_mev": round(min(classical[f] - classical[(k, a)] for f, _ in channels) * MEV, 2),
            "d0_harmonic_mev": None if x is None or not x.d.get("E0") else round(x.d["E0"][0] * MEV, 2),
            "d0_dmc_mev": round(full["d0"] * MEV, 4),
            "d0_dmc_err_mev": None if full["exact"] else round(full["err"] * MEV, 4),
            "d0_shallow_mev": round(shallow["d0"] * MEV, 4),
            "dmc_verdict": verdict,
            "method": "exact (radial)" if full["exact"] else "DMC",
            "dmc_check_mev": round(full["dmc"] * MEV, 4) if full["exact"] else None,
            # walkers are distributed like psi, not |psi|^2 (no trial function): their spread is a
            # convergence diagnostic (growing = falling apart), not the size of the cluster
            "spread_angstrom": round(full["spread"] / BOHR_PER_ANGSTROM, 1),
            "size_growth": round(full["growth"], 3),
            "exact_r_angstrom": round(full["exact_r"] / BOHR_PER_ANGSTROM, 1) if full["exact"] else None,
        })
    return rows
