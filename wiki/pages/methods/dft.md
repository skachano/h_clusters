# Density functional theory

!!! info "Prerequisites"
    [Hartree–Fock](hartree-fock.md)

Density functional theory (DFT) is the workhorse of computational chemistry:
nearly as cheap as [Hartree–Fock](hartree-fock.md), but it includes electron
correlation, so it is usually far more accurate. The catch is that its
central ingredient, the **exchange–correlation functional**, is unknown and
has to be approximated. Hundreds of approximations exist, and each has
blind spots. Hydrogen clusters happen to hit several of them.

## Idea

### The density is enough

A wavefunction for $N$ electrons depends on $3N$ coordinates. The electron
**density** $\rho(\mathbf{r})$, the number of electrons per volume at each
point, depends on just 3. Hohenberg and Kohn proved (1964) that the
ground-state density alone determines everything about the ground state,
including its energy. So in principle there is a **functional** (a function
of a function) $E[\rho]$ that gives the exact energy from the density.

### Kohn–Sham: orbitals back in

Nobody knows how to write the kinetic energy as a functional of the density
accurately. Kohn and Sham (1965) sidestepped this by inventing a system of
*non-interacting* electrons, described by orbitals $\psi_i$, that has the same
density as the real one. The energy is then split into parts that are known
exactly, plus one leftover:

$$
E[\rho] = T_s[\rho] + \int v_\text{nuc}(\mathbf{r})\rho(\mathbf{r})\,d\mathbf{r}
+ J[\rho] + E_\text{xc}[\rho]
$$

- $T_s$: the kinetic energy of the non-interacting electrons (from the orbitals).
- The nuclear attraction and $J$ (the classical Coulomb repulsion of the
  density with itself) are exact.
- $E_\text{xc}$, the **exchange–correlation energy**: everything else. Exchange,
  correlation, and the kinetic energy that $T_s$ misses.

Minimizing gives orbital equations that look just like Hartree–Fock's, with
the exchange operator replaced by the exchange–correlation potential
$v_\text{xc} = \delta E_\text{xc}/\delta\rho$. They are solved with the same
[SCF loop](hartree-fock.md#the-scf-loop).

### Approximating $E_\text{xc}$

If $E_\text{xc}$ were known, DFT would be exact. It isn't, and the
approximations form a hierarchy ("Jacob's ladder") where each rung uses more
information:

| Rung | Uses | Examples |
|---|---|---|
| LDA | $\rho$ | SVWN |
| GGA | $\rho$, $\nabla\rho$ | PBE, BLYP |
| meta-GGA | + kinetic energy density | **r²SCAN** (L0) |
| hybrid | + a fraction of exact (HF) exchange | **B3LYP** (L1b, 20 % HF exchange) |
| range-separated hybrid | HF exchange growing to 100 % at long range | **ωB97X-D4** (L1), **ωB97M-V** (L1V) |

Hybrids mix in Hartree–Fock exchange because HF has exactly the property
that the simpler functionals lack: no self-interaction.

**Dispersion** (the weak attraction between neutral molecules) comes from
correlated electron motion at long range, which standard functionals
don't capture. It is added on: an empirical correction (D3, D4: the "-D4"
in ωB97X-D4) or a non-local correlation functional (VV10: the "-V" in
ωB97M-V). See [missing dispersion](../pitfalls/dispersion.md).

### What DFT gets wrong

Approximate functionals let an electron feel a little of its own charge: the
**self-interaction error**. It makes DFT favour spread-out (delocalized)
electrons. Hydrogen clusters, with few electrons and charged species, show it
clearly ([self-interaction error](../pitfalls/self-interaction-error.md)):

| Property | r²SCAN-3c (L0) | ωB97X-D4 (L1) | Reference |
|---|---|---|---|
| [H₂⁺](app:s/2/1/2) bond length | 1.083 Å | 1.105 Å | 1.058 Å (HF, exact for one electron) |
| [H₂⁺](app:s/2/1/2) frequency | — | 2074 cm⁻¹ | 2322 cm⁻¹ |
| Electron affinity of H | −1.57 eV (H⁻ unbound) | 0.20 eV | 0.73 eV (CCSD(T)), 0.754 exact |
| [H₅⁺](app:s/5/1/1) shape | D₂d, shared proton | D₂d, shared proton | C₂ᵥ H₃⁺·H₂ (MP2, CCSD(T)) |

(The r²SCAN-3c electron affinity also suffers from its small basis set, which
has no diffuse functions; see [diffuse functions](../pitfalls/diffuse-functions.md).)

DFT is also not [variational](../foundations/schrodinger-equation.md#the-variational-principle)
with respect to the exact energy: ωB97X-D4 puts the H atom at −0.50503
hartree, below the exact −0.5.

## Cost

Like HF, formally $N^3$–$N^4$ in the number of basis functions, with tricks
([RI](resolution-of-identity.md)) bringing it down. For [H₁₀](app:s/10/0/1) in the pilot run,
an r²SCAN-3c gradient took 3 s and an ωB97X-D4 gradient 48 s on one core.

## Where this appears in h_clusters

- **L0, r²SCAN-3c**: a "composite" method (Grimme, 2021): r²SCAN with a
  purpose-built triple-ζ basis, D4 dispersion and a basis-set correction,
  tuned for low cost. It pre-optimizes every candidate structure.
- **L1, ωB97X-D4/def2-TZVPPD**: the main DFT geometry level. Chosen over
  ωB97M-V because it has analytic second derivatives: 16 min instead of
  2 h for an [H₁₀](app:s/10/0/1) optimization plus frequencies (`doc/Plan.md`, Phase 4).
- **L1b, B3LYP** (no dispersion): kept for teaching, to show the failures.
- Open-shell states run as unrestricted Kohn–Sham (`UKS`, `engines/orca.py`).
- DFT's [H₅⁺](app:s/5/1/1) shape is the reason the MP2 geometry level L1M exists
  (comment on L1M in `worker/src/hclust/levels.py`).

## References

- W. Koch, M. C. Holthausen, *A Chemist's Guide to Density Functional
  Theory*, 2nd ed. (Wiley, 2001).
- F. Jensen, *Introduction to Computational Chemistry*, 3rd ed., chapter on
  density functional methods.
- S. Grimme et al., *J. Chem. Phys.* **154**, 064103 (2021): r²SCAN-3c.
- A. J. Cohen, P. Mori-Sánchez, W. Yang, *Chem. Rev.* **112**, 289 (2012):
  challenges for DFT, including delocalization error.
