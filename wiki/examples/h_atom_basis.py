"""The hydrogen atom in growing Gaussian basis sets: how the energy converges.

The exact energy is -0.5 hartree. A single Gaussian can't reproduce the cusp of the
1s orbital at the nucleus or its slow exponential tail, so more functions are
needed. Uses an "even-tempered" basis: exponents alpha_k = a * b**k.

Run:

    docker run --rm -v ./wiki/examples:/ex hclust-worker:dev python /ex/h_atom_basis.py
"""

import math

import numpy as np

ORIGIN = np.zeros(3)


def s_gaussian(alpha):
    """A normalized s Gaussian at the origin, in the format of h2_minimal_basis."""
    return np.array([alpha]), np.array([(2 * alpha / math.pi) ** 0.75]), ORIGIN


# --8<-- [start:solve]
def h_atom_energy(alphas):
    """Lowest eigenvalue of H C = S C E in the basis of s Gaussians with these exponents."""
    from h2_minimal_basis import kinetic, nuclear, overlap

    basis = [s_gaussian(a) for a in alphas]
    S = np.array([[overlap(f, g) for g in basis] for f in basis])
    H = np.array([[kinetic(f, g) + nuclear(f, g, ORIGIN) for g in basis] for f in basis])
    s, U = np.linalg.eigh(S)
    X = U @ np.diag(s**-0.5) @ U.T
    return np.linalg.eigvalsh(X.T @ H @ X)[0]
# --8<-- [end:solve]


def best_even_tempered(n):
    """Lowest energy over a grid of even-tempered series alpha_k = a * b**k, k < n."""
    grid_b = [1.0] if n == 1 else np.linspace(1.5, 8.0, 66)
    return min(
        (h_atom_energy(a * b ** np.arange(n)), a, b)
        for a in np.geomspace(0.01, 1.0, 81)
        for b in grid_b
    )


def main():
    print(" n   E (hartree)   error (eV)   exponents")
    for n in range(1, 7):
        e, a, b = best_even_tempered(n)
        exps = ", ".join(f"{x:.3g}" for x in a * b ** np.arange(n))
        print(f"{n:2d}   {e:.6f}      {(e + 0.5) * 27.211386:.4f}       {exps}")


if __name__ == "__main__":
    main()
