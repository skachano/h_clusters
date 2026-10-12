# Chemical and van der Waals bonds

!!! info "Prerequisites"
    [Potential energy surface](potential-energy-surface.md),
    [Missing dispersion](../pitfalls/dispersion.md)

Hydrogen clusters contain two very different kinds of "bond". Inside [H₂](app:s/2/0/1) or
[H₃⁺](app:s/3/1/1) the atoms share electrons: a **chemical (covalent) bond**, worth
electronvolts. Between whole H₂ molecules nothing is shared, and the units
are held together only by the weak attraction of their separate electron
clouds: a **van der Waals bond**, about a thousand times weaker. Most of
what is hard in this project comes from the second kind.

## Idea

### What counts as a van der Waals bond here

In h_clusters a **unit** is a group of atoms joined by chemical bonds: an
H₂, an H₃⁺ core, an H atom, an H⁻ ion. A van der Waals bond is the
attraction *between* units that stay chemically intact. The code decides
this in two ways:

- **Distance:** atoms closer than 1.15 Å (`BOND_CUTOFF`) belong to the same
  unit; everything held together across larger gaps is a link between
  units.
- **Bond order:** the Löwdin/Wiberg bond order counts the electron pairs
  shared between two atoms. It is 1.00 for H₂, 0.50 for H₂⁺ and 4/9 for each
  edge of H₃⁺, but nearly zero for a van der Waals contact. The 3D viewer
  draws bonds more transparent as their order falls, and the thumbnails show
  only bonds above 0.33.

### How the two kinds differ

| | Chemical (covalent) bond: H₂, H₃⁺ | Van der Waals bond: (H₂)₂, H₂·H |
|---|---|---|
| Origin | electrons shared in a common orbital: the bonding orbital is occupied | correlated fluctuations of separate electron clouds (dispersion, $-C_6/R^6$), balanced by Pauli repulsion at contact |
| Electron sharing | yes: bond order ~0.5–1 | essentially none: each unit keeps its own electrons |
| Energy | eV: H₂ $D_e \approx 4.7$ eV | meV: the H₂–H₂ well is 2.6 meV (orientation-averaged), whole clusters 1–10 meV |
| Distance | 0.74 Å (H₂), 0.87 Å (H₃⁺) | 3–3.5 Å between molecule centres |
| Stiffness | stiff, high-frequency vibration (H₂: 4400 cm⁻¹) | very soft, large-amplitude motion |
| Direction | a definite geometry | weakly directional: H₂ rotates almost freely in (H₂)ₖ |
| Additivity | not additive: H₃ is not three H–H bonds | nearly pairwise additive |

The two energy scales differ by a factor of about a thousand, and so do the
consequences of every approximation.

### What each needs from the calculation

- **Electron correlation.** A covalent bond is already there, qualitatively,
  in [Hartree–Fock](../methods/hartree-fock.md). A van der Waals bond is
  *entirely* a correlation effect: Hartree–Fock gives no binding at all, and
  plain DFT misses it ([missing dispersion](../pitfalls/dispersion.md)).
  The campaign uses ωB97X-D4, whose D4 term adds dispersion, and
  [CCSD(T)](../methods/coupled-cluster.md) with diffuse basis sets for
  reliable numbers.
- **Basis-set superposition error.** Neighbouring units borrow each other's
  basis functions and look slightly more bound. The counterpoise correction
  is at most 5 meV here: negligible for a covalent bond, but the same size
  as a whole van der Waals well.
- **Nuclear motion.** For a covalent bond the harmonic
  [zero-point energy](../techniques/zero-point-energy.md) is a modest
  correction (H₂: 0.27 eV out of 4.75). For a van der Waals bond it is as
  large as the well itself, and the harmonic estimate fails: it calls the
  neutral clusters unbound, while diffusion Monte Carlo finds them weakly
  bound ([quantum nuclear effects](../pitfalls/quantum-nuclear-effects.md)).

### A spectrum, not two boxes

The clusters in this project run from pure van der Waals binding to nearly
chemical binding:

1. **Neutral (H₂)ₖ:** pure dispersion.
2. **H₂·H:** dispersion plus a little exchange.
3. **Anions H⁻(H₂)ₖ:** mostly the ion's charge polarizing each H₂ (falling
   off as $R^{-4}$) and attracting its quadrupole, with only slight electron
   sharing. The quadrupole term makes the binding strongly directional:
   about 50 meV with H₂ pointing end-on at the ion, only about 6 meV
   averaged over orientations.
4. **Cations H₃⁺(H₂)ₖ:** ion–molecule binding with real charge transfer;
   the links between units have bond orders of 0.2–0.3. In H₅⁺ a proton is
   shared between the two H₂ units, which is already partly chemical, at
   0.1–0.4 eV.

Strictly, "van der Waals" fits only the neutral clusters. The ion clusters
lie in between, which is why they are 10–100 times more strongly bound.

## Example

| Pair | Well depth | Equilibrium distance | Character |
|---|---|---|---|
| H–H in H₂ | 4.7 eV | 0.74 Å | covalent, bond order 1.00 |
| H₃⁺ + H₂ → H₅⁺ | 0.37 eV | — | ion–molecule, shared proton |
| H⁻ + H₂ (end-on) | 0.05 eV | 3.2 Å (centres) | ion–induced dipole and ion–quadrupole |
| H₂ + H₂ (orientation-averaged) | 0.0026 eV | 3.5 Å | dispersion |
| H + H₂ (orientation-averaged) | 0.0016 eV | 3.55 Å | dispersion |

Numbers from CCSD(T)/aug-cc-pVTZ in this project, counterpoise-corrected for
the weak pairs.

## Where this appears in h_clusters

- Units and the 1.15 Å cutoff: `worker/src/hclust/structures.py`
- Bond orders: `worker/src/hclust/studies/bonds.py`; the per-structure bond
  table and the 3D viewer in the web app
- Pair potentials and their scans: `worker/src/hclust/studies/dmc.py`
- Plan: `doc/Plan.md` §1.2 (what to expect) and the Phase 8 studies

## References

- A. J. Stone, *The Theory of Intermolecular Forces*, 2nd ed. (Oxford, 2013).
- I. G. Kaplan, *Intermolecular Interactions* (Wiley, 2006).
- K. B. Wiberg, *Tetrahedron* **24**, 1083 (1968): bond indices.
