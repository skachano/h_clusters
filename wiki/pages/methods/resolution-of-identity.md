# Resolution of the identity (RI)

!!! info "Prerequisites"
    [Hartree–Fock](hartree-fock.md), [Basis sets](basis-sets.md)

The two-electron integrals $(\mu\nu|\lambda\sigma)$ are the bottleneck of
nearly every method: there are about $N^4/8$ of them for $N$ basis
functions. The **resolution of the identity** (RI), also called **density
fitting**, approximates them with far fewer three-index quantities. It
loses almost no accuracy and makes MP2 several times faster, which is what
made the MP2 geometry level affordable in this project.

## Idea

A two-electron integral is the Coulomb repulsion between two **pair
densities**, $\phi_\mu\phi_\nu$ and $\phi_\lambda\phi_\sigma$. RI expands each
pair density in a second, **auxiliary** basis set $\{\chi_P\}$:

$$
\phi_\mu(\mathbf{r})\phi_\nu(\mathbf{r}) \approx \sum_P c^{\mu\nu}_P\,\chi_P(\mathbf{r})
$$

Choosing the coefficients to minimize the error in the Coulomb energy gives

$$
(\mu\nu|\lambda\sigma) \approx \sum_{PQ} (\mu\nu|P)\,\big[\mathbf{V}^{-1}\big]_{PQ}\,(Q|\lambda\sigma),
\qquad V_{PQ} = (P|Q)
$$

Only three-index integrals $(\mu\nu|P)$ and the two-index matrix $\mathbf{V}$
are needed. The auxiliary basis is typically 3–4 times larger than the
orbital basis, but $N^2 N_\text{aux}$ numbers are still far fewer than $N^4$,
and they can be combined with fast matrix multiplications.

The name comes from the mathematical identity $1 = \sum_P |P\rangle\langle P|$
for a complete set, which RI applies with an incomplete one.

### Flavours

| Name | Approximates | Auxiliary basis |
|---|---|---|
| RI-J | Coulomb part of the Fock matrix | `/J` sets (def2/J) |
| RI-JK | Coulomb and exchange | `/JK` sets (e.g. aug-cc-pVTZ/JK) |
| RI-MP2 | Integrals in the MP2 energy and gradient | `/C` sets (e.g. aug-cc-pVTZ/C) |

The auxiliary sets are fitted to their orbital basis, so they come in matching
pairs. The error is systematic and small: much below chemical accuracy,
and it largely cancels in energy differences.

## Example: why L1M uses it

From the Phase 4 pilot on [H₁₀](app:s/10/0/1), MP2/aug-cc-pVTZ gradients on one core
(`doc/Plan.md`, Phase 4):

| MP2 gradient | Time |
|---|---|
| Conventional, closed shell | 200 s |
| Conventional, open shell | 880 s |
| RI-MP2 + RI-JK | 38 s |

A geometry optimization needs tens of gradients, and numerical frequencies
need about 60 more per structure. The factor of 5–20 decided whether an MP2
geometry level was affordable at all.

## Where this appears in [h_clusters](https://github.com/skachano/h_clusters)

- **L1M** is `RI-MP2 RIJK` with the basis line
  `aug-cc-pVTZ aug-cc-pVTZ/C aug-cc-pVTZ/JK` (orbital basis, then the two
  auxiliary sets) in `worker/src/hclust/levels.py`.
- ORCA 6.1 has no analytic RI-MP2 Hessian, so L1M frequencies are numerical
  (`analytic_hessian=False`), and only the best three structures per state get
  them.
- CCSD(T) (L2) runs without RI: its low-disk integral algorithm (`KC_AOX`)
  can't be combined with RI transformations (Phase 4 pilot).

## References

- F. Weigend, M. Häser, *Theor. Chem. Acc.* **97**, 331 (1997): RI-MP2.
- F. Weigend, *Phys. Chem. Chem. Phys.* **4**, 4285 (2002): RI for exchange (RI-JK) and its auxiliary basis sets.
- F. Jensen, *Introduction to Computational Chemistry*, 3rd ed., sections on
  integral approximations.
