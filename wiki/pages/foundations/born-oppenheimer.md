# Born–Oppenheimer approximation

!!! info "Prerequisites"
    [Schrödinger equation](schrodinger-equation.md)

The full Schrödinger equation treats electrons and nuclei together, which is
hopeless beyond the simplest cases. The Born–Oppenheimer (BO) approximation
splits it in two: first solve for the electrons with the nuclei frozen in
place, then let the nuclei move on the resulting energy landscape. It is the
reason a molecule has a shape at all, and the reason the
[potential energy surface](potential-energy-surface.md) exists.

## Idea

### Fast electrons, slow nuclei

A proton is 1836 times heavier than an electron, and with comparable forces
on both, the electrons move far faster. By the time the nuclei have moved
noticeably, the electrons have long since rearranged to suit the new
positions.

So treat the nuclear positions $\mathbf{R}$ as fixed parameters. Drop the
nuclear kinetic energy from the [molecular Hamiltonian](schrodinger-equation.md#the-molecular-hamiltonian);
what's left is the **electronic Hamiltonian**, and solving it gives an energy
for that one arrangement:

$$
\hat{H}_\text{elec}(\mathbf{R})\,\Psi_\text{elec}(\mathbf{r};\mathbf{R})
= E_\text{elec}(\mathbf{R})\,\Psi_\text{elec}(\mathbf{r};\mathbf{R})
$$

Repeat for every $\mathbf{R}$ and add the nuclear repulsion: the result,
$E(\mathbf{R})$, is the potential energy surface.

### Step two: the nuclei

The nuclei then obey their own Schrödinger equation, with $E(\mathbf{R})$
as the potential energy:

$$
\Big[-\sum_A \frac{1}{2M_A}\nabla_A^2 + E(\mathbf{R})\Big]\chi = E_\text{total}\,\chi
$$

Its solutions $\chi$ describe how the molecule
[vibrates](potential-energy-surface.md#vibrations-and-vibrational-levels) and
rotates. In practice this step is usually done approximately (harmonic
vibrations, rigid rotation; see [thermochemistry](../techniques/thermochemistry.md)).

### One surface for all isotopes

Nuclear masses appear only in the second step. So within BO, H₂, HD and D₂
share **exactly the same** potential energy surface: the same bond length
and the same well depth $D_e$. They differ only in how the nuclei move on it.
Deuterium is twice as heavy, so it vibrates more slowly and has a smaller
zero-point energy, which makes D₂ harder to break:

| | H₂ | D₂ |
|---|---|---|
| $D_e$ (well depth) | 4.75 eV | 4.75 eV |
| Vibrational frequency $\omega_e$ | 4401 cm⁻¹ | 3116 cm⁻¹ (= 4401/√2) |
| $D_0$ (measured) | 4.48 eV | 4.56 eV |

### When it breaks down

BO assumes the electrons always stay on one surface. That fails where two
electronic states come close in energy (near crossings of surfaces), where a
small nuclear motion can switch the electrons from one state to another.
This matters for photochemistry and some reactions. For the ground states of
the clusters in this project, BO is excellent: corrections to H₂'s
dissociation energy are below 0.01 eV.

!!! note "BO is not the same as treating nuclei classically"
    Within BO, the nuclei are still quantum particles: they have zero-point
    energy and can tunnel. Treating them as classical balls on the PES is a
    *further* approximation, and for hydrogen a poor one
    ([quantum nuclear effects](../pitfalls/quantum-nuclear-effects.md)).

## Where this appears in h_clusters

- Every ORCA job is a step-one calculation: fixed nuclei, electrons only. An
  optimization repeats it at many geometries.
- Step two enters through the frequency jobs (harmonic vibrations) and the
  thermochemistry built on them.
- Only H is in the campaign, but the isotope table explains why the
  hydrogen clusters' weak binding is so sensitive to zero-point energy.

## References

- A. Szabo, N. S. Ostlund, *Modern Quantum Chemistry*, §2.1.
- K. P. Huber, G. Herzberg, *Constants of Diatomic Molecules* (1979), and the
  NIST Chemistry WebBook: spectroscopic constants of H₂ and D₂.
