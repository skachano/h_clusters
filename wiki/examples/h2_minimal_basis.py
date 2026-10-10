"""Hartree-Fock and full CI for H2 in the STO-3G basis, from scratch.

Everything ORCA does for an SCF calculation, in about 150 lines of numpy:
build a basis, compute integrals, iterate the Roothaan equations to
self-consistency, then add electron correlation exactly (full CI), which is
cheap here because the basis has only two functions.

Follows Szabo & Ostlund, *Modern Quantum Chemistry*, §3.5. Atomic units
throughout (bohr, hartree).

Run (numpy is all it needs; the worker image has it):

    docker run --rm -v ./wiki/examples:/ex hclust-worker:dev python /ex/h2_minimal_basis.py
"""

import math

import numpy as np

BOHR_TO_ANGSTROM = 0.529177210903
HARTREE_TO_EV = 27.211386245988

# STO-3G: three Gaussians fitted to a Slater 1s function with exponent 1
# (Hehre, Stewart & Pople 1969). Scaling the exponents by zeta**2 gives the
# fit for any other Slater exponent; zeta = 1.24 is the molecular value for H.
STO3G_ALPHA = np.array([0.109818, 0.405771, 2.22766])
STO3G_COEF = np.array([0.444635, 0.535328, 0.154329])
ZETA_H = 1.24


def basis_function(center):
    """One contracted 1s function: (exponents, normalized coefficients, center)."""
    alpha = STO3G_ALPHA * ZETA_H**2
    coef = STO3G_COEF * (2 * alpha / math.pi) ** 0.75
    return alpha, coef, np.asarray(center, dtype=float)


def boys0(t):
    """Boys function F0(t), which appears in every Coulomb integral over Gaussians."""
    if t < 1e-10:
        return 1.0 - t / 3.0
    return 0.5 * math.sqrt(math.pi / t) * math.erf(math.sqrt(t))


def _pairs(f, g):
    """Loop over primitive pairs of two contracted functions."""
    (alpha_a, coef_a, A), (alpha_b, coef_b, B) = f, g
    for a, ca in zip(alpha_a, coef_a):
        for b, cb in zip(alpha_b, coef_b):
            p = a + b
            mu = a * b / p
            P = (a * A + b * B) / p
            yield ca * cb, p, mu, P, np.sum((A - B) ** 2)


def overlap(f, g):
    return sum(c * (math.pi / p) ** 1.5 * math.exp(-mu * ab2) for c, p, mu, _, ab2 in _pairs(f, g))


def kinetic(f, g):
    return sum(
        c * mu * (3 - 2 * mu * ab2) * (math.pi / p) ** 1.5 * math.exp(-mu * ab2)
        for c, p, mu, _, ab2 in _pairs(f, g)
    )


def nuclear(f, g, C, Z=1.0):
    """Attraction of the charge distribution f*g to a nucleus of charge Z at C."""
    return sum(
        -c * 2 * math.pi / p * Z * math.exp(-mu * ab2) * boys0(p * np.sum((P - C) ** 2))
        for c, p, mu, P, ab2 in _pairs(f, g)
    )


def repulsion(f, g, h, k):
    """Two-electron integral (fg|hk) in chemists' notation."""
    total = 0.0
    for c1, p, mu, P, ab2 in _pairs(f, g):
        for c2, q, nu, Q, cd2 in _pairs(h, k):
            total += (
                c1 * c2 * 2 * math.pi**2.5 / (p * q * math.sqrt(p + q))
                * math.exp(-mu * ab2 - nu * cd2)
                * boys0(p * q / (p + q) * np.sum((P - Q) ** 2))
            )
    return total


def integrals(R):
    """All integrals for H2 at bond length R (bohr), atoms on the z axis."""
    nuclei = [np.zeros(3), np.array([0.0, 0.0, R])]
    basis = [basis_function(c) for c in nuclei]
    n = len(basis)
    S = np.array([[overlap(f, g) for g in basis] for f in basis])
    T = np.array([[kinetic(f, g) for g in basis] for f in basis])
    V = np.array([[sum(nuclear(f, g, C) for C in nuclei) for g in basis] for f in basis])
    eri = np.zeros((n, n, n, n))
    for i, j, k, l in np.ndindex(eri.shape):
        eri[i, j, k, l] = repulsion(basis[i], basis[j], basis[k], basis[l])
    return S, T + V, eri, 1.0 / R


