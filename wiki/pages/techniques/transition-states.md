# Transition states and barriers

!!! info "Prerequisites"
    [Potential energy surface](../foundations/potential-energy-surface.md),
    [Frequencies and the Hessian](frequencies.md#imaginary-frequencies),
    [Fragmentation channels](fragmentation.md#products-versus-process-rearrangement-and-barriers)

A channel's $D_e$ compares only the cluster and its products. If the way
between them climbs higher than the products, the real cost of falling
apart is the top of that climb, the **barrier**. Finding it means finding a
*transition state* (TS): a saddle point on the potential energy surface, a
minimum in every direction except one, along which it is a maximum.

## Idea

### The workflow

1. **End points.** The reactant is the cluster minimum. For the products,
   use the **product complex**: the fragments still touching (for example
   [H₅⁺···H](app:s/6/1/2)), relaxed to their own shallow minimum, rather than fragments
   infinitely far apart. Both ends need the same atom numbering, so that
   the path maps each atom to itself.
2. **Path: nudged elastic band (NEB).** A chain of 8–16 *images*, copies of
   the system, is relaxed between the end points all at once. Springs keep
   the images spread along the path, and each image feels only the force
   perpendicular to the path, so the chain settles onto the
   **minimum-energy path**. In the *climbing-image* variant (CI-NEB) the
   highest image climbs up the path to the saddle point.
3. **Refining the TS.** Starting from that image and a computed Hessian,
   an eigenvector-following optimizer walks uphill along one mode and
   downhill along all others. A frequency calculation then confirms the
   saddle: **exactly one imaginary frequency**, whose mode points along the
   reaction.
4. **Checking where it leads: intrinsic reaction coordinate (IRC).**
   Steepest descent from the TS in both directions must end at the intended
   reactant and product complex. Without this check, a saddle point can
   belong to a different reaction.
5. **Accurate energies.** Paths and TS are found at a level with cheap
   gradients; the energies at the minimum, TS and products are then
   recomputed with a better method. The barriers are

$$
E_\text{forward} = E_\text{TS} - E_\text{cluster}, \qquad
E_\text{reverse} = E_\text{TS} - E_\text{products}
$$

both electronic and with zero-point energy. At the TS the ZPE leaves out the
imaginary mode, which is not a vibration.

### When there is no saddle point

Many dissociations have no barrier at all: the fragments attract all the way
out and the energy rises steadily to $D_e$. A TS search then simply fails,
and the right tool is a **relaxed scan**: fix the distance of the leaving
fragment at a series of values and optimize everything else. A curve that
rises monotonically proves that $D_e$ is the threshold. Rates for such
channels need variational transition-state theory or phase-space theory,
because the bottleneck moves with energy.

### Special problems with hydrogen

- **Self-interaction error.** DFT underestimates barriers of hydrogen and
  proton transfer, systematically. It is the same error that erases the C₂ᵥ
  [H₅⁺](app:s/5/1/1) minimum ([self-interaction error](../pitfalls/self-interaction-error.md)),
  so geometries from MP2 and energies from CCSD(T) are the safe choice.
- **Changing spin.** If the cheapest products have a different total spin
  than the cluster, the two states live on different surfaces. The
  bottleneck is then the **minimum-energy crossing point** (MECP) of the two
  surfaces, not a saddle point on one of them.
- **Breaking a covalent bond.** Breaking an H–H bond inside a core ([H₂⁺](app:s/2/1/2),
  [H₃⁺](app:s/3/1/1)) changes the electronic structure strongly, and a single-determinant
  method can fail along the way. Check the T₁ and D₁ diagnostics of
  coupled cluster, or use CASSCF and NEVPT2 along the path.
- **Light nuclei.** Hydrogen tunnels through barriers, and its zero-point
  energy is large. For low barriers they matter as much as the barrier
  height: Wigner or Eckart corrections are the simple estimates, instanton
  and ring-polymer methods the rigorous ones. In [H₅⁺](app:s/5/1/1) the zero-point level
  already lies above the barrier for the proton shuttling between its two
  [H₂](app:s/2/0/1) ends ([quantum nuclear effects](../pitfalls/quantum-nuclear-effects.md)).

## Example: which channels would need what

| Channel type | Example | Rearrangement? | Tool |
|---|---|---|---|
| Loss of a ligand | [H₇⁺](app:s/7/1/1) → [H₅⁺](app:s/5/1/1) + [H₂](app:s/2/0/1), H⁻(H₂)ₖ → H⁻(H₂)ₖ₋₁ + [H₂](app:s/2/0/1) | no | relaxed scan; expected to confirm $D_e$ |
| Van der Waals split | [(H₂)₄](app:s/8/0/1) → [(H₂)₃](app:s/6/0/1) + [H₂](app:s/2/0/1) | no | relaxed scan |
| Rearranging core | [H₆⁺](app:s/6/1/2) → [H₅⁺](app:s/5/1/1) + H (an [H₃⁺](app:s/3/1/1) triangle must form) | yes | NEB → TS → IRC |
| Spin change | high-spin cations to low-spin products | — | MECP |

For [H₆⁺](app:s/6/1/2) → [H₅⁺](app:s/5/1/1) + H no barrier was expected, because the reverse reaction
resembles [H₂⁺](app:s/2/1/2) + [H₂](app:s/2/0/1) → [H₃⁺](app:s/3/1/1) + H, which has none
([fragmentation](fragmentation.md#products-versus-process-rearrangement-and-barriers)).
The NEB calculation finds a small one instead:

- Both ways of assigning the atoms cross a saddle point (one imaginary mode,
  263i and 1023i cm⁻¹) 34 and 16 meV above the products in CCSD(T) energy.
- With harmonic zero-point energy the lower saddle falls 46 meV *below* the
  products ($D_0$ = 0.238 eV), so the threshold stays $D_0$.
- 16 meV is also below what the method can resolve here: the geometries are
  MP2's, and along the path MP2 and CCSD(T) differ by up to 0.1 eV (0.19
  against 0.29 eV at the end).

The other channels below 1 eV, [H₅⁺](app:s/5/1/1) → [H₃⁺](app:s/3/1/1) + [H₂](app:s/2/0/1),
[H₆⁺](app:s/6/1/2) → H₄⁺ + [H₂](app:s/2/0/1) and → [H₃⁺](app:s/3/1/1) + H₃, rise to the products without a
maximum. The check, the [H₅⁺](app:s/5/1/1) proton hop through the D₂d saddle, gives
0.0057 eV (0.13 kcal/mol) with one imaginary mode at 545i cm⁻¹, and −0.037 eV
with zero-point energy: the zero-point level lies above the barrier.

## Where this appears in h_clusters

- The barriers study, `worker/src/hclust/studies/barriers.py`: for each
  channel of [H₅⁺](app:s/5/1/1) and [H₆⁺](app:s/6/1/2) (doublet) below 1 eV, the two best ways of
  assigning the atoms. A CI-NEB at RI-MP2 (level L1M, 10 images) runs from
  the cluster minimum to the fragments pulled 4 Å apart. The end is not
  relaxed into a product complex, because ORCA keeps NEB end points fixed.
  Where the path has a maximum, `OptTS` from a numerical Hessian follows,
  and the saddle counts only with one imaginary mode and if it stayed near
  its starting image (no distance changed by more than 0.25 Å). CCSD(T)
  single points on every image give the energies. There is no IRC yet. Run
  with `python -m hclust study barriers`; the report is
  `data/studies/barriers@baseline.json`.
- The fragmentation tree and the units still use product energies ($D_e$)
  only: `worker/src/hclust/analysis/units.py`.
- ORCA has everything the workflow needs: `NEB-TS` (CI-NEB followed by a TS
  optimization), `ZOOM-NEB`, `OptTS`, `IRC`, relaxed scans (`%geom Scan`)
  and `SurfCrossOpt` for MECPs. The geometry levels L1 (ωB97X-D4) and L1M
  (RI-MP2) have analytic gradients; CCSD(T) single points give the
  energies, as for every other energy in the project.
- Plan: `doc/Plan.md`, Phase 8, barriers.
- Web app: the [Extensions](app:studies) page, "Barriers on the way out".

## References

- G. Henkelman, B. P. Uberuaga, H. Jónsson, *J. Chem. Phys.* **113**, 9901
  (2000): the climbing-image nudged elastic band.
- K. Fukui, *Acc. Chem. Res.* **14**, 363 (1981): the intrinsic reaction
  coordinate.
- J. N. Harvey, M. Aschi, H. Schwarz, W. Koch, *Theor. Chem. Acc.* **99**, 95
  (1998): minimum-energy crossing points between spin surfaces.
- F. Jensen, *Introduction to Computational Chemistry*, 3rd ed., chapter on
  transition-state theory and locating transition structures.
