# H-Clusters: a High-Throughput Computational Chemistry Experiment

Implementation and experiment plan for screening hydrogen clusters
**H_m^n, m = 1…10, n ∈ {−1, 0, +1}** (and optionally several spin
multiplicities) with ORCA, and for exploring the results in a web app.

The main goal is **learning HTC computational chemistry**, so the plan favours
transparent, hand-built components over heavy frameworks. Each phase ends
with something you can run and check against known results.

---

## 1. Scientific questions

For every species H_m^n (and spin state 2S+1):

1. **Shape.** What is the lowest-energy geometry: linear, ring, planar or 3D,
   and which point group? What other low-lying isomers exist?
2. **Local stability.** Is the structure a true minimum on the potential
   energy surface (PES), i.e. are all harmonic frequencies real?
3. **Thermodynamic stability.** Is the cluster bound with respect to *every*
   fragmentation channel H_m^n → H_a^p + H_(m−a)^(n−p)? By how much
   (ΔE, ΔE+ZPE, ΔH(T), ΔG(T,p))?
4. **Electronic stability.** For anions: is the extra electron bound
   (adiabatic and vertical detachment energy > 0)? For all species: what are
   the ionization energy and electron affinity?
5. **Spin.** What is the ground-state multiplicity? How large are the
   singlet–triplet / doublet–quartet gaps?
6. **Conditions.** How does the answer change with temperature and pressure
   (via ΔG), and optionally with an external electric field or a dielectric
   environment?
7. **Method dependence.** How do xTB, DFT and CCSD(T) compare? Where does
   cheap theory fail, and why (self-interaction error, missing dispersion,
   missing diffuse functions)?

### 1.1 The species space

Electron count N = m − n ranges from 0 to 11.

| | n = −1 | n = 0 | n = +1 |
|---|---|---|---|
| m = 1 | H⁻ (2 e) | H (1 e) | H⁺ (0 e, no electronic structure: treated as a bare proton with E = 0) |
| m = 2 | H₂⁻ (3 e) | H₂ (2 e) | H₂⁺ (1 e) |
| … | … | … | … |
| m = 10 | H₁₀⁻ (11 e) | H₁₀ (10 e) | H₁₀⁺ (9 e) |

There are 30 species in total (29 non-trivial).

**Allowed multiplicities** follow from electron parity: an even N gives
1, 3, 5, …; an odd N gives 2, 4, 6, …. The maximum is N + 1.
- Baseline: the lowest allowed multiplicity plus the next one (57 states: H⁺, H and H₂⁺ have only one spin state).
- Extended (optional): up to the third allowed multiplicity where N permits
  (≈ 80 states).

### 1.2 Expected results (sanity anchors)

These are known results the pipeline must reproduce. They make good
regression tests.

| Species | Expectation |
|---|---|
| H₂ | r_e = 0.741 Å, D_e ≈ 4.75 eV (D_0 ≈ 4.48 eV) |
| H₂⁺ | r_e ≈ 1.06 Å, D_e ≈ 2.79 eV; DFT with self-interaction error gets this badly wrong |
| H⁻ | Bound, EA(H) = 0.754 eV; needs diffuse basis functions |
| H₂⁻ | Not bound (a resonance); a calculation in a finite basis may falsely "bind" it |
| H₃⁺ | Equilateral triangle (D₃h), r ≈ 0.873 Å, very stable; D_e(H₃⁺ → H₂ + H⁺) = 4.61 eV (the proton affinity, 4.4 eV, includes ZPE and thermal terms) |
| H₃ | Ground state is repulsive (dissociates to H₂ + H); linear saddle point |
| H₅⁺, H₇⁺, H₉⁺ | H₃⁺ core solvated by H₂ molecules; binding decreases with shell size |
| H₄⁺, H₆⁺, … | Even cations are less stable than their odd neighbours (odd–even alternation) |
| H_m (neutral, m > 2) | Only weak van der Waals complexes of H₂ (+ H); DFT without dispersion fails |
| H_m⁻ | Weak H⁻(H₂)_k complexes |

**Physics caveat.** Hydrogen is the lightest nucleus, so zero-point energy
(ZPE) and quantum nuclear effects are large. Weakly bound clusters that are
minima in the harmonic picture can be unbound once ZPE is included. Always
report both ΔE and ΔE+ZPE. This is one of the most instructive outcomes of
the experiment.

---

## 2. Computational strategy (method ladder)

These systems are tiny (≤ 11 electrons), so even "gold-standard" CCSD(T) is
cheap. This lets the project *benchmark* the cheap methods instead of
trusting them, which is a core HTC habit.

| Level | Method | Purpose | Approx. cost / job |
|---|---|---|---|
| L0′ | GFN2-xTB (standalone `xtb`, or ORCA `! GOAT-EXPLORE XTB`) | Candidate *geometry* generator only; its energies are not used for ranking (see Phase 0 findings) | ms–s |
| L0 | r²SCAN-3c (ORCA) | Pre-optimization and screening of all candidates | s |
| L1 | DFT: ωB97X-D4/def2-TZVPPD, analytic Hessian (was ωB97M-V, now `L1V`; swapped in Phase 4 for cost) | Geometry optimization + frequencies for every promoted candidate | s–min |
| L1M | (U)RI-MP2+RIJK/aug-cc-pVTZ | Second geometry level, free of DFT self-interaction and delocalization error (added in Phase 3: DFT has no C₂v H₅⁺ minimum). Optimize all promoted candidates; numerical frequencies only for the best 3 | min–h |
| L1′ | B3LYP/def2-TZVPPD (no dispersion) | Didactic: shows self-interaction and dispersion failures | s–min |
| L2 | (U)CCSD(T)/aug-cc-pVTZ single points on L1 *and* L1M geometries | Reference energetics; the lower of the two picks the structure | s–min |
| L3 | (U)CCSD(T)/aug-cc-pVTZ optimization (numerical gradients) + frequencies, for the final low-lying structures only | Check that the L1 geometries/minima hold | min–h |
| L4 (opt.) | CCSD(T)/aug-cc-pVQZ or CBS extrapolation | Basis-set convergence study | min–h |

Notes:
- **Diffuse functions are mandatory** for anions. Use the `D` / `aug-` bases
  throughout so all charges are treated consistently.
- **Open shells.** Use UHF/UKS and record ⟨S²⟩. Flag spin contamination
  (deviation > 10 % from S(S+1)). For singlets that may be open-shell
  (stretched H₂-like bonds), also run a broken-symmetry guess
  (`%scf GuessMix`) and keep the lower solution.
- **One-electron systems** (H, H₂⁺): HF is exact within the basis,
  so CCSD(T) is skipped. Two-electron systems: CCSD = FCI.
- **Thermochemistry** uses the rigid-rotor/harmonic-oscillator (RRHO) model
  with a quasi-RRHO treatment of low modes (Grimme). The *pressure*
  dependence enters only through translational entropy (ideal gas). Real
  high-pressure confinement is out of scope.

### 2.1 Structure search (finding the shapes)

The shape is the unknown, so each (m, n, mult) needs a global search. Three
complementary sources of candidates:

1. **Templates** (deterministic): linear chain, ring, H₃⁺ core + H₂ units,
   (H₂)_k arrangements, compact 3D polyhedra (tetrahedron, trigonal
   bipyramid, octahedron, …).
2. **Random structures**: K random geometries per state (start with K = 20)
   with a minimum-distance constraint (e.g. 0.6 Å) inside a sphere that
   scales with m^(1/3).
3. **ORCA GOAT** global optimizer (new in ORCA 6) at GFN2-xTB level. This
   source is *optional*: in Phase 3 it contributed no surviving candidate.
   `! GOAT-EXPLORE XTB`. Use the *explore* variant: plain `GOAT` treats each
   H atom as its own fragment and keeps the bonding pattern fixed, so it
   cannot turn a chain into a ring. ORCA finds xtb through the `XTBEXE`
   environment variable. GOAT's whole final ensemble is passed on as
   candidates, *not* just its global minimum, because GFN2-xTB ranks H
   clusters wrongly. GOAT with a DFT engine is too slow for HTC on one core
   (estimated ~5 h for H₃⁺), so the DFT-level search is our own parallel
   template + random search.

All candidates are pre-optimized at L0 (r²SCAN-3c). A `select` stage then
acts as a per-state barrier: it waits until every job that can feed it has
finished, and then:
1. **Deduplicates.** Two structures are duplicates if ΔE < 0.1 kcal/mol
   *and* the RMS difference of their sorted interatomic-distance vectors is
   < 0.05 Å. That fingerprint is invariant to translation, rotation and atom
   permutation.
2. **Promotes.** The unique, intact structures within 15 kcal/mol (at most
   8 per state) go on to L1 and L1M.
3. **Records every decision** in the `Candidate` table: duplicate-of, rank,
   dissociated, composition, and source (seed generator or GOAT).

Some starting points **fall apart** during optimization. If no contact
between the pieces is shorter than 2.5 Å (`dissociation_cutoff`), the
structure has dissociated. That is recorded as a result, never retried, and
never promoted. A converged optimization ends `done`, an unconverged one
`dissociated`. Bonded units (contacts < 1.15 Å) give a composition label such
as `H3·H2`.

