# Spin and multiplicity

!!! info "Prerequisites"
    [Schrödinger equation](schrodinger-equation.md)

Besides its position, each electron has a **spin**, which can point up or
down. How the spins of a molecule's electrons combine is labelled by the
**multiplicity**. Molecules with the same atoms and charge but different
multiplicity are different electronic states, with different energies,
shapes and stability. Every calculation in this project specifies one.

## Idea

### Electron spin

Spin is an intrinsic angular momentum of the electron, a quantum property
with no exact classical picture. Measured along any axis, it has only two
values: $+\tfrac{1}{2}$ ("up", α) or $-\tfrac{1}{2}$ ("down", β).

Spin matters for chemistry through the **Pauli principle**: no two electrons
may share all their quantum numbers. So one spatial orbital holds at most two
electrons, and they must have opposite spins. In the wavefunction this is
the antisymmetry built into the
[Slater determinant](../methods/hartree-fock.md#step-1-one-orbital-per-electron).

### Total spin and multiplicity

The spins of all electrons add up to a total spin $S$. Paired electrons
(one up, one down) cancel; each unpaired electron adds $\tfrac{1}{2}$. The
**multiplicity** is

$$
2S + 1 = (\text{number of unpaired electrons}) + 1
$$

| Unpaired electrons | $S$ | Multiplicity | Name |
|---|---|---|---|
| 0 | 0 | 1 | singlet |
| 1 | ½ | 2 | doublet |
| 2 | 1 | 3 | triplet |
| 3 | 3/2 | 4 | quartet |

The name comes from spectroscopy: a state with spin $S$ splits into
$2S + 1$ levels in a magnetic field.

### The parity rule

$N$ electrons can only pair up so far. An even $N$ can be fully paired (singlet) or
have 2, 4, … unpaired electrons; an odd $N$ always leaves at least one:

- $N$ even: multiplicity 1, 3, 5, …, $N + 1$
- $N$ odd: multiplicity 2, 4, 6, …, $N + 1$

So [H₃⁺](app:s/3/1/1) (2 electrons) can be a singlet or triplet, [H₃](app:s/3/0/2) (3 electrons) a doublet
or quartet.

### Why spin changes the energy

Spin has no energy term of its own in the Hamiltonian. It acts through the
Pauli principle: electrons with the same spin are kept apart (the exchange
effect), and parallel spins can't share an orbital, so they must occupy
higher ones. The two effects compete. In a chemical bond, pairing wins: two
electrons share the bonding orbital, which is only possible with opposite
spins. That's why most stable molecules, [H₂](app:s/2/0/1) included, are singlets.

Examples from the campaign (CCSD(T)/aug-cc-pVTZ):

| Species | Ground state | Higher-spin state |
|---|---|---|
| [H₂](app:s/2/0/1) | singlet, bound by 4.7 eV | triplet: no bond; the atoms fly apart in every optimization |
| [H₃⁺](app:s/3/1/1) | singlet triangle, −1.3417 hartree | triplet, −1.1155 hartree: 6.2 eV higher |
| [H⁻](app:s/1/-1/1) | singlet, bound | triplet: above H + a free electron, so not a bound state |

### ⟨S²⟩, a check on the wavefunction

An exact wavefunction with spin $S$ has $\langle \hat{S}^2\rangle = S(S+1)$:
0 for a singlet, 0.75 for a doublet, 2 for a triplet, 3.75 for a quartet.
Unrestricted methods can produce wavefunctions with the wrong value, which
signals a contaminated state ([spin contamination](../pitfalls/spin-contamination.md)).

## Where this appears in h_clusters

- `allowed_multiplicities()` in `worker/src/hclust/species.py` implements the
  parity rule. The baseline campaign keeps the two lowest multiplicities of
  each species (`n_mult: 2` in `campaigns/baseline.yaml`), giving 56 states.
- Every ORCA input states charge and multiplicity on the coordinate line,
  e.g. `* xyz 1 3` for triplet [H₃⁺](app:s/3/1/3). States with multiplicity > 1 run
  unrestricted (`UHF`/`UKS`, see `engines/orca.py`).
- ⟨S²⟩ is parsed from every output and stored in the `result` table (`s2`).
- Fragments of a cluster may be in any spin state, so the fragmentation
  analysis needs both multiplicities of every species (`doc/Plan.md` §2.2).
- Web app: each species page compares its two spin states, e.g.
  [H₃⁺](app:s/3/1/1).

## References

- A. Szabo, N. S. Ostlund, *Modern Quantum Chemistry*, §2.5 (spin-adapted
  configurations).
- F. Jensen, *Introduction to Computational Chemistry*, 3rd ed., the
  sections on spin and open-shell systems.
