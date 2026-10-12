# Resource budgeting

!!! info "Prerequisites"
    [Method ladders](method-ladder.md)

A high-throughput run shares one machine among many jobs. Run too few at
once and cores sit idle; run too many and they fight over memory or fill the
disk, and jobs crash in ways that look like chemistry problems. **Resource
budgeting** decides how many jobs run, with how much memory, time and disk
each, and makes the scheduler respect those limits.

## Idea

### Parallelism at the job level

There are two ways to use 16 cores: one job on 16 cores (MPI parallelism
inside the program) or 16 single-core jobs side by side. For many small jobs
the second is better: no communication overhead, a failure affects one job,
and no need to match MPI libraries between the container and the program.
It is the HTC default.

### The resources to budget

| Resource | Limit | What happens if exceeded |
|---|---|---|
| CPU | number of workers | slowdown only |
| Memory | workers × memory per job < free RAM | swapping, or the kernel kills jobs |
| Wall time | timeout per job | a stuck job blocks a worker forever |
| Scratch disk | sum over running jobs < free disk | jobs die with cryptic I/O errors |

### Estimating cost before running

A scheduler can only respect a budget if it can estimate each job's needs
before starting it. Electronic structure costs grow steeply with system
size, so a measurement on the largest system plus a scaling rule is a
practical estimate. For integral-heavy methods the disk use grows roughly
with the fourth power of the number of basis functions, which here is
proportional to m.

## How this project does it

From `resources:` in `campaigns/baseline.yaml` and the pilot measurements
(`doc/Plan.md` §3.1 and Phase 4):

- **Workers: 12**, each a single-core ORCA run (no `%pal` block, so ORCA uses one process).
  The machine has 16 cores but only about 8 of its 15 GB of RAM are free.
- **Memory: `maxcore_mb: 500`** per job (ORCA's `%maxcore`), 12 × 500 MB
  plus overhead.
- **Timeout: 360 min**, long enough for open-shell RI-MP2 numerical
  frequencies of [H₁₀](app:s/10/0/1).
- **Scratch: `scratch_budget_gb: 150`** on `/var/tmp/hclust` (the
  `SCRATCH_DIR` mount in `compose.yaml`). Each level declares its scratch use
  at m = 10 (`scratch_gb_m10` in `levels.py`: 12.5 GB for CCSD(T), 2 GB for
  RI-MP2, 0.5 GB otherwise), and the scheduler estimates

$$
\text{scratch}(m) = \text{scratch}_{m=10} \cdot (m/10)^4
$$

and starts a pending job only if the running jobs' estimates plus its own
fit in the budget (`Runner._next_pending` in `worker/src/hclust/runner.py`).
An idle pool starts anything, so a single oversized job can't deadlock the queue.

ORCA runs in `scratch/<hash>`; only the small output files are moved to
`data/jobs/<hash>/` afterwards, so the large temporary files never reach the
data directory.

### What forced these settings

- The first CCSD(T) run on H₁₀ died with "Failed to add matrix" when `/home`
  ran out of space. CCSD(T)/aVTZ needs about 12 GB of scratch for H₁₀, and its
  low-disk integral mode can't be combined with RI (Phase 4 pilot). Hence the
  separate scratch volume and the budget.
- `%maxcore` is per core and ORCA treats it as a soft limit, so the worker
  count was set by free RAM, not by core count.
- Timeouts kill the whole ORCA process tree (`orca_scf`, `orca_mdci`, …)
  through its process group, so a timed-out job leaves nothing running
  (`_kill_group` in `engines/orca.py`).

## Where this appears in h_clusters

- `resources:` in `campaigns/baseline.yaml`; `Level.scratch_gb_m10` in
  `worker/src/hclust/levels.py`; `Runner.scratch_gb` and `_next_pending` in
  `worker/src/hclust/runner.py`.
- `SCRATCH_DIR` in `.env.example` and the `/scratch` mount in `compose.yaml`.
- Wall time per attempt is recorded (`wall_s` in the `attempt` table): 51
  CPU-hours in the baseline so far.
- Web app: the [Jobs](app:jobs) page shows the run times per stage and level.

## References

- `doc/Plan.md` §3.1 (containers, parallelism, scratch) and Phase 4 (pilot and decisions).
- The [ORCA 6.1 manual](https://www.faccts.de/docs/orca/6.1/manual/): `%maxcore`, `%pal`, and memory and disk use of the
  correlation modules.
