"""Quantum nuclear motion of the anion complexes H-(H2)k, k = 1-4, by diffusion Monte Carlo.

The campaign calls the singlets H3- ... H9- "bound" (D_e 0.02-0.12 eV) but not "bound with
ZPE", as for the neutral clusters (studies/dmc.py), whose model and solver this study reuses:

1. CCSD(T)/aug-cc-pVTZ counterpoise scans of H(-)-H2 at the three Gauss-Legendre angles, H2
   rigid at <r>_0; the H2-H2 curve is the neutral study's.
2. Unlike the neutral case, the H(-)-H2 interaction is strongly anisotropic: the charge-
   quadrupole term makes the collinear well ~50 meV deep, the orientation average only ~6 meV.
   So the H2 units are rigid rotors (B0 = 59.3 cm-1) in DMC, on V0 + V2 P2 + V4 P4 (Legendre
   components from the three angles; the -alpha/2R^4 tail on V0, -Q/R^3 on V2). H2-H2 stays
   isotropic: its anisotropy is small and the H2 units rotate nearly freely.
3. The pair sum is not enough: CCSD(T) on H-(H2)2 finds a three-body energy of -4 to +6 meV
   at contact, attractive with the H2 end-on, repulsive side-on (the opposite of the
   repulsive induced-dipole term an electrostatic model predicts). It is scanned over
   distance, angle and three H2 orientations and added as analysis/dmc.IonThreeBody; four-body
   and higher terms are left out, and tested at the model minima of H7- and H9-.
4. Checks: CCSD(T) (counterpoise) at the model's own minimum of each cluster, against the
   model energy there. Pairs alone underbind H5-...H9- (the non-additive energy is attractive),
   pairs plus the three-body term overbind them by 4-14 % (the four-body terms are
   repulsive), so D0 is bracketed by DMC with and without the three-body term, and "bound"
   must hold for both; for H3- the exact
   coupled-channel level of H(-) + rotating H2; the isotropic model
   (H2 as spheres, as in the neutral study), which can only underbind (free-rotor averaging is
   variational); and the potential 10 % shallower.

Dissociation channel: H-(H2)k -> H-(H2)(k-1) + H2. Losing the ion, (H2)k + H-, costs far
more (k ion-H2 bonds of ~10 meV against H2-H2 bonds of ~0.5 meV).
"""

from collections.abc import Callable
from itertools import combinations

import numpy as np
from sqlmodel import Session

from hclust.analysis.dmc import (
    BOHR_PER_ANGSTROM, MASS_H, MASS_H2, PairPotential, coupled_channel_ground_state, dmc,
    IonThreeBody, ion_rotor_anisotropy, radial_ground_state,
)
from hclust.analysis.verdicts import StateAnalysis
from hclust.engines.orca import OrcaJob, Task
from hclust.geometry import Geometry
from hclust.levels import LEVELS
from hclust.species import State
from hclust.structures import BOND_CUTOFF, fragments
from hclust.studies import dmc as neutral
from hclust.studies.base import run_jobs

STUDY = "dmc_anions"
DISTANCES = neutral.DISTANCES + [12.0, 15.0]  # Å; the -alpha/2R^4 tail reaches further
MASS_HM = MASS_H + 1  # H(-): one more electron
KS = (1, 2, 3, 4)
MEV = neutral.MEV
SCALES = neutral.SCALES
# P_l(cos theta) at the three angles: solves V(theta) = V0 + V2 P2 + V4 P4 for (V0, V2, V4)
_P = np.array([[1, (3 * c * c - 1) / 2, (35 * c ** 4 - 30 * c * c + 3) / 8] for c, _ in neutral.COS_THETA])


def label(k: int) -> str:
    return f"H{2 * k + 1}- (1)"


