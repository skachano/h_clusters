# Selection barriers

!!! info "Prerequisites"
    [Method ladders](method-ladder.md), [Global structure search](../techniques/structure-search.md)

Most steps of a workflow act on one structure at a time: optimize this,
compute frequencies for that. A **selection** acts on a whole group: "the
best three structures of [H₇⁺](app:s/7/1/1)". It can't start until every member of the
group is known, so it is a **barrier**: a point where independent jobs must
all finish before the workflow continues. Barriers are where ranking,
deduplication and filtering happen, and where most of the workflow's
decisions are made.

## Idea

### Per-item stages and barriers

| Kind | Starts when | Example |
|---|---|---|
| Per-item | its own parent job is done | `dft` optimization of one promoted structure |
| Barrier | every job that could feed it has reached a final state | `promote`: pick the best ≤ 8 of all L0 structures of a state |

A barrier must wait for *failures* too: a job that is still retrying might
turn out to be the best structure. "Final state" means done, dissociated or
failed, with no retries left.

Barriers are per **state** here, not global: [H₃⁺](app:s/3/1/1)'s selection doesn't wait for
[H₁₀⁻](app:s/10/-1/2). That keeps the pool of workers busy. Small species pass their barriers
early and their expensive stages start while large ones are still in
pre-optimization.

### What a selection does

1. **Collect** the finished structures of the state.
2. **Drop** the dissociated ones (and, if asked, those that aren't minima).
3. **Deduplicate**: walk the structures from lowest energy up; one that
   matches an already kept structure (energy within 0.1 kcal/mol *and*
   fingerprint RMS within 0.05 Å) is marked a duplicate of it.
4. **Rank and promote** the unique ones: at most `max_per_state`, and only
   those within `energy_window_kcal` of the lowest.
5. **Record every decision**, promoted or not, with the reason.
6. **Spawn** the next stage's jobs for the promoted structures.

## How this project does it

`Runner._maybe_select` checks, whenever a job finishes, whether all upstream
jobs of that state are final; if so `Runner._select` runs once
(`worker/src/hclust/runner.py`). Selections in `campaigns/baseline.yaml`:

| Selection | From | Window | Max | Extra |
|---|---|---|---|---|
| `promote` | `pre` (L0) | 15 kcal/mol | 8 | |
| `dft_best` | `dft` (L1) | 5 kcal/mol | 3 | minima only |
| `mp2_best` | `mp2` (L1M) | 5 kcal/mol | 3 | |

Every decision lands in the `candidate` table: energy, rank, `duplicate_of`,
`dissociated`, `composition`, `source` (which seed generator), `n_imag`, and
whether it was `selected`. From the `promote` stage of the baseline so far:
1016 structures, 120 dissociated, 574 duplicates, 202 promoted.

Each selection logs one line. For singlet [H₃⁺](app:s/3/1/1) in the baseline:

```text
select H3+ (1)    promote: 22 structures, 0 dissociated, 2 unique, 1 promoted
```

22 starts (templates and random) reached only two distinct structures. The
second, 39.4 kcal/mol above the triangle (the linear chain's gap at
r²SCAN-3c, Phase 0), lay far outside the 15 kcal/mol window, so only the
triangle went on.

### Re-running a selection

Because selections are recorded rather than recomputed, changing the
selection rules needs an explicit step. When the dissociation cutoff turned
out to be wrong in Phase 4, `python -m hclust reselect` cleared the records,
and each selection ran again as its inputs finished. Jobs spawned by the old
selections were kept: they are valid calculations, so some states ended up
with more than the nominal 8 or 3 structures.

A stage added to a campaign after its barrier has passed still gets its jobs:
on the next `run`, `Runner._expand` spawns children for finished jobs and
re-spawns from existing selections (campaigns are extensible, Phase 3).

## Where this appears in [h_clusters](https://github.com/skachano/h_clusters)

- `select:` stages and `from:` links in `campaigns/baseline.yaml`; the schema
  (`energy_window_kcal`, `max_per_state`, `minima_only`, dedup tolerances) in
  `worker/src/hclust/campaign.py`.
- `Runner._maybe_select`, `_select`, `_spawn_from_selection` and `reselect`
  in `worker/src/hclust/runner.py`.
- `python -m hclust structures <campaign> --stage promote` lists the candidates.

## References

- `doc/Plan.md` §2.1 (selection) and Phase 3–4 findings.
