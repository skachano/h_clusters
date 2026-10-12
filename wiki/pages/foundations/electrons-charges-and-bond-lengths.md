# Electrons, charge, spin and bond lengths

!!! info "Prerequisites"
    [Hartree–Fock](../methods/hartree-fock.md) (orbitals),
    [Chemical and van der Waals bonds](chemical-and-van-der-waals-bonds.md)

Chemists say that a fragment inside a molecule "lost an electron", or that an
atom "carries a charge of +0.2". Electrons are shared by the whole molecule,
so neither statement can be literally true. This page sorts out what is
physical, what is a model, how charge and spin densities differ, and why bond
lengths are the most trustworthy witness of where the electrons are.

## Idea

### Losing an electron: exact for the molecule, a model inside it

For a **whole molecule** losing an electron is a real event: [H₆](app:s/6/0/1) → [H₆⁺](app:s/6/1/2) + e⁻
changes the electron count from 6 to 5, costs a measurable energy (the
ionization energy) and leaves an exact total charge of +1.

**Inside** the molecule electrons have no owners. They are indistinguishable,
and the wavefunction describes all of them at once, over the whole molecule.
Nothing in nature says "this electron belongs to the central [H₂](app:s/2/0/1)". What can be
observed, or computed without arbitrary choices, is:

- the **electron density**: how much electron there is at each point in
  space (X-ray diffraction measures it);
- the **geometry**: bond lengths (spectroscopy);
- the **spin density**: where the unpaired electron is (EPR);
- **energies**.

### Two bookkeeping schemes on top of the density

- **Orbital occupation.** Describe the molecule with the orbitals of its
  pieces, e.g. the bonding orbital of each [H₂](app:s/2/0/1), and count electrons in them as
  whole numbers. "H₂·H₂⁺·H₂" means 2 + 1 + 2 electrons in the three [H₂](app:s/2/0/1)
  bonding orbitals. These counts are exact only for pieces far apart; when
  the pieces interact, the true orbitals are mixtures and the counts become
  fractional. The whole-number label names the dominant configuration: the
  best single cartoon.
- **Atomic populations.** Take the real, continuous density and divide space
  between the atoms by some rule; the electrons on an atom, subtracted from
  its nuclear charge, give its *partial charge*. The rule is not unique:
  Löwdin, Mulliken, natural (NPA) and Bader charges give different numbers,
  though usually the same trends.

A label like "[H₂⁺](app:s/2/1/2)" is therefore a **formal** charge, a statement about
orbital bookkeeping, while "+0.81 on the outer [H₂](app:s/2/0/1)" is a **partial** charge,
one way of dividing a shared density. They need not agree. Familiar
example: ammonium is written NH₄⁺, yet its nitrogen carries a *negative*
partial charge and the positive charge sits on the hydrogens.

### Charge density and spin density

Every electron is spin-up (α) or spin-down (β), so a molecule has two
densities, $\rho_\alpha(\mathbf r)$ and $\rho_\beta(\mathbf r)$. From them:

$$
\rho = \rho_\alpha + \rho_\beta \quad(\text{charge density}), \qquad
\rho_s = \rho_\alpha - \rho_\beta \quad(\text{spin density})
$$

Since $\rho_\alpha$ and $\rho_\beta$ can vary independently, so can charge
and spin. Only three constraints link them:

- **Pointwise:** $|\rho_s| \le \rho$ everywhere, as neither density can be
  negative. No electrons, no spin.
- **Totals:** $\int\rho = N$ electrons and $\int\rho_s = N_\alpha - N_\beta = 2S$
  (for the usual $M_S = S$ component: 1 for a doublet, 2 for a triplet).
- **Closed shells:** a true singlet has $\rho_s = 0$ everywhere, however its
  charge is distributed.

Atomic charges and spin populations divide space between atoms with the same
rule: charge $= Z - (N_\alpha + N_\beta)$ on the atom, spin $= N_\alpha - N_\beta$.
They vary independently in practice:

| | Charge | Spin |
|---|---|---|
| H atom | 0 | 1 |
| [H₂⁺](app:s/2/1/2) | +0.5 per atom | 0.5 per atom |
| [H₃⁺](app:s/3/1/1), [H₅⁺](app:s/5/1/1) (closed shells) | +1 spread out | 0 everywhere |
| Neutral radicals, e.g. H₂·H | ≈ 0 everywhere | ≈ 1 on the lone H |
| [H₆⁺](app:s/6/1/2) central pair | +0.18 | 0.53 |
| [H₆⁺](app:s/6/1/2) outer [H₂](app:s/2/0/1) (both) | +0.82 | 0.47 |

**Why they come apart: hole plus screening.** Remove one electron from one
orbital φ and change nothing else (Koopmans' picture): the charge gains a
positive hole of shape $|\varphi|^2$, and the spin density is exactly the same
shape, because the unpaired electron left behind sits in that orbital. At
this stage charge and spin coincide. Then all other electrons relax towards
the hole and screen it:

- paired electrons flow in from the neighbours. This moves *charge* a lot,
  but the α and β electrons of a pair shift together, which cancels in
  $\rho_\alpha - \rho_\beta$: *spin* barely moves;
- the singly occupied orbital itself mixes with the neighbours' orbitals,
  which spreads the spin, but less.

In short: **spin follows the unpaired electron, charge follows everything.**
A second-order effect, **spin polarization**, can even give small *negative*
spin density: the unpaired α electron attracts same-spin electrons by
exchange, so a pair's α and β electrons shift slightly differently (the
textbook case is the H atoms of the methyl radical, seen in EPR).

