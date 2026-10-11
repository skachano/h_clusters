# H-Clusters

A high-throughput computational chemistry experiment: are the hydrogen
clusters **H_m^n** (m = 1–10 atoms, charge n = −1, 0, +1, two spin states each)
stable, and what shape do they have? About 2,000 ORCA calculations, from xTB
and DFT up to CCSD(T) at the basis-set limit, are run by a small hand-built
workflow engine and explored in a web app.

The project's purpose is learning HTC computational chemistry, so the pieces
are built by hand rather than taken from a framework. The plan, the methods and
every result with its caveats are in [doc/Plan.md](doc/Plan.md); a learning
wiki (English and Japanese) is in [wiki/](wiki/).

## What it finds

- **Cations are the stable family:** every H_m⁺ survives zero-point energy,
  built as an H₃⁺ core (odd m) or an H₂⁺ core (even m) holding H₂ units.
  D₀(H₅⁺ → H₃⁺ + H₂) = 0.28 eV with anharmonic zero-point energy.
- **Neutral clusters and H⁻(H₂)ₖ anions** are bound electronically (by meV
  for the neutrals, up to ~0.1 eV for the anions), but zero-point energy
  unbinds them. Even-m anions do not hold the extra
  electron at all.
- **Method check:** against CCSD(T), ωB97X-D4 errs by 0.08 eV on average and
  RI-MP2 by 0.04 eV; basis-set and counterpoise errors are below 0.05 eV.

## How it is built

| Part | What it does |
|---|---|
| `worker/` (Python) | `hclust`: campaign specs, content-addressed ORCA jobs in SQLite, a stage DAG (xTB/GOAT search → DFT → MP2 → CCSD(T)) with retries and resume; analysis (fragmentation channels, verdicts, thermochemistry, point groups, our own VPT2); extension studies |
| `api/` (FastAPI) | read-only HTTP API over the results database |
| `web/` (React, TypeScript) | grid of species, species pages with a 3D viewer (normal modes, bond orders, charge and spin halos), trends, benchmark, jobs, extension studies; English and Japanese |
| `wiki/` (MkDocs) | the theory behind it, for learning |

Everything runs in Docker containers (`compose.yaml`).

## Running it

