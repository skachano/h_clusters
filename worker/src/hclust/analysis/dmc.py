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
- `coupled_channel_ground_state`: exact bound state of an atom (or ion) and a rigid rotor H2
  on an anisotropic potential, to test the isotropic averaging.
- `IonThreeBody`: the non-additive energy of an ion and two rotating H2, tabulated from CCSD(T).
- `dmc`: unguided DMC with branching. Without a trial function the ground-state energy is
  exactly the average potential over the walker distribution, E0 = <V>. Optionally the first
  units are rigid rotors (H2 axes diffusing on the sphere) for anisotropic potentials.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from itertools import combinations

import numpy as np

AMU_TO_ME = 1822.888486209
BOHR_PER_ANGSTROM = 1 / 0.529177210903
MASS_H = 1.00782503207 * AMU_TO_ME
MASS_H2 = 2 * MASS_H
B_H2 = 59.322 / 219474.6313705  # Eh, rotational constant of H2 in v = 0 (B0, cm-1)


# --------------------------------------------------------------------------- pair potential


@dataclass
class PairPotential:
    """V(R) in Eh for R in bohr, from points (R_i, V_i) sorted by R.

    Beyond the grid V = -C_p/R^p - C_q/R^q with (p, q) = `tail_powers`: (6, 8) for dispersion,
    (4, 6) around an ion (charge-induced dipole); a single power is matched to the last point.
    Below the grid an exponential wall, or (`wall=False`, for anisotropic terms that need not be
    repulsive) the first value held constant.
    """

    r: np.ndarray
    v: np.ndarray
    tail_powers: tuple[int, ...] = (6, 8)
    has_wall: bool = True
    wall: tuple[float, float] = field(init=False)  # V = a exp(-b (R - R0)) below the grid
    tail: tuple[float, ...] = field(init=False)  # (C_p, C_q) of the tail
    m: np.ndarray = field(init=False, repr=False)  # spline second derivatives

    def __post_init__(self):
        self.r = np.asarray(self.r, dtype=float)
        self.v = np.asarray(self.v, dtype=float)
        if np.any(np.diff(self.r) <= 0):
            raise ValueError("pair potential points must be sorted by distance")
        self.m = _natural_spline(self.r, self.v)
        (r0, r1), (v0, v1) = self.r[:2], self.v[:2]
        if not self.has_wall:
            self.wall = (v0, 0.0)
        elif v0 <= 0 or v1 <= 0 or v1 >= v0:
            raise ValueError("the scan must start on the repulsive wall")
        else:
            self.wall = (v0, np.log(v0 / v1) / (r1 - r0))
        # match the last points: -sum C_p R^-p = V
        k = len(self.tail_powers)
        a = np.array([[-r ** -p for p in self.tail_powers] for r in self.r[-k:]])
        self.tail = tuple(np.linalg.solve(a, self.v[-k:]))

    def __call__(self, r) -> np.ndarray:
        r = np.asarray(r, dtype=float)
        out = np.empty_like(r)
        lo, hi = r < self.r[0], r > self.r[-1]
        mid = ~(lo | hi)
        out[lo] = self.wall[0] * np.exp(-self.wall[1] * (r[lo] - self.r[0]))
        out[hi] = -sum(c / r[hi] ** p for c, p in zip(self.tail, self.tail_powers))
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


