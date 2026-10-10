"""MP2, geometry optimization and the harmonic frequency of H2 in STO-3G.

Builds on h2_minimal_basis.py: the same integrals and SCF, then
  1. the MP2 correlation energy (one occupied and one virtual orbital),
  2. a Newton-Raphson search for the minimum, with numerical derivatives,
  3. the harmonic vibrational frequency from the curvature at the minimum.

Run:

    docker run --rm -v ./wiki/examples:/ex hclust-worker:dev python /ex/h2_mp2_opt_freq.py
"""

import math

import numpy as np

from h2_minimal_basis import BOHR_TO_ANGSTROM, energies, fci, integrals, rhf

AMU_TO_ME = 1822.888486  # atomic mass unit in electron masses
HARTREE_TO_CM = 219474.6314
MU_H2 = 1.00782503 / 2 * AMU_TO_ME  # reduced mass of H2 in electron masses


# --8<-- [start:mp2]
def mp2(eri, eps, C):
    """Second-order correlation energy: one double excitation, sigma_g^2 -> sigma_u^2."""
    g = np.einsum("pi,qj,rk,sl,pqrs->ijkl", C, C, C, C, eri)
    K = g[0, 1, 0, 1]  # (sigma_g sigma_u | sigma_g sigma_u)
    return K**2 / (2 * (eps[0] - eps[1]))
# --8<-- [end:mp2]


# --8<-- [start:newton]
def derivatives(f, R, h=1e-3):
    """First and second derivative by central differences."""
    e_minus, e0, e_plus = f(R - h), f(R), f(R + h)
    return (e_plus - e_minus) / (2 * h), (e_plus - 2 * e0 + e_minus) / h**2


def newton_minimize(f, R, tol=1e-6, max_step=None, verbose=True):
    """Newton-Raphson: model the curve as a parabola, jump to its bottom, repeat.

    With max_step (a trust radius), a step is never longer than max_step, and where
    the curve bends the wrong way (k < 0, no bottom to jump to) it goes downhill instead.
    """
    for step in range(1, 21):
        g, k = derivatives(f, R)
        if verbose:
            print(f"  step {step}: R = {R:.4f} bohr  E = {f(R):.6f}  gradient = {g:+.1e}  curvature = {k:+.3f}")
        if abs(g) < tol:
            return R, k
        dR = -g / k
        if max_step is not None:
            if k <= 0:
                dR = -math.copysign(max_step, g)
            dR = max(-max_step, min(max_step, dR))
        R += dR
        if R <= 0:
            raise RuntimeError(f"step {step} jumped to R = {R:.2f} bohr: not a molecule any more")
    raise RuntimeError("no convergence")
# --8<-- [end:newton]


def harmonic_wavenumber(k):
    """omega = sqrt(k / mu) in atomic units, converted to cm^-1."""
    return math.sqrt(k / MU_H2) * HARTREE_TO_CM


def main():
    R = 1.4
    S, h, eri, E_nn = integrals(R)
    E_hf, eps, C = rhf(S, h, eri)
    E_mp2 = mp2(eri, eps, C)
    E_fci = fci(h, eri, C) - E_hf
    print(f"Correlation energy at R = {R} bohr: MP2 {E_mp2:.4f}, FCI {E_fci:.4f} hartree "
          f"(MP2 recovers {E_mp2 / E_fci:.0%})\n")

    def e_rhf(r):
        return energies(r)[0]

    print("RHF, plain Newton from R = 2.0 bohr:")
    try:
        newton_minimize(e_rhf, 2.0)
    except RuntimeError as err:
        print(f"  failed: {err}\n")

    for name, col in [("RHF", 0), ("FCI", 1)]:
        print(f"{name}, Newton with a 0.3 bohr trust radius from R = 2.0 bohr:")
        R_e, k = newton_minimize(lambda r: energies(r)[col], 2.0, max_step=0.3)
        print(f"  minimum R_e = {R_e * BOHR_TO_ANGSTROM:.4f} Å, force constant k = {k:.4f} hartree/bohr²,"
              f" harmonic frequency = {harmonic_wavenumber(k):.0f} cm⁻¹\n")


if __name__ == "__main__":
    main()
