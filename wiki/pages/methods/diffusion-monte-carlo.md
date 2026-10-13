# Diffusion Monte Carlo

!!! info "Prerequisites"
    [Zero-point energy](../techniques/zero-point-energy.md),
    [Quantum nuclear effects](../pitfalls/quantum-nuclear-effects.md),
    [Chemical and van der Waals bonds](../foundations/chemical-and-van-der-waals-bonds.md)

Diffusion Monte Carlo (DMC) finds the exact ground state of a quantum system
by letting a crowd of random walkers diffuse through configuration space,
multiplying where the potential is low and dying out where it is high. This
project uses it for the **nuclei**, not the electrons: on a potential energy
surface built from CCSD(T), DMC gives the true zero-point energy of the
floppy van der Waals clusters, where the harmonic estimate fails, and
decides whether they are bound at all.

## Idea

### The Schrödinger equation in imaginary time

Replace time $t$ by $-i\tau$ in the time-dependent Schrödinger equation
(atomic units, one particle of mass $m$ for simplicity):

$$
\frac{\partial \Psi}{\partial \tau} = \frac{1}{2m}\nabla^2 \Psi - \big(V(\mathbf{R}) - E_\text{ref}\big)\Psi
$$

Expand any starting $\Psi$ in eigenstates: each component decays as
$e^{-(E_n - E_\text{ref})\tau}$. The excited states die out faster than the
ground state, so after a long enough $\tau$ only the ground state $\psi_0$
survives, and $E_\text{ref}$ that keeps it from growing or shrinking is
$E_0$.

The equation has two parts that are easy to simulate separately:

- $\frac{1}{2m}\nabla^2\Psi$ is **diffusion**: each walker takes a Gaussian
  step of variance $\Delta\tau/m$ per coordinate. Light particles diffuse
  further, and that spreading is exactly the zero-point motion.
- $-(V - E_\text{ref})\Psi$ is **branching**: a walker in a low-potential
  region is copied, one in a high-potential region is deleted, with weight
  $e^{-\Delta\tau\,(V - E_\text{ref})}$.

$E_\text{ref}$ is adjusted every step to keep the population near its target
(here 2000 walkers). Without a trial function ("unguided" DMC) the walkers
are distributed like $\psi_0$ itself, and the ground-state energy is simply
the average potential over them:

$$
E_0 = \langle V \rangle_\text{walkers}
$$

The result is exact on the given potential, up to a statistical error that
shrinks with longer runs and a time-step bias that vanishes as
$\Delta\tau \to 0$.

### Bound or not

A cluster is bound if its ground state lies below that of its fragments:
$D_0 = E_0(\text{fragments}) - E_0(\text{cluster}) > 0$, with both energies
from DMC at the same time step, so the time-step bias largely cancels. An
unbound cluster shows it directly: the walkers drift apart, and their spread
keeps growing.

### Rotating molecules

[H₂](app:s/2/0/1) can be treated as a **rigid rotor**: its axis is a unit vector, and its
rotational energy $B\,j(j+1)$ is diffusion on a sphere with diffusion
constant $B$ (59.3 cm⁻¹ for [H₂](app:s/2/0/1)). Each walker then carries positions and axes,
and the potential may depend on orientation. When the potential is
spherical on average, as for para-H₂ in its $j = 0$ state, [H₂](app:s/2/0/1) can instead be
a point particle on an orientation-averaged potential.

## How this project uses it

1. **Potential.** Counterpoise-corrected CCSD(T)/aug-cc-pVTZ scans of the
   interaction between rigid [H₂](app:s/2/0/1) (at its vibrationally averaged length,
   0.7668 Å) and a second [H₂](app:s/2/0/1) or an H atom, over distance and orientation:
   693 jobs. The [H₂](app:s/2/0/1)–[H₂](app:s/2/0/1) curve is averaged over four standard orientations,
   H–[H₂](app:s/2/0/1) over three angles. A spline joins the points, with an exponential
   wall inside and a $-C_6/R^6 - C_8/R^8$ tail outside.
2. **Clusters** are sums of these pair potentials: (H₂)ₖ and (H₂)ₖ·H for
   k = 1–4. The [H₂](app:s/2/0/1) vibration (4400 cm⁻¹) is far too fast to couple and is
   left out.
