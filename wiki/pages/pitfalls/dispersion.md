# Missing dispersion

!!! info "Prerequisites"
    [DFT](../methods/dft.md), [MP2](../methods/mp2.md)

Two neutral, non-polar molecules such as two H₂ still attract each other
weakly at long range. This **dispersion** (or London, or van der Waals)
attraction comes from correlated motion of electrons on the two molecules.
Hartree–Fock has no correlation, and standard DFT functionals only describe
it at short range, so both miss it completely. For neutral hydrogen
clusters, which are held together by little else, that is the whole story.

## Idea

### Where dispersion comes from

The electrons of H₂ fluctuate: at any instant the charge is slightly
lopsided, a momentary dipole. That dipole polarizes a neighbouring molecule,
whose induced dipole is oriented to attract the first. Averaged over time,
neither molecule has a dipole, but the correlated fluctuations give a net
attraction that falls off as

$$
E_\text{disp} \approx -\frac{C_6}{R^6}
$$

It is weak for small molecules but always present and always attractive,
and it adds up over many atoms.

### Which methods have it

| Method | Dispersion |
|---|---|
| Hartree–Fock | none: no correlation |
| LDA, GGA, meta-GGA, hybrids | only at short range; the long-range $-C_6/R^6$ tail is missing |
| DFT + D3/D4 | added as an empirical pairwise $-C_6/R^6$ term, damped at short range |
| DFT + VV10 (ωB97M-V) | a non-local correlation functional |
| MP2 | yes, from double excitations; often somewhat too strong |
| CCSD(T) | yes, accurate |

"-D4" in ωB97X-D4 and r²SCAN-3c is Grimme's D4 correction, whose $C_6$
coefficients depend on each atom's environment and charge.

## What it means for hydrogen clusters

The plan expects neutral H_m beyond H₂ to be only weak van der Waals
complexes of H₂ units (plus an H atom for odd m) (`doc/Plan.md` §1.2). The
binding is tiny. In the baseline campaign at CCSD(T)/aug-cc-pVTZ, neutral H₃
(H₂·H) lies only about 0.04 kcal/mol (under 2 meV) below H₂ + H. At RI-MP2 the complex
is linear, with the H atom 3.32 Å from the end of the H₂. Without dispersion, such complexes don't exist: the
fragments drift apart during optimization.

That binding is so small that the zero-point energy of the soft intermolecular
motion will decide whether the complex is really bound
([zero-point energy](../techniques/zero-point-energy.md)).

Charged clusters are different. H₃⁺·H₂ (H₅⁺) and H⁻·H₂ are held mainly by the
ion polarizing the H₂ (induction, falling off as $R^{-4}$), which even methods
without dispersion describe. Dispersion is a smaller correction there.

## Where this appears in h_clusters

- Both DFT levels include D4: r²SCAN-3c (L0) and ωB97X-D4 (L1). ωB97M-V
  (L1V) has VV10 instead.
- **L1b**, B3LYP/def2-TZVPPD *without* dispersion, is defined in
  `worker/src/hclust/levels.py` for teaching: run it on the neutral
  complexes to watch them fall apart.
- The dissociation cutoff of 3.5 Å was raised from 2.5 Å precisely so that
  van der Waals pairs at about 3.3 Å are kept (Phase 4 findings).

## References

- S. Grimme, A. Hansen, J. G. Brandenburg, C. Bannwarth, *Chem. Rev.* **116**,
  5105 (2016): dispersion-corrected mean-field electronic structure methods.
- E. Caldeweyher et al., *J. Chem. Phys.* **150**, 154122 (2019): D4.
- A. J. Stone, *The Theory of Intermolecular Forces*, 2nd ed. (Oxford, 2013).
