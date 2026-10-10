"""H- with and without diffuse functions: exact (full CI) energies in s-type Gaussians.

H- has two electrons, so full CI is small: expand the two-electron wavefunction
in products of basis functions, Psi(1,2) = sum_ij C_ij phi_i(1) phi_j(2), and
diagonalize. Only s functions are used, which captures part of the correlation
(the "radial" part); the s-only limit of the electron affinity is about 0.39 eV,
against the exact 0.754 eV.

Run:

    docker run --rm -v ./wiki/examples:/ex hclust-worker:dev python /ex/h_minus_diffuse.py
"""

import numpy as np

from h2_minimal_basis import HARTREE_TO_EV, kinetic, nuclear, overlap, repulsion
from h_atom_basis import ORIGIN, s_gaussian


# --8<-- [start:fci]
def atom_integrals(alphas):
    """One- and two-electron integrals in an orthonormalized basis of s Gaussians."""
    basis = [s_gaussian(a) for a in alphas]
    S = np.array([[overlap(f, g) for g in basis] for f in basis])
    h = np.array([[kinetic(f, g) + nuclear(f, g, ORIGIN) for g in basis] for f in basis])
    n = len(basis)
    eri = np.zeros((n, n, n, n))
    for i, j, k, l in np.ndindex(eri.shape):
        eri[i, j, k, l] = repulsion(basis[i], basis[j], basis[k], basis[l])
    s, U = np.linalg.eigh(S)
    keep = s > 1e-8  # drop near-linear dependencies
    X = U[:, keep] / np.sqrt(s[keep])
    return X.T @ h @ X, np.einsum("pi,qj,rk,sl,pqrs->ijkl", X, X, X, X, eri)


def energies(alphas):
    """E(H) and the exact two-electron E(H-) in this basis."""
    h, eri = atom_integrals(alphas)
    n = len(h)
    one = np.eye(n)
    # <ij|H|kl> for the product phi_i(1) phi_j(2): h on electron 1, h on electron 2, repulsion.
    H2 = (np.einsum("ik,jl->ijkl", h, one) + np.einsum("ik,jl->ijkl", one, h)
          + np.einsum("ikjl->ijkl", eri)).reshape(n * n, n * n)
    return np.linalg.eigvalsh(h)[0], np.linalg.eigvalsh(H2)[0]
# --8<-- [end:fci]


BASES = {
    "fitted to the H atom": [0.133, 0.547, 2.24, 9.19],
    "+ 1 diffuse": [0.04, 0.133, 0.547, 2.24, 9.19],
    "+ 2 diffuse": [0.012, 0.04, 0.133, 0.547, 2.24, 9.19],
    "+ 3 diffuse": [0.0036, 0.012, 0.04, 0.133, 0.547, 2.24, 9.19],
}


def main():
    print(f"{'basis':<22}{'E(H)':>10}{'E(H-)':>10}{'EA (eV)':>10}")
    for name, alphas in BASES.items():
        e_h, e_hm = energies(alphas)
        print(f"{name:<22}{e_h:10.5f}{e_hm:10.5f}{(e_h - e_hm) * HARTREE_TO_EV:10.3f}")


if __name__ == "__main__":
    main()
