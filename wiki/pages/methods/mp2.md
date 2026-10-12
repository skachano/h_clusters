# MP2

!!! info "Prerequisites"
    [Hartree–Fock](hartree-fock.md)

Second-order Møller–Plesset perturbation theory (MP2) is the cheapest way to
add electron correlation to a [Hartree–Fock](hartree-fock.md) calculation.
It treats the difference between real electron repulsion and HF's averaged
version as a small perturbation, and computes its leading correction. MP2
has no self-interaction error and includes dispersion, which makes it this
project's second geometry level (L1M) next to DFT.

## Idea

### Perturbation theory

When a problem is close to one you can solve, write

$$
\hat{H} = \hat{H}_0 + \lambda\hat{V}
$$

with $\hat{H}_0$ solvable and $\hat{V}$ small, and expand the energy in powers
of $\lambda$: $E = E^{(0)} + E^{(1)} + E^{(2)} + \ldots$

Møller and Plesset (1934) chose $\hat{H}_0$ = the sum of
[Fock operators](hartree-fock.md#step-2-the-mean-field), whose solution is the
HF determinant. $\hat{V}$ is then the part of the electron repulsion that the
mean field misses. The first two terms just add up to the HF energy, so the
first correction is second order: that's MP2.

### The MP2 energy

$E^{(2)}$ sums over every way of moving two electrons from occupied orbitals
$i, j$ into empty (virtual) orbitals $a, b$:

$$
E^{(2)} = \sum_{ij}^\text{occ}\sum_{ab}^\text{virt}
\frac{(ia|jb)\big[2(ia|jb) - (ib|ja)\big]}{\varepsilon_i + \varepsilon_j - \varepsilon_a - \varepsilon_b}
$$

(closed shell, spatial orbitals). Each term is a double excitation weighted
by how strongly it couples to the HF state (the integrals in the numerator)
and how much energy it costs (the orbital-energy gap in the denominator).
The denominator is negative, so $E^{(2)}$ is always negative: correlation
lowers the energy.

## Example: H₂ in STO-3G

With one occupied orbital ($\sigma_g$) and one virtual ($\sigma_u$), the sum
has a single term:

```python
--8<-- "h2_mp2_opt_freq.py:mp2"
```

At R = 1.4 bohr ([`h2_mp2_opt_freq.py`](#the-code)):

```text
Correlation energy at R = 1.4 bohr: MP2 -0.0132, FCI -0.0206 hartree (MP2 recovers 64%)
```

The MP2 value matches Szabo & Ostlund. In this tiny basis MP2 gets two thirds
of the exact correlation energy; in large basis sets and for molecules near
their equilibrium geometry it typically gets roughly 80–90 %.

### The code

??? example "Run it and read the full source"
    ```sh
    docker run --rm -v ./wiki/examples:/ex hclust-worker:dev python /ex/h2_mp2_opt_freq.py
    ```
    ```python
    --8<-- "h2_mp2_opt_freq.py"
    ```

## Strengths and weaknesses

- **No self-interaction error.** MP2 starts from HF orbitals, which are free
  of it. This is why MP2 keeps [H₅⁺](app:s/5/1/1)'s C₂ᵥ [H₃⁺·H₂](app:s/5/1/1) structure, which every DFT
  level in the project turns into a shared-proton D₂d structure.
- **Includes dispersion.** The double excitations describe correlated
  fluctuations of electrons on two molecules, which is what dispersion is.
  MP2 tends to overestimate it somewhat.
- **Needs a large basis.** Correlation energy converges slowly with basis
  size. MP2/aug-cc-p**VDZ** already collapses [H₅⁺](app:s/5/1/1) to D₂d; triple-ζ keeps
  C₂ᵥ (`doc/Plan.md`, Phase 4).
- **Fails for stretched bonds and near-degeneracies.** When the gap
  $\varepsilon_a + \varepsilon_b - \varepsilon_i - \varepsilon_j$ becomes small,
  the terms blow up. Perturbation theory assumes HF is a good start, which it
  isn't for [bond breaking](hartree-fock.md#bond-breaking).
- **Open shells:** unrestricted MP2 (UMP2) inherits any
  [spin contamination](../pitfalls/spin-contamination.md) of the UHF reference.
- **Cost:** grows as $N^5$ with the number of basis functions; much cheaper
  with [RI](resolution-of-identity.md).

How MP2 compares on the project's [H₂](app:s/2/0/1) (aug-cc-pVTZ basis):

| | MP2 (L1M) | CCSD(T) (L2) | Exact |
|---|---|---|---|
| r_e | 0.737 Å | — | 0.741 Å |
| Harmonic frequency | 4517 cm⁻¹ | — | 4401 cm⁻¹ |
| Energy | −1.16502 hartree | −1.17263 | −1.17447 |

## Where this appears in h_clusters

- **L1M** in `worker/src/hclust/levels.py`: RI-MP2 with RI-JK and the
  aug-cc-pVTZ basis. It optimizes every promoted structure (stage `mp2`);
  the best three per state get numerical frequencies (`mp2_freq`), because
  ORCA 6.1 has no analytic RI-MP2 Hessian.
- One-electron species (H, [H₂⁺](app:s/2/1/2)) have nothing to correlate: L1M falls back to
  plain HF for them (`correlated=True` in `levels.py`).
- Open-shell states run on a UHF reference.

## References

- A. Szabo, N. S. Ostlund, *Modern Quantum Chemistry*, chapter 6
  (many-body perturbation theory), including the [H₂](app:s/2/0/1) example.
- C. Møller, M. S. Plesset, *Phys. Rev.* **46**, 618 (1934).
- F. Jensen, *Introduction to Computational Chemistry*, 3rd ed., chapter on
  electron correlation methods.