3. **Checks.** Every pair ([H₂·H](app:s/3/0/2), [(H₂)₂](app:s/4/0/1)) is also solved exactly as a one-dimensional
   radial equation; DMC must agree. The code is tested on a 3D harmonic
   oscillator, an exactly solvable Morse dimer and a pair too shallow to bind.
4. **Robustness.** Every cluster is solved again on a potential 10 %
   shallower. "Bound" must survive that; otherwise the verdict is "at
   threshold".

## Example: the neutral clusters are bound after all

The campaign's harmonic analysis calls every neutral cluster beyond [H₂](app:s/2/0/1)
"bound but not with ZPE": $D_e > 0$ but $D_0 < 0$. DMC on the same CCSD(T)
potential says otherwise:

| Cluster | Harmonic $D_0$ (meV) | Quantum $D_0$ (meV) | Well 10 % shallower | Verdict |
|---|---|---|---|---|
| [H₃](app:s/3/0/2) = [H₂·H](app:s/3/0/2) | −8.3 | +0.0007 (exact) | −0.0002 | at threshold |
| [H₄](app:s/4/0/1) = [(H₂)₂](app:s/4/0/1) | −13.4 | +0.238 (exact; DMC 0.231) | +0.167 | bound |
| [H₅](app:s/5/0/2) = [(H₂)₂·H](app:s/5/0/2) | −29.5 | +0.071 ± 0.004 | +0.041 | bound |
| [H₆](app:s/6/0/1) = [(H₂)₃](app:s/6/0/1) | −36.8 | +0.62 ± 0.01 | +0.44 | bound |
| [H₇](app:s/7/0/2) = [(H₂)₃·H](app:s/7/0/2) | −54.8 | +0.10 ± 0.01 | +0.08 | bound |
| [H₈](app:s/8/0/1) = [(H₂)₄](app:s/8/0/1) | −46.0 | +0.90 ± 0.02 | +0.72 | bound |
| [H₉](app:s/9/0/2) = [(H₂)₄·H](app:s/9/0/2) | −52.9 | +0.14 ± 0.02 | +0.10 | bound |

- The harmonic estimate gets the **sign** wrong. It treats the soft
  intermolecular motions as stiff parabolas and overestimates their
  zero-point energy several-fold.
- (H₂)ₖ is bound by 0.2–0.9 meV, i.e. a few kelvin: such clusters can exist
  only in very cold environments such as helium droplets or supersonic jets.
- [H₂·H](app:s/3/0/2) has at most a "halo" state, bound by under a microelectronvolt with
  a mean separation of 37 Å, which disappears on the shallower well. A lone H
  atom does stay with two or more [H₂](app:s/2/0/1), by about 0.1 meV.

The walker spread is a convergence diagnostic, not the cluster size: DMC
without a trial function samples $\psi_0$, not $|\psi_0|^2$.

## Example: the anions, where orientation and three-body forces matter

The singlet anions [H₃⁻](app:s/3/-1/1)–[H₉⁻](app:s/9/-1/1) are [H⁻](app:s/1/-1/1) with one to four [H₂](app:s/2/0/1) around it. Like the
neutral clusters they are bound in $D_e$ but not after harmonic ZPE. The ion
changes two things:

- **Orientation.** The [H⁻](app:s/1/-1/1)–[H₂](app:s/2/0/1) interaction is strongly anisotropic: −52.5 meV
  end-on, −6.15 meV averaged over angles. So [H₂](app:s/2/0/1) is a rotating rigid rotor
  here (rotor DMC), not a sphere. For [H₃⁻](app:s/3/-1/1) the exact answer comes from a
  coupled-channel calculation (the rotor states $j = 0, 2, 4, \ldots$ coupled
  by the anisotropy): $D_0 = 6.83$ meV, with the free-rotor $j = 0$ state
  89 % of the wavefunction. Rotor DMC gives 6.82.
- **Three-body forces.** The ion polarises every [H₂](app:s/2/0/1) at once, and the energy is
  not a sum of pairs. CCSD(T) on whole clusters puts the non-additive part at
  −23, −77 and −125 meV for [H₅⁻](app:s/5/-1/1), [H₇⁻](app:s/7/-1/1) and [H₉⁻](app:s/9/-1/1). The study tabulates the
  three-body term (798 CCSD(T) jobs over distances, angles and [H₂](app:s/2/0/1)
  orientations). Pairs plus three-body then overbind by 4–14 %, because the
  four-body and higher terms are repulsive, while pairs alone underbind. The
  truth lies between the two models.

