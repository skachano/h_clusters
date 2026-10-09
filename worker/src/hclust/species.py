"""Electronic states (m, charge, multiplicity) of H_m clusters."""

from dataclasses import dataclass
from itertools import islice


@dataclass(frozen=True, order=True)
class State:
    """One electronic state of H_m with a given charge and spin multiplicity 2S+1."""

    m: int
    charge: int
    mult: int

    def __post_init__(self) -> None:
        if self.m < 1:
            raise ValueError(f"m must be >= 1, got {self.m}")
        if self.n_electrons < 0:
            raise ValueError(f"H{self.m} cannot have charge {self.charge:+d}")
        if self.mult not in allowed_multiplicities(self.n_electrons):
            raise ValueError(
                f"multiplicity {self.mult} impossible for {self.n_electrons} electrons"
            )

    @property
    def n_electrons(self) -> int:
        return self.m - self.charge

    @property
    def n_unpaired(self) -> int:
        return self.mult - 1

    @property
    def label(self) -> str:
        """E.g. 'H3+ (1)', 'H2- (2)'."""
        sign = {-1: "-", 0: "", 1: "+"}.get(self.charge, f"{self.charge:+d}")
        return f"H{self.m if self.m > 1 else ''}{sign} ({self.mult})"


def allowed_multiplicities(n_electrons: int) -> list[int]:
    """All multiplicities for N electrons, lowest first: N even -> 1, 3, ...; odd -> 2, 4, ..."""
    if n_electrons == 0:
        return [1]
    return list(range(n_electrons % 2 + 1, n_electrons + 2, 2))


def enumerate_states(
    m_range: range = range(1, 11),
    charges: tuple[int, ...] = (-1, 0, 1),
    n_mult: int = 2,
) -> list[State]:
    """States for every (m, charge), keeping the n_mult lowest multiplicities."""
    return [
        State(m, q, mult)
        for m in m_range
        for q in charges
        for mult in islice(allowed_multiplicities(m - q), n_mult)
    ]
