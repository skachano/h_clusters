# Potential energy surface

!!! info "Prerequisites"
    None. This is a good first page.

A molecule's energy depends on where its nuclei are. The **potential energy
surface** (PES) is that function: energy versus nuclear positions. Shapes of
molecules are its valleys, chemical reactions are paths between valleys, and
falling apart is a slope that levels out. Almost every question this project
asks ("what shape is H₅⁺?", "is H₃ stable?") is a question about a PES.

## Idea

### Why nuclei get a surface at all

A proton is 1836 times heavier than an electron. Electrons move so much faster
that, as far as they are concerned, the nuclei stand still. This is the
**Born–Oppenheimer approximation**: fix the nuclei at positions $\mathbf{R}$,
solve for the electrons only, and repeat for every $\mathbf{R}$ you care about.
Each solve gives one number, the electronic energy plus the repulsion between
the fixed nuclei:

$$
E(\mathbf{R}) = E_\text{elec}(\mathbf{R}) + \sum_{A<B} \frac{Z_A Z_B}{|\mathbf{R}_A - \mathbf{R}_B|}
$$

(in atomic units; $Z_A$ is the charge of nucleus $A$, 1 for hydrogen). The
nuclei then move on this surface like balls rolling on a landscape. The
electrons are what *makes* the landscape.

### How many dimensions

$N$ atoms have $3N$ coordinates, but moving or rotating the whole molecule
doesn't change its energy. That leaves $3N - 6$ internal coordinates ($3N - 5$
for a linear molecule).

| Species | Atoms | PES dimensions |
|---|---|---|
| H₂ | 2 | 1 (a curve: the bond length) |
| H₃⁺ | 3 | 3 |
| H₁₀ | 10 | 24 |

H₂ is the only case you can draw. Everything below is easiest to picture on a
curve, then imagine in more dimensions.

### Landmarks

The slope of the surface is the **gradient** $\mathbf{g} = \partial E /
\partial \mathbf{R}$; its curvature is the **Hessian** matrix $\mathbf{H} =
\partial^2 E / \partial \mathbf{R}^2$.

| Landmark | Gradient | Curvature (Hessian eigenvalues) | Meaning |
|---|---|---|---|
| **Minimum** | zero | all positive | A stable structure. A PES can have several: the **isomers**. The lowest is the **global minimum** |
| **Saddle point** (first order) | zero | exactly one negative | A transition state: the highest point on the lowest path between two minima |
| **Asymptote** | goes to zero | | Fragments far apart, e.g. H₂ → H + H |

The gradient finds points where the surface is flat; only the Hessian tells
a minimum from a saddle point. That is why the project computes frequencies
(which come from the Hessian) after every optimization.

### Binding energy

The **dissociation energy** $D_e$ is the depth of the well: the energy of the
separated fragments minus the energy at the minimum. Real molecules can't sit
at the very bottom, because quantum mechanics gives each vibration a minimum
**zero-point energy** (ZPE). The measurable binding energy is therefore

$$
D_0 = D_e - \text{ZPE}
$$

For H₂, $D_e$ = 4.75 eV and $D_0$ = 4.48 eV: the ZPE costs 0.27 eV, about 6 %.
Hydrogen is the lightest atom, so its ZPE effects are the largest of any element. For
the weakly bound clusters in this project ZPE can exceed $D_e$ entirely, so a
cluster with a well on the PES can still fall apart.

### One surface per electronic state

Each combination of charge and spin multiplicity is a different set of
electrons, so it has its own PES. Two hydrogen atoms with paired spins (the
singlet) attract and form H₂. With parallel spins (the triplet) the curve has
essentially no well, only a tiny van der Waals dip: the atoms repel. A "species" in this project, such as H₄⁺ in
the doublet state, is one surface.

## Example: the H₂ curve, computed two ways

