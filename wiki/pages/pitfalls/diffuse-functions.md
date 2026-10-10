# Missing diffuse functions

!!! info "Prerequisites"
    [Basis sets](../methods/basis-sets.md)

The extra electron of an anion is held weakly and spreads far from the
nuclei. A [basis set](../methods/basis-sets.md) built for neutral molecules
has no functions that reach that far, so the calculation squeezes the
electron in, which costs energy. The anion comes out too high, the electron
affinity too small, often negative. The fix is **diffuse functions**: wide
basis functions with small exponents.

## Idea

A Gaussian $e^{-\alpha r^2}$ with exponent $\alpha$ has a size of roughly
$1/\sqrt{\alpha}$ bohr. Standard basis sets are fitted to neutral atoms;
their smallest exponent on hydrogen is around 0.1, a size of about 3 bohr.
A loosely bound electron, though, decays as $e^{-\kappa r}$ with
$\kappa = \sqrt{2\,\text{EA}}$ in atomic units. For H⁻, with EA = 0.0277 hartree,
$\kappa = 0.24$: the electron extends to about 4 bohr and beyond, well past
what the basis can describe.

Since the method is [variational](../foundations/schrodinger-equation.md#the-variational-principle)
in the basis, a cramped electron simply has a higher energy. Adding
functions with smaller exponents (the **aug-** or **-D** in a basis name)
gives it room.

## Example: H⁻ with and without diffuse functions

[`h_minus_diffuse.py`](#the-code) computes H and H⁻ exactly (full CI) in
s-type Gaussians. The start is the 4-function basis optimized for the
neutral H atom on the [basis sets](../methods/basis-sets.md#example-the-hydrogen-atom)
page; then diffuse functions with ever smaller exponents are added:

```text
basis                       E(H)     E(H-)   EA (eV)
fitted to the H atom    -0.49874  -0.46001    -1.054
+ 1 diffuse             -0.49879  -0.50856     0.266
+ 2 diffuse             -0.49881  -0.51325     0.393
+ 3 diffuse             -0.49881  -0.51337     0.396
```

- The neutral atom barely notices the extra functions (−0.49874 →
  −0.49881): its electron doesn't go that far.
- **H⁻ without diffuse functions is unbound by 1.05 eV**, a qualitative error.
  One diffuse function (α = 0.04) is enough to bind it; two converge the
  result.
- The converged 0.39 eV is the limit for s functions only. The real 0.754 eV
  needs p and d functions too, to describe the two electrons avoiding each other
  around the nucleus (angular correlation).

```python
--8<-- "h_minus_diffuse.py:fci"
```

### The code

??? example "Run it and read the full source"
    ```sh
    docker run --rm -v ./wiki/examples:/ex hclust-worker:dev python /ex/h_minus_diffuse.py
    ```
    ```python
    --8<-- "h_minus_diffuse.py"
    ```

## In the project

r²SCAN-3c (L0) comes with its own basis without diffuse functions. Its
electron affinity of H is −1.57 eV, nearly the same failure as the toy model
(self-interaction adds to it). The L1, L1M and L2 bases all have diffuse
functions, and their EAs are positive (0.20, 0.48 and 0.73 eV).

## Costs of diffuse functions

- **Linear dependence.** Diffuse functions on neighbouring atoms overlap almost
  completely, which makes the overlap matrix nearly singular and SCF
  convergence harder. Programs drop near-dependent combinations (the toy code
  does too: `keep = s > 1e-8`).
- **Cost.** More functions; aug-cc-pVTZ has 23 functions per H against 14 in
  cc-pVTZ.
- **False binding.** Very diffuse functions can hold an electron that
  shouldn't be bound at all ([unbound anions](unbound-anions.md)).

## Where this appears in h_clusters

- The plan makes diffuse functions mandatory and uses them for **all**
  species, not just anions, so that every charge state is treated alike
  (`doc/Plan.md` §2): def2-TZVPP**D** (L1), **aug**-cc-pVTZ (L1M, L2).
- L0's lack of diffuse functions is acceptable only because L0 is a
  screening level; anion energies are never taken from it.

## References

- R. A. Kendall, T. H. Dunning Jr., R. J. Harrison, *J. Chem. Phys.* **96**,
  6796 (1992): the augmented (aug-) correlation-consistent basis sets.
- J. Simons, *J. Phys. Chem. A* **112**, 6401 (2008): molecular anions.
