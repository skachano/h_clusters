# Potential energy surface

!!! info "Prerequisites"
    None, though [Schrödinger equation](schrodinger-equation.md) and
    [Born–Oppenheimer approximation](born-oppenheimer.md) give the background.

A molecule's energy depends on where its nuclei are. The **potential energy
surface** (PES) is that function: energy versus nuclear positions. Shapes of
molecules are its valleys, chemical reactions are paths between valleys, and
falling apart is a slope that levels out. Almost every question this project
asks ("what shape is [H₅⁺](app:s/5/1/1)?", "is [H₃](app:s/3/0/2) stable?") is a question about a PES.

## Idea

### Why nuclei get a surface at all

A proton is 1836 times heavier than an electron. Electrons move so much faster
that, as far as they are concerned, the nuclei stand still. This is the
[**Born–Oppenheimer approximation**](born-oppenheimer.md): fix the nuclei at positions $\mathbf{R}$,
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
| [H₂](app:s/2/0/1) | 2 | 1 (a curve: the bond length) |
| [H₃⁺](app:s/3/1/1) | 3 | 3 |
| [H₁₀](app:s/10/0/1) | 10 | 24 |

[H₂](app:s/2/0/1) is the only case you can draw. Everything below is easiest to picture on a
curve, then imagine in more dimensions.

### Landmarks

The slope of the surface is the **gradient** $\mathbf{g} = \partial E /
\partial \mathbf{R}$; its curvature is the **Hessian** matrix $\mathbf{H} =
\partial^2 E / \partial \mathbf{R}^2$.

| Landmark | Gradient | Curvature (Hessian eigenvalues) | Meaning |
|---|---|---|---|
| **Minimum** | zero | all positive | A stable structure. A PES can have several: the **isomers**. The lowest is the **global minimum** |
| **Saddle point** (first order) | zero | exactly one negative | A transition state: the highest point on the lowest path between two minima |
| **Asymptote** | goes to zero | | Fragments far apart, e.g. [H₂](app:s/2/0/1) → H + H |

The gradient finds points where the surface is flat; only the Hessian tells
a minimum from a saddle point. That is why the project computes
[vibrational frequencies](#vibrations-and-vibrational-levels) (which come from
the Hessian) after every optimization.

### Vibrations and vibrational levels

A minimum is where the nuclei *want* to be, but they never sit still there.
Push a ball off the bottom of a bowl and it rolls back, overshoots and rolls
back again. Nuclei on a PES do the same: in [H₂](app:s/2/0/1) the bond keeps stretching and
compressing around $R_e$. That oscillation is a **vibration**.

Near the bottom, any well looks like a parabola, $E \approx E_\text{min} +
\tfrac{1}{2}k(R - R_e)^2$, where the **force constant** $k$ is the curvature of
the PES at the minimum. Classically this is a spring, and it vibrates with
the **angular frequency**

$$
\omega = \sqrt{k/\mu}
$$

with $\mu$ the reduced mass ($m_\text{H}/2$ for [H₂](app:s/2/0/1)). $\omega$ is measured in
radians per second; the ordinary frequency, the number of oscillations per
second, is $\nu = \omega/2\pi$. A stiff bond (large $k$) and light atoms
(small $\mu$) vibrate fast. [H₂](app:s/2/0/1) completes one vibration every
$1/\nu$ = 7.6 femtoseconds.

Quantum mechanics changes one thing: the vibration can't have any energy it
likes. Only a ladder of **vibrational levels** is allowed, numbered by the
**vibrational quantum number** $v = 0, 1, 2, \ldots$. For a parabola they are
evenly spaced:

$$
E_v = \hbar\omega\left(v + \tfrac{1}{2}\right)
$$

A real well widens towards the top, so its levels crowd together there, and
only a finite number fit below the dissociation limit. [H₂](app:s/2/0/1) has 15 (v = 0 to 14).
A molecule that receives more energy than the top of the ladder falls apart.

The important level is the lowest. Even at $v = 0$, at absolute zero, the
energy is $\tfrac{1}{2}\hbar\omega$ above the bottom of the well, not zero.
That leftover is the **zero-point energy** (ZPE). It is forced by the
uncertainty principle: a nucleus confined to a well can't also have exactly
zero momentum, so it can't be at rest at the minimum. At room temperature
almost every [H₂](app:s/2/0/1) molecule is in $v = 0$ (the gap to $v = 1$ is about 20 times
the thermal energy), so $v = 0$ is the state that matters for stability.

!!! note "Units"
    Vibrations are usually quoted as wavenumbers in cm⁻¹, which is what
    ORCA prints:

    $$
    \tilde\nu = \frac{\nu}{c} = \frac{\omega}{2\pi c}
    $$

    Chemists still call $\tilde\nu$ the "frequency". The energy quantum is
    $\hbar\omega = h\nu = hc\tilde\nu$, so in cm⁻¹ it is just $\tilde\nu$
    (1 eV = 8065.5 cm⁻¹). [H₂](app:s/2/0/1)'s harmonic frequency is 4401 cm⁻¹
    ($\nu$ = 1.32 × 10¹⁴ Hz, $\omega$ = 8.29 × 10¹⁴ rad/s), so its harmonic ZPE
    is half of that, 2200 cm⁻¹ = 0.27 eV.

**More atoms, more vibrations.** A molecule with $N$ atoms has $3N - 6$
independent vibrations, the **normal modes**: one per PES dimension. Each has
its own frequency, found from the Hessian (the curvatures of the PES), and
each contributes its own zero-point energy, so

