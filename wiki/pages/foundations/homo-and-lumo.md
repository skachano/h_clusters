# HOMO and LUMO

!!! info "Prerequisites"
    [Hartree–Fock](../methods/hartree-fock.md) (orbitals and orbital energies),
    [Spin and multiplicity](spin-and-multiplicity.md)

Electrons fill orbitals from the bottom up. The **HOMO** is the highest
occupied molecular orbital; the **LUMO** is the lowest unoccupied one. They
are the frontier between the electrons a molecule has and the room it has for
more. Their energies are cheap by-products of every SCF calculation and give
quick estimates: how hard it is to remove an electron (HOMO), whether an
extra one can stay (HOMO of an anion), and how inert a closed shell is (the
gap between them). Each estimate has a known way of going wrong, and this
project runs into most of them.

## Idea

### Orbitals as energy levels

Hartree–Fock gives one orbital energy $\varepsilon_i$ per orbital, as many
orbitals as basis functions. The $N$ electrons go into the lowest ones (two
per orbital in a closed shell); the rest stay empty, as **virtual**
orbitals.

$$
\varepsilon_\text{HOMO} = \max_{i\,\in\,\text{occ}} \varepsilon_i, \qquad
\varepsilon_\text{LUMO} = \min_{a\,\in\,\text{virt}} \varepsilon_a, \qquad
\text{gap} = \varepsilon_\text{LUMO} - \varepsilon_\text{HOMO}
$$

