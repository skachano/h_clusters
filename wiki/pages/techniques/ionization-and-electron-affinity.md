# Ionization energy and electron affinity

!!! info "Prerequisites"
    [Potential energy surface](../foundations/potential-energy-surface.md)

Fragmentation asks whether a cluster loses atoms. The other way to fall
apart is to lose an **electron**. The ionization energy (IE) is the cost of
removing one; the electron affinity (EA) is the energy released when a
neutral species captures one. For the anions in this project, a negative
electron affinity means the extra electron isn't bound: the anion doesn't
exist as a stable species, whatever its calculation says.

## Idea

### Definitions

$$
\text{IE} = E(\text{cation}) - E(\text{neutral}), \qquad
\text{EA} = E(\text{neutral}) - E(\text{anion})
$$

Both are defined so that a positive number means "the electron is held".
A free electron at rest has energy zero, so these are just energy differences
between species with one electron more or less.

### Adiabatic and vertical

Adding or removing an electron changes the best geometry.

- **Adiabatic**: each species at its own optimized geometry. This is the
  thermodynamic energy difference.
- **Vertical**: both at the same geometry, the starting species'. Electrons
  move much faster than nuclei ([Born–Oppenheimer](../foundations/born-oppenheimer.md)),
  so an electron that is knocked out or captured suddenly sees the old
  geometry. For anions, the **vertical detachment energy** (VDE) is
  E(neutral at the anion's geometry) − E(anion).

For single atoms adiabatic and vertical are the same.

### Koopmans' theorem

In Hartree–Fock, $-\varepsilon_\text{HOMO}$ approximates the ionization energy,
ignoring how the other electrons relax once one is gone. For [H₂](app:s/2/0/1) in STO-3G it
gives 15.7 eV ([Hartree–Fock](../methods/hartree-fock.md#example-h2-from-scratch)).
How good the estimate is across the campaign: [HOMO and LUMO](../foundations/homo-and-lumo.md#examples-from-the-campaign).

## Examples from the campaign

CCSD(T)/aug-cc-pVTZ (L2):

| Quantity | Computed | Experiment |
|---|---|---|
| IE(H) = E(H⁺) − E(H) = 0 − (−0.499821) | 13.601 eV | 13.606 eV |
| IE(H₂), adiabatic: −0.602302 − (−1.172635) | 15.52 eV | — |
| IE(H₂), with ZPE | 15.39 eV | 15.43 eV |
| EA(H): −0.499821 − (−0.526562) | 0.728 eV | 0.754 eV |

The ZPE correction for H₂ uses the harmonic frequencies, 4401 cm⁻¹ (H₂) and
2322 cm⁻¹ (H₂⁺): [H₂⁺](app:s/2/1/2)'s weaker bond vibrates more slowly, so ionizing loses
half the difference, 0.13 eV. Measured ionization energies always refer to
the vibrational ground states.

**[H⁻](app:s/1/-1/1): an electron affinity that methods disagree on.** H⁻ has two electrons
around one proton, and the second is held only by correlation. Different
levels give (from the H and H⁻ energies at each level):

| Level | EA(H) |
|---|---|
| r²SCAN-3c (L0) | −1.57 eV: H⁻ unbound |
| ωB97X-D4/def2-TZVPPD (L1) | 0.20 eV |
| RI-MP2/aug-cc-pVTZ (L1M) | 0.48 eV |
| CCSD(T)/aug-cc-pVTZ (L2) | 0.73 eV |
| Exact | 0.754 eV |

DFT's [self-interaction error](../pitfalls/self-interaction-error.md) and,
for L0, the lack of [diffuse functions](../pitfalls/diffuse-functions.md)
both weaken the binding.

**[H₂⁻](app:s/2/-1/2): a negative electron affinity.** At CCSD(T), H₂⁻ is 0.057 hartree
(1.6 eV) *above* H₂ + a free electron. The extra electron isn't bound; real
H₂⁻ exists only as a short-lived resonance. The calculation still returns a
number, because a finite basis set can't let the electron escape
([unbound anions](../pitfalls/unbound-anions.md)).

## Where this appears in h_clusters

- IE, EA and VDE for anions are derived quantities of Phase 5
  (`doc/Plan.md` §2.2); an anion with a negative EA or VDE gets the verdict
  `unbound_electron`, the lowest category.
- They need the neighbouring charge states of the same m, another reason the
  whole species grid is computed.
- E(H⁺) = 0 by definition (`doc/Plan.md` §1.1).
- EA(H) is one of the Phase 1 anchor regression tests (`worker/tests/test_anchors.py`).
- Web app: the [Extensions](app:studies) page compares vertical and
  adiabatic electron removal.

## References

- F. Jensen, *Introduction to Computational Chemistry*, 3rd ed., sections on
  ionization potentials and electron affinities.
- NIST Chemistry WebBook: ionization energies of H and H₂.
- K. R. Lykke, K. K. Murray, W. C. Lineberger, *Phys. Rev. A* **43**, 6104 (1991):
  the electron affinity of H.
