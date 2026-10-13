# Thermochemistry

!!! info "Prerequisites"
    [Zero-point energy](zero-point-energy.md), [Frequencies](frequencies.md)

A calculation gives the energy of one molecule at rest at the bottom of its
well. Experiments happen at a temperature and pressure, with molecules
moving, rotating and vibrating. **Thermochemistry** bridges the two: from the
energy, the geometry and the frequencies it computes enthalpy $H$, entropy $S$
and free energy $G$. The free energy decides what is stable under given
conditions, and for weakly bound clusters entropy can win over binding.

## Idea

### Free energy decides

At constant temperature and pressure, a process happens spontaneously if it
lowers the Gibbs free energy:

$$
G = H - TS, \qquad \Delta G = \Delta H - T\Delta S
$$

$\Delta H$ is the heat taken in (for dissociation: roughly the binding energy).
$\Delta S$ measures the gain in disorder. Splitting one cluster into two
free fragments gains a lot of entropy, mostly because each fragment can move
around on its own. So $-T\Delta S$ favours dissociation, more so at high
temperature: every bound cluster falls apart if it is hot enough.

The equilibrium constant follows from $\Delta G$:

$$
K = e^{-\Delta G/RT}
$$

### Ideal gas, rigid rotor, harmonic oscillator

The standard recipe (RRHO) treats each molecule as an ideal-gas particle whose
energy is a sum of independent parts, each with a textbook formula:

| Part | Needs | Notes |
|---|---|---|
| Translation | mass, $T$, $p$ | The only part that depends on **pressure**: $S_\text{trans}$ grows with $\ln(k_BT/p)$ |
| Rotation | moments of inertia, symmetry number $\sigma$ | Rigid rotor; $\sigma$ counts indistinguishable orientations ([point groups](point-groups.md)) |
| Vibration | frequencies | Harmonic oscillators, including the ZPE |
| Electronic | spin multiplicity | Ground state only: $S_\text{el} = k_B\ln(2S+1)$ |

The enthalpy adds $pV = k_BT$ per molecule to the energy.

**Low frequencies are a problem.** The harmonic entropy of a mode grows
without limit as its frequency goes to zero, so soft cluster modes
(tens to a few hundred cm⁻¹) get unphysically large entropies. Grimme's
**quasi-RRHO** treats modes below about 100 cm⁻¹ as partly free rotors instead.

## Example: is H₅⁺ stable at room temperature?

[H₅⁺](app:s/5/1/1) → [H₃⁺ + H₂](app:s/5/1/1), with CCSD(T) electronic energies plus RI-MP2 thermal
corrections from ORCA at 298.15 K and 1 atm (baseline campaign data):

| Quantity | hartree | kcal/mol |
|---|---|---|
| $\Delta E$ (well depth $D_e$) | 0.013614 | 8.54 |
| $\Delta E_0$ (with ZPE) | 0.009165 | 5.75 |
| $\Delta H$(298 K) | 0.011525 | 7.23 |
| $T\Delta S$(298 K) | 0.009138 | 5.73 |
| $\Delta G$(298 K) | 0.002387 | **1.50** |

$\Delta H$ is larger than $\Delta E_0$ because two fragments carry more
thermal energy (translation, rotation, $pV$) than one cluster. The entropy
term cancels 80 % of the binding.

$\Delta G = +1.5$ kcal/mol gives $K = e^{-1.50/0.593} = 0.08$ atm for
$K = p_{\text{H}_3^+}\,p_{\text{H}_2}/p_{\text{H}_5^+}$. In 1 atm of [H₂](app:s/2/0/1),
[H₅⁺](app:s/5/1/1) outnumbers bare [H₃⁺](app:s/3/1/1) about 12 to 1; in 0.01 atm of [H₂](app:s/2/0/1), bare [H₃⁺](app:s/3/1/1) wins. Roughly
above $T = \Delta H/\Delta S \approx 380$ K, [H₅⁺](app:s/5/1/1) dissociates even at 1 atm.
The cluster is bound, but whether it *exists* depends on conditions.

## Where this appears in [h_clusters](https://github.com/skachano/h_clusters)

- Every frequency job stores ORCA's thermochemistry at 298.15 K in the
  `thermo` field: `zpe`, `innerEnergyU`, `enthalpyH`, `entropyS` (stored as
  $T\cdot S$ in hartree) and `freeEnergyG`.
- The plan (Phase 5) recomputes RRHO/qRRHO at any $T$ and $p$ from the
  stored frequencies, cross-checked against ORCA at 298 K, and the web app's
  [grid](app:?q=d_g) recolours the stability grid as $T$ and $p$ change
  (`doc/Plan.md` §4).
- Point groups give the rotational symmetry numbers (`symmetry_number` in the
  `result` table).

## References

- D. A. McQuarrie, *Statistical Mechanics* (University Science Books, 2000).
- C. J. Cramer, *Essentials of Computational Chemistry*, 2nd ed., chapter on
  thermodynamic properties.
- S. Grimme, *Chem. Eur. J.* **18**, 9955 (2012): the quasi-RRHO treatment of
  low-frequency modes.
