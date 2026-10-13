# Units: language or physics?

!!! info "Prerequisites"
    [Chemical and van der Waals bonds](chemical-and-van-der-waals-bonds.md),
    [Electrons, charge, spin and bond lengths](electrons-charges-and-bond-lengths.md)

We describe clusters as made of units: [(H₂)₄](app:s/8/0/1) is "four [H₂](app:s/2/0/1)", [H₇⁺](app:s/7/1/1) is "[H₃⁺](app:s/3/1/1) with
two [H₂](app:s/2/0/1)". Physics has no "unit" observable, so every such decomposition is a
description. But some descriptions are forced on us by the physics and some
are not. This page says how to tell them apart.

## Idea

### What is strictly real

What exists is the whole system: its Hamiltonian, its wavefunction, and what
can be measured from them (energies, spectra, electron density, geometry).
Electrons are indistinguishable and shared by everything, and no
quantum-mechanical operator answers "which unit does this atom belong to?".
Every decomposition, by distances, bond orders, energies or resemblance to
known molecules, is a way of talking about the whole. In that sense it is
language.

### When language reflects physics: separability

A description becomes more than a convention when the system is
*approximately separable*: the Hamiltonian splits into parts that barely
interact,

$$
\hat H \approx \sum_{\text{units}} \hat H_{\text{unit}} + \hat V_{\text{between}}, \qquad \hat V_{\text{between}} \ \text{small},
$$

and the wavefunction nearly factorises into one factor per unit. Then the
units have real, testable consequences:

1. **Separation of scales:** energies, distances and timescales inside units
   differ greatly from those between them.
2. **Transferability:** a unit in the cluster has nearly the properties it has
   alone.
3. **Robustness:** every reasonable way of dividing gives the same answer.
4. **Quantum numbers of their own:** good approximate quantum numbers belong
   to individual units.

The [Born–Oppenheimer approximation](born-oppenheimer.md) is the same idea one
level down: electrons and nuclei are "units" of a molecule because their
timescales differ.

## Example: three kinds of cluster

### Van der Waals clusters: about as real as it gets

The [H₂](app:s/2/0/1) units in (H₂)ₖ pass every test by large margins:

- **Energy:** 4.7 eV inside an [H₂](app:s/2/0/1), 2–10 meV between them, a factor of about
  a thousand.
- **Time:** the [H₂](app:s/2/0/1) vibration (4400 cm⁻¹) is about a hundred times faster
  than the intermolecular motions (tens of cm⁻¹).
- **Transferability:** in the cluster [H₂](app:s/2/0/1) keeps its free bond length
  (0.74 Å), a bond order near 1, and nearly free rotation.
- **Quantum numbers:** ortho- and para-H₂ (nuclear spin coupled to rotation)
  remain labels of *each [H₂](app:s/2/0/1)* in the cluster. They interconvert only over
  hours to days, so in a real sample each [H₂](app:s/2/0/1) of a cluster really is para or
  ortho: a measurable property that belongs to one unit.
- **Predictive success:** the
  [diffusion Monte Carlo](../methods/diffusion-monte-carlo.md) study treats
  the [H₂](app:s/2/0/1) as rigid units on pair potentials and reproduces the exact
  answers. If the units were mere words, that model would fail.
- **Robustness:** distances, bond orders and fragmentation energies all give
  the same units, and the cheapest split of a neutral cluster (≤ 0.01 eV) is
  far below anything else.

So "[(H₂)₄](app:s/8/0/1) is four [H₂](app:s/2/0/1) molecules" describes a near-factorisation the physics
imposes: spectroscopically it *is* four [H₂](app:s/2/0/1), with small shifts.

### Covalent units: nothing below them

Inside [H₃⁺](app:s/3/1/1) there are no units. Splitting it into [H₂ + H⁺](app:s/3/1/1) fails every test:
the bonding is shared over three centres, nothing is transferable, and the
pieces cost 4.6 eV to separate. [H₃⁺](app:s/3/1/1) is simply the unit.

### Ions: where language starts to matter

The ion clusters lie in between, and the answer degrades gradually:

- **H₃⁺(H₂)ₙ:** largely physical. The [H₃⁺](app:s/3/1/1) core keeps its identity, [H₂](app:s/2/0/1) comes
  off one at a time, and the shell closing at [H₉⁺](app:s/9/1/1) appears in mass spectra.
  But the links cost 0.2–0.4 eV, with real charge transfer, so the
  separation of scales is only about tenfold.
- **[H₅⁺](app:s/5/1/1):** two legitimate descriptions, [H₃⁺·H₂](app:s/5/1/1) at the minimum and [H₂·H⁺·H₂](app:s/5/1/1)
  in the ground state, because the proton's zero-point motion crosses the
  barrier between them
  ([quantum nuclear effects](../pitfalls/quantum-nuclear-effects.md)).
  The decomposition depends on which question you ask.
- **[H₆⁺](app:s/6/1/2) (doublet):** "[H₃⁺ + H₂ + H](app:s/6/1/2)" (what it falls apart into) and
  "[H₂·H₂⁺·H₂](app:s/6/1/2)" (what its pieces resemble) are both defensible and neither is
  complete: the hole is delocalised
  ([electrons, charge, spin and bond lengths](electrons-charges-and-bond-lengths.md)).
  Here the units are mostly language; what is physical is the disagreement
  itself, meaning delocalisation.

## The criterion

A decomposition reveals physical reality to the extent that it is **robust**
(it survives every reasonable choice of method, threshold or partition) and
**predictive** (the units' properties transfer, and models built on them
work). Gaps in energy and timescale are what make both possible. Where the
gaps exist, every method converges and the units are as real as molecules in
a gas. Where they do not, the choice is a convention, and what is physical is
that no unique answer exists.

## Where this appears in h_clusters

- Units from fragmentation energies, at two thresholds placed in the energy
  gaps (1 eV: covalent cores and ligands; 0.013 eV: ion clusters whole), and
  the count of equally good atom assignments that flags delocalisation:
  `worker/src/hclust/analysis/units.py`; the Units card and fragmentation tree
  on each species page of the web app ([H₉⁻](app:s/9/-1/1), for example).
- The distance-based groups (1.15 Å) and Löwdin bond orders, shown alongside.
- An exploratory comparison with units chosen by resemblance to free [H₂](app:s/2/0/1), [H₂⁺](app:s/2/1/2)
  and [H₃⁺](app:s/3/1/1) (bond lengths, spin) agreed for the neutral clusters, the anions
  and the odd cations, and disagreed for the even and high-spin cations
  (`doc/Plan.md`, Phase 8); it is not in the app.

## References

- R. F. W. Bader, *Atoms in Molecules: A Quantum Theory* (Oxford, 1990): a
  partition of the density into atoms, and why atoms in molecules are not
  observables.
- A. J. Stone, *The Theory of Intermolecular Forces*, 2nd ed. (Oxford, 2013):
  the perturbation picture of weakly interacting units.