Requirements: Docker with Compose, and **ORCA 6.1.1** installed on the host
(default `/opt/orca`). ORCA is free for academic use but may not be
redistributed, so it is mounted read-only into the worker, never copied into
an image; get it from the [ORCA forum](https://orcaforum.kofo.mpg.de).

```sh
cp .env.example .env                    # ORCA path, scratch directory, ports

# compute: plan and run a campaign (safe to interrupt and rerun)
docker compose --profile compute run --rm worker python -m hclust plan /campaigns/demo.yaml
docker compose --profile compute run --rm worker python -m hclust run /campaigns/baseline.yaml
docker compose --profile compute run --rm worker python -m hclust analyze baseline --check
docker compose --profile compute run --rm worker python -m hclust study bonds   # see doc/Plan.md, Phase 8

# explore: API on :8000, web app on :5173
docker compose --profile serve up

# learn: the wiki on :8001
docker compose --profile docs up docs
```

The baseline campaign needs ~150 GB of scratch space (CCSD(T) on the largest
clusters); `campaigns/demo.yaml` is a small smoke test.

Tests:

```sh
docker compose --profile compute run --rm worker python -m pytest
docker compose --profile serve run --rm --no-deps api python -m pytest
docker compose run --rm --no-deps web sh -c "npx tsc -b && npx vitest run"
docker compose --profile serve up -d && docker compose --profile test run --rm e2e
```

## Static site (GitHub Pages)

The web app also builds as a static snapshot: the API's answers are exported
as JSON at 21 temperatures × 10 pressures (≈ 63 MB), and the raw ORCA files of
the displayed results go into a release archive (doc/Plan.md, Phase 9).

```sh
docker compose --profile serve run --rm --no-deps api python -m hclust_api.export --out /data/site/data
docker compose --profile static up web-static      # preview: http://localhost:4173/h_clusters/
scripts/publish-data.sh                            # GitHub Release + Pages deploy (needs gh)
```

## Citing

All calculations were run with **ORCA 6.1.1**. ORCA's essential reference:

> F. Neese, *Software update: the ORCA program system, version 6.0*,
> WIREs Comput. Mol. Sci. **2025**, 15, e70019.
> [doi:10.1002/wcms.70019](https://doi.org/10.1002/wcms.70019)

ORCA also suggests, in every output, the papers behind the algorithms that run
used (RI-J, COSX, SHARK, analytic Hessians, CPCM, GOAT, GFN2-xTB, r2SCAN-3c,
D4, …). [doc/orca-citations.md](doc/orca-citations.md) gathers them over all
runs of this project, by priority and with the methods that used each one
(`python -m hclust citations`; outputs now also keep ORCA's `job.bibtex`).

Not in ORCA's lists, added by hand (check before reusing in a paper):

- ωB97X: J.-D. Chai, M. Head-Gordon, *J. Chem. Phys.* **2008**, 128, 084106,
  [doi:10.1063/1.2834918](https://doi.org/10.1063/1.2834918); with D4:
  A. Najibi, L. Goerigk, *J. Comput. Chem.* **2020**, 41, 2562.
- def2 basis sets: F. Weigend, R. Ahlrichs, *Phys. Chem. Chem. Phys.* **2005**, 7, 3297,
  [doi:10.1039/b508541a](https://doi.org/10.1039/b508541a); diffuse def2-TZVPPD:
  D. Rappoport, F. Furche, *J. Chem. Phys.* **2010**, 133, 134105,
  [doi:10.1063/1.3484283](https://doi.org/10.1063/1.3484283).
- aug-cc-pVnZ: T. H. Dunning Jr., *J. Chem. Phys.* **1989**, 90, 1007,
  [doi:10.1063/1.456153](https://doi.org/10.1063/1.456153); R. A. Kendall,
  T. H. Dunning Jr., R. J. Harrison, *J. Chem. Phys.* **1992**, 96, 6796,
  [doi:10.1063/1.462569](https://doi.org/10.1063/1.462569).
- MP2: C. Møller, M. S. Plesset, *Phys. Rev.* **1934**, 46, 618,
  [doi:10.1103/PhysRev.46.618](https://doi.org/10.1103/PhysRev.46.618).
- CCSD(T): K. Raghavachari, G. W. Trucks, J. A. Pople, M. Head-Gordon,
  *Chem. Phys. Lett.* **1989**, 157, 479,
  [doi:10.1016/S0009-2614(89)87395-6](https://doi.org/10.1016/S0009-2614(89)87395-6);
  basis-set extrapolation of the correlation energy: T. Helgaker, W. Klopper,
  H. Koch, J. Noga, *J. Chem. Phys.* **1997**, 106, 9639,
  [doi:10.1063/1.473863](https://doi.org/10.1063/1.473863).
- Counterpoise correction: S. F. Boys, F. Bernardi, *Mol. Phys.* **1970**, 19, 553,
  [doi:10.1080/00268977000101561](https://doi.org/10.1080/00268977000101561).
- Quasi-RRHO entropy: S. Grimme, *Chem. Eur. J.* **2012**, 18, 9955,
  [doi:10.1002/chem.201200497](https://doi.org/10.1002/chem.201200497).
- VPT2 formulas: P. R. Franke, J. F. Stanton, G. E. Douberly,
  *J. Phys. Chem. A* **2021**, 125, 1301.
- Bond indices: K. B. Wiberg, *Tetrahedron* **1968**, 24, 1083,
  [doi:10.1016/0040-4020(68)88057-3](https://doi.org/10.1016/0040-4020(68)88057-3);
  I. Mayer, *Chem. Phys. Lett.* **1983**, 97, 270,
  [doi:10.1016/0009-2614(83)80005-0](https://doi.org/10.1016/0009-2614(83)80005-0).
- 3D viewer, 3Dmol.js: N. Rego, D. Koes, *Bioinformatics* **2015**, 31, 1322,
  [doi:10.1093/bioinformatics/btu829](https://doi.org/10.1093/bioinformatics/btu829).

## Licence

The code and documentation are under the [MIT licence](LICENSE). ORCA is not
part of this repository and has its own licence.
