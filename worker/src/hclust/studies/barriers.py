"""Barriers on the way out: is D_e the real threshold for the cheapest decompositions of H5+
and H6+ (doublet)?

D_e compares end points only. If the minimum-energy path climbs above the products on the
way, the top of the path (a transition state) is the threshold (wiki: techniques/transition-
states). For every channel of each cluster below CHANNEL_EV:

1. End points. The start is the cluster's reference structure (an RI-MP2 minimum). The end
   is a product complex built from the fragments' own reference structures: each fragment is
   aligned onto atoms of the cluster (best permutation, then rotation), and the neutral
   fragment is moved out along the line between the fragment centres until the closest atoms
   are SEPARATION apart. Every way of dividing the atoms among the fragments is ranked by the
   bonding it keeps inside fragments (as in analysis/units.py); the best PATHS ways that are
   not symmetry copies of each other are followed.
2. A climbing-image NEB at L1M (RI-MP2/aug-cc-pVTZ) between the fixed ends.
3. If the path has an interior maximum above both ends, a transition-state optimization from
   the climbing image (OptTS with a numerical Hessian) and its frequencies: one imaginary mode.
4. CCSD(T)/aug-cc-pVTZ single points on every image of the path and on the transition state.

Validation: the proton hop of H5+ between its two equivalent C2v minima, through the D2d
structure, whose height the basis study put at 0.13 kcal/mol at CCSD(T) geometries.
"""

from collections.abc import Callable
from dataclasses import dataclass
from itertools import combinations, permutations

import numpy as np
from sqlmodel import Session

from hclust.analysis.units import Channel, FragmentationTree, Key, key_label
from hclust.analysis.verdicts import StateAnalysis
from hclust.analysis.vpt2 import HARTREE_TO_CM
from hclust.engines.orca import OrcaJob, Task
from hclust.geometry import Geometry
from hclust.levels import LEVELS
from hclust.species import State
from hclust.studies.base import run_jobs
from hclust.units import HARTREE_TO_EV

STUDY = "barriers"
CLUSTERS = ("H5+ (1)", "H6+ (2)")
CHANNEL_EV = 1.0  # channels cheaper than this (D_e)
PATHS = 2  # ways of dividing the atoms followed per channel
SEPARATION = 4.0  # Angstrom between the closest atoms of the fragments at the product end
IMAGES = 10
TOLERANCE = 1e-4  # Eh: an interior maximum must exceed both ends by more than this
BOND_LENGTH, BOND_SOFTNESS = 0.74, 0.25  # Angstrom: weights exp(-max(r - 0.74, 0) / 0.25)


@dataclass(frozen=True)
class Path:
    key: str
    cluster: str  # state label
    channel: str  # e.g. "H5+ + H", or "proton hop"
    groups: str  # which atoms make which fragment, 1-based, e.g. "H5+ {1,2,3,4,6} + H {5}"
    state: State
    start: Geometry
    end: Geometry


# --------------------------------------------------------------------------- geometry


def kabsch(p: np.ndarray, q: np.ndarray) -> tuple[np.ndarray, float]:
    """The rotation of the centred p that best fits the centred q, and the RMSD after it."""
    p0, q0 = p - p.mean(axis=0), q - q.mean(axis=0)
    u, _, vt = np.linalg.svd(p0.T @ q0)
    d = np.sign(np.linalg.det(u @ vt))
    rotation = u @ np.diag([1.0, 1.0, d]) @ vt
    rmsd = float(np.sqrt(np.mean(np.sum((p0 @ rotation - q0) ** 2, axis=1))))
    return rotation, rmsd


def align(fragment: np.ndarray, target: np.ndarray) -> np.ndarray:
    """The fragment's coordinates placed onto `target` (same number of atoms): the atom order
    and rotation that fit best, centred where the target is."""
    if len(fragment) == 1:
        return target.mean(axis=0, keepdims=True).copy()
    best = None
    for order in permutations(range(len(fragment))):
        p = fragment[list(order)]
        rotation, rmsd = kabsch(p, target)
        if best is None or rmsd < best[0] - 1e-9:
            best = (rmsd, (p - p.mean(axis=0)) @ rotation + target.mean(axis=0))
    return best[1]


def ordered_partitions(n: int, sizes: list[int]):
    """Every assignment of atoms 0..n-1 to groups of the given sizes, groups in order."""
    if not sizes:
        yield ()
        return
    for first in combinations(range(n), sizes[0]):
        rest = [i for i in range(n) if i not in first]
        for tail in ordered_partitions(len(rest), sizes[1:]):
            yield (first, *(tuple(rest[i] for i in g) for g in tail))