### 2.2 Derived quantities

For each state, computed from the best structure at each level:

- `is_minimum`: number of imaginary frequencies = 0 (tolerance: |ν| < 20 cm⁻¹
  counts as numerical noise, re-optimize with tighter settings).
- **Point group** and shape class (linear / planar / 3D), principal moments
  of inertia, radius of gyration, bond graph.
- **Fragmentation energies** for all channels. Fragments can be in any charge
  state, and their spins must couple to the state's spin (spin is conserved;
  see Phase 5). Each fragment uses its best computed energy. This is why
  the *whole* species grid must be computed: a nice HTC "closure" property.
  - D_min = min over channels of ΔE_frag. Also ΔE₀ = ΔE + ΔZPE, ΔH(T) and
    ΔG(T, p).
- Ionization energy, electron affinity, and vertical detachment energy for
  anions.
- HOMO–LUMO gap, Mulliken/Löwdin charges and spin populations.
- Multiplicity ladder: E(mult) − E(ground).
- Stability verdict per state, a small ordered enum:
  `unbound_electron` < `not_a_minimum` < `dissociates` <
  `metastable` (minimum, but D_min < 0) < `bound` (D_min > 0) <
  `bound_with_zpe` (D₀,min > 0).

---

## 3. Architecture

```
               ┌──────────────────────── docker compose ────────────────────────┐
               │                                                                 │
  /opt/orca ──►│  worker (Python)      api (Python, FastAPI)    web (TypeScript)  │
   (ro mount)  │  - campaign planner   - read-only REST over    - Vite + React    │
               │  - job runner pool      results DB              - 3Dmol.js viewer │
               │  - ORCA adapter       - thermo recompute       - Plotly charts   │
               │  - parsers            - fragmentation calc     - served by nginx │
               │        │                     ▲                      │            │
               │        ▼                     │                      │            │
               │   ./data/  (bind mount: SQLite DB + raw job dirs)   │            │
               └─────────────────────────────────────────────────────┴────────────┘
```

### 3.1 Containers

- **`worker`**: `python:3.12-slim-bookworm` plus the pinned xtb release
  binary from GitHub. ORCA is **bind-mounted read-only from
  `/opt/orca`**, never copied into the image, because the ORCA licence
  forbids redistribution. Set `PATH` and `LD_LIBRARY_PATH` to include
  `/opt/orca`. Docker runs **rootless** on this machine: container root
  maps to the host user, so the container runs as root, and files in
  `./data` come out owned by you. A `user: 1000` mapping would *break*
  writes.
  - **Parallelism is at the job level**: many concurrent single-core ORCA
    jobs (`%pal nprocs 1`), not MPI. This is the HTC way for small jobs, and
    it avoids matching the container's OpenMPI to the one ORCA was built
    against. The pool size is set by the campaign. The baseline uses 12
    workers × `%maxcore 500`, because only ~8 of the 15 GB of RAM are free.
  - **Scratch:** ORCA runs in `/var/tmp/hclust/<hash>` (`HCLUST_SCRATCH`, on
    the root filesystem with ~237 GB free). Only the kept outputs are moved
    to `data/jobs/<hash>/`. The scheduler keeps the estimated scratch of
    running jobs under `scratch_budget_gb`. Each level declares its scratch
    use at m = 10, scaled by (m/10)⁴; CCSD(T)/aVTZ on H₁₀ needs ~12 GB.
- **`api`**: FastAPI + SQLModel, port 8000 (`API_PORT`). Reuses the
  `hclust` package by mounting `worker/src`. It mounts `./data` writable,
  because SQLite WAL readers need the `-shm` file, and opens the database
  with `mode=ro`, so SQLite itself refuses writes.
- **`web`**: Node 22 for development (`vite dev`). Production build is
  served by nginx, which also proxies `/api` to the `api` service.

- **`docs`**: MkDocs Material (pinned image) serving the learning wiki in
  `wiki/` at `localhost:8001` (`DOCS_PORT`). Pages are plain Markdown with
  KaTeX math, so the web app can later link to or render the same files.

Compose profiles: `compute` (worker), `serve` (api + web) and `docs`, so the
visualisation can run while no calculations are running, and the reverse.

### 3.2 Repository layout

```
h_clusters/
├── doc/Plan.md
├── compose.yaml
├── .env.example               # ORCA_DIR=/opt/orca
├── worker/
│   ├── Dockerfile
│   ├── pyproject.toml         # uv-managed
│   └── src/hclust/
│       ├── species.py         # (m, charge, mult) enumeration, parity rules
│       ├── geometry.py        # Geometry + XYZ I/O
│       ├── levels.py          # method ladder L0…L2
│       ├── results.py         # engine-independent Result
│       ├── structures.py      # seed generators, fingerprints, fragments/composition
│       ├── engines/
│       │   └── orca.py        # input rendering, hashing, run (xtb runs via ORCA GOAT)
│       ├── parse.py           # property.json (orca_2json) + text-only items → Result
│       ├── campaign.py        # campaign YAML schema (pydantic) + DAG validation
│       ├── db.py              # SQLModel tables
│       ├── runner.py          # planning, thread pool, retries, resume
│       ├── workflow.py        # stage DAG: L0 → dedup → L1 → freq → L2 → L3
│       ├── analysis/
│       │   ├── shape.py       # inertia, shape class, radius of gyration
│       │   ├── symmetry.py    # tolerant point groups + symmetry numbers (own code)
│       │   ├── thermo.py      # RRHO / qRRHO at arbitrary T, p
│       │   ├── fragments.py   # channels, spin-allowed asymptotes, D_q, verdicts
│       │   ├── verdicts.py    # DB → best reference per state → verdict rows
│       │   └── anchors.py     # §1.2 sanity anchors as checks
│       └── cli.py             # typer: `python -m hclust plan|run|status` (+ analyze|export later)
├── api/
│   ├── Dockerfile
│   └── src/hclust_api/        # reuses hclust package (installed as dep)
├── web/
│   ├── Dockerfile             # dev (Vite) and prod (nginx) targets
│   ├── src/api/               # schema.d.ts generated from api/openapi.json + hooks
│   ├── src/views/             # Grid, Species, Trends, Benchmark, Jobs
│   ├── src/components/        # 3D viewer, thumbnails, SVG charts
│   └── e2e/                   # Playwright smoke test
├── wiki/
│   ├── mkdocs.yml             # site config + nav
│   └── pages/                 # learning wiki (Markdown + KaTeX)
├── campaigns/
│   └── baseline.yaml          # declarative experiment definition
├── data/                      # git-ignored: hclust.sqlite, jobs/<hash>/…
└── tests/
```

### 3.3 Campaign definition (declarative)

Phase 2 implements `species`, `seeds`, `stages` and `resources`; see
`campaigns/demo.yaml`. The search and selection keys below arrive in Phase 3.

```yaml
# campaigns/baseline.yaml
name: baseline
species:
  m: [1, 10]
  charges: [-1, 0, 1]
  multiplicities: lowest+1      # or: lowest | all_upto: 3
search:
  templates: true
  random_per_state: 20
  goat: true
  dedup: { energy_kcal: 0.1, rmsd_angstrom: 0.1 }
  promote: { window_kcal: 15, max_per_state: 8 }
levels:
  L0p: { engine: orca, keywords: "GOAT-EXPLORE XTB", role: geometries_only }
  L0: { engine: orca, keywords: "r2SCAN-3c Opt" }
  L1: { engine: orca, keywords: "wB97M-V def2-TZVPPD TightOpt Freq" }
  L2: { engine: orca, keywords: "UCCSD(T) aug-cc-pVTZ TightSCF", on: L1.minima }
  L3: { engine: orca, keywords: "UCCSD(T) aug-cc-pVTZ NumGrad Opt NumFreq", on: lowest_per_state }
resources: { workers: 16, maxcore_mb: 600, timeout_min: 120 }
```

### 3.4 Data model (SQLite via SQLModel)

- `State(id, m, charge, mult, n_electrons)`
- `Structure(id, state_id, origin[template|random|goat|opt], parent_id, xyz, fingerprint)`
- `Campaign(id, name, spec_json)`
- `Job(id, campaign_id, state_id, stage, level, task, parent_id,
  input_structure_id, start_structure_id, modifiers, status, attempts, hash,
  error, error_kind, wall_s, created/updated)`. Each job is unique per
  (campaign, stage, input structure), and a retry reuses the same row.
- `Attempt(job_id, n, hash, modifiers, start_structure_id, status, error,
  error_kind, action, cached, wall_s)`: one row per ORCA run.
- `Result(job_id, energy, final_structure_id, s2, homo, lumo, charges,
  frequencies, modes, thermo, n_imag, point_group, opt_converged)`
- `Verdict(campaign_id, state_id, verdict, temperature, pressure, ref_job_id,
  structure_id, geometry_level, energy, zpe, d_e, d_0, d_h, d_g, channel,
  channel_g, spin_gap, detachment, ionization, homo, s2, spin_contaminated,
  point_group, shape, composition, n_candidates)`: rewritten by `analyze`.