def scan_jobs() -> dict[str, OrcaJob]:
    """H(-)-H2 at the three Gauss-Legendre angles, counterpoise triples, plus the H2-H2 scan
    of the neutral study (same jobs, already run)."""
    level = LEVELS["L2"]
    jobs = {k: j for k, j in neutral.scan_jobs().items() if k.startswith("HH|")}

    def add(key, coords, state, ghosts=()):
        jobs[key] = OrcaJob(state, Geometry.hydrogens(coords), level, Task.SP, maxcore_mb=1000,
                            extra_keywords=neutral.KEYWORDS, blocks=neutral.BLOCKS, ghosts=ghosts)

    for r in DISTANCES:
        for i, (c, _) in enumerate(neutral.COS_THETA):
            coords = neutral._h2((0, 0, 0), (np.sqrt(1 - c * c), 0, c)) + [[0, 0, r]]
            add(f"A|{i}|{r:.2f}|AB", coords, State(3, -1, 1))
            add(f"A|{i}|{r:.2f}|A", coords, State(2, 0, 1), (2,))
            add(f"A|{i}|{r:.2f}|B", coords, State(1, -1, 1), (0, 1))
    return jobs


def anion_curves(energies: dict[str, float | None]) -> dict[int, list[tuple[float, float]]]:
    """Legendre components V_l(R) (Eh) of the H(-)-H2 interaction against R (Å), l = 0, 2, 4."""
    out = {0: [], 2: [], 4: []}
    for r in DISTANCES:
        v = [neutral.interaction(energies, f"A|{i}|{r:.2f}") for i in range(len(neutral.COS_THETA))]
        if None not in v:
            for lam, c in zip((0, 2, 4), np.linalg.solve(_P, v)):
                out[lam].append((r, float(c)))
    return out


def anion_potentials(curves) -> dict[int, PairPotential]:
    tails = {0: (4, 6), 2: (3,), 4: (5,)}  # induction; charge-quadrupole; charge-hexadecapole
    return {lam: PairPotential(np.array([r for r, _ in pts]) * BOHR_PER_ANGSTROM, np.array([v for _, v in pts]),
                               tail_powers=tails[lam], has_wall=lam == 0)
            for lam, pts in curves.items()}


def start_geometry(k: int, analyses: list[StateAnalysis]) -> np.ndarray:
    """Unit centres (bohr), the k H2 units first and H(-) last, from the campaign's best
    structure; H2 around the ion at 3 Å if it does not split that way."""
    x = next((a for a in analyses if a.state.label == label(k) and a.reference), None)
    if x is not None:
        g = x.reference.geometry
        units = fragments(g, BOND_CUTOFF)
        h2 = [g.coords[u].mean(axis=0) for u in units if len(u) == 2]
        h = [g.coords[u[0]] for u in units if len(u) == 1]
        if len(h2) == k and len(h) == 1:
            return np.array(h2 + h) * BOHR_PER_ANGSTROM
    dirs = np.array([[0, 0, 1], [0, 0, -1], [1, 0, 0], [-1, 0, 0]], float)[:k]
    return np.vstack([3.0 * dirs, [[0, 0, 0]]]) * BOHR_PER_ANGSTROM


def _scaled(f: Callable | None, scale: float) -> Callable | None:
    return f if f is None or scale == 1.0 else (lambda *a: scale * f(*a))


def best_orientation(v: dict[int, Callable]) -> Callable:
    """The H(-)-H2 energy at the best H2 orientation for each R (for the classical minimum)."""
    c = np.linspace(0, 1, 101)
    p = {lam: np.polynomial.legendre.Legendre.basis(lam)(c) for lam in v}
    return lambda r: np.min(sum(np.multiply.outer(np.asarray(v[lam](r)), p[lam]) for lam in v), axis=-1)


def model_atoms(x: np.ndarray, k: int, axes: list | None = None) -> list[list[float]]:
    """Atoms (Å) of a model geometry x (bohr, H2 centres then the ion), ion last. The H2 axes
    default to pointing at the ion (the collinear H(-)...H-H orientation is the best one)."""
    atoms = []
    for i in range(k):
        atoms += neutral._h2(x[i] / BOHR_PER_ANGSTROM, x[k] - x[i] if axes is None else axes[i])
    return atoms + [list(x[k] / BOHR_PER_ANGSTROM)]