def weights(coords: np.ndarray) -> np.ndarray:
    r = np.linalg.norm(coords[:, None] - coords[None], axis=-1)
    return np.exp(-np.maximum(r - BOND_LENGTH, 0.0) / BOND_SOFTNESS)


def fingerprint(coords: np.ndarray, groups: tuple[tuple[int, ...], ...]) -> tuple:
    """Equal for divisions that are symmetry copies of each other."""
    r = np.linalg.norm(coords[:, None] - coords[None], axis=-1)
    inside = tuple(tuple(sorted(round(r[i, j], 2) for i, j in combinations(g, 2))) for g in groups)
    between = tuple(sorted(round(r[i, j], 2) for a, b in combinations(groups, 2) for i in a for j in b))
    return inside, between


def product_end(start: Geometry, groups, fragments: list[np.ndarray], moving: int) -> Geometry:
    """Each fragment aligned onto its atoms of the start; fragment `moving` pulled out until
    the closest atoms of different fragments are SEPARATION apart."""
    coords = np.empty_like(start.coords)
    for g, frag in zip(groups, fragments):
        coords[list(g)] = align(frag, start.coords[list(g)])
    mine = list(groups[moving])
    others = [i for i in range(len(coords)) if i not in mine]
    direction = coords[mine].mean(axis=0) - coords[others].mean(axis=0)
    direction /= np.linalg.norm(direction)

    def gap(t: float) -> float:
        moved = coords[mine] + t * direction
        return float(np.min(np.linalg.norm(moved[:, None] - coords[others][None], axis=-1)))

    lo, hi = 0.0, 2 * SEPARATION
    while gap(hi) < SEPARATION:
        hi *= 2
    for _ in range(60):  # gap(t) grows with t along this line
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if gap(mid) < SEPARATION else (lo, mid)
    coords[mine] += hi * direction
    return Geometry(start.symbols, coords)


def channel_paths(start: Geometry, parts: list[tuple[str, int, np.ndarray]], n_paths: int = PATHS):
    """The best `n_paths` distinct divisions of the atoms among the fragments (label, charge,
    coordinates), with their product ends: [(groups, end geometry)]."""
    w = weights(start.coords)
    scored = []
    for groups in ordered_partitions(len(start), [len(c) for _, _, c in parts]):
        inside = sum(w[i, j] for g in groups for i, j in combinations(g, 2))
        scored.append((inside, groups))
    scored.sort(key=lambda s: -s[0])
    charges = [q for _, q, _ in parts]
    moving = charges.index(0) if 0 in charges else int(np.argmin([len(c) for _, _, c in parts]))
    chosen, seen = [], set()
    for _, groups in scored:
        fp = fingerprint(start.coords, groups)
        if fp in seen:
            continue
        seen.add(fp)
        chosen.append((groups, product_end(start, groups, [c for _, _, c in parts], moving)))
        if len(chosen) == n_paths:
            break
    return chosen


def describe(groups, labels: list[str]) -> str:
    return " + ".join(f"{label} {{{','.join(str(i + 1) for i in g)}}}" for label, g in zip(labels, groups))


def hop_end(start: Geometry) -> Geometry:
    """H5+ (C2v, H3+.H2) with the proton handed over: the apex of the H3+ triangle (the atom
    nearest the H2) stays, the H2 becomes the triangle's base and the old base the H2. That is
    the mirror image through the apex across the apex-H2 axis, turned 90 degrees about it, with
    the two pairs' atoms exchanged."""
    x = start.coords
    r = np.linalg.norm(x[:, None] - x[None], axis=-1)
    triangle = next(t for t in combinations(range(5), 3) if all(r[i, j] < 1.2 for i, j in combinations(t, 2)))
    pair = [i for i in range(5) if i not in triangle]
    mid = x[pair].mean(axis=0)
    apex = min(triangle, key=lambda i: np.linalg.norm(x[i] - mid))
    base = [i for i in triangle if i != apex]
    u = (mid - x[apex]) / np.linalg.norm(mid - x[apex])
    y = x - x[apex]
    y = y - 2 * np.outer(y @ u, u)  # mirror through the plane at the apex, normal u
    k = np.array([[0, -u[2], u[1]], [u[2], 0, -u[0]], [-u[1], u[0], 0]])
    turn = np.eye(3) + k + k @ k  # 90 degrees about u (Rodrigues)
    y = y @ turn.T + x[apex]
    end = x.copy()
    # Each pair goes to the other's place; within it, each atom to the nearer image, or the
    # path would also turn both H2 end over end (through the planar D2h saddle).
    for dst, src in ((base, pair), (pair, base)):
        if np.linalg.norm(x[dst] - y[src]) > np.linalg.norm(x[dst] - y[src[::-1]]):
            src = src[::-1]
        end[dst] = y[src]
    return Geometry(start.symbols, end)


