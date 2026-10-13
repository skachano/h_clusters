# Frequencies and the Hessian

!!! info "Prerequisites"
    [Potential energy surface](../foundations/potential-energy-surface.md),
    [Geometry optimization](geometry-optimization.md)

A frequency calculation computes the curvature of the potential energy
surface at a structure and turns it into vibrations. It answers two
questions: is this structure a true minimum (all frequencies real), and how
much [zero-point](zero-point-energy.md) and thermal energy does it have? In
this project every structure that reaches the reference level has been
checked this way.

## Idea

### From curvature to frequency

For one coordinate, a well with curvature $k$ (the force constant) and a
vibrating mass $\mu$ oscillates at $\omega = \sqrt{k/\mu}$
([vibrations](../foundations/potential-energy-surface.md#vibrations-and-vibrational-levels)).
With many atoms, the curvature is the **Hessian** matrix of second
derivatives, $H_{ij} = \partial^2 E/\partial x_i\,\partial x_j$, over all $3N$
Cartesian coordinates. Dividing by the masses gives the **mass-weighted
Hessian**

$$
\tilde H_{ij} = \frac{H_{ij}}{\sqrt{m_i m_j}}
$$

Its eigenvectors are the **normal modes**, independent collective motions of
the atoms, and its eigenvalues are $\omega^2$. Six eigenvalues (five for a
linear molecule) are zero: overall translation and rotation. The remaining
$3N - 6$ are the vibrations.

### Imaginary frequencies

At a minimum every eigenvalue is positive. At a saddle point one (or more)
is negative, so $\omega = \sqrt{\text{negative}}$ is imaginary. Programs print
it as a negative number or with an "i", e.g. 546i cm⁻¹. The mode belonging
to it points downhill: moving the atoms along it lowers the energy.

| Imaginary frequencies | Structure |
|---|---|
| 0 | minimum |
| 1 | first-order saddle point (transition state) |
| 2 or more | higher-order saddle point |

Small imaginary values (tens of cm⁻¹) on floppy clusters are often numerical
noise from an optimization that isn't converged tightly enough.

### Analytic and numerical Hessians

Some methods have **analytic** second derivatives (HF, many DFT
functionals): one calculation gives the whole Hessian. Otherwise the Hessian
is built **numerically** from gradients: displace each of the $3N$
coordinates forwards and backwards and difference the gradients, which costs
$6N$ gradient calculations.

## Example: [H₂](app:s/2/0/1) and the cost of approximations

The toy [`h2_mp2_opt_freq.py`](geometry-optimization.md#the-code) gets the
force constant from the curvature of the energy curve at the minimum:

```text
RHF: minimum R_e = 0.7122 Å, force constant k = 0.5729 hartree/bohr², harmonic frequency = 5481 cm⁻¹
FCI: minimum R_e = 0.7349 Å, force constant k = 0.4771 hartree/bohr², harmonic frequency = 5002 cm⁻¹
```

The experimental harmonic frequency is 4401 cm⁻¹. HF/STO-3G is 25 % too high:
missing correlation makes bonds too stiff, a well-known HF trend, and the tiny
basis adds more. The project's levels with aug-cc-pVTZ or def2-TZVPPD do far
better:

| [H₂](app:s/2/0/1) harmonic frequency | cm⁻¹ |
|---|---|
| ωB97X-D4/def2-TZVPPD (L1) | 4441 |
| RI-MP2/aug-cc-pVTZ (L1M) | 4517 |
| Experiment | 4401 |

## Example: [H₃⁺](app:s/3/1/1) and [H₅⁺](app:s/5/1/1)

[H₃⁺](app:s/3/1/1) (L1) has 3 × 3 − 6 = 3 modes: **2743, 2743 and 3368 cm⁻¹**. The pair
with identical frequencies is a *degenerate* mode, forced by the triangle's
D₃h symmetry ([point groups](point-groups.md)); 3368 cm⁻¹ is the symmetric
"breathing" of the triangle.

[H₅⁺](app:s/5/1/1) shows how frequencies tell structures apart (`doc/Plan.md`, Phase 3):

| [H₅⁺](app:s/5/1/1) at RI-MP2/aug-cc-pVTZ | Frequencies |
|---|---|
| C₂ᵥ [H₃⁺·H₂](app:s/5/1/1) | 9 real, the lowest 203 cm⁻¹ (the soft [H₂](app:s/2/0/1)–[H₃⁺](app:s/3/1/1) motion) |
| D₂d shared proton | 1 imaginary, **546i cm⁻¹**: a saddle point at this level |

At the DFT levels the D₂d structure is a minimum instead. The imaginary
mode of D₂d at MP2 moves the central proton towards one [H₂](app:s/2/0/1), the motion that
turns it into C₂ᵥ.

## Where this appears in [h_clusters](https://github.com/skachano/h_clusters)

- Tasks `freq` and `optfreq` add `Freq` (analytic) or `NumFreq` (numerical,
  for levels with `analytic_hessian=False`) in `engines/orca.py`. L1 was
  switched to ωB97X-D4 because it has an analytic Hessian: 231 s for [H₁₀](app:s/10/0/1),
  against about 2 h numerically with ωB97M-V.
- When the analytic Hessian's equations (CP-SCF) don't converge, the runner
  retries with `NumFreq` from the optimized geometry (error kind `cpscf`).
- **Saddle points are pushed downhill**: if a result has imaginary
  frequencies, `displace_along_imaginary_mode()` in `worker/src/hclust/runner.py`
  moves the atoms 0.1 Å along the most imaginary mode (alternating sign
  between attempts) and re-optimizes. This turned a linear [H₃⁺](app:s/3/1/1) chain into the
  triangle (Phase 2) and both MP2 D₂d [H₅⁺](app:s/5/1/1) structures into C₂ᵥ (Phase 3).
  After 3 attempts the structure is kept as a saddle point (`n_imag > 0`).
- Stages with `minima_only` or `when: minimum` (`campaigns/baseline.yaml`)
  only pass on structures with no imaginary frequencies.
- Frequencies and normal modes are stored per result (`frequencies`, `modes`).
- [Web app](app:): the 3D viewer on each species page animates the normal modes, e.g.
  [H₃⁺](app:s/3/1/1).

## References

- E. B. Wilson, J. C. Decius, P. C. Cross, *Molecular Vibrations* (Dover, 1980).
- F. Jensen, *Introduction to Computational Chemistry*, 3rd ed., sections on
  vibrational frequencies.
