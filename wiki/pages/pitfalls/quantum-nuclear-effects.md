# Quantum nuclear effects

!!! info "Prerequisites"
    [Born–Oppenheimer approximation](../foundations/born-oppenheimer.md),
    [Zero-point energy](../techniques/zero-point-energy.md)

Most of computational chemistry pictures nuclei as balls sitting at the
minimum of the potential energy surface, with vibrations added as small
harmonic wiggles. Nuclei are quantum particles too, and hydrogen nuclei are
light enough for that to matter: they spread out, tunnel through barriers,
and for floppy clusters don't sit in any single minimum at all. These
effects are the hardest part of hydrogen cluster physics, and mostly outside
what this project's methods compute.

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
| Harmonic (this project) | parabola at each minimum | 1 Hessian |
| VPT2 | perturbative anharmonic corrections around a minimum | cubic and quartic derivatives |
| Vibrational CI, MCTDH | solve the nuclear Schrödinger equation on a fitted PES | needs a global PES |
| Diffusion Monte Carlo | exact nuclear ground state by random walks | many PES evaluations |
| Path-integral MD | each nucleus as a ring of beads, quantum statistics at temperature T | many PES evaluations per step |

All except VPT2 need the PES at very many geometries, usually through a
fitted analytic surface.

### Nuclear spin

Protons have spin ½ too. Exchanging two protons must change the sign of the total
wavefunction, which couples nuclear spin to rotation: H₂ comes as *para*
(nuclear spins paired, even rotational levels) and *ortho* (parallel, odd
levels). At low temperatures this changes rotational energies and entropies.
The project's thermochemistry ignores it.

## Where this appears in h_clusters

- Every vibrational quantity in the project is harmonic: frequencies, ZPE
  and thermochemistry (`Freq`/`NumFreq` in `engines/orca.py`).
- The plan names the risk: "Harmonic ZPE is unreliable for floppy H₂ units"
  (`doc/Plan.md` §7), and the physics caveat in §1.2: clusters that are minima
  in the harmonic picture can be unbound once ZPE is included.
- Optional extensions (Phase 8): a VPT2 spot-check on H₅⁺, or a discussion of
  path-integral approaches.
- Reporting both ΔE and ΔE₀, and the separate `bound_with_zpe` verdict, keep
  the harmonic ZPE's influence visible rather than hidden in one number.

## References

- M. E. Tuckerman, *Statistical Mechanics: Theory and Molecular Simulation*
  (Oxford, 2010): path integrals.
- T. E. Markland, M. Ceriotti, *Nat. Rev. Chem.* **2**, 0109 (2018): nuclear
  quantum effects enter the mainstream.
