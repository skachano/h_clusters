# Semi-empirical tight binding (GFN2-xTB)

!!! info "Prerequisites"
    [Hartree–Fock](hartree-fock.md), [DFT](dft.md)

GFN2-xTB is a **semi-empirical** method: the same kind of orbital
calculation as DFT, but with most integrals replaced by simple formulas whose
parameters were fitted to reference data. It is thousands of times faster
than DFT, fast enough to run global searches over thousands of structures.
The price is that it is only as good as its parametrization, and hydrogen
clusters lie outside the chemistry it was fitted to.

## Idea

xTB ("extended tight binding", Grimme and coworkers) cuts every corner that
DFT spends time on:

- **Minimal basis, valence electrons only**: a handful of functions per atom.
- **Approximate integrals**: the Hamiltonian matrix elements are computed from
  overlaps and fitted element parameters, not from integrals over the
  real Hamiltonian.
- **Simplified electrostatics**: electron repulsion through atomic partial
  charges and multipoles.
- **Built-in dispersion** (D4) for noncovalent interactions.

The SCF loop still runs, but on tiny matrices with cheap elements. "GFN"
names the target: **G**eometries, vibrational **F**requencies and
**N**oncovalent interactions, the properties its parameters were mainly fitted to.

## What happened in this project

The Phase 0 smoke test was [H₃⁺](app:s/3/1/1), the simplest real cluster
(`doc/Plan.md`, Phase 0 findings):

| Method | Lowest structure | Linear vs triangle |
|---|---|---|
| GFN2-xTB | **linear**, r = 1.03 Å | linear 0.9 kcal/mol *below* |
| r²SCAN-3c | triangle, r = 0.870 Å | linear 39.4 kcal/mol above |
| CCSD(T)/cc-pVTZ | triangle, r = 0.875 Å | linear 40.5 kcal/mol above |

GFN2-xTB gets the shape of H₃⁺ qualitatively wrong. Its parameters for
hydrogen were fitted to hydrogen in ordinary molecules (C–H, O–H bonds), not
to three-centre two-electron bonds or bare cationic hydrogen clusters. That
is the general lesson about parametrized methods: they interpolate well and
extrapolate badly, and the failure gives no warning.

As a result:

- xTB is used **only to propose geometries**, never to rank them. Its energy
  window for GOAT is wide (`MaxEn 30` kcal/mol in `engines/orca.py`), so a
  structure it ranks too high still gets passed on.
- r²SCAN-3c (L0), not xTB, does the screening.
- GOAT with xTB found nothing that the template and random search didn't, so
  it is off by default in the baseline campaign (Phase 3 findings).

## Where this appears in h_clusters

- `Level("XTB", "XTB", kind="xtb")` in `worker/src/hclust/levels.py`.
- Used through ORCA's `! GOAT-EXPLORE XTB`
  ([structure search](../techniques/structure-search.md)). ORCA finds the
  `xtb` binary through the `XTBEXE` environment variable set in the worker
  `Dockerfile`.

## References

- C. Bannwarth, S. Ehlert, S. Grimme, *J. Chem. Theory Comput.* **15**, 1652
  (2019): GFN2-xTB.
- C. Bannwarth et al., *WIREs Comput. Mol. Sci.* **11**, e1493 (2021):
  extended tight-binding methods, an overview.
