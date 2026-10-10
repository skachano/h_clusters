# Units

!!! info "Prerequisites"
    None.

Quantum chemistry uses its own units, and papers, programs and this wiki mix
several energy units freely. This page is a reference: what each unit is,
how to convert, and what size of number to expect.

## Atomic units

In **atomic units** (a.u.) the electron mass, the electron charge, the
reduced Planck constant $\hbar$ and $4\pi\varepsilon_0$ are all set to 1. The
Schrödinger equation then has no constants left in it, which is why
equations in this wiki look so bare. Programs compute in atomic units
internally.

| Quantity | Atomic unit | Value |
|---|---|---|
| Length | bohr ($a_0$) | 0.529177 Å |
| Energy | hartree ($E_h$) | 27.2114 eV |
| Mass | electron mass ($m_e$) | 1 amu = 1822.89 $m_e$; a proton is 1836.15 $m_e$ |

The hydrogen atom's ground-state energy is exactly −½ hartree, and its
most probable electron–nucleus distance is exactly 1 bohr.

## Energy units

| Unit | 1 hartree = | Where you'll meet it |
|---|---|---|
| hartree (Eh) | 1 | Total energies in ORCA output |
| eV | 27.2114 | Bond energies, ionization energies |
| kcal/mol | 627.509 | Relative energies in chemistry; this project's selection windows |
| kJ/mol | 2625.50 | Same, SI-flavoured |
| cm⁻¹ | 219 474.6 | Vibrational frequencies |
| K (as $E/k_B$) | 315 775 | Temperatures |

kcal/mol and kJ/mol are energies *per mole* of molecules; eV and hartree
are per molecule. 1 eV = 23.06 kcal/mol = 8065.5 cm⁻¹.

!!! note "Wavenumbers"
    A wavenumber $\tilde\nu$ in cm⁻¹ is the number of waves per centimetre of light with
    that energy, $E = hc\tilde\nu$. Spectroscopy reports vibrations this way.
    ORCA prints frequencies in cm⁻¹ although, strictly, they are wavenumbers.

## Energy scales

The numbers that matter in this project span six orders of magnitude:

| Energy | eV | kcal/mol |
|---|---|---|
| Total energy of H₁₀ (its size) | ≈ 160 | ≈ 3700 |
| H₂ bond ($D_e$) | 4.75 | 110 |
| H₃⁺ → H₂ + H⁺ | 4.6 | 106 |
| H⁻ → H + e⁻ (electron affinity) | 0.75 | 17 |
| H₅⁺ → H₃⁺ + H₂ ($D_e$, this project's CCSD(T)) | 0.37 | 8.5 |
| H₂ zero-point energy | 0.27 | 6.2 |
| "Chemical accuracy" | 0.043 | 1 |
| Thermal energy $k_BT$ at 298 K | 0.026 | 0.59 |
| C₂ᵥ vs D₂d H₅⁺ (CCSD(T)) | 0.006 | 0.13 |

Two consequences:

- **Total energies are huge, the chemistry is in tiny differences.** A
  relative energy of 0.1 kcal/mol is a difference in the fifth decimal of a
  total energy in hartree. Calculations must be converged far tighter than
  the differences you care about (hence `TightSCF` in every input).
- **Weak binding competes with thermal energy.** A cluster bound by a few
  kcal/mol falls apart easily at room temperature
  ([thermochemistry](../techniques/thermochemistry.md)).

## Where this appears in h_clusters

- `worker/src/hclust/units.py` holds the conversions (CODATA 2018):
  `BOHR_TO_ANGSTROM`, `HARTREE_TO_EV`, `HARTREE_TO_KCAL`.
- Energies are stored in hartree in the `result` table; geometries in Å.
- Campaign thresholds are in kcal/mol: `energy_window_kcal: 15` for
  promotion, a 0.1 kcal/mol window for duplicate detection.

## References

- CODATA 2018 recommended values of the fundamental constants (NIST).