**Provenance and idempotence.** The job hash is
`sha256(rendered ORCA input + engine version)`. Rerunning the campaign skips
completed hashes, so the campaign is *resumable* and *cacheable*. Keep the
raw `*.out`, `*.property.txt` and `*.json` files under `data/jobs/<hash>/`.
Keep the database as an index over them, never as the only copy.

### 3.5 Job runner (the HTC core, built by hand on purpose)

- A single orchestrator process owns the DB, so there are no write races in
  SQLite. A **thread** pool runs the jobs: each thread only waits on an
  external ORCA process, so no worker processes are needed.
- Each ORCA run gets its own process session. On a timeout or Ctrl-C the
  whole tree (`orca` + `orca_scf`/`orca_mdci` …) is killed, and running jobs
  go back to the queue.
- A stage DAG: a job becomes runnable when its parent result exists (e.g. a
  freq job needs an opt job).
- **Error handling playbook** (record each attempt):
  - SCF not converged → retry with `SlowConv`, then `VerySlowConv`. ORCA 6
    already falls back to TRAH by itself. At most 3 attempts per job.
  - Optimization not converged → restart from the last geometry, up to 2 times.
  - Imaginary frequency → displace along the mode (±0.1 Å, alternating sign)
    and re-optimize. After 3 attempts, keep it as a saddle point (done,
    `n_imag > 0`). Stages with `when: minimum` do not continue from it.
  - Fragmentation detected → mark as `dissociated`, store the fragments.
  - Timeout → mark as `failed` and let it surface in the dashboard.
- `hclust status` gives a live table of states × levels.
- Send a push notification when a long campaign finishes.
- Later, for comparison: port the same workflow to **jobflow/quacc** or
  **AiiDA** to see what the frameworks give you (and what they cost).

### 3.6 Example ORCA inputs

L1 optimization + frequencies:
```
! wB97M-V def2-TZVPPD TightOpt Freq TightSCF UKS
%maxcore 600
%pal nprocs 1 end
* xyzfile 1 1 start.xyz
```
L2 single point:
```
! UCCSD(T) aug-cc-pVTZ TightSCF
%maxcore 600
* xyzfile 1 1 l1_opt.xyz
```
Parse the results with `orca_2json` (ships with ORCA 6) or with the
`*.property.txt` file. Use `cclib` as a fallback.

---

## 4. Web app

The app is read-only over the results. It has five main views:

1. **Periodic grid (overview).** Rows are charge (−1, 0, +1) and columns are
   m = 1…10. Each cell shows a thumbnail of the ground-state shape, the
   multiplicity, and a colour for the stability verdict or D_min. Controls:
   method level, T, p, and ΔE / ΔE₀ / ΔG. The odd–even alternation in
   cations should jump out visually.
2. **Species detail.**
   - A 3D viewer (3Dmol.js) of the best structure. Toggle between isomers
     and multiplicities, and animate normal modes (an imaginary mode shows
     why a structure is a saddle point).
   - An isomer energy ladder and a spin-state ladder.
   - A fragmentation-channel table or bar chart that highlights the weakest
     channel.
   - Properties: point group, ⟨S²⟩, gap, charges/spins, IE/EA/VDE.
   - Links to raw ORCA outputs.
3. **Trends.** Plots versus m, one series per charge:
   - binding energy per atom
   - D_min
   - second energy difference Δ₂E(m) = E(m+1) + E(m−1) − 2E(m), which shows
     "magic numbers"
   - HOMO–LUMO gap
4. **Conditions.** A temperature slider (10–3000 K) and a log-pressure
   slider. The API recomputes ΔG for every channel from the stored
   frequencies, and the grid recolours live, so you can see which clusters
   survive at which temperature.
5. **Method benchmark + HTC dashboard.**
   - Parity plots of xTB/DFT versus CCSD(T) for energies and geometries,
     with error statistics.
   - Job counts by status, wall-time histograms and a failure log. This
     shows the operational side of HTC.

API (built in Phase 6; T in K, p in atm, energies in eV; full schema in
`api/openapi.json`, interactive at `/docs`):
```
GET /api/campaigns
GET /api/campaigns/{c}/grid?temperature&pressure&quantity=d_e|d_0|d_h|d_g
GET /api/campaigns/{c}/states?temperature&pressure
GET /api/campaigns/{c}/states/{m}/{charge}/{mult}?temperature&pressure
GET /api/campaigns/{c}/trends?quantity=binding_per_atom|d_e|d_0|d_g|second_difference|gap
GET /api/campaigns/{c}/benchmark?test=L1|L1M
GET /api/campaigns/{c}/jobs/summary
GET /api/structures/{id}.xyz
GET /api/structures/{id}/modes
GET /api/jobs/{id}
GET /api/jobs/{id}/files/{job.inp|job.out|job.property.json|job.xyz|job_trj.xyz}
```
Generate a typed TS client from FastAPI's OpenAPI schema
(`openapi-typescript`) so the frontend and backend stay in sync.

---

## 5. Phased implementation plan

Each phase has a concrete **done when** criterion.

### Phase 0: Environment (½ day) — ✅ done 2026-10-09
- `git init` this directory as its own repository. It previously sat inside
  the home dotfiles repo.
- `compose.yaml` and the worker Dockerfile, with the `/opt/orca` read-only
  mount.
- Smoke tests inside the container: `orca` HF on H₂, `xtb` on H₂, and
  `! GOAT-EXPLORE XTB` on H₃⁺. Run them with
  `docker compose run --rm worker smoke/run_smoke.sh`.
- **Done when** all three run in the container and their outputs land in
  `./data`.

**Findings:**
- Docker is rootless, so there is no UID mapping (see §3.1). ORCA 6.1.1 runs
  fine in Debian bookworm from the mount, and it finds xtb through
  `XTBEXE`.
- Plain `GOAT` keeps the bonding pattern fixed (each H atom is a separate
  fragment), so it cannot change the shape. `GOAT-EXPLORE` is required.
- **GFN2-xTB gets H₃⁺ qualitatively wrong.** It puts the linear structure
  0.9 kcal/mol *below* the triangle and gives r = 1.03 Å.
  - CCSD(T)/cc-pVTZ: the triangle has r = 0.875 Å, and linear is
    +40.5 kcal/mol higher.
  - r²SCAN-3c: the triangle has r = 0.870 Å, and linear is +39.4 kcal/mol.
  - Consequence: r²SCAN-3c is the screening level (L0), and xtb only
    proposes geometries.
- GOAT-EXPLORE with r²SCAN-3c is far too slow on one core (estimated ~5 h
  for H₃⁺: ~1400 gradients per GOAT worker, at least 24 worker runs).

### Phase 1: Single-job engine + parsing (1–2 days) — ✅ done 2026-10-09
- ORCA adapter, input templating, output parsing into `Result`, and job
  hashing.
- **Done when** H, H⁻, H₂, H₂⁺ and H₃⁺ at L1 and L2 reproduce the anchors in
  §1.2 (r_e within 0.01 Å, energies within 0.05 eV of the references for
  CCSD(T)). Encode these as `pytest` regression tests.
- How to run the tests:
  - `docker compose run --rm worker python -m pytest` runs everything.
  - Add `-m "not orca"` to skip ORCA and use only the stored fixtures.
  - Job directories are `data/jobs/<sha256(ORCA version + input)[:16]>/`.
    Finished jobs are reused rather than rerun.

**Findings:**
- Structured data comes from `orca_2json job -property`: energies,
  geometries, frequencies, normal modes, RRHO terms and charges. ⟨S²⟩,
  orbital energies, optimization convergence and point group are parsed
  from the `.out` text.
- A job counts as successful only if "ORCA TERMINATED NORMALLY" is in the
  output. A failed CCSD(T) run still leaves a `property.json` behind from
  its SCF step.
- ωB97M-V (VV10) has no analytic Hessian, so L1 uses `NumFreq` (H₃⁺: ~1 min
  on one core). CCSD(T) aborts with a single electron, so one-electron
  systems fall back to HF, which is exact within the basis.
- ORCA's point-group detection is too strict to rely on: it calls an
  equilateral L1 H₃⁺ (ΔR < 3·10⁻⁴ Å) C₂v. Our own tolerant
  `symmetry.py` (Phase 5) is required. (Done in Phase 5: it finds D₃h.)
- Anchor results (eV; L1 = ωB97M-V/def2-TZVPPD, L2 = CCSD(T)/aug-cc-pVTZ
  at the L1 geometry):

  | Quantity | L2 | L1 | Exact |
  |---|---|---|---|
  | E(H) error | 0.005 | 0.160 | 0 |
  | EA(H) | 0.728 | **0.052** | 0.755 |
  | D_e(H₂) | 4.707 | 4.715 | 4.748 |
  | D_e(H₂⁺ → H + H⁺) | 2.761 | 2.717 | 2.793 |
  | D_e(H₃⁺ → H₂ + H⁺) | 4.602 | 4.422 | 4.609 |
  | r_e(H₂⁺), Å | — | **1.137** | 1.057 |

  The self-interaction error of DFT is plain to see. ωB97M-V barely binds
  the electron in H⁻ and stretches H₂⁺ by 0.08 Å (recorded as a strict
  `xfail`). DFT *ranking* of anions and of odd-electron cations must
  therefore be checked against L2. Other L1 values: r(H₂) = 0.740 Å,
  ω(H₂) = 4454 cm⁻¹ (exact 4401), r(H₃⁺) = 0.8754 Å.

