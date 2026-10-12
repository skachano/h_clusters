"""Quantum nuclear motion of weakly bound clusters: diffusion Monte Carlo (DMC).

Harmonic zero-point energy fails for van der Waals clusters of H2: the intermolecular
motions are large-amplitude and anharmonic. DMC solves the nuclear Schrödinger equation
exactly (up to statistical and time-step error) on a given potential, so it decides whether
a cluster has a bound ground state at all.

Model (doc/Plan.md, Phase 8, DMC study): every H2 is a rigid sphere (para-H2, J = 0: its
rotational ground state is isotropic), the H atom a point, the potential a sum of isotropic
pair potentials fitted to CCSD(T) scans (studies/dmc.py). Atomic units throughout.

- `PairPotential`: natural cubic spline through the scan, an exponential wall below it and
  -C6/R^6 - C8/R^8 beyond it.
- `radial_ground_state`: exact bound state of a two-body system (finite differences), the
  benchmark for DMC on the dimers.
- `dmc`: unguided DMC with branching. Without a trial function the ground-state energy is
  exactly the average potential over the walker distribution, E0 = <V>.
"""

from dataclasses import dataclass, field
from itertools import combinations

import numpy as np

AMU_TO_ME = 1822.888486209
BOHR_PER_ANGSTROM = 1 / 0.529177210903
MASS_H = 1.00782503207 * AMU_TO_ME
MASS_H2 = 2 * MASS_H


# --------------------------------------------------------------------------- pair potential


@dataclass
class PairPotential:
    """V(R) in Eh for R in bohr, from points (R_i, V_i) sorted by R."""

    r: np.ndarray
    v: np.ndarray
    wall: tuple[float, float] = field(init=False)  # V = a exp(-b (R - R0)) below the grid
    tail: tuple[float, float] = field(init=False)  # V = -C6/R^6 - C8/R^8 beyond the grid
    m: np.ndarray = field(init=False, repr=False)  # spline second derivatives

    def __post_init__(self):
        self.r = np.asarray(self.r, dtype=float)
        self.v = np.asarray(self.v, dtype=float)
        if np.any(np.diff(self.r) <= 0):
            raise ValueError("pair potential points must be sorted by distance")
        self.m = _natural_spline(self.r, self.v)
        (r0, r1), (v0, v1) = self.r[:2], self.v[:2]
        if v0 <= 0 or v1 <= 0 or v1 >= v0:
            raise ValueError("the scan must start on the repulsive wall")
        self.wall = (v0, np.log(v0 / v1) / (r1 - r0))
        # match the last two points: -C6 R^-6 - C8 R^-8 = V
        a = np.array([[-r ** -6, -r ** -8] for r in self.r[-2:]])
        c6, c8 = np.linalg.solve(a, self.v[-2:])
        self.tail = (c6, c8)

    def __call__(self, r) -> np.ndarray:
        r = np.asarray(r, dtype=float)
        out = np.empty_like(r)
        lo, hi = r < self.r[0], r > self.r[-1]
        mid = ~(lo | hi)
        out[lo] = self.wall[0] * np.exp(-self.wall[1] * (r[lo] - self.r[0]))
        c6, c8 = self.tail
        out[hi] = -c6 / r[hi] ** 6 - c8 / r[hi] ** 8
        out[mid] = _spline_eval(self.r, self.v, self.m, r[mid])
        return out

    def minimum(self) -> tuple[float, float]:
        """(R_min, V_min) on a fine grid."""
        grid = np.linspace(self.r[0], self.r[-1], 20001)
        v = self(grid)
        k = int(np.argmin(v))
        return float(grid[k]), float(v[k])


def _natural_spline(x, y):
    n = len(x)
    h = np.diff(x)
    a = np.zeros((n, n))
    rhs = np.zeros(n)
    a[0, 0] = a[-1, -1] = 1
    for i in range(1, n - 1):
        a[i, i - 1], a[i, i], a[i, i + 1] = h[i - 1], 2 * (h[i - 1] + h[i]), h[i]
        rhs[i] = 6 * ((y[i + 1] - y[i]) / h[i] - (y[i] - y[i - 1]) / h[i - 1])
    return np.linalg.solve(a, rhs)


def _spline_eval(x, y, m, t):
    k = np.clip(np.searchsorted(x, t) - 1, 0, len(x) - 2)
    h = x[k + 1] - x[k]
    a, b = (x[k + 1] - t) / h, (t - x[k]) / h
    return a * y[k] + b * y[k + 1] + ((a ** 3 - a) * m[k] + (b ** 3 - b) * m[k + 1]) * h ** 2 / 6


# --------------------------------------------------------------------------- exact dimer


