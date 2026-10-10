# Geometry optimization

!!! info "Prerequisites"
    [Potential energy surface](../foundations/potential-energy-surface.md)

A geometry optimization finds the shape of a molecule: starting from a
guess, it moves the atoms downhill on the potential energy surface until the
forces on them vanish. It finds the *nearest* minimum, not necessarily the
lowest one, so finding all the shapes takes a
[structure search](structure-search.md) on top.

## Idea

### Following the gradient

The gradient $\mathbf{g} = \partial E/\partial\mathbf{R}$ points uphill; the
force on the atoms is $-\mathbf{g}$. Modern methods compute it
**analytically** at about the cost of one or two energies, so every step of an
optimization costs one energy plus one gradient.

Simply stepping along $-\mathbf{g}$ (steepest descent) works but is slow:
in a long narrow valley it zigzags across instead of running along the floor.

### Newton–Raphson

Better: model the surface around the current point as a parabola, using the
curvature (the Hessian $\mathbf{H}$) too, and jump straight to the parabola's
bottom:

$$
\Delta\mathbf{R} = -\mathbf{H}^{-1}\mathbf{g}
$$

On a true parabola this lands on the minimum in one step; near a minimum it
converges very fast. Its weakness is far from the minimum, where the
parabola is a poor model.

### What real optimizers do

- **Quasi-Newton**: the exact Hessian is expensive, so start from a cheap
  guess and improve it from the gradients seen so far (the BFGS update).
  This is ORCA's default.
- **Trust radius**: never step farther than some maximum, and shrink it if a
  step goes uphill.
- **Internal coordinates**: step in bond lengths and angles rather than
  Cartesian x, y, z, where the PES is closer to a parabola.
- **Convergence criteria**: stop when the energy change, the largest and RMS
  gradient components, and the largest and RMS steps are all below
  thresholds. `TightOpt` uses stricter thresholds than plain `Opt`.

## Example: H₂ by Newton–Raphson

[`h2_mp2_opt_freq.py`](#the-code) optimizes the toy H₂ from a stretched start,
R = 2.0 bohr, with numerical derivatives. Plain Newton fails:

```text
RHF, plain Newton from R = 2.0 bohr:
  step 1: R = 2.0000 bohr  E = -1.049171  gradient = +1.6e-01  curvature = +0.070
  failed: step 1 jumped to R = -0.26 bohr: not a molecule any more
```

At 2.0 bohr the RHF curve is almost flat in curvature (+0.07, close to its
inflection point), so the parabola's bottom is far away: $\Delta R = -0.16/0.07 = -2.3$
bohr, straight through the other atom. With a 0.3 bohr trust radius:

```text
RHF, Newton with a 0.3 bohr trust radius from R = 2.0 bohr:
  step 1: R = 2.0000 bohr  E = -1.049171  gradient = +1.6e-01  curvature = +0.070
  step 2: R = 1.7000 bohr  E = -1.092006  gradient = +1.2e-01  curvature = +0.187
  step 3: R = 1.4000 bohr  E = -1.116714  gradient = +2.8e-02  curvature = +0.482
  step 4: R = 1.3410 bohr  E = -1.117499  gradient = -2.9e-03  curvature = +0.582
  step 5: R = 1.3459 bohr  E = -1.117506  gradient = -2.2e-05  curvature = +0.573
  step 6: R = 1.3459 bohr  E = -1.117506  gradient = -1.4e-09  curvature = +0.573
```

Two capped steps while the model is poor, then pure Newton steps, each
squaring the error: the gradient goes 10⁻³ → 10⁻⁵ → 10⁻⁹. That fast final
convergence is the hallmark of Newton's method.

```python
--8<-- "h2_mp2_opt_freq.py:newton"
```

### The code

??? example "Run it and read the full source"
    ```sh
    docker run --rm -v ./wiki/examples:/ex hclust-worker:dev python /ex/h2_mp2_opt_freq.py
    ```
    ```python
    --8<-- "h2_mp2_opt_freq.py"
    ```

## Pitfalls

- **Local, not global.** The optimizer stops in whatever valley it starts in.
  A linear H₃⁺ chain stays linear if nothing breaks its symmetry.
- **Stuck on saddle points.** If the start has symmetry, the gradient keeps
  it, and the optimizer can converge to a saddle point. Only
  [frequencies](frequencies.md) tell.
- **Flat surfaces.** Weakly bound clusters have very soft directions (an H₂
  unit sliding around a core). The gradient is tiny everywhere, and the
  optimizer needs many steps.
- **Falling apart.** Starting from a random geometry, fragments may drift
  apart and the optimization never converges. That is a result about the
  cluster, not a failure ([structure search](structure-search.md#how-this-project-does-it)).

## Where this appears in h_clusters

- Tasks `opt` and `optfreq` (`worker/src/hclust/engines/orca.py`) add the
  level's optimization keyword: `TightOpt` for L1/L1M, `Opt` for the screening
  level L0.
- The default limit of 50 optimizer cycles was too short for floppy
  clusters (Phase 4: H₂ units still sliding after 3 × 50 cycles), so L0, L1
  and L1M set `%geom MaxIter 150`.
- When an optimization runs out of cycles, the runner **restarts** it from
  its last geometry (`_next_action` in `worker/src/hclust/runner.py`, at most
  3 attempts). In the baseline campaign so far, 372 attempts ended in a
  restart. In Phase 3, 16 of 21 H₅⁺ pre-optimizations needed one.
- Every optimized structure is stored with its parent job, so the chain from
  seed to final geometry stays traceable (`structure` table).

## References

- F. Jensen, *Introduction to Computational Chemistry*, 3rd ed., chapter on
  optimization techniques.
- H. B. Schlegel, *WIREs Comput. Mol. Sci.* **1**, 790 (2011): geometry
  optimization.
