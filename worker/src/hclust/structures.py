"""Seed geometries for the structure search, and structure comparison.

Generators are deterministic (random ones take an explicit seed), so that planning a
campaign twice produces the same structures and therefore the same jobs.
"""

from collections.abc import Callable

import numpy as np

from hclust.geometry import Geometry

H2_BOND = 0.74
H3_PLUS_BOND = 0.87
# Contacts shorter than this are chemical bonds when naming units ("H3+H2").
BOND_CUTOFF = 1.15
# A structure whose pieces are all farther apart than this has fallen apart. Ion-molecule
# and van der Waals complexes (H-.H2, H3+(H2)n, H2.H2) have contacts of 2.5-3.3 A, so a
# tighter cutoff discards real complexes (Plan, Phase 4); whether they are *bound* is an
# energetic question for the analysis.
DISSOCIATION_CUTOFF = 3.5


# --------------------------------------------------------------------------- templates


def chain(m: int, spacing: float = 0.9) -> list[Geometry]:
    """A linear chain along z: the simplest seed that exists for every m."""
    return [Geometry.hydrogens([[0.0, 0.0, i * spacing] for i in range(m)], f"chain {spacing}")]


def ring(m: int, side: float = 0.9) -> list[Geometry]:
    if m < 3:
        return []
    radius = side / (2 * np.sin(np.pi / m))
    phi = 2 * np.pi * np.arange(m) / m
    coords = np.column_stack([radius * np.cos(phi), radius * np.sin(phi), np.zeros(m)])
    return [Geometry.hydrogens(coords, f"ring {side}")]


def sphere(m: int, nearest: float = 0.9) -> list[Geometry]:
    """m points spread over a sphere (a compact 3D polyhedron), nearest neighbours `nearest` apart."""
    if m < 4:
        return []
    points = _sphere_points(m)
    return [Geometry.hydrogens(points * nearest / _min_distance(points), f"sphere {nearest}")]


def h2_units(m: int, separation: float = 1.8) -> list[Geometry]:
    """(H2)_k, plus one H atom for odd m, with unit centres spread over a sphere."""
    if m < 4:
        return []
    k, extra = divmod(m, 2)
    centres = _unit_centres(k + extra, separation)
    coords = []
    for i, centre in enumerate(centres[:k]):
        axis = _perpendicular(centre, i)
        coords += [centre + axis * H2_BOND / 2, centre - axis * H2_BOND / 2]
    if extra:
        coords.append(centres[k])
    return [Geometry.hydrogens(coords, f"h2_units {separation}")]


def h3_core(m: int, distance: float = 1.5) -> list[Geometry]:
    """An H3+ triangle solvated by H2 units (plus one H for even m): the H_(2k+1)^+ motif.

    Units sit first on the three vertices (radially out, in-plane), then above and below
    the triangle.
    """
    if m < 4:
        return []
    r = H3_PLUS_BOND / np.sqrt(3)
    phi = 2 * np.pi * np.arange(3) / 3
    vertices = np.column_stack([r * np.cos(phi), r * np.sin(phi), np.zeros(3)])
    sites = [v / np.linalg.norm(v) * (r + distance) for v in vertices]
    sites += [np.array([0, 0, distance]), np.array([0, 0, -distance])]
    k, extra = divmod(m - 3, 2)
    if k + extra > len(sites):
        return []
    coords = list(vertices)
    for i, site in enumerate(sites[:k]):
        axis = np.array([0.0, 0.0, 1.0]) if i < 3 else np.array([1.0, 0.0, 0.0])
        coords += [site + axis * H2_BOND / 2, site - axis * H2_BOND / 2]
    if extra:
        coords.append(sites[k])
    return [Geometry.hydrogens(coords, f"h3_core {distance}")]


def templates(m: int) -> list[Geometry]:
    """Every template that exists for m."""
    return [g for make in (chain, ring, sphere, h2_units, h3_core) for g in make(m)]


def random_clusters(
    m: int, count: int = 20, seed: int = 0, min_distance: float = 0.6,
    connect: float = 1.6, density: float = 0.8,
) -> list[Geometry]:
    """`count` random connected clusters inside a sphere of radius density * m^(1/3) + 0.4 A.

    Every pair is at least `min_distance` apart, and every atom is within `connect` of
    another one (no pre-made fragments).
    """
    if m == 1:
        return [Geometry.hydrogens([[0.0, 0.0, 0.0]], "random")]
    rng = np.random.default_rng([seed, m])
    radius = density * m ** (1 / 3) + 0.4
    found: list[Geometry] = []
    for _ in range(100_000):
        if len(found) == count:
            break
        directions = rng.normal(size=(m, 3))
        directions /= np.linalg.norm(directions, axis=1, keepdims=True)
        points = directions * radius * rng.uniform(size=(m, 1)) ** (1 / 3)  # uniform in the ball
        g = Geometry.hydrogens(points - points.mean(axis=0), f"random seed={seed}")
        d = g.distance_matrix()
        np.fill_diagonal(d, np.inf)
        if d.min() >= min_distance and len(fragments(g, connect)) == 1:
            found.append(g)
    if len(found) < count:
        raise RuntimeError(f"only {len(found)} of {count} random clusters for m={m}")
    return found


