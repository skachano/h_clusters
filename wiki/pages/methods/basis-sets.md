# Basis sets

!!! info "Prerequisites"
    [Hartree–Fock](hartree-fock.md)

A computer can't store an orbital as an arbitrary 3D function. Every method
here expands orbitals in a finite set of fixed functions, the **basis set**,
and only the expansion coefficients are optimized. The basis is half of
every "level of theory" (method/basis, like CCSD(T)/aug-cc-pVTZ), and for
correlated methods it is often the larger source of error.

## Idea

### Why Gaussians

The exact orbitals of the H atom fall off as $e^{-\zeta r}$ (Slater
functions): a sharp cusp at the nucleus and a slow exponential tail. But
integrals over Slater functions on several atoms are very hard to compute.
Gaussians, $e^{-\alpha r^2}$, have the wrong shape (no cusp, a tail that dies
too fast), but the product of two Gaussians on different atoms is another
Gaussian between them, so every integral has a closed form. That's how the
toy code in [Hartree–Fock](hartree-fock.md#example-h2-from-scratch) computes all
its integrals in a few lines.

The fix for the wrong shape: use several Gaussians per orbital. A
**contracted** function is a fixed combination of Gaussians ("primitives")
fitted to look like a Slater function; STO-3G uses three.

### Building a better basis

| Ingredient | What it adds | Why |
|---|---|---|
| **Split valence** (double-ζ, triple-ζ, …) | 2, 3, … functions per valence orbital, of different sizes | Orbitals can expand or contract in a molecule |
| **Polarization** functions | Higher angular momentum: p and d on H | Orbitals can bend and shift off the nucleus, as in a bond |
| **Diffuse** functions | Very wide functions (small α) | Loosely bound electrons: anions, weak interactions ([diffuse functions](../pitfalls/diffuse-functions.md)) |

### Names

Two families appear in this project:

- **Dunning's correlation-consistent** sets, cc-pV**X**Z with X = D, T, Q, 5
  (double, triple, … ζ). They are designed so that correlation energy
  converges systematically as X grows. The **aug-** prefix adds one diffuse
  function of each angular momentum.
- **Karlsruhe** sets, def2-SVP, def2-TZVP, def2-TZVPP, … The final **D**
  in def2-TZVPP**D** adds diffuse functions.

Functions per hydrogen atom:

| Basis | Shells | Functions |
|---|---|---|
| STO-3G | 1s | 1 |
| cc-pVDZ | 2s1p | 5 |
| cc-pVTZ | 3s2p1d | 14 |
| aug-cc-pVTZ | 4s3p2d | 23 |

So an H₁₀ calculation in aug-cc-pVTZ has 230 basis functions. The real
triplet H₃⁺ job quoted on the [Hartree–Fock page](hartree-fock.md#the-same-thing-in-orca)
has 3 × 23 = 69.

## Example: the hydrogen atom

[`h_atom_basis.py`](#the-code) solves the H atom with $n$ s-type Gaussians
whose exponents form an even-tempered series $\alpha_k = a\,b^k$, with $a$
and $b$ optimized for each $n$. Because the method is
[variational](../foundations/schrodinger-equation.md#the-variational-principle),
every added function lowers the energy towards the exact −0.5 hartree:

```text
 n   E (hartree)   error (eV)   exponents
 1   -0.424412      2.0569       0.282
 2   -0.485808      0.3862       0.2, 1.32
 3   -0.495825      0.1136       0.158, 0.777, 3.81
 4   -0.498750      0.0340       0.133, 0.547, 2.24, 9.19
 5   -0.499562      0.0119       0.119, 0.428, 1.54, 5.55, 20
 6   -0.499839      0.0044       0.106, 0.35, 1.15, 3.81, 12.6, 41.5
```

The optimizer pushes exponents both ways: large ones (narrow functions) to
build up the cusp at the nucleus, small ones for the tail. Each extra
function buys about a factor of 3 in accuracy. The project's aug-cc-pVTZ
gives the H atom 0.005 eV too high, about as good as six optimized s functions.

### The code

??? example "Run it and read the full source"
    ```sh
    docker run --rm -v ./wiki/examples:/ex hclust-worker:dev python /ex/h_atom_basis.py
    ```
    ```python
    --8<-- "h_atom_basis.py"
    ```

## Convergence and the CBS limit

The HF energy converges quickly with basis size. The correlation energy does
not: it needs functions of ever higher angular momentum to describe how
electrons avoid each other at short range, and it converges roughly as
$X^{-3}$ for cc-pV$X$Z. A common remedy is to compute two basis sets (e.g.
TZ and QZ) and **extrapolate** to the complete basis set (CBS) limit.

Another basis artefact is the **basis set superposition error** (BSSE): in a
complex A·B, fragment A borrows B's basis functions to lower its own energy,
which makes binding look stronger. The counterpoise correction removes it by
computing each fragment in the full basis of the complex.

## Where this appears in h_clusters

- L1 uses def2-TZVPPD; L1M and L2 use aug-cc-pVTZ (with the matching
  auxiliary sets for [RI](resolution-of-identity.md)). r²SCAN-3c (L0) comes
  with its own small triple-ζ basis, without diffuse functions.
- Diffuse functions are used for *all* species, not only anions, so that every
  charge state is treated the same way (`doc/Plan.md` §2).
- Basis size changes answers: MP2 with aug-cc-pVDZ collapses H₅⁺ to D₂d,
  aug-cc-pVTZ keeps C₂ᵥ.
- A TZ → QZ → CBS convergence study is the optional level L4 (Plan, Phase 8).

## References

- F. Jensen, *Introduction to Computational Chemistry*, 3rd ed., chapter on
  basis sets.
- T. H. Dunning Jr., *J. Chem. Phys.* **90**, 1007 (1989): correlation-consistent
  basis sets.
- F. Weigend, R. Ahlrichs, *Phys. Chem. Chem. Phys.* **7**, 3297 (2005):
  the def2 basis sets.
- The Basis Set Exchange, basissetexchange.org: every standard basis set,
  downloadable.
