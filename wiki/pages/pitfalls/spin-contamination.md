# Spin contamination

!!! info "Prerequisites"
    [Spin and multiplicity](../foundations/spin-and-multiplicity.md),
    [Hartree–Fock](../methods/hartree-fock.md#bond-breaking)

Unrestricted calculations (UHF, UKS) give spin-up and spin-down electrons
separate orbitals. That flexibility lowers the energy and fixes bond
breaking, but the resulting wavefunction may no longer have a definite total
spin: a "doublet" partly mixed with a quartet, say. This **spin
contamination** distorts energies and geometries, and propagates into
correlated methods built on top. The value of ⟨S²⟩ measures it.

## Idea

### Restricted and unrestricted

- **Restricted** (RHF): paired electrons share a spatial orbital. A closed-shell
  RHF determinant is a pure singlet.
- **Restricted open-shell** (ROHF): paired electrons share orbitals, unpaired
  ones are singly occupied. Pure spin, but less flexible.
- **Unrestricted** (UHF): α and β electrons have independent orbitals. The
  energy can only go down, but the determinant is generally a mixture of
  spin states.

### Measuring it

For a pure state with spin $S$, $\langle\hat{S}^2\rangle = S(S+1)$:

| Multiplicity | Exact ⟨S²⟩ |
|---|---|
| singlet | 0 |
| doublet | 0.75 |
| triplet | 2.00 |
| quartet | 3.75 |

A UHF doublet with ⟨S²⟩ = 0.80 has picked up some quartet character (and
higher). A common rule of thumb is to worry above a few percent deviation;
the plan flags deviations above 10 %.

### When it's a feature

Sometimes contamination is the price of the right physics. A stretched [H₂](app:s/2/0/1) is
two H atoms with opposite spins. RHF can't describe that (its energy goes far
too high), but a **broken-symmetry** UHF solution, with the α electron on one
atom and the β on the other, gets the energy right while having ⟨S²⟩ ≈ 1:
halfway between singlet and triplet. The energy is useful; the spin label isn't.

### Consequences

- UHF energies of contaminated states are too high or too low depending on
  the contaminant; geometries shift.
- **UMP2 suffers badly**: perturbation theory on a contaminated reference
  converges poorly.
- **CCSD(T)** is more forgiving: its singles largely correct the reference.
- Remedies: an ROHF reference, spin-projection, or (for strongly contaminated
  cases) multireference methods.

## Examples from the campaign

The worst ⟨S²⟩ values at the UHF reference of RI-MP2 (L1M), baseline campaign:

| State | ⟨S²⟩ | Exact | Deviation |
|---|---|---|---|
| [H₃⁻](app:s/3/-1/3) triplet | 2.200 | 2.00 | 10 % |
| [H₈⁺](app:s/8/1/2) doublet | 0.825 | 0.75 | 10 % |
| [H₄⁻](app:s/4/-1/4) quartet | 3.891 | 3.75 | 4 % |
| [H₁₀⁺](app:s/10/1/4) quartet | 3.824 | 3.75 | 2 % |

Most states are much cleaner. The two worst sit right at the plan's 10 %
threshold, so their MP2 geometries deserve a second look. Their CCSD(T)
energies, which decide the structures, are less affected.

## Where this appears in h_clusters

- ⟨S²⟩ is parsed from every ORCA output into the `s2` column of the `result` table.
- States with multiplicity > 1 run `UHF` or `UKS`; closed-shell singlets run
  restricted (`engines/orca.py`).
- The plan's consistency checks include "⟨S²⟩ within tolerance" after each
  campaign, and suggest a broken-symmetry guess (`%scf GuessMix`) for
  singlets with stretched H–H contacts (`doc/Plan.md` §2 and §6).
- For DFT (UKS), ⟨S²⟩ is computed from the Kohn–Sham determinant, which is
  not the real wavefunction, so it is only a rough indicator.

## References

- A. Szabo, N. S. Ostlund, *Modern Quantum Chemistry*, §3.8 (unrestricted
  open-shell Hartree–Fock).
- F. Jensen, *Introduction to Computational Chemistry*, 3rd ed., sections on
  spin contamination.