$$
\text{ZPE} = \sum_{i=1}^{3N-6} \tfrac{1}{2}\hbar\omega_i
$$

A negative curvature gives an imaginary frequency: that direction is downhill,
not a vibration, and the structure is a saddle point rather than a minimum.

### Binding energy: $D_e$ and $D_0$

Both measure how much energy it takes to pull a molecule apart into its
fragments. They differ in where you start:

- $D_e$ starts from the **bottom of the well**, the minimum of the PES. The
  subscript *e* stands for *equilibrium* geometry. It is what an electronic
  structure calculation gives directly, but no real molecule has this much
  binding, because none sits at the very bottom.
- $D_0$ starts from the **lowest vibrational level**, $v = 0$. It is the energy
  actually needed to break a molecule in its ground state, and what experiments
  measure.

The diagram shows [H₂](app:s/2/0/1)'s well with its vibrational levels, from a Morse
potential: a standard model curve fitted to [H₂](app:s/2/0/1)'s measured well depth and
vibration frequency. (The Morse model holds 17 levels rather than [H₂](app:s/2/0/1)'s real
15, but its ZPE and $D_0$ come out right.) Hover a level for its energy.

--8<-- "morse_levels.svg.html"

For a diatomic like [H₂](app:s/2/0/1), the fragments are single atoms, which can't vibrate.
So the whole ZPE of the molecule is lost on breaking, and

$$
D_0 = D_e - \text{ZPE}: \qquad 4.48\ \text{eV} = 4.75\ \text{eV} - 0.27\ \text{eV}
$$

**When the fragments are molecules too**, they keep zero-point energy of their
own. In general it is the *change* in ZPE that counts:

$$
D_0 = D_e - \Delta\text{ZPE}, \qquad
\Delta\text{ZPE} = \text{ZPE}(\text{cluster}) - \sum_\text{fragments} \text{ZPE}(\text{fragment})
$$

Take [H₅⁺](app:s/5/1/1) → [H₃⁺](app:s/3/1/1) + [H₂](app:s/2/0/1). The cluster has $3 \cdot 5 - 6 = 9$ normal modes; the
fragments have $3 + 1 = 4$ between them. The extra five are the soft motions
of [H₂](app:s/2/0/1) against [H₃⁺](app:s/3/1/1) that hold the cluster together, and each brings its own
zero-point energy. So $\Delta\text{ZPE}$ is typically positive and $D_0 < D_e$.

Hydrogen is the lightest atom, so its frequencies and ZPE are the largest of
any element. For the weakly bound clusters in this project, $\Delta\text{ZPE}$
can be larger than $D_e$. Then $D_0$ is negative: the PES has a well, but it
is too shallow to hold even the $v = 0$ level, and the cluster falls apart
even at absolute zero.

### One surface per electronic state

Each combination of charge and spin multiplicity is a different set of
electrons, so it has its own PES. Two hydrogen atoms with paired spins (the
singlet) attract and form [H₂](app:s/2/0/1). With parallel spins (the triplet) the curve has
essentially no well, only a tiny van der Waals dip: the atoms repel. A "species" in this project, such as [H₄⁺](app:s/4/1/2) in
the doublet state, is one surface.

## Example: the H₂ curve, computed two ways

[`h2_minimal_basis.py`](#the-code) computes the [H₂](app:s/2/0/1) energy at many bond
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
  [H₁₀](app:s/10/0/1), it starts many optimizations from different seed geometries and keeps the
  distinct results.
- **Geometry optimization** at each level in `worker/src/hclust/levels.py`
  (L0, L1, L1M) follows the gradient downhill to the nearest minimum.
- **Frequencies** check that each optimized structure is a minimum (all
  positive Hessian eigenvalues) and give its ZPE (`doc/Plan.md` §1, question 2).
  [H₃](app:s/3/0/2) is a known case where the stationary point is a saddle point. ORCA
  computes *harmonic* frequencies (the parabola approximation), which is least
  reliable for the floppy [H₂](app:s/2/0/1)-against-core motions (`doc/Plan.md` §7).
- **$D_e$ vs $D_0$:** binding energies are reported both without and with ZPE
  (ΔE and ΔE₀, `doc/Plan.md` §1.2), because the two can disagree on whether a
  cluster is bound.
- **Fragmentation channels** are the asymptotes: $D_\text{min}$ is the
  smallest dissociation energy over all ways of splitting a cluster
  (`doc/Plan.md` §1, question 3).
- **Method dependence is real here:** the DFT levels L0 and L1 turn the C₂ᵥ
  [H₅⁺](app:s/5/1/1) minimum into a proton-shared D₂d structure, while MP2 keeps it (comment on
  L1M in `worker/src/hclust/levels.py`). C₂ᵥ and D₂d are
  [point groups](../techniques/point-groups.md), names for the two shapes'
  symmetry. This is exactly why the project has more than
  one geometry level.
- Web app: the [grid](app:?q=d_e) shows each species' weakest channel by $D_e$;
  [switched to $D_0$](app:?q=d_0) it shows which clusters stay bound once ZPE is included.

## References

- A. Szabo, N. S. Ostlund, *Modern Quantum Chemistry*, §2.1 (Born–Oppenheimer
  approximation) and §3.5 (the minimal-basis [H₂](app:s/2/0/1) calculations reproduced here).
- F. Jensen, *Introduction to Computational Chemistry*, 3rd ed., chapters on
  optimization techniques and the Born–Oppenheimer approximation.
- W. Kołos, L. Wolniewicz, *J. Chem. Phys.* **49**, 404 (1968): the essentially exact
  [H₂](app:s/2/0/1) energy curve.
