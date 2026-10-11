"""Anharmonic zero-point energy by second-order vibrational perturbation theory (VPT2).

ORCA 6.1's own VPT2 could not be used (Plan, Phase 8): it needs analytic Hessians, which
RI-MP2 lacks, and DFT has no C2v H5+ minimum. So the quartic force field is built here from
Hessians at displaced geometries, and the energy from the asymmetric-top VPT2 formulas.

Conventions: dimensionless normal coordinates q (H0 = sum_i w_i/2 (p_i^2 + q_i^2)), the
potential V = 1/6 sum phi_ijk q_i q_j q_k + 1/24 sum phi_ijkl q_i q_j q_k q_l over all
index orders, every constant in cm-1.

- Anharmonicity constants chi_rr, chi_rs: Franke, Stanton & Douberly, J. Phys. Chem. A 125,
  1301 (2021), eqs. 23-24 (including the Coriolis term).
- Constant term G0 (the part of the ground-state energy that does not depend on quanta):
  the standard nonresonant expression, checked against exact diagonalization of model
  potentials in tests/test_vpt2.py (VPT2 error falls as lambda^4 with the anharmonicity).
- Rotation: the Watson term -1/4 sum B and the ground-state Coriolis energy
  sum_a B_a sum_{i<j} zeta_ij^2 (w_i - w_j)^2 / (4 w_i w_j), which is what the Coriolis
  terms in chi and G0 add up to at v = 0.
"""

from dataclasses import dataclass
from itertools import combinations

import numpy as np

HARTREE_TO_CM = 219474.6313632
AMU_TO_ME = 1822.888486209
BOHR_PER_ANGSTROM = 1 / 0.529177210903
B_FACTOR_CM = 16.857629206  # B (cm-1) = 16.8576 / I (amu Å^2)


@dataclass
class Vpt2:
    omega: np.ndarray  # harmonic frequencies, cm-1
    chi: np.ndarray  # anharmonicity constants (vibrational + Coriolis), cm-1
    chi_vib: np.ndarray  # the same without the Coriolis term
    g0: float  # constant term, vibrational part, cm-1
    rotation: float  # Watson -1/4 sum B, cm-1
    coriolis: float  # ground-state Coriolis energy, cm-1

    @property
    def harmonic(self) -> float:
        return float(self.omega.sum() / 2)

    @property
    def zpe(self) -> float:
        """sum w/2 + G0 + 1/4 sum_{r<=s} chi_rs (+ rotational terms), cm-1."""
        n = len(self.omega)
        vib_chi = sum(self.chi_vib[r, s] for r in range(n) for s in range(r, n))
        return self.harmonic + self.g0 + vib_chi / 4 + self.rotation + self.coriolis

    @property
    def correction(self) -> float:
        return self.zpe - self.harmonic


