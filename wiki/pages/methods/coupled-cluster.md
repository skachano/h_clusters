# Coupled cluster

!!! info "Prerequisites"
    [Hartree–Fock](hartree-fock.md), [MP2](mp2.md)

Coupled cluster (CC) theory is the most reliable routine method for
molecules: **CCSD(T)** is called the "gold standard" of quantum chemistry.
With a large enough basis set it typically gets relative energies within
about 1 kcal/mol. It is also expensive, which is why this project uses it
only for single-point energies on geometries found by cheaper methods.

## Idea

### Excitations, all at once

Full CI writes the exact wavefunction as the HF determinant $\Phi_0$ plus
every possible excited determinant. That is exact but the number of
determinants explodes with system size. Coupled cluster writes the
wavefunction instead as

$$
\Psi_\text{CC} = e^{\hat{T}}\,\Phi_0, \qquad \hat{T} = \hat{T}_1 + \hat{T}_2 + \hat{T}_3 + \ldots
$$

$\hat{T}_1$ creates single excitations (one electron moved to a virtual
orbital), $\hat{T}_2$ doubles, and so on, each with coefficients
("amplitudes") to be solved for. The exponential is the key:

$$
e^{\hat{T}} = 1 + \hat{T} + \tfrac{1}{2}\hat{T}^2 + \ldots
$$

Truncating $\hat{T}$ at doubles (**CCSD**) still produces $\tfrac{1}{2}\hat{T}_2^2$:
products of two independent double excitations, i.e. quadruple excitations,
for free. Two electron pairs far apart correlate independently, and the
product describes exactly that. This makes CC **size-consistent**: the energy
of two molecules far apart equals the sum of their separate energies. Truncated
CI doesn't have this property, which is fatal for computing binding energies.

### CCSD(T)

Triple excitations matter for chemical accuracy but are expensive to include
fully. CCSD(T) adds them by perturbation theory, as a correction computed
once from the CCSD amplitudes. The parentheses mean "perturbative".

| Method | Cost (basis functions $N$) |
|---|---|
| HF, DFT | $N^3$–$N^4$ |
| MP2 | $N^5$ |
| CCSD | $N^6$ |
| CCSD(T) | $N^7$ |
| Full CI | exponential |

### Two electrons: exact

With two electrons there are no triple excitations, and CCSD is identical to
full CI. So the project's CCSD(T) energies of [H₂](app:s/2/0/1), [H₃⁺](app:s/3/1/1) and [H⁻](app:s/1/-1/1) are exact
*within the basis set*. Their remaining errors measure the basis alone:

| Quantity (CCSD(T)/aug-cc-pVTZ) | Computed | Exact | Error |
|---|---|---|---|
| E(H₂), hartree | −1.17263 | −1.17447 | 0.0018 (0.05 eV) |
| $D_e$(H₂) | 4.707 eV | 4.748 eV | 0.04 eV |
| $D_e$(H₃⁺ → H₂ + H⁺) | 4.602 eV | 4.609 eV | 0.007 eV |
| EA(H) | 0.728 eV | 0.754 eV | 0.03 eV |

Errors partly cancel in energy *differences*, which is why the H₃⁺ binding
energy is far more accurate than the total H₂ energy. Closing the remaining
gap needs bigger basis sets or extrapolation to the
[complete basis set limit](basis-sets.md#convergence-and-the-cbs-limit).

### Limits

CCSD(T) assumes the HF determinant is a good starting point (a
"single-reference" method). For strongly stretched bonds or near-degenerate
states, where several determinants matter equally, it degrades; multireference
methods are then needed. It is also not variational. The project runs CCSD(T) without analytic
gradients (`analytic_gradient=False` for L2 in `levels.py`), so a CCSD(T)
geometry optimization would need numerical gradients: the optional level L3
in the plan.

## Where this appears in h_clusters

- **L2**, `CCSD(T) aug-cc-pVTZ` in `worker/src/hclust/levels.py`: single
  points on the minima from both geometry branches (stages `dft_ref` and
  `mp2_ref`); the lower energy decides the structure.
- It settled the [H₅⁺](app:s/5/1/1) question: C₂ᵥ (MP2 geometry) is 0.13 kcal/mol below
  D₂d (DFT geometry), matching the literature.
- Cost from the pilot: CCSD(T)/aVTZ on [H₁₀](app:s/10/0/1) takes 13 min and **12 GB of
  scratch disk**, which is why the scheduler budgets disk space
  ([resource budgeting](../htc/resource-budgeting.md)).
- One-electron species fall back to HF; CCSD(T) aborts with one electron.

## References

- I. Shavitt, R. J. Bartlett, *Many-Body Methods in Chemistry and Physics*
  (Cambridge, 2009).
- T. D. Crawford, H. F. Schaefer III, *Rev. Comput. Chem.* **14**, 33 (2000):
  an introduction to coupled cluster theory.
- K. Raghavachari, G. W. Trucks, J. A. Pople, M. Head-Gordon,
  *Chem. Phys. Lett.* **157**, 479 (1989): CCSD(T).