### Phase 2: Job DB + runner (2 days) — ✅ done 2026-10-09
- SQLModel schema, campaign YAML, stage DAG, worker pool, retries, the
  `status` CLI, and resumability.
- **Done when** an interrupted campaign (Ctrl-C mid-run) resumes without
  redoing finished jobs.
- Commands:
  - `docker compose run --rm worker python -m hclust run /campaigns/demo.yaml`
  - `… python -m hclust status demo`
  - `campaigns/` is mounted read-only at `/campaigns`. The database is
    `data/hclust.sqlite` (WAL mode).
- Tests: the runner logic (DAG, SCF ladder, opt restart, saddle
  displacement, interrupt/resume, crash recovery) is unit-tested with a
  scripted fake ORCA.

**Findings (demo campaign):**
- Scope: m = 1–4, two spin states, chain seeds, L0 opt → L1 optfreq → L2 sp
  on minima. That is 55 jobs, ~15 min wall time on 16 workers. One job
  failed and 8 needed retries.
- The resumability check passed. SIGINT mid-run left no ORCA processes and
  returned the 1 running job to the queue. The rerun executed only that job
  and its child, and a third run executed nothing.
  - Lesson: in a container, signal the Python process, not its `sh -c`
    wrapper.
- Displacement along imaginary modes turned a linear H₃⁺ chain into the
  equilateral triangle (0.875 Å).
- Chains also show why Phase 3 needs **fragmentation detection**. Several
  "minima" and saddle points are really separated fragments:
  - H₂ (triplet) at 4.1 Å
  - H₃ = H₂ + H at 3.9 Å
  - H₄ singlet = 2 H₂ at 3.4 Å, a saddle point with 2 imaginary modes on a
    flat van der Waals surface
  - H₄⁻ (quartet): its L0 optimization never converges while the fragments
    drift apart

### Phase 3: Structure search (2–3 days) — ✅ done 2026-10-09
- Templates, a random generator, GOAT, L0 pre-optimization, dedup by
  fingerprint, fragmentation detection, and promotion.
- **Done when** the search finds the D₃h triangle for H₃⁺ and the
  H₃⁺·H₂ (C₂v) structure for H₅⁺ starting from random geometries.
- What was built:
  - Seed generators: `chain`, `ring`, `sphere`, `h2_units`, `h3_core`, the
    `templates` bundle, and `random` (seeded, uniform in a ball,
    connected).
  - A `select` stage with the `Candidate` table.
  - Seeds can be routed to any stage (`into:`), and a stage can have several
    inputs (`from: [..]`).
  - GOAT is a task that fans its ensemble out into child jobs.
  - Campaigns are **extensible**: stages added to a finished campaign get
    their jobs on the next `run`, and only that new work runs.
  - `python -m hclust structures <campaign> --stage <name>` lists the
    structures per state.
- Acceptance campaign: `campaigns/phase3_check.yaml`, 20 random seeds per
  state.

**Findings:**
- **H₃⁺:** all 20 random starts reach the triangle (L0 0.870 Å, L1 0.875 Å,
  MP2 0.871 Å).
- **H₅⁺: DFT has no C₂v minimum.**
  - At r²SCAN-3c and ωB97M-V, all 20 random starts (and the `h3_core`
    template, which starts as C₂v H₃⁺·H₂) end in the proton-shared
    [H₂–H–H₂]⁺ structure: D₂d, 4 × 1.13 Å, a minimum with all frequencies
    real. A planar variant lies 0.29 kcal/mol higher at L0.
  - MP2/aug-cc-pVTZ has the C₂v H₃⁺·H₂ minimum (H₂ 0.761 Å, H₃⁺ unit
    0.811/0.969/0.969 Å), while D₂d is a saddle point (546i cm⁻¹). The
    runner displaced both promoted structures along their imaginary modes
    into C₂v.
  - CCSD(T)/aVTZ: C₂v is 0.13 kcal/mol below D₂d at MP2 geometries, and
    0.16 kcal/mol below the ωB97M-V geometry. This matches the literature.
  - This is DFT delocalization error favouring a delocalized, shared proton.
    Hence the new **L1M (MP2) geometry level** next to L1.
  - Physics caveat: 0.13 kcal/mol is far below H₅⁺'s zero-point energy, so
    the real molecule is fluxional.
- **GOAT (xTB):** 220 s for H₅⁺. Its single ensemble member (xtb's linear
  chain) was the one optimization that never converged, so it added no
  candidate. GOAT is therefore off by default for Phase 4 (cost grows with
  m; value so far is zero).
- **Optimizer behaviour:** 16 of the 21 H₅⁺ pre-optimizations needed a
  restart. Optimizations started from random geometries often exceed
  ORCA's default cycle limit, and the restart rule recovers them.

### Phase 4: Full baseline campaign (1 day, plus compute time) — ✅ done 2026-10-11
- Run L0 → select → L1 and L1M (+freq) → L2 for all 29 species × baseline
  multiplicities.
- `campaigns/baseline.yaml` has 56 states and 1,293 initial L0 jobs
  (templates + 20 random seeds per state). The pipeline is:
  1. `pre` (L0) → `promote` (15 kcal/mol, ≤ 8 per state)
  2. DFT branch: `dft` (L1 optfreq) → `dft_best` (minima only, 5 kcal/mol,
     ≤ 3) → `dft_ref` (L2)
  3. MP2 branch: `mp2` (L1M opt) → `mp2_best` (5 kcal/mol, ≤ 3) →
     `mp2_freq` (L1M optfreq) → `mp2_ref` (L2 on minima)
- Launch: `docker compose run -d --name hc-baseline worker python -m hclust run /campaigns/baseline.yaml`.
  Follow it with `docker logs -f hc-baseline` and `… python -m hclust status baseline`.
- **Done when** every state has a terminal status, and failures are
  explained or fixed.

**Pilot (H₁₀, one core) and the decisions it forced:**

| Step | Time |
|---|---|
| r²SCAN-3c gradient | 3 s (closed shell), 15 s (open shell) |
| ωB97M-V gradient | 100 s; numerical frequencies ≈ 60 gradients ≈ **2.1 h** per structure |
| ωB97X-D4 gradient | 48 s; analytic Hessian 231 s, so opt + freq ≈ **16 min** |
| MP2/aVTZ gradient (conventional) | 200 s closed shell, **880 s** open shell; numerical frequencies 4–15 h |
| RI-MP2+RIJK/aVTZ gradient | 38 s (no analytic RI-MP2 Hessian in ORCA 6.1) |
| CCSD(T)/aVTZ | **13 min, 12 GB scratch disk**. The default run died with "Failed to add matrix" when `/home` ran out of space. `KC_AOX` needs as much disk and cannot be combined with RI transformation. |

What the plan as written would have cost: ~800 CPU-hours (2–3 days on 16
cores), and CCSD(T) for H₉/H₁₀ could not run at all with 14 GB free.

Decisions:
- L1 = ωB97X-D4. Like ωB97M-V it gives D₂d H₅⁺, and it reproduces the
  Phase 1 anchors.
