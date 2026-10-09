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
- Baseline: the lowest allowed multiplicity plus the next one (≈ 58 states).
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
| H₃⁺ | Equilateral triangle (D₃h), r ≈ 0.873 Å, very stable; proton affinity of H₂ ≈ 4.4 eV |
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
| L1′ | B3LYP/def2-TZVPPD (no dispersion) | Didactic: shows self-interaction and dispersion failures | s–min |
| L2 | (U)CCSD(T)/aug-cc-pVTZ single points on L1 geometries | Reference energetics | s–min |
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
3. **ORCA GOAT** global optimizer (new in ORCA 6) at GFN2-xTB level:
   `! GOAT-EXPLORE XTB`. Use the *explore* variant: plain `GOAT` treats each
   H atom as its own fragment and keeps the bonding pattern fixed, so it
   cannot turn a chain into a ring. ORCA finds xtb through the `XTBEXE`
   environment variable. GOAT's whole final ensemble is passed on as
   candidates, *not* just its global minimum, because GFN2-xTB ranks H
   clusters wrongly. GOAT with a DFT engine is too slow for HTC on one core
   (estimated ~5 h for H₃⁺), so the DFT-level search is our own parallel
   template + random search.

All candidates are pre-optimized at L0 (r²SCAN-3c). They are then **deduplicated** by
energy (ΔE < 0.1 kcal/mol) plus a geometric fingerprint (sorted
interatomic-distance vector or RMSD after alignment, permutation-invariant).
The unique structures within an energy window (e.g. 15 kcal/mol, at most
8 per state) are promoted to L1.

Some starting points will **fall apart** during optimization (fragments fly
away). Detect this with a connectivity graph (H–H cutoff ≈ 1.3 Å for
covalent contacts, ≈ 3.5 Å for van der Waals contacts). Record it as a
result ("dissociates"), not as a failure.

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
               │  - ORCA/xtb adapters  - thermo recompute       - Plotly charts   │
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
├── .env.example               # ORCA_DIR=/opt/orca, N_WORKERS=16
├── worker/
│   ├── Dockerfile
│   ├── pyproject.toml         # uv-managed
│   └── src/hclust/
│       ├── species.py         # (m, charge, mult) enumeration, parity rules
│       ├── structures.py      # templates, random generator, dedup/fingerprints
│       ├── engines/
│       │   ├── orca.py        # input rendering (Jinja2), run, parse
│       │   └── xtb.py
│       ├── parse.py           # orca_2json / property file → typed results
│       ├── db.py              # SQLModel tables
│       ├── runner.py          # job queue, process pool, retries, timeouts
│       ├── workflow.py        # stage DAG: L0 → dedup → L1 → freq → L2 → L3
│       ├── analysis/
│       │   ├── symmetry.py    # point group (pymatgen PointGroupAnalyzer)
│       │   ├── thermo.py      # RRHO / qRRHO at arbitrary T, p
│       │   └── fragments.py   # channel enumeration, D_min, verdicts
│       └── cli.py             # typer: `hclust plan|run|status|analyze|export`
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
- `Job(id, hash, state_id, structure_id, level, kind[sp|opt|freq|goat],
  status[pending|running|done|failed|dissociated], attempts, wall_s,
  workdir, orca_version, created/updated)`
- `Result(job_id, energy_eh, s2, homo, lumo, charges_json, spins_json,
  final_xyz, freqs_json, modes_json, zpe, point_group, converged)`
- `Verdict(state_id, level, best_structure_id, d_min, d0_min, verdict, channel)`

**Provenance and idempotence.** The job hash is
`sha256(rendered ORCA input + engine version)`. Rerunning the campaign skips
completed hashes, so the campaign is *resumable* and *cacheable*. Keep the
raw `*.out`, `*.property.txt` and `*.json` files under `data/jobs/<hash>/`.
Keep the database as an index over them, never as the only copy.

### 3.5 Job runner (the HTC core, built by hand on purpose)

- A single orchestrator process owns the DB, so there are no write races in
  SQLite. A `ProcessPoolExecutor` / `asyncio` subprocess pool runs the jobs.
- A stage DAG: a job becomes runnable when its parent result exists (e.g. a
  freq job needs an opt job).
- **Error handling playbook** (record each attempt):
  - SCF not converged → retry with `SlowConv`, `SOSCF`, then `TRAH`.
  - Optimization not converged → restart from the last geometry, up to 2 times.
  - Imaginary frequency → displace along the mode (±0.1 Å) and re-optimize.
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

### Phase 1: Single-job engine + parsing (1–2 days)
- ORCA/xtb adapters, input templating, output parsing into `Result`, and
  job hashing.
- **Done when** H, H⁻, H₂, H₂⁺ and H₃⁺ at L1 and L2 reproduce the anchors in
  §1.2 (r_e within 0.01 Å, energies within 0.05 eV of the references for
  CCSD(T)). Encode these as `pytest` regression tests.

### Phase 2: Job DB + runner (2 days)
- SQLModel schema, campaign YAML, stage DAG, process pool, retries, the
  `status` CLI, and resumability.
- **Done when** an interrupted campaign (Ctrl-C mid-run) resumes without
  redoing finished jobs.

### Phase 3: Structure search (2–3 days)
- Templates, a random generator, GOAT, L0 pre-optimization, dedup by
  fingerprint, fragmentation detection, and promotion.
- **Done when** the search finds the D₃h triangle for H₃⁺ and the
  H₃⁺·H₂ (C₂v) structure for H₅⁺ starting from random geometries.

### Phase 4: Full baseline campaign (1 day, plus compute time)
- Run L0 → L1 (+freq) → L2 for all 29 species × baseline multiplicities.
- Rough budget: ~58 states × ~30 candidates × L0, then ~58 × 8 × L1, then L2
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
