# Zero-point energy

!!! info "Prerequisites"
    [Potential energy surface](../foundations/potential-energy-surface.md#vibrations-and-vibrational-levels),
    [Frequencies](frequencies.md)

Even at absolute zero a molecule vibrates: the lowest vibrational level
lies above the bottom of the well. That leftover energy, the **zero-point
energy** (ZPE), is small for most chemistry but large for hydrogen, the
lightest atom. For the weakly bound clusters in this project it decides
whether a cluster holds together at all.

## Idea

In the harmonic approximation each normal mode $i$ with frequency $\omega_i$
contributes half a quantum:

$$
\text{ZPE} = \sum_{i=1}^{3N-6} \tfrac{1}{2}\hbar\omega_i
$$

So the ZPE comes straight out of a [frequency calculation](frequencies.md).
Light atoms vibrate fast ($\omega \propto 1/\sqrt{\mu}$), so their ZPE is
large; the [isotope table](../foundations/born-oppenheimer.md#one-surface-for-all-isotopes)
shows the effect for [H₂](app:s/2/0/1) against D₂.

What matters for stability is the **change** of ZPE in a process. Breaking
a cluster into fragments turns some of its vibrations into free translations
and rotations of the pieces, which have no zero-point energy. So the
fragments together usually have less ZPE than the cluster, and

$$
D_0 = D_e - \Delta\text{ZPE}, \qquad
\Delta\text{ZPE} = \text{ZPE}(\text{cluster}) - \sum \text{ZPE}(\text{fragments}) > 0
$$

([binding energy](../foundations/potential-energy-surface.md#binding-energy-d_e-and-d_0)).

## Example: H₅⁺ → H₃⁺ + H₂ { #example-h5-h3-h2 }

From the baseline campaign: electronic energies at CCSD(T)/aug-cc-pVTZ,
ZPEs from RI-MP2/aug-cc-pVTZ harmonic frequencies, both at the MP2 geometries.

| | Energy (hartree) | ZPE (hartree) | ZPE (eV) |
|---|---|---|---|
| [H₅⁺](app:s/5/1/1) (C₂ᵥ) | −2.527957 | 0.035458 | 0.965 |
| [H₃⁺](app:s/3/1/1) | −1.341728 | 0.020718 | 0.564 |
| [H₂](app:s/2/0/1) | −1.172615 | 0.010291 | 0.280 |

- $D_e$ = (−1.341728 − 1.172615) − (−2.527957) = 0.013614 hartree = **8.54 kcal/mol**
- ΔZPE = 0.035458 − (0.020718 + 0.010291) = 0.004449 hartree = **2.79 kcal/mol**
- $D_0$ = 8.54 − 2.79 = **5.75 kcal/mol**

A third of the binding energy is eaten by zero-point energy. [H₅⁺](app:s/5/1/1)'s nine modes
include five that don't exist in the fragments; the softest, 203 cm⁻¹, is the
[H₂](app:s/2/0/1) unit rocking against [H₃⁺](app:s/3/1/1).

## How reliable is it?

The harmonic formula assumes each well is a parabola. That is good for stiff
bonds (H₂, [H₃⁺](app:s/3/1/1)) and poor for the soft, floppy motions that hold clusters
together, where the real potential is strongly anharmonic and the ZPE can be
off by a large fraction. For [H₅⁺](app:s/5/1/1) the effect goes further: its C₂ᵥ and D₂d
structures differ by only 0.13 kcal/mol, far less than the ZPE, so the
real molecule doesn't sit in either well. Its central proton moves freely
between the two [H₂](app:s/2/0/1) units (it is "fluxional").
See [quantum nuclear effects](../pitfalls/quantum-nuclear-effects.md).

## Where this appears in h_clusters

- ORCA reports the ZPE with every frequency job; it is stored in the
  `thermo` field of each result (`"zpe"`, in hartree).
- The plan reports binding energies both as ΔE and ΔE₀ = ΔE + ΔZPE, and the
  stability verdict has a separate top category, `bound_with_zpe`, for
  clusters with $D_{0,\min} > 0$ (`doc/Plan.md` §2.2).
- Phase 8 goes beyond the harmonic ZPE: VPT2 for [H₂](app:s/2/0/1), [H₃⁺](app:s/3/1/1) and [H₅⁺](app:s/5/1/1), and
  [diffusion Monte Carlo](../methods/diffusion-monte-carlo.md) for the
  neutral clusters, where the harmonic $D_0 < 0$ turns out to be wrong.
- Web app: compare the [grid by $D_e$](app:?q=d_e) with the
  [grid by $D_0$](app:?q=d_0) to see which clusters ZPE unbinds; the
  [Extensions](app:studies) page has the VPT2 and DMC studies.

## References

- F. Jensen, *Introduction to Computational Chemistry*, 3rd ed., sections on
  vibrational frequencies and thermochemistry.
- D. A. McQuarrie, *Statistical Mechanics*: the harmonic oscillator and its
  zero-point energy.