[`h2_minimal_basis.py`](#the-code) computes the H₂ energy at many bond
lengths with two methods (explained in [Hartree–Fock](../methods/hartree-fock.md)),
both in the smallest possible basis set, STO-3G:

- **Hartree–Fock (RHF)**: the electrons each feel only the *average* repulsion of
  the other.
- **Full CI**: the exact answer within the basis set.

--8<-- "h2_pes.svg.html"

| R (bohr) | R (Å) | E(RHF) (hartree) | E(FCI) (hartree) |
|---|---|---|---|
| 0.60 | 0.318 | −0.6683 | −0.6765 |
| 0.80 | 0.423 | −0.9473 | −0.9576 |
| 1.00 | 0.529 | −1.0660 | −1.0790 |
| 1.20 | 0.635 | −1.1103 | −1.1267 |
| 1.40 | 0.741 | −1.1167 | −1.1373 |
| 1.60 | 0.847 | −1.1031 | −1.1288 |
| 2.00 | 1.058 | −1.0492 | −1.0885 |
| 2.50 | 1.323 | −0.9658 | −1.0305 |
| 3.00 | 1.588 | −0.8853 | −0.9852 |
| 4.00 | 2.117 | −0.7611 | −0.9438 |
| 5.00 | 2.646 | −0.6864 | −0.9349 |
| 6.00 | 3.175 | −0.6451 | −0.9334 |

What the curve shows:

1. **Repulsive wall.** At short distance the nuclear repulsion $1/R$ dominates and the
   energy shoots up.
2. **Minimum.** Full CI puts the bottom of the well at 0.74 Å and Hartree–Fock at
   0.71 Å; experiment says 0.741 Å. Geometries are often the easiest thing to
   get right.
3. **Asymptote.** As the atoms separate, full CI levels off at exactly
   2 E(H) = −0.933 hartree, two isolated atoms. Hartree–Fock keeps rising, to
   0.29 hartree (7.8 eV) too high at 3.2 Å. This is a famous failure of
   restricted Hartree–Fock; [Hartree–Fock](../methods/hartree-fock.md#what-hartreefock-misses)
   explains why it happens.
4. **Depth.** Full CI gives $D_e$ = 5.55 eV, but experiment says 4.75 eV. Full
   CI is exact *within the basis*, so the error is the basis set: two functions
   are far too few. The exact energy at 1.4 bohr is −1.1745 hartree, 0.037 hartree
   below this full CI. The isolated atom suffers even more (−0.4666 hartree
   instead of the exact −0.5), so the error doesn't cancel and the well looks
   too deep.

The lesson for everything else in this wiki: **a PES belongs to a method and a
basis set**, not just to a molecule. Change either and the minima can move,
appear or vanish.

### The code

???+ example "Run it"
    ```sh
    docker run --rm -v ./wiki/examples:/ex hclust-worker:dev python /ex/h2_minimal_basis.py
    ```

??? example "Full source: `wiki/examples/h2_minimal_basis.py`"
    ```python
    --8<-- "h2_minimal_basis.py"
    ```

## Where this appears in h_clusters

- **Structure search** (`doc/Plan.md` §2.1, `worker/src/hclust/structures.py`)
  looks for all the low minima on each species' PES. With 24 dimensions for
  H₁₀, it starts many optimizations from different seed geometries and keeps the
  distinct results.
- **Geometry optimization** at each level in `worker/src/hclust/levels.py`
  (L0, L1, L1M) follows the gradient downhill to the nearest minimum.
- **Frequencies** check that each optimized structure is a minimum (all
  positive Hessian eigenvalues) and give its ZPE (`doc/Plan.md` §1, question 2).
  H₃ is a known case where the stationary point is a saddle point.
- **Fragmentation channels** are the asymptotes: $D_\text{min}$ is the
  smallest dissociation energy over all ways of splitting a cluster
  (`doc/Plan.md` §1, question 3).
- **Method dependence is real here:** the DFT levels L0 and L1 turn the C₂ᵥ
  H₅⁺ minimum into a proton-shared D₂d structure, while MP2 keeps it (comment on L1M in
  `worker/src/hclust/levels.py`). This is exactly why the project has more than
  one geometry level.

## References

- A. Szabo, N. S. Ostlund, *Modern Quantum Chemistry*, §2.1 (Born–Oppenheimer
  approximation) and §3.5 (the minimal-basis H₂ calculations reproduced here).
- F. Jensen, *Introduction to Computational Chemistry*, 3rd ed., chapters on
  optimization techniques and the Born–Oppenheimer approximation.
- W. Kołos, L. Wolniewicz, *J. Chem. Phys.* **49**, 404 (1968): the essentially exact
  H₂ energy curve.