# --------------------------------------------------------------------------- study


def build_paths(analyses: list[StateAnalysis], log: Callable[[str], None] = print) -> list[Path]:
    by_key = {(a.state.m, a.state.charge, a.state.mult): a for a in analyses}
    tree = FragmentationTree([a.best for a in analyses if a.best is not None])
    paths = []
    for a in analyses:
        if a.state.label not in CLUSTERS or a.reference is None:
            continue
        start = a.reference.geometry
        key: Key = (a.state.m, a.state.charge, a.state.mult)
        for channel in tree.channels(key):
            if channel.electron or channel.cost * HARTREE_TO_EV >= CHANNEL_EV:
                continue
            refs = [by_key.get(p) for p in channel.parts]
            if any(r is None or r.reference is None for r in refs):
                log(f"{a.state.label} -> {channel.label}: a fragment has no reference structure")
                continue
            labels = [key_label(p) for p in channel.parts]
            parts = [(label, p[1], r.reference.geometry.coords) for label, p, r in zip(labels, channel.parts, refs)]
            for n, (groups, end) in enumerate(channel_paths(start, parts)):
                paths.append(Path(f"{a.state.label}|{channel.label}|{n}", a.state.label, channel.label,
                                  describe(groups, labels), a.state, start, end))
        if a.state.label == "H5+ (1)":
            paths.append(Path(f"{a.state.label}|hop|0", a.state.label, "proton hop", "C2v -> C2v",
                              a.state, start, hop_end(start)))
    return paths


def zpe(frequencies) -> float | None:
    """Harmonic ZPE (Eh) of the real modes; an imaginary mode is not a vibration."""
    if frequencies is None:
        return None
    return 0.5 * sum(f for f in frequencies if f > 0) / HARTREE_TO_CM


def d_zero(channel: Channel, by_key: dict, cluster: StateAnalysis) -> float | None:
    """The channel's D_0 (Eh): D_e plus the products' harmonic ZPE minus the cluster's."""
    def zpe_of(x: StateAnalysis | None) -> float | None:
        return x.best.thermo.zpe if x is not None and x.best is not None and x.best.thermo else None
    zpes = [zpe_of(by_key.get(k)) for k in channel.parts]
    if zpe_of(cluster) is None or None in zpes:
        return None
    return channel.cost + sum(zpes) - zpe_of(cluster)


def on_path(start: Geometry, ts: Geometry, tolerance: float = 0.25) -> bool:
    """Whether a TS search stayed near the image it started from: no sorted interatomic
    distance moved by more than `tolerance` (Angstrom). A search can slide off to a saddle of
    another rearrangement, which says nothing about the path's own maximum."""
    def distances(x):
        r = np.linalg.norm(x[:, None] - x[None], axis=-1)
        return np.sort(r[np.triu_indices(len(x), 1)])
    return bool(np.abs(distances(start.coords) - distances(ts.coords)).max() <= tolerance)


