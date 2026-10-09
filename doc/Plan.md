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
| L1 | DFT: ωB97M-V/def2-TZVPPD (alt. ωB97X-D4, r²SCAN-3c) | Geometry optimization + frequencies for every candidate | s–min |
| L1M | (U)MP2/aug-cc-pVTZ | Second geometry optimization + frequencies, free of DFT self-interaction and delocalization error (added in Phase 3: DFT has no C₂v H₅⁺ minimum) | min |
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
  and spin state, so use each fragment's best computed energy. This is why
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
    against. Default pool size: 16 workers on a 20-core machine. Memory:
    `%maxcore` ≈ 600 MB per job (15 GB RAM).
- **`api`**: FastAPI + SQLModel. Mounts `./data` read-only.
- **`web`**: Node 22 for development (`vite dev`). Production build is
  served by nginx, which also proxies `/api` to the `api` service.

Compose profiles: `compute` (worker) and `serve` (api + web), so the
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
│       │   ├── symmetry.py    # point group (pymatgen PointGroupAnalyzer)
│       │   ├── thermo.py      # RRHO / qRRHO at arbitrary T, p
│       │   └── fragments.py   # channel enumeration, D_min, verdicts
│       └── cli.py             # typer: `python -m hclust plan|run|status` (+ analyze|export later)
├── api/
│   ├── Dockerfile
│   └── src/hclust_api/        # reuses hclust package (installed as dep)
├── web/
│   ├── Dockerfile
│   └── src/ (React + TS)
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
- `Verdict(state_id, level, best_structure_id, d_min, d0_min, verdict, channel)`

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

API sketch:
```
GET /states?level=L2
GET /states/{m}/{charge}/{mult}
GET /structures/{id}.xyz
GET /structures/{id}/modes
GET /grid?level=L2&T=298&p=1e5&quantity=dG
GET /trends?level=L2&quantity=d_min
GET /benchmark?ref=L2&test=L1
GET /jobs/summary
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
  `symmetry.py` (Phase 5) is required.
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

### Phase 4: Full baseline campaign (1 day, plus compute time)
- Run L0 → select → L1 and L1M (+freq) → L2 for all 29 species × baseline
  multiplicities.
- Rough budget: ~57 states × ~30 candidates × L0, then ~57 × 8 × L1, then L2
  on the minima. That is a few thousand jobs, hours of wall time on 16
  workers.
- **Done when** every state has a terminal status, and failures are
  explained or fixed.

### Phase 5: Analysis library (2 days)
- Point groups, thermo (RRHO/qRRHO at any T, p, cross-checked against
  ORCA's own thermo at 298 K), fragmentation channels, and verdicts.
- **Done when** `hclust analyze` produces a verdict table that agrees with
  §1.2.

### Phase 6: API (1–2 days)
- FastAPI endpoints from §4, an OpenAPI schema, and caching for `/grid`.

### Phase 7: Web app (4–6 days)
- Grid → detail → trends → conditions → benchmark/dashboard, in that order.
  The grid plus the 3D viewer are the minimum viable app.

### Phase 8: Extensions (pick any)
- **Multiplicities:** extend to `all_upto: 3`, with the spin-ladder view.
- **L3/L4:** CCSD(T) geometries and a basis-set convergence study (TZ → QZ
  → CBS).
- **Electric field:** `%scf EField` scan to see field-induced
  (de)stabilization and alignment.
- **Dielectric environment:** CPCM with a few ε values. This is educational
  only; a hydrogen cluster in solvent is unphysical, but it shows how charged
  species respond.
- **Anharmonic ZPE / quantum nuclear effects:** a VPT2 spot-check on H₅⁺,
  or a discussion of path-integral approaches.
- **Framework port:** reimplement Phase 2 with jobflow/quacc or AiiDA and
  compare.
- **Bigger m:** push to m = 15–20 to see where the H₃⁺(H₂)_k shell picture
  breaks down.

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
