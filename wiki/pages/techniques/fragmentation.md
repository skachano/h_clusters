# Fragmentation channels

!!! info "Prerequisites"
    [Potential energy surface](../foundations/potential-energy-surface.md#binding-energy-d_e-and-d_0)

Being a minimum on the potential energy surface makes a cluster *locally*
stable: small distortions don't destroy it. Whether it is stable against
falling apart is a separate question. A cluster can break into fragments
in many ways, each a **fragmentation channel**, and it is only as stable as
its weakest channel. Answering this needs the energies of every possible
fragment, which is why the campaign computes the whole grid of species.

## Idea

### Enumerating channels

H_m^n can split into two pieces, H_a^p and H_(m−a)^(n−p), where the charges
of the pieces add up to the total. Each piece must be a species the project
computes (charge −1, 0 or +1). For [H₅⁺](app:s/5/1/1) that gives four channels:

| Channel | Pieces |
|---|---|
| [H₃⁺](app:s/3/1/1) + [H₂](app:s/2/0/1) | the expected one: lose a solvating [H₂](app:s/2/0/1) |
| [H₄⁺](app:s/4/1/2) + H | lose an atom |
| [H₄](app:s/4/0/1) + H⁺ | lose a bare proton |
| [H₃](app:s/3/0/2) + [H₂⁺](app:s/2/1/2) | the charge goes to the [H₂](app:s/2/0/1) |

Each fragment can be in any computed spin state, and the plan uses the
lowest-energy one (`doc/Plan.md` §2.2). Strictly, total spin is conserved
when a cluster falls apart, so some combinations are spin-forbidden; taking
the lowest gives the most cautious estimate of the cluster's stability.

### Dissociation energy of a channel

$$
\Delta E_\text{channel} = E(\text{H}_a^p) + E(\text{H}_{m-a}^{n-p}) - E(\text{H}_m^n)
$$

with each energy the lowest found for that species at the same level of
theory. Positive means the cluster is lower in energy than the fragments.
The **weakest channel** sets the cluster's stability:

$$
D_\text{min} = \min_\text{channels} \Delta E_\text{channel}
$$

The same can be done with ZPE included ($D_{0,\min}$), or as $\Delta H(T)$
and $\Delta G(T, p)$ ([thermochemistry](thermochemistry.md)); the weakest
channel can differ between them.

### Verdicts

The plan combines this with the other stability checks into one ordered
verdict per state (`doc/Plan.md` §2.2):

```mermaid
flowchart LR
  A[unbound_electron] --> B[not_a_minimum] --> C[dissociates] --> D[metastable] --> E[bound] --> F[bound_with_zpe]
```

- `unbound_electron`: an anion that loses its extra electron
  ([electron affinity](ionization-and-electron-affinity.md)).
- `not_a_minimum`: no structure without imaginary frequencies.
- `dissociates`: every optimization fell apart.
- `metastable`: a minimum, but $D_\text{min} < 0$: some channel is downhill,
  possibly behind a barrier.
- `bound`: $D_\text{min} > 0$.
- `bound_with_zpe`: $D_{0,\min} > 0$ as well.

### Products versus process: rearrangement and barriers

A channel's $D_e$ compares two end points: the cluster at its minimum and
the products, each relaxed to its own minimum.

**Rearrangement is already included, and it lowers the cost.** Energy does
not depend on the path, so however the atoms rearrange on the way out, only
the end points count. Relaxing into the products' own structures always
releases energy compared with pulling the pieces apart frozen:

$$
D_\text{frozen} = D_e + E_\text{relaxation} \;\ge\; D_e
$$

$D_e$ (and $D_0$, with zero-point energies at the relaxed minima) is the
*adiabatic* cost, already credited with that relaxation. For [H₆⁺](app:s/6/1/2) → [H₅⁺](app:s/5/1/1) + H,
where an [H₃⁺](app:s/3/1/1) triangle must form that the cluster does not contain, the frozen
cost would be much larger than the 0.30 eV of $D_e$.

**What $D_e$ misses: a barrier on the way out.** If the minimum-energy path
rises above the products' energy (a *reverse barrier*), the real threshold is
the top of the path:

$$
E_\text{threshold} = \max\big(D_e,\ E_\text{TS} - E_\text{cluster}\big)
$$

"Which decomposition is cheapest to *achieve*" is the channel with the
lowest threshold, not the lowest $D_e$; collision-induced dissociation
experiments measure exactly these thresholds.

- **No barrier:** ion–molecule and van der Waals splits, such as
  H₃⁺(H₂)ₙ → H₃⁺(H₂)ₙ₋₁ + [H₂](app:s/2/0/1). The products attract all the way out and
  nothing has to rearrange, so the threshold equals $D_0$.
- **Possibly a barrier:** splits that need rearrangement. For [H₆⁺](app:s/6/1/2) → [H₅⁺](app:s/5/1/1) + H
  none is expected: the reverse resembles [H₂⁺](app:s/2/1/2) + [H₂](app:s/2/0/1) → [H₃⁺](app:s/3/1/1) + H, the barrierless
  ion–molecule reaction that forms [H₃⁺](app:s/3/1/1) in interstellar clouds. That is an
  expectation, not a calculation.

**Thresholds are not the whole story either.** Just above threshold the
cheapest channel dominates; at higher energies, a channel whose transition
region is "loose" (more floppy states) can outcompete it. RRKM or
phase-space theory predicts such branching ratios.

To find barriers, compute the minimum-energy path: relaxed scans along the
leaving fragment's distance, or a nudged-elastic-band (NEB) search between
the cluster and the separated products, with accurate single points along
the way ([transition states and barriers](transition-states.md)).

## Example: H₅⁺

CCSD(T)/aug-cc-pVTZ energies from the baseline campaign (lowest structure of
each species):

| Channel | Fragment energies (hartree) | ΔE (eV) |
|---|---|---|
| [H₃⁺](app:s/3/1/1) + [H₂](app:s/2/0/1) | −1.341728 − 1.172635 | **0.370** |
| [H₄⁺](app:s/4/1/2) + H | −1.850284 − 0.499821 | 4.84 |
| [H₃](app:s/3/0/2) + [H₂⁺](app:s/2/1/2) | −1.672511 − 0.602302 | 6.89 |
| [H₄](app:s/4/0/1) + H⁺ | [H₄](app:s/4/0/1) not yet computed at this level | — |

with E(H₅⁺) = −2.527957 hartree. Losing an [H₂](app:s/2/0/1) is by far the cheapest way
apart, as expected for an [H₃⁺](app:s/3/1/1) core solvated by [H₂](app:s/2/0/1): $D_\text{min}$ = 0.37 eV
(8.5 kcal/mol). Once ZPE is included it drops to 5.75 kcal/mol
([zero-point energy](zero-point-energy.md#example-h5-h3-h2)).

The missing row shows the "closure" property: a verdict for [H₅⁺](app:s/5/1/1) needs [H₄](app:s/4/0/1) to be
finished too.

## Where this appears in h_clusters

- Channel enumeration and verdicts are Phase 5 (`analysis/fragments.py`); the
  `Verdict` table stores `d_min`, `d0_min`, the verdict and the weakest
  channel per state and level (`doc/Plan.md` §3.4).
- The cation channels are the source of the odd–even alternation expected in
  §1.2: [H₅⁺](app:s/5/1/1), [H₇⁺](app:s/7/1/1), [H₉⁺](app:s/9/1/1) (an [H₃⁺](app:s/3/1/1) core plus [H₂](app:s/2/0/1) units) should be more stable than
  their even neighbours.
- The fragmentation tree and the units built on it (`analysis/units.py`)
  use $D_e$ and so assume every channel is barrierless; no dissociation
  path has been computed yet.
- The *structural* check that a single optimized structure hasn't fallen
  apart is separate: the 3.5 Å contact cutoff in
  [structure search](structure-search.md#how-this-project-does-it).
- Web app: each species page lists its channels and draws its fragmentation
  tree, e.g. [H₅⁺](app:s/5/1/1).

## References

- M. Okumura, L. I. Yeh, Y. T. Lee, *J. Chem. Phys.* **88**, 79 (1988):
  infrared spectra of H₃⁺(H₂)ₙ clusters.
- T. Baer, W. L. Hase, *Unimolecular Reaction Dynamics: Theory and
  Experiments* (Oxford, 1996): thresholds, RRKM and phase-space theory.
- `doc/Plan.md` §1 (question 3) and §2.2.