# --8<-- [start:rhf]
def rhf(S, h, eri, n_occ=1, max_iter=100, tol=1e-10, verbose=False):
    """Restricted Hartree-Fock: solve F C = S C eps until F stops changing."""
    s, U = np.linalg.eigh(S)
    X = U @ np.diag(s**-0.5) @ U.T  # symmetric orthogonalization, X^T S X = 1
    P = np.zeros_like(h)  # zero density: the first Fock matrix is just h ("core guess")
    E_old = 0.0
    for it in range(1, max_iter + 1):
        J = np.einsum("ijkl,kl->ij", eri, P)  # Coulomb: repulsion from the mean density
        K = np.einsum("ikjl,kl->ij", eri, P)  # exchange: from antisymmetry of the wavefunction
        F = h + J - 0.5 * K
        E = 0.5 * np.sum(P * (h + F))
        eps, Cp = np.linalg.eigh(X.T @ F @ X)
        C = X @ Cp
        P_new = 2 * C[:, :n_occ] @ C[:, :n_occ].T
        if verbose:
            print(f"  iter {it:2d}  E_elec = {E:.10f}")
        if abs(E - E_old) < tol and np.max(np.abs(P_new - P)) < tol**0.5:
            return E, eps, C
        P, E_old = P_new, E
    raise RuntimeError("SCF did not converge")

# --8<-- [end:rhf]


def fci(h, eri, C):
    """Exact correlation energy in this basis: mix |sigma_g^2> with |sigma_u^2>."""
    h_mo = C.T @ h @ C
    g = np.einsum("pi,qj,rk,sl,pqrs->ijkl", C, C, C, C, eri)
    H = np.array([
        [2 * h_mo[0, 0] + g[0, 0, 0, 0], g[0, 1, 0, 1]],
        [g[0, 1, 0, 1], 2 * h_mo[1, 1] + g[1, 1, 1, 1]],
    ])
    return np.linalg.eigvalsh(H)[0]


def hydrogen_atom_energy():
    """Energy of one H atom in the same basis (one electron: no SCF needed)."""
    f = basis_function(np.zeros(3))
    return kinetic(f, f) + nuclear(f, f, np.zeros(3))


def energies(R):
    """Total energies (hartree) at bond length R (bohr): RHF and full CI."""
    S, h, eri, E_nn = integrals(R)
    E_hf, _, C = rhf(S, h, eri)
    return E_hf + E_nn, fci(h, eri, C) + E_nn


def scan(R_values):
    return [(R, *energies(R)) for R in R_values]


def main():
    R = 1.4
    print(f"H2 / STO-3G at R = {R} bohr ({R * BOHR_TO_ANGSTROM:.3f} Å)\n")
    S, h, eri, E_nn = integrals(R)
    print(f"overlap S12 = {S[0, 1]:.4f}")
    E_hf, eps, C = rhf(S, h, eri, verbose=True)
    E_fci = fci(h, eri, C)
    print(f"\norbital energies   {eps[0]:.4f} (sigma_g, occupied)  {eps[1]:.4f} (sigma_u, empty)")
    print(f"nuclear repulsion  {E_nn:.4f}")
    print(f"E(RHF)             {E_hf + E_nn:.4f}")
    print(f"E(FCI)             {E_fci + E_nn:.4f}")
    print(f"correlation energy {E_fci - E_hf:.4f}  ({(E_fci - E_hf) * HARTREE_TO_EV:.2f} eV)")

    E_H = hydrogen_atom_energy()
    print(f"\nE(H atom)          {E_H:.4f}   so 2 E(H) = {2 * E_H:.4f}")

    print("\nPotential energy curve")
    print(" R/bohr   R/Å     E(RHF)     E(FCI)")
    for R, e_hf, e_fci in scan([0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0]):
        print(f"{R:6.2f}  {R * BOHR_TO_ANGSTROM:6.3f}  {e_hf:9.4f}  {e_fci:9.4f}")

    print("\nMinimum and dissociation energy D_e = 2 E(H) - E(min)")
    fine = scan(np.arange(1.20, 1.60, 0.005))
    for name, col in [("RHF", 1), ("FCI", 2)]:
        R_min, *e = min(fine, key=lambda row: row[col])
        D_e = 2 * E_H - e[col - 1]
        print(f"{name}: R_e = {R_min * BOHR_TO_ANGSTROM:.3f} Å   D_e = {D_e * HARTREE_TO_EV:.2f} eV")


if __name__ == "__main__":
    main()
