# Methods

How the electronic energy is approximated, from cheap to accurate: the rungs of the project's [method ladder](../htc/method-ladder.md). Diffusion Monte Carlo is the exception: it solves for the motion of the nuclei on a given energy surface.

- [Hartree–Fock](hartree-fock.md): the mean field and the SCF loop; H₂ from scratch
- [Density functional theory](dft.md): functionals, dispersion corrections, and what DFT gets wrong
- [MP2](mp2.md): the cheapest correlation; the second geometry level
- [Coupled cluster](coupled-cluster.md): CCSD(T), the reference energies
- [Diffusion Monte Carlo](diffusion-monte-carlo.md): the exact nuclear ground state by random walks; are the weak clusters bound?
- [Semi-empirical tight binding (GFN2-xTB)](xtb.md): very fast, and wrong about H₃⁺
- [Basis sets](basis-sets.md): Gaussians, ζ, polarization, diffuse; convergence
- [Resolution of the identity (RI)](resolution-of-identity.md): the integral approximation that made MP2 affordable
