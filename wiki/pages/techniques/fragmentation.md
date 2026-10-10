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
computes (charge −1, 0 or +1). For H₅⁺ that gives four channels:

| Channel | Pieces |
|---|---|
| H₃⁺ + H₂ | the expected one: lose a solvating H₂ |
| H₄⁺ + H | lose an atom |
| H₄ + H⁺ | lose a bare proton |
| H₃ + H₂⁺ | the charge goes to the H₂ |

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

## Example: H₅⁺

CCSD(T)/aug-cc-pVTZ energies from the baseline campaign (lowest structure of
each species):

| Channel | Fragment energies (hartree) | ΔE (eV) |
|---|---|---|
| H₃⁺ + H₂ | −1.341728 − 1.172635 | **0.370** |
| H₄⁺ + H | −1.850284 − 0.499821 | 4.84 |
| H₃ + H₂⁺ | −1.672511 − 0.602302 | 6.89 |
| H₄ + H⁺ | H₄ not yet computed at this level | — |

with E(H₅⁺) = −2.527957 hartree. Losing an H₂ is by far the cheapest way
apart, as expected for an H₃⁺ core solvated by H₂: $D_\text{min}$ = 0.37 eV
(8.5 kcal/mol). Once ZPE is included it drops to 5.75 kcal/mol
([zero-point energy](zero-point-energy.md#example-h5-h3-h2)).

The missing row shows the "closure" property: a verdict for H₅⁺ needs H₄ to be
finished too.

## Where this appears in h_clusters

- Channel enumeration and verdicts are Phase 5 (`analysis/fragments.py`); the
  `Verdict` table stores `d_min`, `d0_min`, the verdict and the weakest
  channel per state and level (`doc/Plan.md` §3.4).
- The cation channels are the source of the odd–even alternation expected in
  §1.2: H₅⁺, H₇⁺, H₉⁺ (an H₃⁺ core plus H₂ units) should be more stable than
  their even neighbours.
- The *structural* check that a single optimized structure hasn't fallen
  apart is separate: the 3.5 Å contact cutoff in
  [structure search](structure-search.md#how-this-project-does-it).

## References

- M. Okumura, L. I. Yeh, Y. T. Lee, *J. Chem. Phys.* **88**, 79 (1988):
  infrared spectra of H₃⁺(H₂)ₙ clusters.
- `doc/Plan.md` §1 (question 3) and §2.2.
