# Job hashing and deduplication

!!! info "Prerequisites"
    None.

High-throughput computing means thousands of calculations, run and rerun
over days, with crashes, fixes and new stages in between. The simplest tool
for keeping that manageable is to give every calculation an **address
derived from its content**: a hash of exactly what was run. Identical
calculations then get the same address automatically, so nothing is ever
computed twice, and every result can be traced to its precise inputs.

## Idea

### Content addressing

A cryptographic hash function such as SHA-256 maps any text to a fixed-length
fingerprint. The same text always gives the same hash, and any change, even
one character, gives a completely different one. Collisions (two different
texts with the same hash) are practically impossible.

Hash everything that determines a calculation's result, and the hash *is* the
calculation's identity:

- the full input file (method, basis, keywords, charge, multiplicity, coordinates),
- the program version, because a different version may give different results.

Things that don't change the result (which campaign asked for it, when, on
which worker) stay out of the hash.

### What it buys

| Property | How |
|---|---|
| **Caching** | Before running, check whether a finished result with this hash exists. |
| **Deduplication** | Two stages or seeds that produce the identical input share one calculation. |
| **Provenance** | The result directory's name points back to its exact input. |
| **Safe changes** | Changing a setting changes the hash, so old and new results never get mixed up. |

The rule that makes it work: the input must be **deterministic**. Random
seed geometries are generated with explicit seeds, and coordinates are
written with fixed formatting, so planning the same campaign twice produces
byte-identical inputs.

## How this project does it

```python
def job_hash(input_text: str, version: str) -> str:
    """Content address of a job: same input + same ORCA version -> same result."""
    return hashlib.sha256(f"orca {version}\n{input_text}".encode()).hexdigest()[:16]
```

The first 16 hex characters (64 bits) name the job directory,
`data/jobs/<hash>/`. A real one from the baseline campaign,
`data/jobs/0022770b3e8c125a/job.inp`:

```text
# hclust H3+ (3) L2 sp
! CCSD(T) aug-cc-pVTZ UHF TightSCF
%maxcore 500
* xyz 1 3
H      0.5434963710    -0.6212694821    -1.0029636119
...
```

`run_orca()` in `worker/src/hclust/engines/orca.py` first looks in that
directory: if `job.out` exists and contains `ORCA TERMINATED NORMALLY`, it
parses the stored output instead of running ORCA. Only normal termination
counts; a crashed run may leave partial files behind.

### Lessons from the campaign

- **Two identical jobs at once.** For m = 1, the `chain` and `random` seed
  generators both produce a single H atom at the origin, so their jobs had
  the same hash and therefore the same scratch directory. Run concurrently,
  one deleted the directory under the other. The scheduler now holds back a
  job whose hash is already running; when it starts later it's a cache hit
  (Phase 4 incidents).
- **Changing settings mid-campaign.** When L0 switched from `TightOpt` to `Opt`
  with `MaxIter 150`, only new L0 jobs got new hashes. Finished jobs kept
  their results, and the hash records which settings each one used.
- **Retries are new hashes.** A retry with `SlowConv`, or a restart from a
  new geometry, changes the input, so each attempt has its own hash, stored in
  the `attempt` table.

## Where this appears in h_clusters

- `OrcaJob.hash`, `job_hash()` and `orca_version()` in
  `worker/src/hclust/engines/orca.py`.
- The `job` and `attempt` tables store each run's hash; the `cached` column
  of `attempt` marks cache hits (15 so far in the baseline).
- Seed generators in `worker/src/hclust/structures.py` are deterministic
  ("planning a campaign twice produces the same structures and therefore the
  same jobs").

## References

- `doc/Plan.md` §3.4 (provenance and idempotence).
- The same idea underlies Git, Nix and build caches such as Bazel's.