def cluster_jobs(prefix: str, x: np.ndarray, k: int, axes: list | None = None) -> dict[str, OrcaJob]:
    """CCSD(T)/aVTZ of H-(H2)k at geometry x (model_atoms), every unit and, for k >= 2, every
    pair of units, all in the full basis: the many-body expansion of the binding."""
    atoms = model_atoms(x, k, axes)
    everyone = set(range(2 * k + 1))
    units = {f"h2.{i}": {2 * i, 2 * i + 1} for i in range(k)} | {"ion": {2 * k}}
    jobs = {}

    def add(key, state, own):
        jobs[f"{prefix}|{key}"] = OrcaJob(state, Geometry.hydrogens(atoms), LEVELS["L2"], Task.SP, maxcore_mb=1500,
                                          extra_keywords=neutral.KEYWORDS, blocks=neutral.BLOCKS,
                                          ghosts=tuple(sorted(everyone - set(own))))
    add("AB", State(2 * k + 1, -1, 1), everyone)
    add("ion", State(1, -1, 1), units["ion"])
    for i in range(k):
        add(f"h2.{i}", State(2, 0, 1), units[f"h2.{i}"])
    if k >= 2:
        for a, b in combinations(units, 2):
            own = units[a] | units[b]
            add(f"pair|{a}|{b}", State(len(own), -1 if "ion" in (a, b) else 0, 1), own)
    return jobs


def check_jobs(geometries: dict[int, np.ndarray]) -> dict[str, OrcaJob]:
    """The many-body expansion at the model minimum of each cluster."""
    return {key: job for k, x in geometries.items() for key, job in cluster_jobs(f"M|{k}", x, k).items()}


def check_binding(energies: dict[str, float | None], prefix: str, k: int) -> float | None:
    """Counterpoise-corrected total binding (Eh, > 0 bound) to H(-) + k H2."""
    parts = [energies.get(f"{prefix}|{p}") for p in ["AB", "ion"] + [f"h2.{i}" for i in range(k)]]
    return None if None in parts else sum(parts[1:]) - parts[0]


def many_body(energies: dict[str, float | None], prefix: str, k: int) -> float | None:
    """Non-additive part (Eh, < 0 attractive) of the CCSD(T) binding: total interaction minus
    the sum of pair interactions, all in the cluster's basis."""
    units = [f"h2.{i}" for i in range(k)] + ["ion"]
    mono = {u: energies.get(f"{prefix}|{u}") for u in units}
    pairs = {(a, b): energies.get(f"{prefix}|pair|{a}|{b}") for a, b in combinations(units, 2)}
    total = check_binding(energies, prefix, k)
    if None in mono.values() or None in pairs.values() or total is None:
        return None
    return -total - sum(e - mono[a] - mono[b] for (a, b), e in pairs.items())


# Three-body scan of H-(H2)2: ion-H2 distances (Å, H2 centres) and the angle between the two
# H2 at the ion (degrees). Three orientations: both H2 end-on (pointing at the ion), both
# side-on (perpendicular to the plane), one of each; off-diagonal (R1 != R2) end-on points test
# the combination rule.
TRIPLE_R = (2.9, 3.1, 3.3, 3.6, 4.0, 4.6)
TRIPLE_ANGLES = (60.0, 90.0, 109.47, 120.0, 150.0, 180.0)
TRIPLE_ODD = ((2.9, 3.6), (3.1, 4.0), (3.3, 4.6))


def triple_geometry(r1: float, r2: float, angle: float) -> np.ndarray:
    """Unit centres (bohr): H2 at r1 on +z, H2 at r2 at `angle` from it, the ion at the origin."""
    t = np.radians(angle)
    return np.array([[0, 0, r1], [r2 * np.sin(t), 0, r2 * np.cos(t)], [0, 0, 0]]) * BOHR_PER_ANGSTROM


def triple_points() -> list[tuple[float, float, float]]:
    return ([(r, r, a) for r in TRIPLE_R for a in TRIPLE_ANGLES]
            + [(r1, r2, a) for r1, r2 in TRIPLE_ODD for a in (120.0, 180.0)])


ORIENTATIONS = {"end": "T", "side": "TS", "mixed": "TX"}  # key prefixes