def radial_ground_state(potential, mu: float, r_max: float = 600.0, n: int = 20000,
                        r_min: float = 2.0) -> tuple[float, float]:
    """Lowest s-wave level of -u''/(2 mu) + V(r) u = E u on [r_min, r_max], u = 0 at both ends.

    Returns (E, <r>). E >= 0 means no bound state in this box. Halo states (bound by microvolts,
    tens of Å across) need a large box, hence the tridiagonal solver: bisection on the Sturm
    sequence for E, inverse iteration for the wave function.
    """
    r = np.linspace(r_min, r_max, n + 2)[1:-1]
    h = r[1] - r[0]
    k = 1 / (2 * mu * h * h)
    diag, off = 2 * k + potential(r), -k

    def below(e):  # number of eigenvalues below e (Sturm sequence of the LDL^T factors)
        count, q = 0, diag[0] - e
        count += q < 0
        for d in diag[1:]:
            q = d - e - off * off / (q if q != 0 else 1e-300)
            count += q < 0
        return count

    lo, hi = float(diag.min() - 2 * k), float(diag.min() + 2 * k)
    while below(hi) < 1:
        hi += 4 * k
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        lo, hi = (lo, mid) if below(mid) >= 1 else (mid, hi)
    e = 0.5 * (lo + hi)
    u = np.ones(n)
    for _ in range(3):  # inverse iteration: (H - e') u_new = u, tridiagonal (Thomas algorithm)
        u = _tridiagonal_solve(diag - (e - 1e-12 * max(1.0, abs(e))), off, u)
        u /= np.linalg.norm(u)
    p = u * u
    return e, float(np.sum(r * p) / np.sum(p))


def _tridiagonal_solve(diag, off, rhs):
    n = len(diag)
    c, d = np.empty(n), np.empty(n)
    c[0], d[0] = off / diag[0], rhs[0] / diag[0]
    for i in range(1, n):
        m = diag[i] - off * c[i - 1]
        c[i], d[i] = off / m, (rhs[i] - off * d[i - 1]) / m
    x = np.empty(n)
    x[-1] = d[-1]
    for i in range(n - 2, -1, -1):
        x[i] = d[i] - c[i] * x[i + 1]
    return x


# --------------------------------------------------------------------------- DMC


@dataclass
class DmcResult:
    energy: float  # Eh, ground-state energy relative to the separated particles
    error: float  # one standard error from block averaging
    size: float  # mean particle distance from the centre, bohr (last half of the run)
    size_growth: float  # its ratio, last quarter over second quarter (>> 1: falling apart)
    trace: np.ndarray = field(repr=False)  # <V> per step after equilibration


def dmc(masses, pair_potentials: dict[tuple[int, int], PairPotential], start: np.ndarray, *,
        walkers: int = 2000, dt: float = 20.0, steps: int = 30000, equilibration: int = 10000,
        seed: int = 0) -> DmcResult:
    """Unguided DMC for point particles with pair potentials (all pairs listed in the dict).

    `start` (n, 3) bohr is spread a little for each walker. The reference energy steers the
    population towards `walkers`; E0 = <V> over the walkers, averaged after equilibration.
    """
    rng = np.random.default_rng(seed)
    masses = np.asarray(masses, dtype=float)
    n = len(masses)
    pairs = [(i, j, pair_potentials[(i, j)]) for i, j in combinations(range(n), 2)]
    sigma = np.sqrt(dt / masses)[None, :, None]
    x = start[None] + 0.1 * rng.standard_normal((walkers, n, 3))

    def potential(x):
        v = np.zeros(len(x))
        for i, j, pot in pairs:
            v += pot(np.linalg.norm(x[:, i] - x[:, j], axis=1))
        return v

    v = potential(x)
    e_ref = float(v.mean())
    trace, sizes = [], []
    for step in range(steps):
        x = x + sigma * rng.standard_normal(x.shape)
        v_new = potential(x)
        weight = np.exp(-dt * (0.5 * (v + v_new) - e_ref))
        copies = np.minimum((weight + rng.random(len(weight))).astype(int), 3)
        x, v = np.repeat(x, copies, axis=0), np.repeat(v_new, copies)
        if len(x) == 0:
            raise RuntimeError("all walkers died: time step too large")
        e_ref = float(v.mean()) - 0.1 / dt * np.log(len(x) / walkers)
        if step >= equilibration:
            trace.append(float(v.mean()))
            centre = x.mean(axis=1, keepdims=True)
            sizes.append(float(np.linalg.norm(x - centre, axis=2).mean()))
    trace, sizes = np.array(trace), np.array(sizes)
    q = len(sizes) // 4
    return DmcResult(
        energy=float(trace.mean()), error=block_error(trace), size=float(sizes[2 * q:].mean()),
        size_growth=float(sizes[3 * q:].mean() / sizes[q:2 * q].mean()), trace=trace,
    )


def block_error(series: np.ndarray, blocks: int = 20) -> float:
    """Standard error of the mean of a correlated series, from `blocks` block averages."""
    usable = len(series) // blocks * blocks
    means = series[:usable].reshape(blocks, -1).mean(axis=1)
    return float(means.std(ddof=1) / np.sqrt(blocks))