def vpt2(omega, cubic, quartic, rotational=None, zeta=None) -> Vpt2:
    """VPT2 from harmonic frequencies, the full cubic force field and (semi-diagonal) quartic.

    `cubic[i,j,k]` = phi_ijk, `quartic[i,i,j,j]` = phi_iijj (other quartic elements unused);
    `rotational` = (B_x, B_y, B_z) in cm-1 and `zeta[a, i, j]` the Coriolis constants.
    """
    w = np.asarray(omega, dtype=float)
    f3 = np.asarray(cubic, dtype=float)
    f4 = np.asarray(quartic, dtype=float)
    n = len(w)
    chi = np.zeros((n, n))
    for r in range(n):
        chi[r, r] = f4[r, r, r, r] / 16 - sum(
            f3[r, r, s] ** 2 * (1 / (2 * w[r] + w[s]) + 4 / w[s] - 1 / (2 * w[r] - w[s]))
            for s in range(n)
        ) / 32
    for r, s in combinations(range(n), 2):
        x = f4[r, r, s, s] / 4 - sum(f3[r, r, t] * f3[s, s, t] / w[t] for t in range(n)) / 4
        x -= sum(
            f3[r, s, t] ** 2 * (
                1 / (w[r] + w[s] + w[t]) + 1 / (-w[r] + w[s] + w[t])
                + 1 / (w[r] - w[s] + w[t]) - 1 / (w[r] + w[s] - w[t])
            )
            for t in range(n)
        ) / 8
        chi[r, s] = chi[s, r] = x
    chi_vib = chi.copy()

    g0 = (
        sum(f4[i, i, i, i] for i in range(n)) / 64
        - 7 / 576 * sum(f3[i, i, i] ** 2 / w[i] for i in range(n))
        + 3 / 64 * sum(
            f3[i, i, j] ** 2 * w[j] / (4 * w[i] ** 2 - w[j] ** 2)
            for i in range(n) for j in range(n) if i != j
        )
        - 1 / 4 * sum(
            f3[i, j, k] ** 2 * w[i] * w[j] * w[k] / _delta(w[i], w[j], w[k])
            for i, j, k in combinations(range(n), 3)
        )
    )

    rotation = coriolis = 0.0
    if rotational is not None:
        b = np.asarray(rotational, dtype=float)
        rotation = -b.sum() / 4
        if zeta is not None:
            z = np.asarray(zeta, dtype=float)
            for a in range(3):
                for i, j in combinations(range(n), 2):
                    chi[i, j] += b[a] * z[a, i, j] ** 2 * (w[i] / w[j] + w[j] / w[i])
                    chi[j, i] = chi[i, j]
                    coriolis += b[a] * z[a, i, j] ** 2 * (w[i] - w[j]) ** 2 / (4 * w[i] * w[j])
    return Vpt2(omega=w, chi=chi, chi_vib=chi_vib, g0=float(g0), rotation=float(rotation), coriolis=float(coriolis))


def _delta(wi: float, wj: float, wk: float) -> float:
    return (wi + wj + wk) * (wi - wj - wk) * (-wi + wj - wk) * (-wi - wj + wk)


# --------------------------------------------------------------------------- force field


@dataclass
class NormalModes:
    """Harmonic analysis of a Cartesian Hessian at a stationary point (atomic units inside)."""

    omega: np.ndarray  # cm-1
    vectors: np.ndarray  # (n_vib, n_atoms*3), mass-weighted, orthonormal
    masses: np.ndarray  # amu per atom
    coords: np.ndarray  # Å, centred at the centre of mass

    def displacement(self, mode: int, dq: float) -> np.ndarray:
        """Cartesian displacement (Å) for a step dq in dimensionless coordinate `mode`."""
        w_au = self.omega[mode] / HARTREE_TO_CM
        dQ = dq / np.sqrt(w_au)  # mass-weighted, sqrt(m_e) bohr
        dx = self.vectors[mode].reshape(-1, 3) * dQ / np.sqrt(self.masses[:, None] * AMU_TO_ME)
        return dx / BOHR_PER_ANGSTROM

    def dimensionless_hessian(self, hessian: np.ndarray) -> np.ndarray:
        """d2V/dq_i dq_j (cm-1) from a Cartesian Hessian (Eh/bohr^2)."""
        m = np.repeat(self.masses * AMU_TO_ME, 3)
        hq = self.vectors @ (hessian / np.sqrt(np.outer(m, m))) @ self.vectors.T
        w_au = self.omega / HARTREE_TO_CM
        return hq / np.sqrt(np.outer(w_au, w_au)) * HARTREE_TO_CM

    def rotational_constants_and_zeta(self) -> tuple[np.ndarray, np.ndarray]:
        """B (cm-1) about the principal axes and zeta[a, i, j] in that frame."""
        x = self.coords
        inertia = np.eye(3) * np.sum(self.masses * (x**2).sum(1)) - np.einsum("a,ai,aj->ij", self.masses, x, x)
        moments, axes = np.linalg.eigh(inertia)
        b = B_FACTOR_CM / moments
        l = self.vectors.reshape(len(self.omega), -1, 3) @ axes  # modes in the principal frame
        zeta = np.stack([
            l[:, :, (a + 1) % 3] @ l[:, :, (a + 2) % 3].T - l[:, :, (a + 2) % 3] @ l[:, :, (a + 1) % 3].T
            for a in range(3)
        ])
        return b, zeta


