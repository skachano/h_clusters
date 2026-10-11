"""Point groups with a tolerance (ORCA's detection is too strict, Plan Phase 1).

A symmetry operation is accepted when it maps every atom onto an atom within `tolerance`
(Å). Candidate axes and plane normals come from the principal axes, the atoms, midpoints and
differences of atom pairs, and normals of atom pairs; the group then follows the usual
flowchart (linear → cubic → Cn, Dn families → low symmetry). Molecules here have at most
a few dozen atoms, so testing every candidate is cheap.
"""

from itertools import combinations

import numpy as np

from hclust.analysis.shape import masses
from hclust.geometry import Geometry

DEFAULT_TOLERANCE = 0.05  # Å
MAX_ORDER = 10


def point_group(geometry: Geometry, tolerance: float = DEFAULT_TOLERANCE) -> tuple[str, int]:
    """(Schoenflies symbol, rotational symmetry number), e.g. ('D3h', 6), ('C∞v', 1)."""
    x = _centered(geometry)
    if len(x) == 1:
        return "Kh", 1
    if _on_one_line(x, tolerance):
        return ("D∞h", 2) if _maps(x, -np.eye(3), tolerance) else ("C∞v", 1)

    candidates = _candidate_directions(x)
    axes: dict[int, int] = {}  # candidate index -> highest proper rotation order
    for i, d in enumerate(candidates):
        n = max((n for n in range(2, MAX_ORDER + 1) if _maps(x, _rotation(d, 2 * np.pi / n), tolerance)),
                default=1)
        if n > 1:
            axes[i] = n
    planes = [d for d in candidates if _maps(x, _reflection(d), tolerance)]
    inversion = _maps(x, -np.eye(3), tolerance)

    high = [i for i, n in axes.items() if n >= 3]
    if len(high) >= 2:  # cubic groups
        orders = {axes[i] for i in high}
        if 5 in orders:
            return ("Ih", 60) if inversion else ("I", 60)
        if 4 in orders:
            return ("Oh", 24) if inversion else ("O", 24)
        if inversion:
            return "Th", 12
        return ("Td", 12) if planes else ("T", 12)
    if not axes:
        if planes:
            return "Cs", 1
        return ("Ci", 1) if inversion else ("C1", 1)

    def rank(i: int) -> tuple:
        """Highest order first; among equal C2 axes (D2d), the S4 axis inside the mirror planes."""
        d, n = candidates[i], axes[i]
        s2n = _maps(x, _reflection(d) @ _rotation(d, np.pi / n), tolerance)
        return n, s2n, sum(abs(p @ d) < 1e-2 for p in planes)

    best = max(axes, key=rank)
    principal, n = candidates[best], axes[best]
    perpendicular_c2 = [
        candidates[i] for i, k in axes.items()
        if k % 2 == 0 and abs(candidates[i] @ principal) < 1e-2
    ]
    horizontal = any(abs(abs(p @ principal) - 1) < 1e-2 for p in planes)
    vertical = [p for p in planes if abs(p @ principal) < 1e-2]
    if perpendicular_c2:
        if horizontal:
            return f"D{n}h", 2 * n
        return (f"D{n}d", 2 * n) if vertical else (f"D{n}", 2 * n)
    if horizontal:
        return f"C{n}h", n
    if vertical:
        return f"C{n}v", n
    if _maps(x, _reflection(principal) @ _rotation(principal, np.pi / n), tolerance):
        return f"S{2 * n}", n
    return f"C{n}", n


def _on_one_line(x: np.ndarray, tolerance: float) -> bool:
    """All atoms within `tolerance` of the axis of least inertia."""
    axis = np.linalg.eigh(np.eye(3) * (x**2).sum() - x.T @ x)[1][:, 0]
    return bool(np.linalg.norm(x - np.outer(x @ axis, axis), axis=1).max() < tolerance)


def _centered(geometry: Geometry) -> np.ndarray:
    m = masses(geometry)
    return geometry.coords - (m[:, None] * geometry.coords).sum(axis=0) / m.sum()


def _candidate_directions(x: np.ndarray) -> list[np.ndarray]:
    """Unit vectors that may be symmetry axes or plane normals, without near-duplicates."""
    inertia = np.eye(3) * (x**2).sum() - x.T @ x
    raw = list(np.linalg.eigh(inertia)[1].T) + list(x)
    for a, b in combinations(x, 2):
        raw += [a + b, a - b, np.cross(a, b)]
    out: list[np.ndarray] = []
    for v in raw:
        norm = np.linalg.norm(v)
        if norm < 1e-3:
            continue
        v = v / norm
        if not any(abs(v @ u) > 0.999 for u in out):
            out.append(v)
    return out


def _rotation(axis: np.ndarray, angle: float) -> np.ndarray:
    a = np.asarray(axis, dtype=float)
    k = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(angle) * k + (1 - np.cos(angle)) * k @ k


def _reflection(normal: np.ndarray) -> np.ndarray:
    n = np.asarray(normal, dtype=float)
    return np.eye(3) - 2 * np.outer(n, n)


def _maps(x: np.ndarray, op: np.ndarray, tolerance: float) -> bool:
    """Every transformed atom lands within `tolerance` of a distinct atom."""
    y = x @ np.asarray(op).T
    d = np.linalg.norm(y[:, None, :] - x[None, :, :], axis=-1)
    nearest = d.argmin(axis=1)
    return bool(d.min(axis=1).max() < tolerance and len(set(nearest)) == len(x))
