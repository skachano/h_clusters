# Point groups and symmetry

!!! info "Prerequisites"
    None, though [Frequencies](frequencies.md) helps for the examples.

A molecule's **point group** is the set of symmetry operations (rotations,
reflections, inversions) that leave it looking unchanged. It is a compact
name for its shape: "D₃h" says [H₃⁺](app:s/3/1/1) is an equilateral triangle. Symmetry
also has consequences: it makes some vibrations degenerate, sets the
rotational entropy, and keeps an optimizer on a symmetric path.

## Idea

### Symmetry operations

| Symbol | Operation |
|---|---|
| $E$ | identity (do nothing) |
| $C_n$ | rotate by $360°/n$ about an axis |
| $\sigma$ | reflect through a plane ($\sigma_h$ perpendicular to the main axis, $\sigma_v$ containing it) |
| $i$ | invert through the centre: $(x, y, z) \to (-x, -y, -z)$ |
| $S_n$ | rotate by $360°/n$, then reflect through the perpendicular plane |

The operations that leave a molecule unchanged always form a mathematical
group, and only a limited number of such groups exist.

### Point groups met in this project

| Point group | Elements (main ones) | Example |
|---|---|---|
| D∞h | infinite-fold axis, $i$ | [H₂](app:s/2/0/1), symmetric linear chains |
| C∞v | infinite-fold axis, no $i$ | asymmetric linear chains |
| D₃h | $C_3$, three $C_2$, $\sigma_h$ | [H₃⁺](app:s/3/1/1): equilateral triangle |
| C₂ᵥ | $C_2$, two $\sigma_v$ | [H₅⁺](app:s/5/1/1) (MP2): an [H₂](app:s/2/0/1) on one corner of [H₃⁺](app:s/3/1/1), perpendicular to the triangle |
| D₂d | $S_4$, $C_2$ axes, two $\sigma_d$ | [H₅⁺](app:s/5/1/1) (DFT): a proton between two crossed [H₂](app:s/2/0/1) |
| T_d | tetrahedral | four points on a sphere |
| C₁ | none ($E$ only) | no symmetry at all |

### Why it matters

- **Degenerate modes.** Symmetric molecules have vibrations with exactly equal
  frequencies. [H₃⁺](app:s/3/1/1)'s 2743 cm⁻¹ mode comes twice: in D₃h the two
  distortions of the triangle are related by a 120° rotation, so they must
  have the same energy.
- **Rotational entropy.** The **symmetry number** $\sigma$ counts how many
  rotations map the molecule onto itself. Rotating [H₂](app:s/2/0/1) by 180° gives an
  indistinguishable molecule, so only half its orientations are distinct:
  $S_\text{rot}$ is reduced by $k_B\ln\sigma$ ([thermochemistry](thermochemistry.md)).
  Values in the campaign: [H₂](app:s/2/0/1) 2, [H₃⁺](app:s/3/1/1) 6, C₂ᵥ [H₅⁺](app:s/5/1/1) 2, D₂d [H₅⁺](app:s/5/1/1) 4.
- **Optimizations keep symmetry.** The gradient of a symmetric structure is
  itself symmetric, so an optimizer can't break symmetry on its own and can
  stop at a symmetric saddle point. That's why the runner displaces along
  imaginary modes ([frequencies](frequencies.md#where-this-appears-in-h_clusters)).
- **Selection rules** in spectroscopy follow from the symmetry of each mode.

## Tolerances

Real computed geometries are never exactly symmetric: optimizations stop
when the forces are *small*, not zero. A symmetry finder therefore needs a
tolerance, and a too-strict one gives the wrong answer. Two examples from
this project:

- ORCA labelled an ωB97M-V [H₃⁺](app:s/3/1/1) C₂ᵥ, although its three bonds differed by less
  than 3·10⁻⁴ Å (Phase 1 findings).
- In the baseline campaign, three RI-MP2 [H₅⁺](app:s/5/1/1) results with the same energy to
  10⁻⁶ hartree and the same bond lengths to 10⁻⁴ Å are labelled C₂ᵥ, C₁ and C₁.

## Where this appears in [h_clusters](https://github.com/skachano/h_clusters)

- ORCA's point group and symmetry number are parsed into the `result` table
  (`point_group`, `symmetry_number`), but are not trusted for analysis.
- Phase 5 adds the project's own `analysis/symmetry.py` with a tolerant
  finder (pymatgen's `PointGroupAnalyzer`), and a shape class (linear, planar,
  3D) per structure (`doc/Plan.md` §2.2).
- Duplicate detection doesn't use symmetry at all: the
  [distance fingerprint](structure-search.md#how-this-project-does-it) compares
  structures directly.
- [Web app](app:): the [grid](app:) and each species page show the point group and
  shape class of every structure.

## References

- F. A. Cotton, *Chemical Applications of Group Theory*, 3rd ed. (Wiley, 1990).
- P. W. Atkins, J. de Paula, *Physical Chemistry*, chapter on molecular symmetry.
