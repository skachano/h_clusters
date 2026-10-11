"""Shape descriptors from the geometry alone: inertia, shape class, radius of gyration.

Point groups come from ORCA (printed with the thermochemistry of every frequency job), so
that the symmetry number used here is the one ORCA used for its own entropy.
"""

from typing import Literal

import numpy as np

from hclust.geometry import Geometry

MASS_AMU = {"H": 1.008}  # ORCA's mass for H (Total Mass 3.02 AMU for H3+)

ShapeClass = Literal["atom", "linear", "planar", "3D"]


def masses(geometry: Geometry) -> np.ndarray:
    return np.array([MASS_AMU[s] for s in geometry.symbols])


def principal_moments(geometry: Geometry) -> np.ndarray:
    """Principal moments of inertia (amu Å²), ascending."""
    m = masses(geometry)
    r = geometry.coords - (m[:, None] * geometry.coords).sum(axis=0) / m.sum()
    inertia = np.eye(3) * np.sum(m * (r**2).sum(axis=1)) - np.einsum("i,ij,ik->jk", m, r, r)
    return np.sort(np.linalg.eigvalsh(inertia))


def is_linear(geometry: Geometry, tolerance: float = 1e-3) -> bool:
    """Smallest moment ~0 (amu Å²): every atom on one axis."""
    return len(geometry) == 2 or (len(geometry) > 2 and principal_moments(geometry)[0] < tolerance)


def shape_class(geometry: Geometry, tolerance: float = 1e-2) -> ShapeClass:
    """Planar when Ic = Ia + Ib (all atoms in the plane of the two smaller axes)."""
    if len(geometry) == 1:
        return "atom"
    if is_linear(geometry):
        return "linear"
    a, b, c = principal_moments(geometry)
    return "planar" if abs(c - a - b) < tolerance * c else "3D"


def radius_of_gyration(geometry: Geometry) -> float:
    """Mass-weighted RMS distance from the centre of mass (Å)."""
    m = masses(geometry)
    r = geometry.coords - (m[:, None] * geometry.coords).sum(axis=0) / m.sum()
    return float(np.sqrt(np.sum(m * (r**2).sum(axis=1)) / m.sum()))
