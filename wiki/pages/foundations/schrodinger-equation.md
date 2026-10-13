# Schrödinger equation

!!! info "Prerequisites"
    None.

Every number this project computes is an approximate solution of one
equation. The Schrödinger equation says which energies a system of electrons
and nuclei can have, and what the electrons are doing in each of them. It
can be solved exactly only for one-electron systems such as the H atom and
[H₂⁺](app:s/2/1/2); every method in this wiki is a different way to approximate it for
everything else.

## Idea

### Wavefunction and energy

In quantum mechanics a particle has no definite position. It is described by
a **wavefunction** $\Psi$, and $|\Psi|^2$ is the probability of finding it at
a given place. For a molecule, $\Psi$ depends on the positions of *all* its
electrons and nuclei at once.

For a system that isn't changing in time, the allowed states satisfy the
**time-independent Schrödinger equation**:

$$
\hat{H}\,\Psi = E\,\Psi
$$

$\hat{H}$, the **Hamiltonian**, is the operator for the total energy. The
equation is an eigenvalue problem: only special wavefunctions (the
eigenfunctions) solve it, each with one definite energy $E$. The lowest is the
**ground state**; the rest are **excited states**.

### The molecular Hamiltonian

Label the electrons $i, j, \ldots$ and the nuclei $A, B, \ldots$. Electron $i$ is
at position $\mathbf{r}_i$, and nucleus $A$, with charge $Z_A$ and mass $M_A$, is
at $\mathbf{R}_A$ (throughout this wiki, lowercase $\mathbf{r}$ is for electrons
and uppercase $\mathbf{R}$ for nuclei). The potential energy depends only on
the distances between the particles:

- $r_{iA} = |\mathbf{r}_i - \mathbf{R}_A|$, between electron $i$ and nucleus $A$,
- $r_{ij} = |\mathbf{r}_i - \mathbf{r}_j|$, between two electrons,
- $R_{AB} = |\mathbf{R}_A - \mathbf{R}_B|$, between two nuclei.

$\nabla_i^2$ and $\nabla_A^2$ take second derivatives with respect to the
coordinates of electron $i$ and of nucleus $A$. In [atomic units](units.md):

$$
\hat{H} =
-\sum_i \frac{1}{2}\nabla_i^2
-\sum_A \frac{1}{2M_A}\nabla_A^2
-\sum_{i,A} \frac{Z_A}{r_{iA}}
+\sum_{i<j} \frac{1}{r_{ij}}
+\sum_{A<B} \frac{Z_A Z_B}{R_{AB}}
$$

The five terms, in order: kinetic energy of the electrons, kinetic energy of
the nuclei, electron–nucleus attraction, electron–electron repulsion, and
nucleus–nucleus repulsion. The $\nabla^2$ terms measure how sharply the
wavefunction curves: a wavefunction squeezed into a small region curves
sharply and so has high kinetic energy. That is why electrons don't fall
into the nucleus.

That's the whole of chemistry, with no adjustable parameters (relativity and
magnetic effects aside, which are negligible for hydrogen). The difficulty is
purely mathematical: the $1/r_{ij}$ term couples every electron to every
other one, so the equation doesn't split into one-electron pieces.

### What can be solved exactly

| System | Electrons | Exact? |
|---|---|---|
| H atom | 1 | Yes, on paper: $E_n = -\frac{1}{2n^2}$ hartree, so $E_1 = -0.5$ hartree = −13.6 eV |
| [H₂⁺](app:s/2/1/2) (nuclei held fixed) | 1 | Yes, numerically to any precision |
| [H₂](app:s/2/0/1), [H⁻](app:s/1/-1/1), [H₃⁺](app:s/3/1/1), … | ≥ 2 | No. Only approximations, some of them very good |

### The variational principle

The most useful fact for approximating: **any** trial wavefunction gives an
energy at or above the true ground-state energy,

$$
E_\text{trial} = \frac{\langle\Psi_\text{trial}|\hat{H}|\Psi_\text{trial}\rangle}{\langle\Psi_\text{trial}|\Psi_\text{trial}\rangle} \;\geq\; E_0
$$

So a lower energy means a better wavefunction, and you can improve a guess
by adjusting it to minimize the energy. [Hartree–Fock](../methods/hartree-fock.md),
full CI and every [basis set](../methods/basis-sets.md) rely on this.
(MP2, coupled cluster and DFT are *not* variational in this sense; their
energies can fall below the exact one.)

## Example

The hydrogen atom with one Gaussian function $e^{-\alpha r^2}$ as the trial
wavefunction. The best exponent, $\alpha = 0.283$, gives −0.4244 hartree:
above the exact −0.5, as the variational principle demands, and 2.06 eV too
high. Adding functions can only lower the energy, and six of them bring it
within 0.004 eV ([`h_atom_basis.py`](../methods/basis-sets.md#example-the-hydrogen-atom)).

## Where this appears in [h_clusters](https://github.com/skachano/h_clusters)

- Each species H_m^n has $N = m - n$ electrons
  (`worker/src/hclust/species.py`), from 0 (H⁺) to 11 ([H₁₀⁻](app:s/10/-1/2)).
- H⁺ has no electrons, so there is nothing to solve: its energy is
  defined as 0 (`doc/Plan.md` §1.1), and `engines/orca.py` refuses to run it.
- The H atom is the one case with a known exact answer, so it measures each
  level's error directly: CCSD(T)/aug-cc-pVTZ (L2) gives −0.49982 hartree
  (0.005 eV off), ωB97X-D4 (L1) gives −0.50503 (0.14 eV *below* exact,
  possible because DFT isn't variational).

## References

- A. Szabo, N. S. Ostlund, *Modern Quantum Chemistry*, chapters 1–2
  (mathematical background, the electronic problem, the variational principle).
- D. J. Griffiths, *Introduction to Quantum Mechanics*: the hydrogen atom.