def triple_axes(x: np.ndarray, orientation: str) -> list:
    end = [x[i] - x[2] for i in range(2)]
    side = [np.array([0.0, 1.0, 0.0])] * 2
    return {"end": end, "side": side, "mixed": [end[0], side[1]]}[orientation]


def triple_prefix(orientation: str, r1: float, r2: float, angle: float) -> str:
    return f"{ORIENTATIONS[orientation]}|{r1:.2f}|{r2:.2f}|{angle:g}"


def triple_jobs() -> dict[str, OrcaJob]:
    jobs = {}
    for r1, r2, a in triple_points():
        x = triple_geometry(r1, r2, a)
        for o in ORIENTATIONS if r1 == r2 else ("end",):
            jobs |= cluster_jobs(triple_prefix(o, r1, r2, a), x, 2, triple_axes(x, o))
    return jobs


def three_body_tables(energies: dict[str, float | None]) -> dict:
    """IonThreeBody arguments (r in bohr, cos theta increasing, tables in Eh) from the scan."""
    angles = sorted(TRIPLE_ANGLES, reverse=True)  # 180 ... 60: cos theta increasing
    tables = {}
    for o in ORIENTATIONS:
        t = np.array([[many_body(energies, triple_prefix(o, r, r, a), 2) for a in angles] for r in TRIPLE_R],
                     dtype=float)
        if np.isnan(t).any():
            raise RuntimeError(f"three-body scan incomplete ({o})")
        tables[o] = t
    end = tables["end"]
    # decay beyond the grid: the mean slope of ln|E3| over the last interval, end-on
    kappa = float(np.mean(np.log(end[-2] / end[-1]))) / ((TRIPLE_R[-1] - TRIPLE_R[-2]) * BOHR_PER_ANGSTROM)
    return {"r": np.array(TRIPLE_R) * BOHR_PER_ANGSTROM, "cos_theta": np.cos(np.radians(angles)),
            "end": end, "side": tables["side"], "mixed": tables["mixed"], "kappa": kappa}


def _sum(*terms: Callable | None) -> Callable | None:
    terms = [t for t in terms if t is not None]
    return None if not terms else lambda x, u: sum(t(x, u) for t in terms)


