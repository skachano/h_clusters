# Quantum nuclear effects

!!! info "Prerequisites"
    [Born–Oppenheimer approximation](../foundations/born-oppenheimer.md),
    [Zero-point energy](../techniques/zero-point-energy.md)

Most of computational chemistry pictures nuclei as balls sitting at the
minimum of the potential energy surface, with vibrations added as small
harmonic wiggles. Nuclei are quantum particles too, and hydrogen nuclei are
light enough for that to matter: they spread out, tunnel through barriers,
and for floppy clusters don't sit in any single minimum at all. These
effects are the hardest part of hydrogen cluster physics. The campaign
itself treats them harmonically; two Phase 8 studies go beyond that (VPT2
for the cations, [diffusion Monte Carlo](../methods/diffusion-monte-carlo.md)
for the weak clusters).

## Idea

### Nuclei are waves

Within [Born–Oppenheimer](../foundations/born-oppenheimer.md#step-two-the-nuclei),
nuclei have their own wavefunction on the PES. A heavy nucleus has a
compact wavefunction, close to a point at the minimum. A proton's spreads
over a sizable region: in H₂ the ground-state bond length fluctuates by
about ±0.1 Å.

Consequences that grow as the mass drops:

- **Zero-point energy**: a large fraction of a weak binding energy
  ([zero-point energy](../techniques/zero-point-energy.md)).
- **Anharmonicity**: the wavefunction samples the PES far from the minimum,
  where the harmonic parabola is wrong. The harmonic ZPE becomes unreliable
  for soft modes.
- **Tunnelling and delocalization**: when a barrier between two minima is
  lower than the ZPE, the nuclei aren't localized in either well.
- **Isotope effects**: H and D clusters can differ in structure and stability
  although their PES is identical.

### H₅⁺: a molecule without a structure

At CCSD(T), H₅⁺'s C₂ᵥ structure (H₃⁺·H₂) is 0.13 kcal/mol below the D₂d one (a
proton shared by two H₂), which is the barrier for the proton to move from
one H₂ to the other. H₅⁺'s zero-point energy is about 22 kcal/mol. The barrier
is far below the ZPE, so the central proton isn't localized on one side: in
its ground state, the central proton's wavefunction spreads over both sides,
shared between the two H₂ units, although the shared-proton D₂d structure
isn't a minimum. The question "which structure is H₅⁺?" has no classical answer.

### Methods that go beyond

| Method | Idea | Cost |
|---|---|---|
| Harmonic (the campaign) | parabola at each minimum | 1 Hessian |
| VPT2 (Phase 8) | perturbative anharmonic corrections around a minimum | cubic and quartic derivatives |
| Vibrational CI, MCTDH | solve the nuclear Schrödinger equation on a fitted PES | needs a global PES |
| [Diffusion Monte Carlo](../methods/diffusion-monte-carlo.md) (Phase 8) | exact nuclear ground state by random walks | many PES evaluations |
| Path-integral MD | each nucleus as a ring of beads, quantum statistics at temperature T | many PES evaluations per step |

All except VPT2 need the PES at very many geometries, usually through a
fitted analytic surface. The DMC study builds one from pair potentials fitted
to CCSD(T) scans: cheap to evaluate a billion times.

### What the harmonic picture gets wrong here

The campaign's harmonic ZPE makes every neutral cluster beyond H₂ unbound
($D_0 < 0$ by 8–55 meV). Diffusion Monte Carlo on a CCSD(T) potential finds
the opposite: (H₂)ₖ is bound by 0.2–0.9 meV and a lone H atom stays with two
or more H₂ by about 0.1 meV; only H₂·H is at the threshold of binding. The
harmonic approximation treats the soft intermolecular motions as stiff
parabolas and overestimates their zero-point energy several-fold. For the
cations, where the binding is much larger, VPT2 changes $D_0$ of
H₅⁺ → H₃⁺ + H₂ only from 0.244 to 0.280 eV.

### Nuclear spin

Protons have spin ½ too. Exchanging two protons must change the sign of the total
wavefunction, which couples nuclear spin to rotation: H₂ comes as *para*
(nuclear spins paired, even rotational levels) and *ortho* (parallel, odd
levels). At low temperatures this changes rotational energies and entropies.
The project's thermochemistry ignores it; the DMC study assumes para-H₂,
whose $j = 0$ ground state is spherical.

## Where this appears in h_clusters

- Every vibrational quantity in the project is harmonic: frequencies, ZPE
  and thermochemistry (`Freq`/`NumFreq` in `engines/orca.py`).
- The plan names the risk: "Harmonic ZPE is unreliable for floppy H₂ units"
  (`doc/Plan.md` §7), and the physics caveat in §1.2: clusters that are minima
  in the harmonic picture can be unbound once ZPE is included.
- Phase 8 studies: VPT2 on H₂, H₃⁺ and H₅⁺ (`studies/anharmonic.py`), and
  diffusion Monte Carlo of the neutral clusters (`studies/dmc.py`; see
  [diffusion Monte Carlo](../methods/diffusion-monte-carlo.md)).
- Reporting both ΔE and ΔE₀, and the separate `bound_with_zpe` verdict, keep
  the harmonic ZPE's influence visible rather than hidden in one number.

## References

- M. E. Tuckerman, *Statistical Mechanics: Theory and Molecular Simulation*
  (Oxford, 2010): path integrals.
- T. E. Markland, M. Ceriotti, *Nat. Rev. Chem.* **2**, 0109 (2018): nuclear
  quantum effects enter the mainstream.