def coupled_channel_ground_state(v_lambda: dict[int, Callable], mu: float, b_rot: float = B_H2,
                                 j_max: int = 8, r_min: float = 3.0, r_max: float = 60.0,
                                 n: int = 500) -> tuple[float, dict[int, float]]:
    """Lowest J = 0 level of an atom and a para-H2 rigid rotor, V(R, g) = sum V_l(R) P_l(cos g).

    Total J = 0 ties the orbital momentum to the rotor's (l = j), so each channel j = 0, 2, ...
    carries (1/(2 mu R^2) + B) j(j+1); the potential couples them through <j|P_l|j'>. Radial
    sinc DVR on (r_min, r_max) (Colbert & Miller 1992). Returns (E, weight of each j).
    """
    js = list(range(0, j_max + 1, 2))
    x, w = np.polynomial.legendre.leggauss(4 * j_max + 8)
    p = {j: np.sqrt((2 * j + 1) / 2) * np.polynomial.legendre.Legendre.basis(j)(x) for j in js}
    coupling = {lam: np.array([[np.sum(w * p[a] * p[b] * np.polynomial.legendre.Legendre.basis(lam)(x))
                                for b in js] for a in js]) for lam in v_lambda}
    i = np.arange(1, n)
    r = r_min + (r_max - r_min) * i / n
    d, s = np.subtract.outer(i, i), np.add.outer(i, i)
    with np.errstate(divide="ignore"):
        t = np.where(d == 0, (2 * n * n + 1) / 3 - 1 / np.sin(np.pi * i / n) ** 2,
                     (-1.0) ** d * (1 / np.sin(np.pi * d / (2 * n)) ** 2 - 1 / np.sin(np.pi * s / (2 * n)) ** 2))
    t *= np.pi ** 2 / (2 * (r_max - r_min) ** 2) / (2 * mu)
    m = len(r)
    h = np.zeros((len(js) * m, len(js) * m))
    v = {lam: np.asarray(f(r), dtype=float) for lam, f in v_lambda.items()}
    for a, ja in enumerate(js):
        h[a * m:(a + 1) * m, a * m:(a + 1) * m] = t + np.diag(ja * (ja + 1) * (1 / (2 * mu * r * r) + b_rot))
        for b in range(len(js)):
            h[a * m:(a + 1) * m, b * m:(b + 1) * m] += np.diag(sum(coupling[lam][a, b] * v[lam] for lam in v))
    e, vec = np.linalg.eigh(h)
    u = vec[:, 0].reshape(len(js), m)
    return float(e[0]), {j: float(np.sum(u[a] ** 2)) for a, j in enumerate(js)}