The [H₂](app:s/2/0/1) example in [Hartree–Fock](../methods/hartree-fock.md#example-h2-from-scratch)
has only two orbitals: the bonding $\sigma_g$ at −0.578 hartree, holding both
electrons (the HOMO), and the antibonding $\sigma_u$ at +0.670 hartree, empty
(the LUMO).

**Open shells.** In unrestricted HF (UHF), spin-up and spin-down electrons
have separate orbitals with separate energies, so there are two HOMOs and two
LUMOs. For a doublet the highest occupied orbital is the singly occupied one
(the SOMO). This project takes the highest occupied and the lowest empty
orbital over both spins.

### HOMO: the ionization energy (Koopmans' theorem)

If one electron is removed from orbital $i$ and all the other orbitals are
kept frozen, the energy rises by exactly $-\varepsilon_i$. So

$$
\text{IE} \approx -\varepsilon_\text{HOMO}
$$

This is **Koopmans' theorem**. Two errors, of opposite sign, are left out:

- **Relaxation.** The remaining electrons rearrange once one is gone, which
  lowers the cation's energy. Alone, it makes $-\varepsilon_\text{HOMO}$ too
  large.
- **Correlation.** HF misses more correlation energy in the species with
  more electrons, so the neutral is too high and the IE too small.

For ordinary molecules they partly cancel, and $-\varepsilon_\text{HOMO}$ is
within about 1 eV of the measured **vertical** ionization energy. Vertical,
because the orbitals belong to one geometry: the estimate knows nothing about
the cation relaxing to a structure of its own.

### LUMO: the electron affinity, much less reliably

By the same argument, $\text{EA} \approx -\varepsilon_\text{LUMO}$, but this
estimate is poor. A virtual orbital is computed in the field of all $N$
electrons, which it is not part of: an added electron would be repelled by
all of them, and nothing lets them relax around it. Virtual orbitals come
out too high and too diffuse.

The basis set makes it worse. When the neutral cannot bind an extra electron,
the true LUMO is a free electron with energy zero, which a finite basis cannot
represent. The calculation reports instead the most diffuse function it has,
somewhere above zero, and that number changes with every basis set. The LUMO
of a neutral molecule in a diffuse basis says more about the basis than about
the molecule ([unbound anions](../pitfalls/unbound-anions.md)).

### The gap

In Koopmans' picture the gap is $\text{IE} - \text{EA}$, the **fundamental
gap**: what it costs to move an electron from one molecule to another far
away. It is not an excitation energy. A photon moves an electron within one
molecule, where it stays attracted by the hole it left, so excitation
energies are lower.

As a qualitative measure the gap is useful:

- A **large gap** means a closed shell that neither gives up nor accepts
  electrons easily: chemically hard and inert. Half the gap,
  $(\text{IE} - \text{EA})/2$, is Pearson's **chemical hardness**.
- A **small gap** means nearby configurations compete. A single determinant
  then describes the molecule badly, and perturbation theory, whose
  denominators are orbital-energy differences, breaks down
  ([MP2](../methods/mp2.md)).
- **Frontier-orbital** reasoning (Fukui) explains reactions by the overlap of
  one molecule's HOMO with another's LUMO.

### DFT orbitals

Kohn–Sham DFT also has orbitals and orbital energies. With the exact
functional the HOMO energy would equal minus the vertical IE exactly; with
approximate functionals it does not. The
[self-interaction error](../pitfalls/self-interaction-error.md) lets each
electron repel itself, which pushes the HOMO up, often by several eV. It is
worst for anions: r²SCAN-3c puts the HOMO of the bound [H⁻](app:s/1/-1/1) at +6.4 eV,
far above zero. This project therefore reads its frontier orbitals from HF.

## Examples from the campaign

HF orbitals of the CCSD(T)/aug-cc-pVTZ reference (L2) for the ground states,
in eV, next to the CCSD(T) energy for removing an electron (adiabatic, from
the verdicts):

| Species | Composition | HOMO | LUMO | Gap | −HOMO | CCSD(T) IE or detachment |
|---|---|---|---|---|---|---|
| H | H | −13.60 | +0.42 | 14.03 | 13.60 | 13.60 |
| [H₂](app:s/2/0/1) | [H₂](app:s/2/0/1) | −16.16 | +1.43 | 17.59 | 16.16 | 15.52 |
| [H₃](app:s/3/0/2) | H₂·H | −13.64 | +0.45 | 14.09 | 13.64 | 9.00 |
| [H₄](app:s/4/0/1) | H₂·H₂ | −16.01 | +1.31 | 17.32 | 16.01 | 13.47 |
| [H⁻](app:s/1/-1/1) | [H⁻](app:s/1/-1/1) | −1.24 | +6.59 | 7.83 | 1.24 | 0.73 |
| [H₃⁻](app:s/3/-1/1) | H₂·H⁻ | −1.28 | +3.85 | 5.13 | 1.28 | 0.78 |
| [H₉⁻](app:s/9/-1/1) | (H₂)₄·H⁻ | −1.57 | +3.68 | 5.25 | 1.57 | 0.99 |
| [H₃⁺](app:s/3/1/1) | [H₃⁺](app:s/3/1/1) | −32.91 | −5.38 | 27.53 | | |
| [H₅⁺](app:s/5/1/1) | H₃⁺·H₂ | −24.39 | −4.42 | 19.97 | | |
| [H₉⁺](app:s/9/1/1) | H₃⁺·(H₂)₃ | −21.92 | −3.53 | 18.39 | | |

Reading the table:

- **H atom: Koopmans is exact.** With one electron there is nothing to relax
  and nothing to correlate, so $-\varepsilon_\text{HOMO}$ = 13.60 eV is the
  ionization energy.
- **[H₂](app:s/2/0/1): a typical Koopmans error.** 16.16 eV against 15.52 eV. Part of the
  difference is vertical against adiabatic: [H₂⁺](app:s/2/1/2) has a longer bond.
- **[H₃](app:s/3/0/2) and [H₄](app:s/4/0/1): vertical is not adiabatic.** The HOMO of a cluster is that of
  its loosest unit: the H atom's 1s in H₂·H (−13.64 eV), [H₂](app:s/2/0/1)'s $\sigma_g$ in
  H₂·H₂ (−16.01 eV). Every neutral doublet in the campaign has its HOMO at
  −13.6 eV and every neutral singlet near −16.0 eV. But once ionized these
  clusters rearrange around an [H₃⁺](app:s/3/1/1) core (H₃⁺, and H₃⁺·H for [H₄⁺](app:s/4/1/2)), which
  releases a lot of energy, so the
  adiabatic IE is 4.6 eV (H₃) and 2.5 eV (H₄) below Koopmans. The orbital
  energy can't know that.
- **The [H⁻](app:s/1/-1/1) family: the HOMO labels the extra electron.** Every bound
  anion singlet has its HOMO between −1.2 and −1.6 eV, the [H⁻](app:s/1/-1/1) ion's lone
  pair. Each added [H₂](app:s/2/0/1) lowers it (−1.24, −1.28, −1.35, −1.45, −1.57 eV for
  [H⁻](app:s/1/-1/1) to [H₉⁻](app:s/9/-1/1)) and raises the detachment energy with it (0.73 to 0.99 eV): the
  [H₂](app:s/2/0/1) molecules stabilize the charge. Koopmans overestimates both, by about
  0.5 eV.
- **[H⁻](app:s/1/-1/1) in HF: a negative HOMO, yet no binding.** HF does not bind [H⁻](app:s/1/-1/1) at all:
  its HF energy is above that of H. The HOMO is still −1.24 eV because
  Koopmans keeps the orbitals frozen, and the remaining electron, stuck in the
  diffuse anion orbital, is a poor H atom. [H⁻](app:s/1/-1/1) is bound only through
  correlation, which CCSD(T) supplies.
- **LUMOs of neutrals: basis-set artefacts.** +0.4 to +1.4 eV for every
  neutral, all of them diffuse functions of aug-cc-pVTZ. The H atom has a
  bound anion (EA 0.75 eV) and still a positive LUMO (+0.42 eV): the LUMO
  estimate of the EA fails even in sign. In STO-3G the LUMO of [H₂](app:s/2/0/1) is the
  antibonding $\sigma_u$ at +18.2 eV, a different orbital altogether.
- **Cations: negative LUMOs.** A cation attracts an electron, so even its
  empty orbitals are bound.
- **[H₃⁺](app:s/3/1/1) has the largest gap of the campaign** (27.5 eV): two electrons in a
  bonding orbital spread over three protons, the simplest aromatic system.
  Adding [H₂](app:s/2/0/1) molecules raises its HOMO from −32.9 eV towards the −16.2 eV of
  free [H₂](app:s/2/0/1), as the positive charge is shared by more ligands.

### The unbound-anion flag

An anion whose extra electron is not bound still returns a HOMO, from the
pseudo-continuum state of the most diffuse functions. In aug-cc-pVTZ and
def2-TZVPPD that state lies near +1 eV, while bound anions lie below
+0.2 eV (ωB97X-D4) or −0.7 eV (HF). The campaign uses the gap between them as a
cheap test: an anion with a HOMO above +0.5 eV is flagged `unbound`, and its
geometry is not trusted. The decisive test is still the energy: whether the
anion is below the neutral plus a free electron
([Ionization energy and electron affinity](../techniques/ionization-and-electron-affinity.md)).

## Where this appears in h_clusters

- **Parsing.** `_frontier_orbitals` in `worker/src/hclust/parse.py` reads the
  last `ORBITAL ENERGIES` block of an ORCA output and takes the highest
  occupied and lowest empty orbital over both spins. For MP2 and CCSD(T) jobs
  these are the orbitals of the HF reference. They are stored in hartree
  (`homo`, `lumo` in the `result` table).
- **Unbound anions.** `Level.unbound_homo_ev` in `worker/src/hclust/levels.py`
  sets the +0.5 eV threshold for ωB97X-D4, ωB97M-V, RI-MP2 and the HF
  reference of CCSD(T). r²SCAN-3c has none: its self-interaction error and
  lack of diffuse functions put even bound [H⁻](app:s/1/-1/1) above +4 eV (`doc/Plan.md`,
  Phase 4).
- **Verdicts.** A state's reference structure must not be an unbound anion by
  its own HOMO or its geometry job's (`worker/src/hclust/analysis/verdicts.py`).
- Web app: "HOMO / LUMO (HF)" among the properties on each species page, e.g.
  [H₃⁺](app:s/3/1/1), and the [HOMO–LUMO gap](app:trends) across the grid
  on the Trends page.

## References

- T. Koopmans, *Physica* **1**, 104 (1934): the theorem.
- A. Szabo, N. S. Ostlund, *Modern Quantum Chemistry*, §3.3 (Koopmans'
  theorem, with the relaxation and correlation errors).
- K. Fukui, T. Yonezawa, H. Shingu, *J. Chem. Phys.* **20**, 722 (1952):
  frontier orbitals.
- J. P. Perdew, R. G. Parr, M. Levy, J. L. Balduz, *Phys. Rev. Lett.* **49**,
  1691 (1982): the Kohn–Sham HOMO and the ionization energy.
- J.-L. Bredas, *Mater. Horiz.* **1**, 17 (2014): "Mind the gap!", the
  fundamental, optical and HOMO–LUMO gaps.