- L1M = RI-MP2+RIJK. It keeps the C₂v H₅⁺, which is now an ORCA regression
  test. Note that MP2/**aVDZ** already collapses H₅⁺ to D₂d, so the
  triple-ζ basis is required.
- MP2 frequencies only after a second selection (≤ 3 per state).
- Scratch on `/var/tmp`, with a disk budget in the scheduler.
- Estimate: ~120 CPU-hours ≈ 10–14 h on 12 workers.

**Incidents:** the first launch crashed within minutes. Two *identical*
jobs ran at the same time: for m = 1 the `chain` and `random` seeds give the
same atom, so the hash and therefore the scratch directory were the same,
and one job deleted the directory under the other. The scheduler now holds
back a job whose hash is already running (it then becomes a cache hit). Any
exception inside a job now fails only that job, not the orchestrator. The
restart recovered the 12 interrupted jobs.

**Second incident, about 1.5 h in:** 5 H₇⁺/H₇⁻ L0 pre-optimizations failed
after 3 × 50 `TightOpt` cycles. They were not stuck: they were still
descending (ΔE ≈ 3–7·10⁻⁵ Eh, steps up to 0.14 Å) as H₂ units slid across a
flat surface.
- Fix: L0 now uses `Opt` with `%geom MaxIter 150`. It is only a screening
  level; L1 and L1M re-optimize tightly. Other levels keep their inputs and
  hashes.
- New command `python -m hclust retry-failed <campaign> [--stage]` gives
  failed jobs fresh attempts. It skips jobs whose state's selection already
  ran: 1 H₇⁻ start stays failed.
- The orchestrator was stopped with `docker stop` (12 running jobs went
  back to the queue), and the failures were requeued and resumed. Jobs that
  were already done keep their `TightOpt` results; the job hash records
  which settings each one used.

**First pass finished** after ~13 h: 1,322 done, 333 dissociated, 27 failed.

Failure causes:
- 14 ωB97X-D4 frequency jobs: the CP-SCF solver of the analytic Hessian
  did not converge, mostly on open-shell states. These are now classified as
  `cpscf` and retried with `NumFreq` from the optimized geometry, which the
  parser now recovers from failed runs.
- 12 ωB97X-D4/RI-MP2 optimizations ran out of 3 × 50 cycles on floppy m ≥ 7
  clusters. L1 and L1M now get `MaxIter 150`.

Review of the "dissociated" structures showed that the **2.5 Å cutoff was
wrong**:
- Converged MP2 structures with contacts of 2.5–3.3 Å are real complexes:
  H⁻·H₂ (2.84 Å), H₃⁺(H₂)₃, and H₂·H / (H₂)₂ van der Waals pairs (~3.3 Å).
  They were discarded before reaching CCSD(T).
- Fragments that really flew apart are ≥ 5 Å apart (e.g. the DFT anions).
- The cutoff is now **3.5 Å**, as §2.1 originally suggested. Whether a
  complex is *bound* is an energetic question for Phase 5.

Repair:
1. `python -m hclust reselect` cleared all 1,232 selection records.
2. `retry-failed --reopen` requeued 267 jobs: the 27 failures, plus 240
   "dissociated" optimizations whose last geometry is intact at 3.5 Å, which
   restart from that geometry.
3. The relaunched campaign redoes every selection as its inputs finish.

Jobs created from the old selections are kept. They are valid calculations,
so some states end up with more than the nominal 8/3 structures.

**Second pass finished** after ~27 h more (it was stopped once with
`docker stop` and resumed with `docker start hc-baseline`; 2 jobs were
requeued and nothing else was lost):

| | Jobs |
|---|---|
| Done | 1,963 |
| Dissociated | 143 |
| Failed | 12 |
| Total | 2,118 (462 needed a retry) |

- 148 CCSD(T) reference energies (`dft_ref` 60, `mp2_ref` 88) for 56 states.
- ~181 CPU-hours of ORCA in total, against the 120 estimated. My 4–8 h
  estimate for the rerun was wrong: at 3.5 Å many neutral and anion states
  promote 8 structures instead of 0–3, which added ~360 jobs, mostly at
  m ≥ 8.

  | Stage | Jobs | CPU-hours |
  |---|---|---|
  | `pre` (r²SCAN-3c) | 1,284 | 26 |
  | `dft` (ωB97X-D4 opt+freq) | 277 | 56 |
  | `mp2` (RI-MP2 opt) | 277 | 42 |
  | `mp2_freq` (RI-MP2 opt+NumFreq) | 120 | 43 |
  | `dft_ref` + `mp2_ref` (CCSD(T)) | 145 | 13 |

**Failure review (second pass):**
- **25 "failures" were dissociations.** 24 ωB97X-D4 CP-SCF failures (neutral
  H₃, high-spin H₄–H₈, triplet H₃⁻) and 1 SCF failure (H₁₀⁻ → 5 H₂) had a
  last geometry in pieces. The runner correctly did not retry them, but it
  labelled a job `dissociated` only after a failed *optimization*.
  - Fix: any terminal failure whose last geometry is fragmented is now
    `dissociated`.
  - `python -m hclust relabel <campaign>` repairs existing rows.
- **The 12 remaining failures are unbound anions, not optimizer trouble.**
  They are RI-MP2 optimizations of H₇⁻–H₁₀⁻ (doublets, triplets, quartets)
  that ran 3 × 150 cycles.
  - In every one the HOMO lies at **+0.9 to +1.15 eV**, while bound anions
    (H⁻ and the H⁻-containing odd-m singlets) lie at −1.4 eV.
  - Such an anion cannot hold its extra electron. A free electron in a
    finite basis set settles in the most diffuse functions (a
    pseudo-continuum state near +1 eV in aug-cc-pVTZ), and that state shifts
    unevenly as the H₂ units move. The energy climbed by up to +23 kcal/mol
    over a trajectory, almost all of it in the HF part, with S² = 0.750
    throughout and forces of ~10⁻⁵ next to 0.02–0.16 Å steps.
  - Chemistry: a hydrogen anion holds the electron only as H⁻ (two paired
    electrons). (H₂)ₙ⁻ doublets and quartets have no H⁻, and odd-m triplets
    would need an unpaired electron next to it.
  - They are left failed: no further optimization can converge a structure
    that does not exist.

**Unbound-anion flag.** The problem is wider than the failures: most
*converged* anion results in those states sit at +1 eV too, so their
geometries and CCSD(T) energies are basis-set artefacts.
- `Level.unbound_homo_ev`: an anion whose HOMO lies above **+0.5 eV** is
  `unbound`. It applies to ωB97X-D4, ωB97M-V, RI-MP2 and the HF reference of
  CCSD(T).

  | Level | Bound anions (HOMO) | Unbound anions (HOMO) |
  |---|---|---|
  | r²SCAN-3c (no flag) | H⁻ at **+6.4 eV** | — |
  | ωB97X-D4 | ≤ +0.13 eV | ≥ +0.89 eV |
  | RI-MP2, HF reference of CCSD(T) | ≤ −0.74 eV | ≥ +0.92 eV |

  r²SCAN-3c cannot tell (self-interaction error, no diffuse functions), so
  its results are never flagged and the screening stage passes everything
  on.
- `result.unbound` and `candidate.unbound` columns. Selections skip unbound
  structures like dissociated ones, the selection log counts them, and
  `structures` marks them `e⁻`. `relabel` fills in the flag for stored
  results: **126 baseline results are unbound**.
- Selections made before the flag existed were not redone: 33 unbound
  structures had been promoted, so some MP2 frequency and CCSD(T) time went
  into them. Their results carry the flag.

| Anion states | Verdict from the HOMO |
|---|---|
| H⁻, odd-m singlets H₃⁻–H₉⁻ (all contain H⁻) | bound at every level |
| H⁻ triplet, H₂⁻ (both spins), even-m doublets H₄⁻–H₁₀⁻, H₇⁻ and H₉⁻ triplets | unbound at every level |
| even-m quartets, H₃⁻ and H₅⁻ triplets | mixed: some structures bound (see below) |

The H₃⁻ triplet is bound at ωB97X-D4 but unbound at RI-MP2. The final
verdict for every anion comes from the CCSD(T) electron affinity (Phase 5).

**Trapped tetrahedral H₄⁻ (quartet).** The bound quartets near −3.5 eV are
all one unit: a regular H₄ tetrahedron (1.76 Å at MP2, 1.85 Å at ωB97X-D4,
charge −0.25 on each atom, S² ≈ 3.77). H₆⁻–H₁₀⁻ quartets add 1–3 H₂
molecules at ~1.8 Å.
- Five electrons in four 1s orbitals: a₁² t₂³, three parallel spins that
  cannot pair into H–H bonds. It is a true minimum (no imaginary
  frequencies at ωB97X-D4 or MP2), and the electron is bound (vertical
  detachment ≈ 3.5 eV).
- CCSD(T) energies against fragment limits:

  | Compared with | H₄⁻ | H₆⁻ | H₈⁻ | H₁₀⁻ |
  |---|---|---|---|---|
  | H⁻ + 3 H (+ H₂ molecules) | −1.53 eV | −1.59 | −1.67 | −1.73 |
  | H₂ molecules + 2 H + free e⁻ | **+2.45 eV** | +2.38 | +2.31 | +2.25 |
  | neutral triplet + free e⁻ | +2.45 eV | +2.40 | +2.33 | +2.28 |

- So it is **metastable**: ~2.4 eV (≈55 kcal/mol) above the open, spin-allowed
  channel H₂ + H + H + e⁻, and kinetically trapped. Each attached H₂ lowers
  the gap by only ~0.07 eV.
- At ωB97X-D4 it was often the lowest *bound* structure of its state, so
  `dft_best` sent it to CCSD(T) (H₈⁻, H₁₀⁻ quartets). That is a correct
  result but not the state's ground arrangement; the Phase 5 verdict
  (`metastable`) must come from fragment limits, not from the flag.
- Not yet analysed: an H₃ triangle with an attached H₂ in the H₅⁻ triplet
  (HOMO −2.1 eV, 35 kcal/mol above the state's lowest CCSD(T) energy)
  looks like the same kind of trapped structure.

**Lessons:**
- A failure label is a claim. Check it (here: the last geometry and the
  HOMO) before retrying, and fix the classifier, not just the rows.
- For anions, check that the extra electron is bound before trusting a
  geometry. The HOMO sign is a cheap first test at levels with diffuse
  functions and little self-interaction error; the energy comparison is the
  real one.

### Phase 5: Analysis library (2 days) — ✅ done 2026-10-11
- Point groups, thermo (RRHO/qRRHO at any T, p, cross-checked against
  ORCA's own thermo at 298 K), fragmentation channels, and verdicts.
- **Done when** `hclust analyze` produces a verdict table that agrees with
  §1.2.
- What was built (`worker/src/hclust/analysis/`):
  - `thermo.py`: ideal-gas RRHO with Grimme's quasi-RRHO entropy at any T
    and p, ORCA's conventions (harmonic thermal energy, qRRHO entropy with
    ν₀ = 100 cm⁻¹, modes < 1 cm⁻¹ dropped, S_el = k ln(2S+1)).
  - `symmetry.py`: our own point-group detector with a 0.05 Å tolerance
    (no pymatgen dependency) and the rotational symmetry number.
  - `shape.py`: principal moments, linear/planar/3D, radius of gyration.
  - `fragments.py`: binary channels (charges −1…+1) plus electron
    detachment for anions, lowest asymptotes by recursion (so binary
    channels reach every multi-fragment limit), D_q for q = E, E₀, H(T),
    G(T, p), and the verdict ladder.
  - `verdicts.py`: picks each state's reference structure and writes the
    `verdict` table; `anchors.py`: §1.2 as 17 checks.
  - `python -m hclust analyze <campaign> [-T K] [-p atm] [--check]`.
- **The reference energy of a state** is its lowest CCSD(T)/aVTZ single
  point (on an ωB97X-D4 or RI-MP2 geometry, whichever is lower) on a
  structure that is a minimum at its geometry level and not flagged as an
  unbound anion. ZPE and thermal terms come from that geometry's own
  frequencies (ωB97X-D4 or RI-MP2, unscaled).
- Verdicts for states without a reference: `unbound_electron` (an anion
  whose results are all flagged), `not_a_minimum` (intact structures, none
  a minimum), `dissociates` (nothing intact). H and H⁺ are `atom`.

**Decisions made while building it:**
- **Spin is conserved.** First version: fragments took their lowest energy
  over all spins. Then every high-spin state "dissociated" into low-spin
  fragments and its D just repeated its spin gap (H₄⁻ quartet: −7.2 eV
  against H₂ + H₂ + e⁻). Now fragment spins must couple to the state's
  spin, |S₁ − S₂| ≤ S ≤ S₁ + S₂ (the electron has S = ½). Hydrogen has no
  spin–orbit coupling to drive a spin-forbidden break-up; that a state is
  not the species' ground state is what the separate `spin_gap` says.
- **Own point groups.** ORCA's detection is too strict (Phase 1). Ours
  agrees with ORCA on the symmetric cases (H₂, H₂⁺, C₂ᵥ H₅⁺/H₇⁺, D₃h H₃⁺)
  and finds the textbook symmetry where ORCA says C₁: D₂d H₆⁺, D₃h H₉⁺,
  D₃h for the triplet H₃⁻. 23 of 42 best structures differ from ORCA;
  at a 0.005 Å tolerance most floppy ones drop back to C₁, which measures
  how floppy they are.
- **qRRHO residual.** ORCA reproduces to 10⁻⁶ Eh except for modes below
  ~50 cm⁻¹, where ORCA's free-rotor entropy is ~0.03 k per mode lower than
  Grimme's published formula (survey of 300 jobs; no single constant
  explains it). Effect: ≤ 1.5·10⁻⁴ Eh (0.1 kcal/mol) in TS at 298 K for the
  floppiest clusters.
- **Conventions and gaps:** the free electron has E = 0 and no thermal
  terms; the bare proton has E = 0 and translational terms only. No
  counterpoise correction: van der Waals D_e values of ~0.01 eV are of the
  order of the aVTZ basis-set superposition error. Vertical detachment
  energies need neutral single points at anion geometries, which were not
  run; the HF HOMO (Koopmans) is stored instead.

**Results (CCSD(T)/aug-cc-pVTZ, 298.15 K, 1 atm):** 17/17 anchors pass.

| Anchor | Computed | Reference |
|---|---|---|
| H₂ r_e, D_e, D₀ | 0.743 Å, 4.707 eV, 4.432 eV | 0.741 Å, 4.747, 4.478 |
| H₂⁺ r_e, D_e | 1.058 Å, 2.789 eV | 1.057 Å, 2.79 |
| EA(H) | 0.728 eV | 0.754 |
| H₃⁺ | D₃h, 0.871 Å, D_e(H₂ + H⁺) 4.601 eV | D₃h, 0.873 Å, 4.61 |
| H₂⁻ (both spins) | unbound_electron | not bound |
| H₃ (2) | bound by 0.001 eV (van der Waals H₂·H), D₀ −0.008 eV | falls apart |
| H₅⁺, H₇⁺, H₉⁺ | H₃⁺ core + H₂, D_e 0.370 > 0.216 > 0.191 eV | binding decreases |
| H-atom separation energy of Hₙ⁺ | odd n 4.6–6.5 eV, even n 0.08–0.29 eV | odd–even alternation |
| Neutral H_m, m > 2 | D_e ≤ 0.010 eV, D₀ < 0 | weak vdW complexes |
| Odd H_m⁻ | singlet H⁻(H₂)ₖ, D_e 0.02–0.12 eV | weak complexes |
| Even H_m⁻ | doublets unbound, quartets metastable | (new anchor, see below) |

Verdicts per state:

| Verdict | States |
|---|---|
| bound_with_zpe | H⁻, H₂, H₂⁺, H₃⁺, all doublet/singlet cations H₄⁺–H₁₀⁺, the triplet/quartet cations H₃⁺ (3), H₄⁺ (4), H₅⁺ (3), H₆⁺ (4), H₇⁺ (3), H₁₀⁺ (4) |
| bound (D_e > 0, D₀ < 0) | neutral ground states H₃–H₉, H₁₀ (3), the H₄/H₆/H₈ triplets and H₉ (4); H₃⁻/H₅⁻/H₇⁻/H₉⁻ singlets; H₈⁺ (4), H₉⁺ (3) |
| metastable | H₃⁻ (3), H₅⁻ (3), and the H₄⁻–H₁₀⁻ quartets (tetrahedral H₄⁻ core, −2.3 to −2.5 eV) |
| unbound_electron | H⁻ (3), H₂⁻, H₄⁻/H₆⁻/H₈⁻/H₁₀⁻ doublets, H₉⁻ (3) |
| not_a_minimum | H₇ (4), H₁₀ (1): floppy (H₂)₅ with 2–3 imaginary modes below 80 cm⁻¹ after 3 displacements |
| dissociates | H₂ (3), H₃ (4), H₅ (4), H₇⁻ (3) |

**Findings:**
- **Zero-point energy decides most weak complexes.** Every neutral cluster
  (D_e 0.001–0.010 eV) and every H⁻(H₂)ₖ anion (0.016–0.115 eV) is bound
  in D_e and unbound in D₀: the physics caveat of §1.2, now quantified.
- **The ion clusters survive ZPE:** H₅⁺ (D₀ 0.24 eV), H₇⁺ (0.10), H₉⁺
  (0.11) and the even H₄⁺–H₁₀⁺ (0.03–0.24 eV). D₀ is not monotonic
  (H₉⁺ ≥ H₇⁺) although D_e is: harmonic ZPE of floppy modes is the weak
  point.
- **Temperature:** D_G(20 K) ≈ D₀. At 298 K and 1 atm, H₇⁺ and H₉⁺ have
  D_G < 0 (entropy wins); at 1000 K only H₂ and H₃⁺ stay bound.
- **Triplet H₃⁺** is a bound linear minimum, D_e 0.37 eV against
  H₂⁺ + H. To my knowledge the literature puts the well depth near this
  value, though I have not checked a source.
- **Even anions** have no bound state at all: the doublets cannot hold the
  electron, and the quartets are trapped tetrahedral H₄⁻ cores ~2.4 eV
  above H₂ molecules + 2 H + e⁻ (Phase 4).

### Phase 6: API (1–2 days) — ✅ done 2026-10-11
- FastAPI endpoints from §4, an OpenAPI schema, and caching for `/grid`.
- What was built (`api/`):
  - `docker compose --profile serve up api` → http://localhost:8000/docs.
    The image holds only the dependencies (uv, `api/uv.lock`); the API and
    `hclust` sources are mounted, and uvicorn reloads on changes.
  - `service.py`: one `Store` per process. `load()` reads the database
    (~1.5 s for the baseline) and is cached until a cheap fingerprint
    (job count, last job update, result count) changes; `evaluate()` at a
    given T and p (~15 ms) sits in an LRU of 256 entries. Measured: first
    grid 1.46 s, a new temperature 30 ms, a repeated one 9 ms.
  - The analysis was split into `load()` (database → plain data, no session)
    and `evaluate(data, T, p, geometry_level, energy)` for this. The same
    code feeds `hclust analyze`.
  - **Ground state of a species** (grid cell): the multiplicity with the
    lowest intact energy at the geometry level (RI-MP2 first), minimum or
    not. So H₁₀ shows its singlet (`not_a_minimum`), not the triplet that
    happens to have a reference, and even anions show their unbound
    doublet.
  - State detail adds the full **channel table** (each binary split with the
    spin-allowed limit it leads to, e.g. `H3 + H` → `H2 + H + H`), the
    isomer ladder, the multiplicities, IE/detachment, HF HOMO/LUMO and
    the geometry.
  - `api/openapi.json` is committed for the web app's generated TypeScript
    client; a test fails when it is out of date
    (`python -m hclust_api.openapi` regenerates it).
  - 10 API tests run a small campaign through the real runner with a fake
    ORCA and read it back over HTTP.

**Benchmark (D_e at the geometry level's own energies against CCSD(T) on
the same structures):**

| Level | States | MAE | Max error |
|---|---|---|---|
| ωB97X-D4/def2-TZVPPD | 34 | 0.084 eV | 0.64 eV (H₃⁻) |
| RI-MP2/aug-cc-pVTZ | 33 | 0.037 eV | 0.37 eV (H₄⁻ quartet) |

- The anions dominate both. ωB97X-D4 gives EA(H) = 0.20 eV (CCSD(T)
  0.73 eV), yet binds H⁻·H₂ at its own geometry by +0.42 eV where
  CCSD(T) at that geometry says −0.22 eV: delocalization error, as for
  H₅⁺ in Phase 3. MP2 underbinds H⁻ by 0.25 eV.

### Phase 7: Web app (4–6 days) — ✅ done 2026-10-11
- Grid → detail → trends → conditions → benchmark/dashboard, in that order.
  The grid plus the 3D viewer are the minimum viable app.
- What was built (`web/`, React 19 + TypeScript + Vite 7):
  - `docker compose --profile serve up` → http://localhost:5173 (Vite dev
    server, hot reload, proxies `/api`). `--profile prod` builds the static
    app into nginx (75 MB image, port 8080; nginx proxies `/api` and serves
    client-side routes).
  - Typed client: `npm run gen:api` turns `api/openapi.json` into
    `src/api/schema.d.ts` (openapi-typescript); requests go through
    openapi-fetch and TanStack Query (refetches keep the previous frame).
  - **Grid:** rows = charge, columns = m; each cell is the species' ground
    state with a projected shape thumbnail, multiplicity, verdict and the
    chosen D. **Conditions** are a log temperature slider (10–3000 K), a
    log pressure slider (10⁻⁶–10³ atm) and D_e / D₀ / D_H / D_G; they live
    in the URL, so every view and link agrees, and the grid recolours live
    (cached evaluations, Phase 6). A table view carries the same data.
  - **Species detail:** 3Dmol.js viewer (structure rotated onto its
    principal axes) with **normal-mode animation** (imaginary modes
    labelled), channel chart (each spin-allowed split and where it ends
    up, D_e/D₀/D_G), isomer table, spin-state ladder, properties, and links
    to the raw ORCA input/output. Lazy-loaded: 3Dmol is most of the bundle.
  - **Trends** (binding per atom, D_e, D₀, D_G, Δ₂E, HOMO–LUMO gap),
    **Benchmark** (parity plots ωB97X-D4 and RI-MP2 vs CCSD(T), error
    tiles, worst states), **Jobs** dashboard (counts, per-stage table,
    run-time histograms, failure log with output links).
  - Light and dark themes (system default plus a toggle); phone width works
    (the grid scrolls inside its card).
- **Charts follow a data-viz method** (plain SVG, no chart library):
  - Colour is assigned by job and the palettes were *validated*, not
    eyeballed: charge = 3 categorical slots (all-pairs CVD ΔE ≥ 9.2);
    stability = 3-step ordinal blue (metastable < bound < bound with ZPE;
    the three "no structure" verdicts are neutral gray plus text); D = a
    binned blue/red diverging scale with a gray midpoint (|D| < 0.01 eV).
    The red arm was derived at the blue ramp's OKLCH lightness; both arms
    pass the ordinal checks in light and dark.
  - Identity is never colour alone: verdict text in every cell, legends,
    marker shapes per charge (anion and neutral binding energies per atom
    coincide almost exactly, so the anions are rings around the neutral
    dots), table views, tooltips on hover and keyboard focus.
- **Tests:** 10 Vitest tests (helpers; grid and species views against a
  mocked API, 3Dmol mocked) and a Playwright smoke test in the
  `mcr.microsoft.com/playwright` image (`--profile test run --rm e2e`):
  grid → H₃⁺ detail (weakest channel H₂ + H⁺, 3D canvas present), and
  H₇⁺ D_G changing sign between 20 K and 1000 K.
- Found by looking at screenshots (Playwright, light/dark/phone): the 3D
  view showed H₅⁺ from an uninformative angle; trend lines scaled their
  text to ~18 px; anion markers hid under neutral ones; duplicate isomers
  (the same structure reached on several paths) cluttered the ladder; and
  Vite rejected the `web` host name used by the test container.

### Phase 8: Extensions — ✅ first round done 2026-10-11
- Chosen: gap-fillers (vertical energies, counterpoise), anharmonic ZPE for
  H₅⁺, electric field and CPCM, the L3/L4 basis study; added on the way:
  bond orders and per-atom populations in the 3D viewer.
- **Study framework** (`worker/src/hclust/studies/`): jobs outside the stage
  DAG, run with `python -m hclust study <name>`. Same content-addressed
  jobs and resume as the campaign (one SlowConv retry on SCF failure),
  results in the `study_result` table, a report in
  `data/studies/<name>@<campaign>.json`, served at
  `/api/campaigns/{c}/studies/{name}` and shown on the **Extensions** page.
  A study's `data()` is recomputed from the kept outputs on every rerun,
  so analysis fixes need no new ORCA runs. Engine additions: ghost atoms
  (`H:`) and extra input blocks; inputs without them hash as before.
- **Vertical energies** (CCSD(T)/aVTZ, 39 jobs): VDE(H⁻) = 0.728 eV
  (experiment 0.754; 0.748 at CBS). Vertical ionization of the radical
  neutrals ≈ 13.5 eV (the H atom's, 13.6) and of the closed-shell ones
  ≈ 16.1 eV (H₂'s), against adiabatic 8.2–9.0 and 13.0–13.5 eV: the cation
  relaxes to an H₃⁺ (or H₂⁺) core. The metastable
  high-spin anions have positive VDEs (0.8–2.1 eV) although the extra
  electron is unbound adiabatically.
- **Counterpoise** (88 jobs; fragments of the weakest channel, ghosts on the
  partner): BSSE ≤ 5 meV, every complex stays bound in D_e. D₀ after CP is
  unchanged in sign: ZPE, not basis-set error, unbinds the neutral and
  H⁻(H₂)ₖ complexes.
- **Anharmonic ZPE (VPT2, RI-MP2).** ORCA 6.1's VPT2 could not be used (it
  needs analytic Hessians, which RI-MP2 lacks; DFT has no C2v H₅⁺
  minimum), so it is ours (`analysis/vpt2.py`): quartic force field from
  Hessians at ±0.05 amu^½·bohr along each mode, χ from Franke, Stanton &
  Douberly (JPCA 2021), G₀, Watson and Coriolis terms. Validated by exact
  diagonalization of model potentials (error ∝ λ⁴; deliberately broken
  formulas fail). Results: H₂ correction −22 cm⁻¹ (matches the exact
  −ωₑxₑ/4 + Y₀₀); H₃⁺ VPT2 ZPE 4417 cm⁻¹ against ≈ 4362 accurate (VPT2 is
  known to struggle there); H₅⁺ −444 cm⁻¹, so **D₀(H₅⁺ → H₃⁺ + H₂) rises
  from 0.244 to 0.280 eV**. The 203 cm⁻¹ torsion and the shared-proton
  modes make H₅⁺ a hard case for VPT2: treat ±0.02 eV as the uncertainty.
- **Basis set and geometry (L3/L4):** CCSD(T) aVTZ → CBS(3/4) changes D_e by
  ≤ 0.045 eV (H₂: 4.751 eV, exact 4.748). CCSD(T)/aVTZ optimizations lower
  the energy by only 3–8 cm⁻¹ against the RI-MP2 structures (H₃⁺ 0.8749 Å,
  accurate 0.873). H₅⁺ D2d − C2v: 0.135 → 0.139 kcal/mol (≈ 48 cm⁻¹) — far
  below the ZPE, so H₅⁺ is effectively fluxional.
- **Dielectric (CPCM, ωB97X-D4, ε = 2/10/80):** ion–molecule complexes lose
  80–95 % of D_e by ε = 80; neutral H₄ barely changes. The gas-phase DFT
  numbers overbind the H⁻ complexes (H₃⁻: 0.43 eV vs 0.05 eV at CCSD(T),
  self-interaction error), so only the trend means anything.
- **Electric field (ωB97X-D4, 0–0.02 a.u. ≈ 1 V/Å, neutral clusters):** α_zz(H₂)
  = 6.54 a.u. (reference 6.38), rising with F. D_e changes by ≤ 3 meV ≈
  −½·Δα·F²: van der Waals binding is insensitive. Getting there took two
  fixes: with a field ORCA optimizes in Cartesians, and (1) the orientational
  torque (~10⁻⁵ Eh/rad²) is the size of the DFT grid noise, so every field
  job uses DefGrid3; (2) the loose H₆/H₈ complexes slide on flat surfaces
  without ever meeting TightOpt's step criteria (energy still falling
  ~10⁻⁸ Eh per cycle), so the field jobs use ORCA's normal criteria with
  400 cycles (ORCA then accepts converged energy and gradient). An exact
  initial Hessian made it worse (near-zero rotational curvature, 0.19 Å
  steps).
- **Bond orders and atoms** (one ωB97X-D4 single point per stored
  structure, 118): the campaign outputs print Mayer orders only above 0.1
  and from the HF density at the correlated levels, so this study prints the
  overlap, density and spin-density matrices and computes the **Wiberg
  index in the Löwdin basis with the spin density included**,
  B_AB = 2Σ(P̃α² + P̃β²). ORCA's own Löwdin orders omit the spin term (H₂⁺:
  0.25 instead of 0.5), and its UKS "DENSITY" print is the α density
  (trace N_α), told apart from the total by the electron count. Checks:
  H₂ 1.00, H₂⁺ 0.50, H₃⁺ 4/9, triplet H₂ 0, closed shells equal to ORCA's
  values to 4 digits. Findings: H₂ units in neutral clusters stay at
  0.97–0.99 with ≈ 0.02 links (van der Waals); ion cores hold their H₂
  units with 0.2–0.35 links; the H₂ unit attached to H₃⁺ in H₅⁺ drops to
  0.60. Mayer orders (kept for comparison) dip below zero with these diffuse
  bases. Per atom: Löwdin charge and spin, Mayer free valence (≈ 0.99 on
  the radical H of doublet H₃).
- **Web:** the 3D viewer draws bonds either by distance (now our 1.15 Å rule:
  3Dmol's own guess only bonded H–H between 0.71 and 0.99 Å and dropped the
  1.04–1.06 Å bonds of H₂⁺ and the H₂⁺ cores of H₆⁺/H₈⁺/H₁₀⁺) or by bond
  order (one cylinder per bond, thickness ∝ √order, opacity 0.75·(e^{3·order} − 1)/(e³ − 1): weak links almost transparent, none solid;
  below 0.03 not drawn; legend). Hovering a bond or an atom shows its
  numbers; the same data is in atom and bond tables. "Highlight atoms"
  (none / charge / spin) draws a see-through halo per atom: colour = sign
  (red/blue for charge, orange/green for spin), size and opacity = magnitude
  on one fixed scale for all species (charge ±0.5, spin ±1), so neutral
  clusters stay plain while e.g. H⁻ in H₃⁻ glows red; atoms turn grey so only
  halos carry colour. It shows that the unpaired electron of H₆⁺ is spread
  over all six atoms (0.27 on each central H, 0.12 on each outer one).
  Grid thumbnails draw bonds with Löwdin order > 0.33 (served with the grid,
  one query), the distance rule only as a fallback: H₅⁺/H₇⁺/H₉⁺ now read as an
  H₃⁺ triangle with separate H₂ units (links 0.2–0.3), while the anions' H⁻
  links (≈ 0.4 with ωB97X-D4, likely overstated by self-interaction error)
  are drawn as bonds. Small clusters are
  zoomed in (3Dmol fits at least a 5 Å box).
- Not done (still open): multiplicities `all_upto: 3`, framework port,
  bigger m, per-atom/per-bond energy decomposition (LED/EDA).

### Phase 9: Static site on GitHub Pages (2–3 days) — planned
- **Goal:** publish the web app as a read-only snapshot. Pages serves static
  files only, so FastAPI does not run there: the app reads JSON exported from
  the API, at a precomputed grid of conditions. Raw ORCA files go to a GitHub
  Release archive instead of the site. Target size ≈ 45–50 MB (limit: 1 GB
  per site, 100 MB per file, ~100 GB/month bandwidth).
- **Prerequisites (owner):** a GitHub repository with Pages enabled (source:
  GitHub Actions; free Pages needs a public repo). Publishing ORCA *outputs*
  is not redistributing ORCA, but check the licence terms once before the
  first release. `data/` stays untracked: the database never goes to git.
- **1. Exporter** (`api/src/hclust_api/export.py`,
  `docker compose --profile serve run --rm --no-deps api python -m hclust_api.export --out site/data`):
  - Calls the real app through FastAPI's TestClient, so every file is
    byte-for-byte what the API would answer; path = URL, query folded into
    the path (`campaigns/baseline/grid/d_g/T298.15_p1.json`).
  - Conditions grid in `manifest.json`: 20 temperatures log-spaced over
    10–3000 K plus 298.15 K, × 10 pressures (one per decade, 10⁻⁶–10³ atm,
    including 1 atm) = 210 conditions.
  - Export only what depends on what: grid D_e/D₀ once, D_H per
    temperature, D_G per (T, p); species detail, state list and the D_G
    trend per (T, p); benchmark, jobs summary, studies, xyz/modes/bonds once.
    Estimate: 210 × (36 KB grid + 56 × 3 KB details + trends) ≈ 45 MB.
  - Writes `manifest.json` (conditions, campaigns, git commit, export time,
    file count, total size) and fails if any file is over 25 MB or the total
    over 200 MB.
- **2. Static build of the web app** (`VITE_STATIC=1`, `VITE_BASE=/<repo>/`):
  - `client.ts`: a static transport behind openapi-fetch's late-bound fetch
    maps `/api/...?...` to `${BASE}data/...json` (the exporter's naming, one
    shared function, unit-tested); the views do not change.
  - Conditions snap to the manifest grid (nearest in log T and log p); the
    sliders step through grid points and the bar says "precomputed values".
  - Router: `HashRouter` in the static build (Pages has no fallback for
    client routes; `/#/c/baseline/s/5/1/1` links keep working);
    `BrowserRouter` stays for the dev and nginx builds. `vite.config` takes
    `base` from `VITE_BASE`.
  - Raw-file links: point to the Release archive and name the path inside it
    (`jobs/<hash>/job.out`); the "job record" link is hidden.
- **3. Raw outputs as a Release asset:** `scripts/release-outputs.sh` packs
  the files behind displayed results (reference CCSD(T) jobs, their geometry
  and frequency jobs, study jobs: ≈ 350 dirs, ≈ 450 MB → ≈ 50–80 MB as
  `.tar.xz`), split below 2 GB per asset, `gh release create
  data-<date>`. The site links the matching release from the manifest.
- **4. Publishing:** the exported `site/data` is also attached to the
  release (`site-data.tar.gz`), not committed, so git history stays small.
  `.github/workflows/pages.yml` (on push to main and manual dispatch):
  download `site-data.tar.gz` from the latest data release → `npm ci` →
  static build → copy data → `actions/upload-pages-artifact` →
  `actions/deploy-pages`. Re-exporting data = new release + workflow run.
- **5. Tests:**
  - Exporter: every URL the app can request at a grid point exists
    (enumerated from the routes and the manifest); exported JSON validates
    against the OpenAPI schemas; spot-check equality with the live API.
  - Web: static URL mapping and snapping (Vitest).
  - Playwright against the static build served by `vite preview` with the
    real base path: grid → species → 3D viewer, the temperature slider
    changes D_G, a deep link loads, no request returns 404.
- **Not included:** live recomputation at arbitrary T and p (would need the
  thermochemistry ported to TypeScript), per-file raw-output links (the
  archive is one download), the wiki (could be published alongside later).

---

## 6. Testing & validation

- **Unit tests:** species enumeration and parity, fingerprint dedup
  (invariance to permutation and rotation), fragment-channel enumeration,
  thermo against hand-checked values, and ORCA parsing against stored
  sample outputs (so no ORCA is needed in CI).
- **Regression tests:** the anchors from §1.2. Mark them `@pytest.mark.orca`
  so they run only where ORCA is mounted.
- **Consistency checks** after each campaign:
  - The energy decreases or stays the same from L0-optimized to
    L1-optimized ordering, or else a flag is raised.
  - ⟨S²⟩ is within tolerance.
  - No state is left without a terminal status.
  - Fragment energies exist for every channel used.
- **Frontend:** component tests (Vitest) and one Playwright smoke test of
  grid → detail.

---

## 7. Risks & mitigations

| Risk | Mitigation |
|---|---|
| False binding of anions in a finite basis (e.g. H₂⁻) | Check VDE/ADE, compare TZ vs QZ basis; flag anions whose EA changes sign with basis |
| Spin contamination / wrong SCF solution | ⟨S²⟩ check, broken-symmetry guess, `! UKS` with stability analysis (`%scf STABPerform true`) |
| Missing global minimum | Several search sources, check that results are stable as K grows, compare against literature for H₅⁺ and H₇⁺ |
| Weak vdW clusters dominated by method artefacts | Rely on CCSD(T) as the reference, show DFT±dispersion side by side, report ΔE₀ |
| Harmonic ZPE is unreliable for floppy H₂ units | Report it as a caveat, and do a VPT2 spot-check (Phase 8) |
| ORCA/MPI or library mismatch in the container | Single-core jobs only; mount ORCA with its own `lib/` on `LD_LIBRARY_PATH` |
| ORCA licence | Never bake ORCA into images and never publish images that contain it |

---

## 8. Learning outcomes checklist

- [ ] Explain why HTC needs job hashing, provenance and resumability
- [ ] Build a method ladder and quantify the error of each rung against a reference
- [ ] Do a global structure search and recognise its failure modes
- [ ] Tell local (Hessian), thermodynamic (fragmentation) and electronic (detachment) stability apart
- [ ] See how ZPE and entropy change "stable" into "unstable" as T rises
- [ ] Recognise the self-interaction, dispersion and basis-set failures on concrete examples
- [ ] Present a high-dimensional result space in an interactive UI