def run(session: Session, campaign: str, analyses: list[StateAnalysis], workers: int,
        log: Callable[[str], None], walkers: int = 2000, dt: float = 10.0, steps: int = 100000,
        equilibration: int = 20000) -> list[dict]:
    results = run_jobs(session, f"{STUDY}@{campaign}", scan_jobs(), workers=workers, log=log)
    energies = {k: (r.energy if r.ok else None) for k, r in results.items()}
    hh = neutral.potentials({"H2-H2": neutral.averaged_curves(energies)["H2-H2"]})["H2-H2"]
    curves = anion_curves(energies)
    v = anion_potentials(curves)
    log("H(-)-H2 V_l (meV): " + "; ".join(
        f"{r:g} Å " + " ".join(f"{curves[lam][i][1] * MEV:+.2f}" for lam in (0, 2, 4))
        for i, (r, _) in enumerate(curves[0])))
    r_min, v_min = v[0].minimum()
    log(f"H(-)-H2: isotropic well {v_min * MEV:.2f} meV at {r_min / BOHR_PER_ANGSTROM:.2f} Å, "
        f"C4 = {v[0].tail[0]:.2f} (alpha/2 = 2.71), V2 tail {v[2].tail[0]:.3f} Eh bohr^3")

    # the three-body term from the H-(H2)2 scan
    triples = run_jobs(session, f"{STUDY}@{campaign}", triple_jobs(), workers=workers, log=log)
    triple_e = {key: (r.energy if r.ok else None) for key, r in triples.items()}
    tables = three_body_tables(triple_e)
    for o in ORIENTATIONS:
        log(f"three-body, {o} (meV, rows R = {', '.join(f'{r:g}' for r in TRIPLE_R)} Å; columns 180...60°): "
            + "; ".join(" ".join(f"{e * MEV:+.2f}" for e in row) for row in tables[o]))
    log(f"three-body decay beyond {TRIPLE_R[-1]} Å: kappa = {tables['kappa']:.3f} / bohr")

    def three_of(k):
        return IonThreeBody(k, list(range(k)), **tables) if k >= 2 else None

    probe = three_of(2)
    for r1, r2, a in triple_points():
        if r1 != r2:
            x = triple_geometry(r1, r2, a)
            log(f"  three-body at {r1}/{r2} Å, {a:g}°: CCSD(T) "
                f"{many_body(triple_e, triple_prefix('end', r1, r2, a), 2) * MEV:+.2f}, "
                f"model {probe(x[None], None)[0] * MEV:+.2f} meV")

    # the model's minima, and CCSD(T) there
    minima = {}
    for k in KS:
        three = three_of(k)
        best = {(i, j): (best_orientation(v) if j == k else hh) for i, j in combinations(range(k + 1), 2)}
        e_min, x_min = neutral.minimise(best, start_geometry(k, analyses), three)
        aniso = ion_rotor_anisotropy(k, {lam: v[lam] for lam in (2, 4)})
        u = (x_min[k] - x_min[:k]) / np.linalg.norm(x_min[k] - x_min[:k], axis=1, keepdims=True)
        iso = sum(float((v[0] if j == k else hh)(np.array([np.linalg.norm(x_min[i] - x_min[j])]))[0])
                  for i, j in combinations(range(k + 1), 2))
        e3 = float(three(x_min[None], None)[0]) if three else 0.0
        e_collinear = iso + e3 + float(aniso(x_min[None], u[None])[0])
        minima[k] = {"e": e_min, "x": x_min, "e3": e3, "collinear": e_collinear}
    checks = run_jobs(session, f"{STUDY}@{campaign}", check_jobs({k: m["x"] for k, m in minima.items()}),
                      workers=workers, log=log)
    check_e = {key: (r.energy if r.ok else None) for key, r in checks.items()}
    for k, m in minima.items():
        m["ccsdt"] = check_binding(check_e, f"M|{k}", k)
        m["ccsdt_many"] = many_body(check_e, f"M|{k}", k) if k >= 2 else 0.0
        log(f"  {label(k)} at the model minimum: binding model {-m['collinear'] * MEV:.1f} meV "
            f"(three-body {m['e3'] * MEV:+.1f}), CCSD(T) "
            f"{'-' if m['ccsdt'] is None else f'{m['ccsdt'] * MEV:.1f}'} meV (non-additive "
            f"{'-' if m['ccsdt_many'] is None else f'{m['ccsdt_many'] * MEV:+.1f}'} meV)")

    by_label = {x.state.label: x for x in analyses}
    energy = {s: {0: (0.0, 0.0)} for s in SCALES}  # rotor model, per scale
    energy_iso = {0: (0.0, 0.0)}
    energy_pairs = {0: (0.0, 0.0)}
    classical = {0: 0.0}
    rows = []
    for k in KS:
        n = k + 1
        masses = [MASS_H2] * k + [MASS_HM]
        start = start_geometry(k, analyses)
        three = three_of(k)
        iso_pairs = {(i, j): (v[0] if j == k else hh) for i, j in combinations(range(n), 2)}
        classical[k], e3 = minima[k]["e"], minima[k]["e3"]
        mu = MASS_H2 * MASS_HM / (MASS_H2 + MASS_HM)

        def run_dmc(scale, rotor, seed, with_three=True):
            aniso = ion_rotor_anisotropy(k, {lam: v[lam] for lam in (2, 4)}) if rotor else None
            pair = {key: _scaled(p, scale) for key, p in iso_pairs.items()}
            t3 = None if three is None or not with_three else three if rotor else three.averaged()
            return dmc(masses, pair, start, walkers=walkers, dt=dt, steps=steps, equilibration=equilibration,
                       seed=seed, many_body=_scaled(_sum(t3, aniso), scale), rotors=k if rotor else 0)

        result = {}
        for scale in SCALES:
            res = run_dmc(scale, True, 100 + k)
            energy[scale][k] = (res.energy, res.error)
            d0 = energy[scale][k - 1][0] - res.energy
            err = float(np.hypot(energy[scale][k - 1][1], res.error))
            row = {"d0": d0, "err": err, "spread": res.size, "growth": res.size_growth, "exact": k == 1}
            if k == 1:  # the dimer: the exact coupled-channel level decides, DMC is the check
                e_cc, weights = coupled_channel_ground_state({lam: _scaled(v[lam], scale) for lam in v}, mu)
                row.update(d0=-e_cc, err=0.0, dmc=d0, j0=weights[0])
            result[scale] = row
            log(f"  {label(k)} x{scale} rotors: E_DMC = {res.energy * MEV:.3f} ± {res.error * MEV:.3f} meV, "
                f"D0 = {row['d0'] * MEV:.3f} ± {row['err'] * MEV:.3f} meV, spread "
                f"{res.size / BOHR_PER_ANGSTROM:.2f} Å (growth {res.size_growth:.3f})"
                + (f"; DMC {d0 * MEV:.3f}, j = 0 weight {row['j0']:.3f}" if k == 1 else ""))
        # the isotropic model of the neutral study (H2 as spheres), full potential only
        if k == 1:
            e, size = radial_ground_state(iso_pairs[(0, 1)], mu, r_min=3.0, r_max=600, n=20000)
            energy_iso[k], iso, exact_r = (e, 0.0), -e, size
        else:
            res = run_dmc(1.0, False, 200 + k)
            energy_iso[k], iso, exact_r = (res.energy, res.error), energy_iso[k - 1][0] - res.energy, None
        log(f"  {label(k)} isotropic: D0 = {iso * MEV:.3f} meV")
        # pairs only (rotors, no three-body): underbinds, as the pairs plus three-body overbind
        if k == 1:
            energy_pairs[k], pairs_only = energy[SCALES[0]][k], result[SCALES[0]]["d0"]
        else:
            res = run_dmc(1.0, True, 300 + k, with_three=False)
            energy_pairs[k] = (res.energy, res.error)
            pairs_only = energy_pairs[k - 1][0] - res.energy
            result["pairs"] = {"d0": pairs_only, "err": float(np.hypot(energy_pairs[k - 1][1], res.error)),
                               "growth": res.size_growth, "exact": False}
        log(f"  {label(k)} pairs only: D0 = {pairs_only * MEV:.3f} meV")
        full, shallow = result[SCALES[0]], result[SCALES[1]]
        variants_bound = neutral._bound(shallow) and ("pairs" not in result or neutral._bound(result["pairs"]))
        verdict = ("bound" if neutral._bound(full) and variants_bound else
                   "threshold" if neutral._bound(full) else "unbound")
        x = by_label.get(label(k))
        rows.append({
            "state": label(k),
            "channel": f"{'H-' if k == 1 else f'H{2 * k - 1}-'} + H2",
            "d_e_ccsdt_mev": None if x is None or not x.d.get("E") else round(float(x.d["E"][0]) * MEV, 2),
            "d_e_model_mev": round((classical[k - 1] - classical[k]) * MEV, 2),
            "three_body_mev": round(e3 * MEV, 2),
            "total_model_mev": round(-minima[k]["collinear"] * MEV, 1),
            "total_ccsdt_mev": None if minima[k]["ccsdt"] is None else round(minima[k]["ccsdt"] * MEV, 1),
            "d0_harmonic_mev": None if x is None or not x.d.get("E0") else round(float(x.d["E0"][0]) * MEV, 2),
            "d0_dmc_mev": round(full["d0"] * MEV, 3),
            "d0_dmc_err_mev": None if full["exact"] else round(full["err"] * MEV, 3),
            "d0_shallow_mev": round(shallow["d0"] * MEV, 3),
            "d0_isotropic_mev": round(iso * MEV, 3),
            "d0_pairs_only_mev": round(pairs_only * MEV, 3),
            "dmc_verdict": verdict,
            "method": "exact (coupled channels)" if full["exact"] else "DMC",
            "dmc_check_mev": round(full["dmc"] * MEV, 3) if full["exact"] else None,
            "spread_angstrom": round(full["spread"] / BOHR_PER_ANGSTROM, 1),
            "size_growth": round(full["growth"], 3),
            "exact_r_angstrom": round(exact_r / BOHR_PER_ANGSTROM, 1) if exact_r else None,
        })
    return rows