**Measuring and computing.** Charge density is measured by X-ray
diffraction; spin density by EPR hyperfine couplings or polarized neutron
diffraction. Computed spin density is the more fragile of the two:
unrestricted methods can mix in higher spin states
([spin contamination](../pitfalls/spin-contamination.md)), broken-symmetry
solutions can show spin in a true singlet, and DFT's
[self-interaction error](../pitfalls/self-interaction-error.md) spreads a hole
too widely, which shows more in the spin than in the charge.

### Why bond length follows the bonding orbital

What holds two hydrogen nuclei together is electron density *between* them.
The bonding orbital σ puts its density there, so the fuller it is, the
stronger and shorter the bond:

| | Electrons in σ | Bond order | Bond length | $D_e$ |
|---|---|---|---|---|
| [H₂](app:s/2/0/1) | 2 | 1 | 0.74 Å | 4.7 eV |
| [H₂⁺](app:s/2/1/2) | 1 | ½ | 1.06 Å | 2.8 eV |

The bond order is (bonding − antibonding electrons) / 2. The relation also
works with fractions: drain part of a bonding orbital's density and the bond
lengthens part of the way. Bond lengths are measurable and need no partition
rule, so they are the most trustworthy evidence of how full each bonding
orbital effectively is.

### "Character"

A piece of a molecule has the **character** of a free molecule when its
local properties resemble that molecule's: bond length, bond order, spin.
It is a statement of resemblance, not a claim that the free molecule sits
inside unchanged.

## Example: H₆⁺, the H₂·H₂⁺·H₂ sandwich

The lowest [H₆⁺](app:s/6/1/2) (doublet) is a chain of three pairs: a central pair 1.05 Å
long between two outer [H₂](app:s/2/0/1) of 0.79 Å, linked at 1.22 Å. The literature
describes it as H₂·H₂⁺·H₂. Our ωB97X-D4 analysis:

| | Central pair | Each outer [H₂](app:s/2/0/1) | Free [H₂⁺](app:s/2/1/2) | Free [H₂](app:s/2/0/1) |
|---|---|---|---|---|
| Bond length | 1.05 Å | 0.79 Å | 1.06 Å | 0.74 Å |
| Löwdin bond order | 0.39 | 0.55 | 0.5 | 1.0 |
| Spin (unpaired electron) | 0.53 | 0.24 | 1 | 0 |
| Löwdin charge | +0.18 | +0.41 | +1 | 0 |

- **Bond length, bond order and spin** say the central pair has the
  character of [H₂⁺](app:s/2/1/2): one electron in a bonding orbital, half the unpaired
  electron on it.
- **The charge** looks inverted: most of the positive charge is on the outer
  [H₂](app:s/2/0/1). The half-empty bonding orbital of the central pair is a strong electron
  acceptor; the outer [H₂](app:s/2/0/1) donate density from their filled bonding orbitals
  into it (this three-centre bonding holds the sandwich together). About
  0.8 e moves towards the centre, so the formal +1 of "[H₂⁺](app:s/2/1/2)" ends up mostly on
  the donors.
- **Charge and spin part ways** exactly as hole plus screening predicts: the
  spin still marks where the hole is (mostly central), the charge shows the
  hole plus about 0.8 e of screening from the outer [H₂](app:s/2/0/1).
- **The outer bonds** confirm the donation: having given up part of their
  bonding density, they lengthen from 0.74 to 0.79 Å and their bond order
  falls from 1.0 to 0.55. The central pair, given a little density back, is
  slightly shorter than free [H₂⁺](app:s/2/1/2).

So "H₂·H₂⁺·H₂" is a good cartoon of where the hole started and what the
central bond looks like, but the hole is partly spread over the outer [H₂](app:s/2/0/1)
(spin roughly 50 : 25 : 25), and the positive charge mostly is. The ion is
closer to one delocalized (H₂H₂H₂)⁺ unit than to an [H₂⁺](app:s/2/1/2) with two spectators.

Two caveats: partial charges depend on the partition rule, and ωB97X-D4,
like most functionals, spreads a hole too widely
([self-interaction error](../pitfalls/self-interaction-error.md)), so a
correlated method would likely put somewhat more of it on the central pair.

## Where this appears in h_clusters

- Löwdin charges, spin populations and bond orders: the bonds study,
  `worker/src/hclust/studies/bonds.py`; the atom and bond tables and the
  "Highlight atoms" halos on each species page of the web app ([H₆⁺](app:s/6/1/2), for example)
- Units of a cluster and their atoms (where [H₆⁺](app:s/6/1/2) shows up as delocalized):
  `worker/src/hclust/analysis/units.py`
- Plan: `doc/Plan.md`, Phase 8 (bonds study, units from fragmentation)

## References

- C. P. Slichter, *Principles of Magnetic Resonance*, 3rd ed. (Springer,
  1990): hyperfine couplings and spin density.

- A. Szabo, N. S. Ostlund, *Modern Quantum Chemistry* (Dover, 1996), §3.4.6:
  population analysis.
- F. Jensen, *Introduction to Computational Chemistry*, 3rd ed., chapter on
  wave function analysis: population analysis and atomic charges.
- R. F. W. Bader, *Atoms in Molecules: A Quantum Theory* (Oxford, 1990).
