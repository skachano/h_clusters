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

H₂ can be treated as a **rigid rotor**: its axis is a unit vector, and its
rotational energy $B\,j(j+1)$ is diffusion on a sphere with diffusion
constant $B$ (59.3 cm⁻¹ for H₂). Each walker then carries positions and axes,
and the potential may depend on orientation. When the potential is
spherical on average, as for para-H₂ in its $j = 0$ state, H₂ can instead be
a point particle on an orientation-averaged potential.

## How this project uses it

1. **Potential.** Counterpoise-corrected CCSD(T)/aug-cc-pVTZ scans of the
   interaction between rigid H₂ (at its vibrationally averaged length,
   0.7668 Å) and a second H₂ or an H atom, over distance and orientation:
   693 jobs. The H₂–H₂ curve is averaged over four standard orientations,
   H–H₂ over three angles. A spline joins the points, with an exponential
   wall inside and a $-C_6/R^6 - C_8/R^8$ tail outside.
2. **Clusters** are sums of these pair potentials: (H₂)ₖ and (H₂)ₖ·H for
   k = 1–4. The H₂ vibration (4400 cm⁻¹) is far too fast to couple and is
   left out.
3. **Checks.** Every pair (H₂·H, (H₂)₂) is also solved exactly as a one-dimensional
   radial equation; DMC must agree. The code is tested on a 3D harmonic
   oscillator, an exactly solvable Morse dimer and a pair too shallow to bind.
4. **Robustness.** Every cluster is solved again on a potential 10 %
   shallower. "Bound" must survive that; otherwise the verdict is "at
   threshold".

## Example: the neutral clusters are bound after all

The campaign's harmonic analysis calls every neutral cluster beyond H₂
"bound but not with ZPE": $D_e > 0$ but $D_0 < 0$. DMC on the same CCSD(T)
potential says otherwise:

| Cluster | Harmonic $D_0$ (meV) | Quantum $D_0$ (meV) | Well 10 % shallower | Verdict |
|---|---|---|---|---|
| H₃ = H₂·H | −8.3 | +0.0007 (exact) | −0.0002 | at threshold |
| H₄ = (H₂)₂ | −13.4 | +0.238 (exact; DMC 0.231) | +0.167 | bound |
| H₅ = (H₂)₂·H | −29.5 | +0.071 ± 0.004 | +0.041 | bound |
| H₆ = (H₂)₃ | −36.8 | +0.62 ± 0.01 | +0.44 | bound |
| H₇ = (H₂)₃·H | −54.8 | +0.10 ± 0.01 | +0.08 | bound |
| H₈ = (H₂)₄ | −46.0 | +0.90 ± 0.02 | +0.72 | bound |
| H₉ = (H₂)₄·H | −52.9 | +0.14 ± 0.02 | +0.10 | bound |

- The harmonic estimate gets the **sign** wrong. It treats the soft
  intermolecular motions as stiff parabolas and overestimates their
  zero-point energy several-fold.
- (H₂)ₖ is bound by 0.2–0.9 meV, i.e. a few kelvin: such clusters can exist
  only in very cold environments such as helium droplets or supersonic jets.
- H₂·H has at most a "halo" state, bound by under a microelectronvolt with
  a mean separation of 37 Å, which disappears on the shallower well. A lone H
  atom does stay with two or more H₂, by about 0.1 meV.

The walker spread is a convergence diagnostic, not the cluster size: DMC
without a trial function samples $\psi_0$, not $|\psi_0|^2$.

## Limitations

- The potential is the weak point, not DMC: the aug-cc-pVTZ basis and the
  orientation averaging make the well depths uncertain by about 10 %, which
  is why every cluster is also solved on a shallower well.
- Three-body forces are left out for the neutral clusters; they are small
  for dispersion-bound H₂, but not around an ion.
- A time step of 10 a.u. biases cluster energies by a few percent; halving
  it from 20 a.u. changed no verdict.

## Where this appears in h_clusters

- Solver: `worker/src/hclust/analysis/dmc.py` (DMC, exact radial solver,
  pair potentials); tests in `worker/tests/test_dmc.py`
- Study: `worker/src/hclust/studies/dmc.py`, run with
  `python -m hclust study dmc`; report in `data/studies/dmc@baseline.json`
- Web app: the Extensions page, "Quantum nuclear motion: diffusion Monte Carlo"
- Plan: `doc/Plan.md`, Phase 8, DMC study

## References

- J. B. Anderson, *J. Chem. Phys.* **63**, 1499 (1975): DMC for the
  Schrödinger equation.
- I. Kosztin, B. Faber, K. Schulten, *Am. J. Phys.* **64**, 633 (1996):
  an introduction to DMC.
- M. A. Suhm, R. O. Watts, *Phys. Rep.* **204**, 293 (1991): quantum Monte
  Carlo for molecular vibrations and van der Waals clusters.