def normal_modes(symbols, coords_angstrom, hessian, masses_amu) -> NormalModes:
    """Project translations and rotations out of a Cartesian Hessian and diagonalize it."""
    m = np.asarray(masses_amu, dtype=float)
    x = np.asarray(coords_angstrom, dtype=float)
    x = x - (m[:, None] * x).sum(0) / m.sum()
    n = len(m)
    sqm = np.repeat(np.sqrt(m * AMU_TO_ME), 3)
    hmw = hessian / np.outer(sqm, sqm)
    # translations and rotations (mass-weighted), orthonormalized
    rigid = []
    for k in range(3):
        t = np.zeros((n, 3))
        t[:, k] = 1
        rigid.append((t * np.sqrt(m)[:, None]).ravel())
        r = np.cross(np.eye(3)[k], x)
        rigid.append((r * np.sqrt(m)[:, None]).ravel())
    q, s, _ = np.linalg.svd(np.array(rigid).T, full_matrices=False)
    q = q[:, s > 1e-6 * s.max()]
    p = np.eye(3 * n) - q @ q.T
    evals, evecs = np.linalg.eigh(p @ hmw @ p)
    keep = np.argsort(np.abs(evals))[q.shape[1]:]  # drop the rigid-body zeros
    keep = keep[np.argsort(evals[keep])]
    omega = np.sign(evals[keep]) * np.sqrt(np.abs(evals[keep])) * HARTREE_TO_CM
    return NormalModes(omega=omega, vectors=evecs[:, keep].T, masses=m, coords=x)


def force_field(modes: NormalModes, hessians: dict[tuple[int, int], np.ndarray], h0: np.ndarray, dq: np.ndarray):
    """Cubic and semi-diagonal quartic constants (cm-1) from Hessians at +-dq along each mode.

    `hessians[(k, +1)]`, `hessians[(k, -1)]`: Cartesian Hessians at q_k = +-dq[k].
        phi_ijk  = (H_ij(+k) - H_ij(-k)) / (2 dq_k)          (averaged over index orders)
        phi_ijkk = (H_ij(+k) + H_ij(-k) - 2 H_ij(0)) / dq_k^2
    """
    n = len(modes.omega)
    d0 = modes.dimensionless_hessian(h0)
    cubic = np.zeros((n, n, n))
    quartic = np.zeros((n, n, n, n))
    for k in range(n):
        plus = modes.dimensionless_hessian(hessians[(k, 1)])
        minus = modes.dimensionless_hessian(hessians[(k, -1)])
        cubic[:, :, k] = (plus - minus) / (2 * dq[k])
        second = (plus + minus - 2 * d0) / dq[k] ** 2
        for i in range(n):
            quartic[i, i, k, k] = second[i, i]
    # symmetrize the cubic constants over index orders (numerical noise)
    sym = sum(np.transpose(cubic, p) for p in [(0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0)]) / 6
    # phi_iikk and phi_kkii come from different displacements: average them
    for i in range(n):
        for k in range(n):
            avg = (quartic[i, i, k, k] + quartic[k, k, i, i]) / 2
            quartic[i, i, k, k] = quartic[k, k, i, i] = avg
    return sym, quartic


def default_steps(omega: np.ndarray, mass_weighted_step: float = 0.05) -> np.ndarray:
    """Dimensionless steps equal to `mass_weighted_step` amu^1/2 bohr (CFOUR's default)."""
    w_au = np.asarray(omega) / HARTREE_TO_CM
    return mass_weighted_step * np.sqrt(AMU_TO_ME) * np.sqrt(w_au)
