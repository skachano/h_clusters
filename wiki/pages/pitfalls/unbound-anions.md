# Finite-basis "binding" of unbound anions

!!! info "Prerequisites"
    [Ionization energy and electron affinity](../techniques/ionization-and-electron-affinity.md),
    [Missing diffuse functions](diffuse-functions.md)

Ask a program for [H₂⁻](app:s/2/-1/2) and it returns an energy, an optimized geometry and
frequencies, as if the anion existed. It doesn't: the extra electron isn't
bound, and would leave immediately. The calculation can't show that,
because a finite basis set gives the electron nowhere to go. Spotting
these phantom anions is part of reading results critically.

## Idea

### Bound, unbound, resonance

An anion is **bound** if its energy is below that of the neutral molecule
plus a free electron (energy zero): a positive electron affinity. If it
isn't, the extra electron belongs to the continuum of free-electron states.
Some such states live briefly before the electron escapes; these are
**resonances**. [H₂⁻](app:s/2/-1/2) is one: it forms when slow electrons hit [H₂](app:s/2/0/1), and loses
its electron again within femtoseconds.

### What a finite basis does

A free electron is a spread-out wave. A finite basis can't represent one,
so the continuum is replaced by a few discrete states built from the most
diffuse functions available. The calculation finds the lowest of them: the
neutral molecule plus an electron parked in its outermost basis functions,
at an energy somewhat above the neutral. Every number it reports describes
that artificial state.

- The **energy** is above the neutral's, and drops towards it as more diffuse
  functions are added: the variational principle letting the electron
  escape a bit further each time.
- **Geometries and frequencies** are meaningless.
- With some methods and bases, the energy can even fall *below* the neutral:
  false binding.

## Example: H₂⁻ in the campaign

| Level | E(H₂⁻) − E(H₂) | [H₂⁻](app:s/2/-1/2) "bond length" | "Frequency" |
|---|---|---|---|
| r²SCAN-3c (L0) | +4.70 eV | 1.72 Å | — |
| ωB97X-D4 (L1) | +2.25 eV | 0.89 Å | 6000 cm⁻¹ |
| RI-MP2 (L1M) | +1.72 eV | 0.93 Å | 3215 cm⁻¹ |
| CCSD(T) (L2) | +1.56 eV | — | — |

The anion is above the neutral at every level: unbound, as expected. The
geometries disagree wildly and the frequencies make no sense (6000 cm⁻¹ is
far above [H₂](app:s/2/0/1)'s own 4401 cm⁻¹). Nothing in the individual outputs warns about it.

## Warning signs

- **Negative electron affinity**: compare with the neutral at the same level.
  This is the decisive test.
- **Positive HOMO energy.** An orbital with positive energy holds an electron
  that would be better off at infinity. In the campaign, [H₂⁻](app:s/2/-1/2)'s HOMO is
  positive at every level (+0.05 hartree at CCSD(T)), and so is the HOMO of
  the unbound triplet [H⁻](app:s/1/-1/3). Bound singlet [H⁻](app:s/1/-1/1) has a negative HOMO with HF
  orbitals (−0.05 hartree at L1M and L2). DFT is less reliable here:
  [self-interaction](self-interaction-error.md) can push the HOMO of a truly
  bound anion above zero (ωB97X-D4 gives +0.005 hartree for [H⁻](app:s/1/-1/1)). The
  campaign turns this into a flag
  ([HOMO and LUMO](../foundations/homo-and-lumo.md#the-unbound-anion-flag)).
- **Strong basis dependence**: the energy keeps falling as diffuse functions
  are added.
- **Odd geometries or frequencies** unlike those of the neutral.

## Where this appears in h_clusters

- `H₂⁻` is a Phase 1 sanity anchor: "not bound (a resonance); a calculation in
  a finite basis may falsely bind it" (`doc/Plan.md` §1.2).
- The verdict `unbound_electron`, from a negative EA or VDE, sits below every
  other stability category, so an anion's structural results are ignored
  once its electron is unbound (`doc/Plan.md` §2.2).
- HOMO and LUMO energies are stored for every result (`homo`, `lumo` in the
  `result` table, in hartree).
- Web app: the species page of an unbound anion explains why it has no
  structure, e.g. [H₂⁻](app:s/2/-1/2).

## References

- J. Simons, *J. Phys. Chem. A* **112**, 6401 (2008): molecular anions.
