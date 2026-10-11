"""Fragmentation channels, lowest asymptotes and stability verdicts (doc/Plan.md, 2.2).

Everything here is pure: it works on the best energy of each state, whatever level it comes
from. A *species* is (m, charge); a *state* adds the multiplicity.

- A channel of H_m^n is a split into two species H_a^p + H_(m-a)^(n-p) (charges -1..+1), or,
  for an anion, electron detachment H_m^- -> H_m + e-.
- The lowest asymptote of a species is the minimum over its own states and over all its
  channels, recursively. Binary channels therefore reach every multi-fragment limit
  (H4 -> H2 + H + H goes through H4 -> H2 + H2 or H3 + H, whichever is lower).
- Spin is conserved: fragment spins S1, S2 must couple to the state's S
  (|S1 - S2| <= S <= S1 + S2; the electron has S = 1/2). A spin-forbidden channel is not a
  way to fall apart (hydrogen has no spin-orbit coupling to drive it); that the state is not
  the species' ground state is what the spin gap says.
- D_q = (lowest channel) - (state), for q in E, E0 = E + ZPE, H(T) and G(T, p).
- The bare proton H+ is a state with E = 0 (no electrons); the free electron has E = 0 and no
  thermal terms (a common convention for ion thermochemistry).
"""

from dataclasses import dataclass
from enum import Enum
from functools import cache

from hclust.analysis.thermo import Thermo
from hclust.species import allowed_multiplicities

Species = tuple[int, int]  # (m, charge)
ELECTRON = "e-"
QUANTITIES = ("E", "E0", "H", "G")


class Verdict(str, Enum):
    """Ordered from least to most stable (the order of the enum)."""

    UNBOUND_ELECTRON = "unbound_electron"
    NOT_A_MINIMUM = "not_a_minimum"
    DISSOCIATES = "dissociates"
    METASTABLE = "metastable"  # a minimum, but some channel lies lower (D_e < 0)
    BOUND = "bound"  # D_e > 0
    BOUND_WITH_ZPE = "bound_with_zpe"  # D_0 > 0 as well
    ATOM = "atom"  # H and H+: nothing to fall apart into


@dataclass(frozen=True)
class StateEnergy:
    """The best structure of one state: electronic energy plus thermal corrections."""

    m: int
    charge: int
    mult: int
    energy: float  # Eh
    thermo: Thermo | None = None  # None: no frequencies, so only E is defined

    def value(self, q: str) -> float | None:
        if q == "E":
            return self.energy
        if self.thermo is None:
            return None
        return self.energy + {"E0": self.thermo.zpe, "H": self.thermo.h, "G": self.thermo.g}[q]


@dataclass(frozen=True)
class Limit:
    """An energy and the fragments that reach it, e.g. (H2, H2, H+)."""

    value: float
    parts: tuple[str, ...]

    def __add__(self, other: "Limit") -> "Limit":
        return Limit(self.value + other.value, tuple(sorted(self.parts + other.parts, key=_order)))

    @property
    def label(self) -> str:
        return " + ".join(self.parts)


def species_label(m: int, charge: int, mult: int | None = None) -> str:
    """'H3+', 'H-', 'H10'; with '(3)' for a multiplicity above the lowest allowed one."""
    label = f"H{m if m > 1 else ''}{ {-1: '-', 0: '', 1: '+'}[charge] }"
    if mult is not None and mult != allowed_multiplicities(m - charge)[0]:
        label += f"({mult})"
    return label


def couples(mult_1: int, mult_2: int, mult: int) -> bool:
    """Can spins with multiplicities mult_1 and mult_2 add up to multiplicity mult?"""
    low, high = abs(mult_1 - mult_2) + 1, mult_1 + mult_2 - 1
    return low <= mult <= high and (high - mult) % 2 == 0


def channels(m: int, charge: int) -> list[tuple[Species, Species | None]]:
    """Binary splits of H_m^charge, plus (H_m, None) = electron detachment for anions."""
    out: list[tuple[Species, Species | None]] = []
    for a in range(1, m // 2 + 1):
        for p in (-1, 0, 1):
            q = charge - p
            if q not in (-1, 0, 1) or (a == m - a and p > q):
                continue
            out.append(((a, p), (m - a, q)))
    if charge == -1:
        out.append(((m, 0), None))
    return out


class Asymptotes:
    """Lowest spin-allowed limits of every state for each quantity, from the best energies."""

    def __init__(self, states: list[StateEnergy]):
        self.states = {(s.m, s.charge, s.mult): s for s in states}
        self.lowest = cache(self._lowest)

    def own(self, species: Species, mult: int, q: str) -> Limit | None:
        """The state itself, without falling apart."""
        state = self.states.get((*species, mult))
        if state is None or (v := state.value(q)) is None:
            return None
        return Limit(v, (species_label(*species, mult),))

    def _lowest(self, species: Species, mult: int, q: str) -> Limit | None:
        candidates = [x for x in (self.own(species, mult, q), self.channel_limit(species, mult, q)) if x]
        return min(candidates, key=lambda x: x.value) if candidates else None

    def channel_limit(self, species: Species, mult: int, q: str) -> Limit | None:
        """The lowest limit with total multiplicity `mult` reachable by falling apart."""
        best = None
        for first, second in channels(*species):
            for mult_1 in allowed_multiplicities(first[0] - first[1]):
                for mult_2 in [2] if second is None else allowed_multiplicities(second[0] - second[1]):
                    if not couples(mult_1, mult_2, mult):
                        continue
                    a = self.lowest(first, mult_1, q)
                    b = Limit(0.0, (ELECTRON,)) if second is None else self.lowest(second, mult_2, q)
                    if a is not None and b is not None and (best is None or a.value + b.value < best.value):
                        best = a + b
        return best

    def lowest_with_electron(self, species: Species, mult: int, q: str = "E") -> Limit | None:
        """Lowest limit of `species` + e- with total multiplicity `mult` (ionization, detachment)."""
        limits = [
            x + Limit(0.0, (ELECTRON,)) for m in allowed_multiplicities(species[0] - species[1])
            if couples(m, 2, mult) and (x := self.lowest(species, m, q)) is not None
        ]
        return min(limits, key=lambda x: x.value) if limits else None

    def dissociation(self, state: StateEnergy, q: str) -> tuple[float, str] | None:
        """D_q of a state: lowest channel minus the state (positive = bound). None if unknown."""
        own = state.value(q)
        limit = self.channel_limit((state.m, state.charge), state.mult, q)
        if own is None or limit is None:
            return None
        return limit.value - own, limit.label


def judge(
    state: StateEnergy | None, d_e: float | None, d_0: float | None, *,
    m: int, charge: int, has_intact: bool, all_unbound: bool, has_minimum: bool,
) -> Verdict:
    """The verdict of one state, from its best reference energy (or the lack of one)."""
    if m == 1 and charge >= 0:
        return Verdict.ATOM
    if state is None:
        if charge == -1 and all_unbound:
            return Verdict.UNBOUND_ELECTRON
        if has_intact and not has_minimum:
            return Verdict.NOT_A_MINIMUM
        return Verdict.DISSOCIATES
    if d_e is None or d_e < 0:
        return Verdict.METASTABLE
    if d_0 is not None and d_0 > 0:
        return Verdict.BOUND_WITH_ZPE
    return Verdict.BOUND


def _order(part: str) -> tuple:
    """Fragments largest first, the electron last: 'H3+ + H2 + e-'."""
    if part == ELECTRON:
        return (1, 0, "")
    digits = part.split("(")[0][1:].rstrip("+-")
    return (0, -(int(digits) if digits else 1), part)