Results, $D_0$ in meV for losing one [H₂](app:s/2/0/1):

| Cluster | Harmonic | Pairs only | Pairs + three-body | 10 % shallower | [H₂](app:s/2/0/1) as spheres | Verdict |
|---|---|---|---|---|---|---|
| [H₃⁻](app:s/3/-1/1) = [H⁻·H₂](app:s/3/-1/1) | −13.9 | 6.83 (exact) | 6.83 (exact) | 5.52 | 3.44 | bound |
| [H₅⁻](app:s/5/-1/1) = [H⁻(H₂)₂](app:s/5/-1/1) | −28 | 7.28 | 8.56 ± 0.05 | 6.92 | 4.11 | bound |
| [H₇⁻](app:s/7/-1/1) = [H⁻(H₂)₃](app:s/7/-1/1) | −39 | 7.61 | 11.17 ± 0.11 | 8.23 | 4.79 | bound |
| [H₉⁻](app:s/9/-1/1) = [H⁻(H₂)₄](app:s/9/-1/1) | −46 | 8.06 | 12.46 ± 0.23 | 10.02 | 5.22 | bound |

- All four anions are bound, in every variant, by 7–13 meV (80–150 K): ten to
  a hundred times more than the neutral clusters.
- Orientation doubles the binding: [H₂](app:s/2/0/1) lines up with the ion's field, which a
  sphere cannot do.
- With pairs alone, each further [H₂](app:s/2/0/1) is bound by about the same 7.3–8.1 meV; the
  growth with size comes from the three-body term, whose exact size is the
  main uncertainty.
- The study also exposed a gap in the campaign. For [H₅⁻](app:s/5/-1/1) and [H₇⁻](app:s/7/-1/1) the MP2
  optimisations had stopped at shallow saddle points, so their reference
  energies came from DFT geometries with [H⁻](app:s/1/-1/1) too close to [H₂](app:s/2/0/1) (2.1 Å instead
  of 2.5–2.7 Å, see
  [self-interaction error](../pitfalls/self-interaction-error.md)). Restarted
  from the DMC model's minima, MP2 found true minima 50 and 23 meV lower in
  CCSD(T) energy; the harmonic column uses those.

## Limitations

- The potential is the weak point, not DMC: the aug-cc-pVTZ basis and the
  orientation averaging make the well depths uncertain by about 10 %, which
  is why every cluster is also solved on a shallower well.
- Three-body forces are left out for the neutral clusters, where they are
  small. For the anions they are large and only bracketed: pairs alone
  underbind, pairs plus three-body overbind.
- A time step of 10 a.u. biases cluster energies by a few percent; halving
  it from 20 a.u. changed no verdict.

## Where this appears in [h_clusters](https://github.com/skachano/h_clusters)

- Solver: `worker/src/hclust/analysis/dmc.py` (DMC, exact radial solver,
  pair potentials); tests in `worker/tests/test_dmc.py`
- Studies: `worker/src/hclust/studies/dmc.py` (neutral) and
  `worker/src/hclust/studies/dmc_anions.py` (anions; coupled channels, rotor
  DMC and the three-body table in `analysis/dmc.py`), run with
  `python -m hclust study dmc` or `dmc_anions`; reports in
  `data/studies/dmc@baseline.json` and `dmc_anions@baseline.json`
- [Web app](app:): the [Extensions](app:studies) page, "Quantum nuclear motion: diffusion Monte
  Carlo" and "Quantum nuclear motion of the anions H⁻(H₂)ₖ"
- Plan: `doc/Plan.md`, Phase 8, DMC study and anion DMC

## References

- J. B. Anderson, *J. Chem. Phys.* **63**, 1499 (1975): DMC for the
  Schrödinger equation.
- I. Kosztin, B. Faber, K. Schulten, *Am. J. Phys.* **64**, 633 (1996):
  an introduction to DMC.
- M. A. Suhm, R. O. Watts, *Phys. Rep.* **204**, 293 (1991): quantum Monte
  Carlo for molecular vibrations and van der Waals clusters.