class IonThreeBody:
    """Three-body energy of an ion and two rotating H2, tabulated from CCSD(T).

    For each ion-H2-H2 triple, E3 = a + b [P2(c1) + P2(c2)] + d P2(c1) P2(c2), with c_i the
    cosine between H2 i's axis and its line to the ion. a, b, d follow from three orientations
    computed at each (R, theta) of the scan (R the ion-H2 distance, theta the H2-ion-H2 angle):
    both end-on (c = 1), both side-on (c = 0), one of each. Unequal distances use the mean
    R = (R1 + R2)/2 (checked against off-diagonal points). Natural splines in R and cos(theta);
    held constant inside the grid's smallest R and angle, decaying as exp(-kappa (R - R_max))
    beyond its largest R.
    """

    def __init__(self, ion: int, rotors: list[int], r: np.ndarray, cos_theta: np.ndarray,
                 end: np.ndarray, side: np.ndarray, mixed: np.ndarray, kappa: float):
        """r (bohr) and cos_theta increasing; end/side/mixed (Eh) shaped (len(r), len(cos_theta))."""
        self.ion, self.rotors, self.r, self.c, self.kappa = ion, rotors, np.asarray(r), np.asarray(cos_theta), kappa
        end, side, mixed = (np.asarray(t, dtype=float) for t in (end, side, mixed))
        # P2 = 1 (end-on), -1/2 (side-on): end = a + 2b + d, side = a - b + d/4, mixed = a + b/2 - d/2
        s = (end - mixed) / 1.5  # b + d
        b = (end - side - 0.75 * s) / 2.25
        d = s - b
        self.coef = {"a": end - 2 * b - d, "b": b, "d": d}
        self.m_r = {k: [_natural_spline(self.r, t[:, j]) for j in range(len(self.c))] for k, t in self.coef.items()}
        eye = np.eye(len(self.c))
        self.m_c = [_natural_spline(self.c, eye[j]) for j in range(len(self.c))]

    def coefficients(self, r_mean: np.ndarray, cos_theta: np.ndarray) -> dict[str, np.ndarray]:
        r = np.clip(r_mean, self.r[0], self.r[-1])
        c = np.clip(cos_theta, self.c[0], self.c[-1])
        decay = np.exp(-self.kappa * np.maximum(r_mean - self.r[-1], 0))
        eye = np.eye(len(self.c))
        weights = [_spline_eval(self.c, eye[j], self.m_c[j], c) for j in range(len(self.c))]
        out = {}
        for k, t in self.coef.items():
            cols = [_spline_eval(self.r, t[:, j], self.m_r[k][j], r) for j in range(len(self.c))]
            out[k] = decay * sum(w * col for w, col in zip(weights, cols))
        return out

    def averaged(self) -> Callable[[np.ndarray, np.ndarray | None], np.ndarray]:
        """The term for H2 as spheres (free rotors, <P2> = 0): only a remains."""
        return lambda x, u: self(x, u, average=True)

    def __call__(self, x: np.ndarray, u: np.ndarray | None, average: bool = False) -> np.ndarray:
        """Energy (Eh) of walkers x (w, n, 3); u (w, rotors, 3) the H2 axes, None for end-on."""
        out = np.zeros(len(x))
        d = {i: x[:, self.ion] - x[:, i] for i in self.rotors}
        r = {i: np.linalg.norm(v, axis=1) for i, v in d.items()}
        p2 = {}
        for n, i in enumerate(self.rotors):
            c = np.ones(len(x)) if u is None else np.sum(d[i] * u[:, n], axis=1) / r[i]
            p2[i] = 1.5 * c * c - 0.5
        for a, i in enumerate(self.rotors):
            for j in self.rotors[a + 1:]:
                cos_t = np.sum(d[i] * d[j], axis=1) / (r[i] * r[j])
                k = self.coefficients(0.5 * (r[i] + r[j]), cos_t)
                if average:
                    out += k["a"]
                    continue
                out += k["a"] + k["b"] * (p2[i] + p2[j]) + k["d"] * p2[i] * p2[j]
        return out


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
        seed: int = 0, many_body: Callable | None = None, rotors: int = 0,
        b_rot: float = B_H2) -> DmcResult:
    """Unguided DMC for point particles with pair potentials (all pairs listed in the dict),
    plus an optional term `many_body(x, u)` over walkers x (w, n, 3): non-additive, or
    orientation-dependent through the axes u (w, rotors, 3) of the first `rotors` units.

    A rotor's Hamiltonian B j^2 = -B (Laplacian on the sphere) is diffusion of its axis: each
    step adds a Gaussian of variance 2 B dt per component and renormalises. The ground state
    found is even in u -> -u (para-H2) whenever the potential is.

    `start` (n, 3) bohr is spread a little for each walker. The reference energy steers the
    population towards `walkers`; E0 = <V> over the walkers, averaged after equilibration.
    """
    rng = np.random.default_rng(seed)
    masses = np.asarray(masses, dtype=float)
    n = len(masses)
    pairs = [(i, j, pair_potentials[(i, j)]) for i, j in combinations(range(n), 2)]
    sigma = np.sqrt(dt / masses)[None, :, None]
    x = start[None] + 0.1 * rng.standard_normal((walkers, n, 3))
    u = _unit(rng.standard_normal((walkers, rotors, 3))) if rotors else None
    sigma_rot = np.sqrt(2 * b_rot * dt)

    def potential(x, u):
        v = np.zeros(len(x))
        for i, j, pot in pairs:
            v += pot(np.linalg.norm(x[:, i] - x[:, j], axis=1))
        return v if many_body is None else v + many_body(x, u)

    v = potential(x, u)
    e_ref = float(v.mean())
    trace, sizes = [], []
    for step in range(steps):
        x = x + sigma * rng.standard_normal(x.shape)
        if rotors:
            u = _unit(u + sigma_rot * rng.standard_normal(u.shape))
        v_new = potential(x, u)
        weight = np.exp(-dt * (0.5 * (v + v_new) - e_ref))
        copies = np.minimum((weight + rng.random(len(weight))).astype(int), 3)
        x, v = np.repeat(x, copies, axis=0), np.repeat(v_new, copies)
        if rotors:
            u = np.repeat(u, copies, axis=0)
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


def _unit(v: np.ndarray) -> np.ndarray:
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def ion_rotor_anisotropy(ion: int, v_lambda: dict[int, Callable]) -> Callable:
    """sum over rotors i of sum_{l > 0} V_l(R_i) P_l(cos g_i), g_i the angle between rotor i's
    axis and its line to the ion (the l = 0 part belongs in the pair potentials)."""
    legendre = {lam: np.polynomial.legendre.Legendre.basis(lam) for lam in v_lambda if lam}

    def energy(x, u):
        out = np.zeros(len(x))
        for i in range(u.shape[1]):
            d = x[:, ion] - x[:, i]
            r = np.linalg.norm(d, axis=1)
            c = np.sum(d * u[:, i], axis=1) / r
            for lam, p in legendre.items():
                out += v_lambda[lam](r) * p(c)
        return out
    return energy


def block_error(series: np.ndarray, blocks: int = 20) -> float:
    """Standard error of the mean of a correlated series, from `blocks` block averages."""
    usable = len(series) // blocks * blocks
    means = series[:usable].reshape(blocks, -1).mean(axis=1)
    return float(means.std(ddof=1) / np.sqrt(blocks))
