# Self-interaction error

!!! info "Prerequisites"
    [DFT](../methods/dft.md), [Hartree–Fock](../methods/hartree-fock.md)

In approximate DFT, an electron feels a small repulsion from its own charge.
That **self-interaction error** pushes electrons to spread out more than
they should: bonds that share few electrons come out too long and too weak
or too strong, loosely held electrons come out unbound, and structures with
a delocalized charge come out too low. Hydrogen clusters, with few electrons
and many charged species, are a showcase for it.

## Idea

### Where it comes from

DFT's Coulomb energy $J[\rho]$ is the repulsion of the whole electron density
with itself, including each electron with itself. For one electron that is
pure nonsense: there is nothing to repel. In the exact functional the
exchange–correlation energy cancels it exactly:

$$
J[\rho_1] + E_\text{xc}[\rho_1] = 0 \quad \text{for any one-electron density } \rho_1
$$

[Hartree–Fock](../methods/hartree-fock.md#step-2-the-mean-field) satisfies this
automatically (its exchange cancels the self-Coulomb term). Approximate
functionals don't: some self-repulsion is left over.

### What it does

An electron that repels itself lowers its energy by spreading out, so
approximate DFT favours **delocalized** electrons and charges. This is often
called **delocalization error**:

- **Stretched one-electron bonds** are too stable: [H₂⁺](app:s/2/1/2) with its electron
  smeared over two protons comes out too low in energy at long distance.
- **Anions** are underbound: the extra electron's self-repulsion pushes it
  away, sometimes off the molecule entirely.
- **Shared charges** are favoured: a proton sitting symmetrically between
  two [H₂](app:s/2/0/1) units looks better than a localized [H₃⁺·H₂](app:s/5/1/1).
- **Barriers** to reactions come out too low, because transition states are
  usually more delocalized.

Hybrid functionals reduce it by mixing in HF exchange; range-separated
hybrids (ωB97X) use 100 % HF exchange at long range. Neither removes it.

## Examples from this project

**[H₂⁺](app:s/2/1/2), one electron.** Hartree–Fock is exact here, so every deviation of DFT
is self-interaction:

| [H₂⁺](app:s/2/1/2) | r²SCAN-3c (L0) | ωB97X-D4 (L1) | HF (exact in basis) | Exact |
|---|---|---|---|---|
| Bond length | 1.083 Å | 1.105 Å | 1.058 Å | 1.057 Å |
| Harmonic frequency | — | 2074 cm⁻¹ | 2322 cm⁻¹ | 2322 cm⁻¹ |
| $D_e$ (→ [H + H⁺](app:s/2/1/2)) | 2.91 eV | 2.91 eV | 2.79 eV | 2.79 eV |

The bond is too long and too soft but too strong: the electron is happier
spread over both protons than it should be.

**[H⁻](app:s/1/-1/1), an anion.** The electron affinity of H is 0.754 eV. ωB97X-D4 gives
0.20 eV, r²SCAN-3c leaves [H⁻](app:s/1/-1/1) unbound (−1.57 eV, made worse by its lack of
[diffuse functions](diffuse-functions.md)). MP2 and CCSD(T), built on HF
orbitals, give 0.48 and 0.73 eV
([electron affinity](../techniques/ionization-and-electron-affinity.md)).

**[H₅⁺](app:s/5/1/1), a shared proton.** Every DFT level in the project, and ωB97M-V too,
turns the C₂ᵥ [H₃⁺·H₂](app:s/5/1/1) structure into a D₂d structure with the proton shared
equally between two [H₂](app:s/2/0/1) units (four bonds of 1.13 Å). MP2 keeps C₂ᵥ; at MP2
the D₂d structure is a saddle point (546i cm⁻¹), and CCSD(T) puts C₂ᵥ
0.13 kcal/mol lower (`doc/Plan.md`, Phase 3).

## How to protect against it

- Check DFT against a method without self-interaction: MP2 or CCSD(T).
  The plan does this for every state.
- Be most suspicious of anions, odd-electron cations and structures where a
  charge could be shared.
- One-electron systems: use HF, which is exact.

## Where this appears in [h_clusters](https://github.com/skachano/h_clusters)

- The **L1M** (RI-MP2) geometry level exists because of the [H₅⁺](app:s/5/1/1) result (comment
  in `worker/src/hclust/levels.py`).
- The anchor tests (`worker/tests/test_anchors.py`) keep the DFT [H₂⁺](app:s/2/1/2) bond
  length as a strict expected failure, so a change that "fixes" it would be noticed.
- CCSD(T) single points on both the DFT and MP2 geometries decide each
  structure (`dft_ref`, `mp2_ref` in `campaigns/baseline.yaml`).
- [Web app](app:): the [Benchmark](app:benchmark) page compares each geometry
  level's $D_e$ with CCSD(T); the anions are where DFT fails.

## References

- J. P. Perdew, A. Zunger, *Phys. Rev. B* **23**, 5048 (1981): self-interaction
  correction.
- A. J. Cohen, P. Mori-Sánchez, W. Yang, *Science* **321**, 792 (2008):
  insights into current limitations of DFT (delocalization error).