def run(session: Session, campaign: str, analyses: list[StateAnalysis], workers: int,
        log: Callable[[str], None]) -> list[dict]:
    study = f"{STUDY}@{campaign}"
    mp2, ccsdt = LEVELS["L1M"], LEVELS["L2"]
    paths = build_paths(analyses, log)
    neb = run_jobs(session, study, {
        p.key: OrcaJob(p.state, p.start, mp2, Task.NEB, maxcore_mb=1000, end_geometry=p.end, neb_images=IMAGES)
        for p in paths
    }, workers=workers, log=log)

    singles, ts_jobs, bumps, state_of = {}, {}, {}, {}
    for p in paths:
        r = neb[p.key]
        if not r.path:
            continue
        for i, g in enumerate(r.path):
            singles[f"{p.key}|img|{i}"] = OrcaJob(p.state, g, ccsdt, Task.SP, maxcore_mb=1500)
        e = r.path_energies
        top = max(range(1, len(e) - 1), key=e.__getitem__)
        bumps[p.key] = e[top] > max(e[0], e[-1]) + TOLERANCE
        if bumps[p.key] and r.ok:
            ts_jobs[f"{p.key}|ts"] = OrcaJob(p.state, r.geometry or r.path[top], mp2, Task.TS, maxcore_mb=1000)
            state_of[f"{p.key}|ts"] = p.state
    ts = run_jobs(session, study, ts_jobs, workers=workers, log=log)
    stayed = {key: r.ok and on_path(ts_jobs[key].geometry, r.geometry) for key, r in ts.items()}
    for key, r in ts.items():
        if stayed[key] and r.n_imag == 1:
            singles[f"{key}|L2"] = OrcaJob(state_of[key], r.geometry, ccsdt, Task.SP, maxcore_mb=1500)
    sp = run_jobs(session, study, singles, workers=workers, log=log)

    by_label = {a.state.label: a for a in analyses}
    by_key = {(x.state.m, x.state.charge, x.state.mult): x for x in analyses}
    tree = FragmentationTree([x.best for x in analyses if x.best is not None])
    rows = []
    for p in paths:
        a, r = by_label[p.cluster], neb[p.key]
        channel = None if p.channel == "proton hop" else next(
            (c for c in tree.channels((a.state.m, a.state.charge, a.state.mult)) if c.label == p.channel), None)
        d_e = None if channel is None else channel.cost
        d_0 = None if channel is None else d_zero(channel, by_key, a)
        row = {"state": p.cluster, "channel": p.channel, "atoms": p.groups,
               "d_e_ev": None if d_e is None else round(d_e * HARTREE_TO_EV, 4),
               "d_0_ev": None if d_0 is None else round(d_0 * HARTREE_TO_EV, 4)}
        if not r.path:
            rows.append(row | {"barrier_verdict": "failed", "neb_converged": False})
            continue
        e = r.path_energies
        cc = [sp.get(f"{p.key}|img|{i}") for i in range(len(e))]
        cc = [x.energy if x is not None and x.ok else None for x in cc]
        row |= {
            "neb_converged": bool(r.ok),
            "end_mp2_ev": round((e[-1] - e[0]) * HARTREE_TO_EV, 4),
            "max_mp2_ev": round((max(e[1:-1]) - e[0]) * HARTREE_TO_EV, 4),
            "end_ccsdt_ev": None if None in (cc[0], cc[-1]) else round((cc[-1] - cc[0]) * HARTREE_TO_EV, 4),
            "max_ccsdt_ev": None if None in cc else round((max(cc[1:-1]) - cc[0]) * HARTREE_TO_EV, 4),
        }
        t = ts.get(f"{p.key}|ts")
        t_cc = sp.get(f"{p.key}|ts|L2")
        if bumps.get(p.key) and stayed.get(f"{p.key}|ts") and t.n_imag == 1 and t_cc is not None and t_cc.ok and cc[0] is not None:
            barrier = t_cc.energy - cc[0]
            z_ts, z_start = zpe(t.frequencies), zpe(a.reference.frequencies)
            row |= {
                "ts_imag_cm": round(float(min(t.frequencies)), 1),
                "barrier_ev": round(barrier * HARTREE_TO_EV, 4),
                "barrier_0_ev": None if None in (z_ts, z_start) else round((barrier + z_ts - z_start) * HARTREE_TO_EV, 4),
                "above_products_ev": None if d_e is None else round((barrier - d_e) * HARTREE_TO_EV, 4),
            }
            if d_0 is not None and z_ts is not None and z_start is not None:
                row["above_products_0_ev"] = round((barrier + z_ts - z_start - d_0) * HARTREE_TO_EV, 4)
            if d_e is None:
                row["barrier_verdict"] = "isomerization"
            else:
                row["barrier_verdict"] = "above" if barrier > d_e else "submerged"
        elif bumps.get(p.key):
            # a maximum on the path, no TS confirmed: the search failed, or found another saddle
            row["barrier_verdict"] = "elsewhere" if t is not None and t.ok and not stayed[f"{p.key}|ts"] else "unconfirmed"
            if t is not None:
                row["ts_imag_cm"] = None if t.frequencies is None else round(float(min(t.frequencies)), 1)
                row["ts_n_imag"] = t.n_imag
        else:
            row["barrier_verdict"] = "none"
        if d_e is not None:
            row["threshold_ev"] = round(max(d_e * HARTREE_TO_EV, row.get("barrier_ev") or 0.0), 4)
        rows.append(row)
    return rows