GENERATORS: dict[str, Callable[..., list[Geometry]]] = {
    "chain": chain,
    "ring": ring,
    "sphere": sphere,
    "h2_units": h2_units,
    "h3_core": h3_core,
    "templates": templates,
    "random": random_clusters,
}


# --------------------------------------------------------------------------- analysis


def fragments(geometry: Geometry, cutoff: float = DISSOCIATION_CUTOFF) -> list[list[int]]:
    """Connected components of the graph with edges between atoms closer than `cutoff`."""
    adjacent = geometry.distance_matrix() < cutoff
    unseen, components = set(range(len(geometry))), []
    while unseen:
        stack = [unseen.pop()]
        component = []
        while stack:
            i = stack.pop()
            component.append(i)
            for j in np.flatnonzero(adjacent[i]):
                if j in unseen:
                    unseen.remove(j)
                    stack.append(int(j))
        components.append(sorted(component))
    return sorted(components, key=lambda c: (-len(c), c))


def is_dissociated(geometry: Geometry, cutoff: float = DISSOCIATION_CUTOFF) -> bool:
    return len(fragments(geometry, cutoff)) > 1


def composition(geometry: Geometry, cutoff: float = BOND_CUTOFF) -> str:
    """Bonded units, largest first: 'H3+H2' style without charges, e.g. 'H3·H2'."""
    return "·".join(f"H{len(f)}" if len(f) > 1 else "H" for f in fragments(geometry, cutoff))


def fingerprint(geometry: Geometry) -> np.ndarray:
    """Sorted interatomic distances: invariant to translation, rotation and atom permutation."""
    return geometry.distances()


def same_structure(a: Geometry, b: Geometry, tolerance: float = 0.05) -> bool:
    """RMS difference of the fingerprints below `tolerance` (Angstrom)."""
    fa, fb = fingerprint(a), fingerprint(b)
    return len(fa) == len(fb) and (len(fa) == 0 or np.sqrt(np.mean((fa - fb) ** 2)) < tolerance)


# --------------------------------------------------------------------------- helpers


def _sphere_points(n: int, steps: int = 500) -> np.ndarray:
    """Fibonacci points relaxed by pairwise repulsion on the unit sphere (deterministic)."""
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    theta = np.pi * (1 + 5**0.5) * i
    p = np.column_stack([np.cos(theta) * np.sin(phi), np.sin(theta) * np.sin(phi), np.cos(phi)])
    for _ in range(steps):
        diff = p[:, None, :] - p[None, :, :]
        dist = np.linalg.norm(diff, axis=-1) + np.eye(n)
        force = (diff / dist[..., None] ** 3).sum(axis=1)
        p = p + 0.01 * force
        p /= np.linalg.norm(p, axis=1, keepdims=True)
    return p


def _unit_centres(n: int, separation: float) -> np.ndarray:
    if n == 1:
        return np.zeros((1, 3))
    if n == 2:
        return np.array([[0, 0, -separation / 2], [0, 0, separation / 2]])
    if n == 3:
        r = separation / np.sqrt(3)
        phi = 2 * np.pi * np.arange(3) / 3
        return np.column_stack([r * np.cos(phi), r * np.sin(phi), np.zeros(3)])
    points = _sphere_points(n)
    return points * separation / _min_distance(points)


def _perpendicular(v: np.ndarray, i: int) -> np.ndarray:
    """A unit vector perpendicular to v (or to z for v = 0); alternates for variety."""
    ref = np.array([0.0, 0.0, 1.0]) if np.linalg.norm(v) < 1e-8 else v
    trial = np.array([1.0, 0.0, 0.0]) if i % 2 == 0 else np.array([0.0, 1.0, 0.0])
    axis = np.cross(ref, trial)
    if np.linalg.norm(axis) < 1e-8:
        axis = np.cross(ref, np.array([0.0, 0.0, 1.0]))
    return axis / np.linalg.norm(axis)


def _min_distance(points: np.ndarray) -> float:
    d = np.linalg.norm(points[:, None] - points[None], axis=-1)
    return float(d[np.triu_indices(len(points), 1)].min())
