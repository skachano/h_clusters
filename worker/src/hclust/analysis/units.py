"""Units of a cluster from how it falls apart: fragmentation trees and energy thresholds.

A distance cutoff alone mislabels the ion clusters (H6+ came out as three H2), and bond orders
form a continuum with no gap to cut in. Energies have gaps: a split costs <= 0.01 eV between
neutral van der Waals units, 0.05-0.4 eV between an ion and its ligands, and >= 2.8 eV inside
the covalent cores (H2, H2+, H3+). So:

- The *fragmentation tree* of a state: every binary channel (H_m^q -> H_a^p + H_b^r, spin
  allowed) with its cost D_e, each fragment a state with its own channels, down to atoms.
  Fragments are states at their own best energies (not their lowest limits), so every step of
  the tree is visible; a metastable fragment shows a negative cost.
- The *units* at a threshold: split along every channel cheaper than the threshold, recursively,
  until nothing cheaper is left. The pieces left are the units; all orders of splitting are
  followed, and if they end in different pieces, every alternative is kept. Two thresholds sit
  in the gaps: CORE_EV gives the covalent cores and their ligands (H3+ + 2 H2), CLUSTER_EV keeps
  ion clusters whole and splits only van der Waals units.
- Electron detachment appears in the tree but never splits a unit: H- (EA 0.75 eV) is a core.
- `assign_atoms` maps a set of units onto a structure's atoms: the partition with the right unit
  sizes (and charges) that keeps the most bond order inside units. Several equally good
  partitions mean the units are delocalised (H6+: two equivalent H3+), and are counted.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from functools import cache
from itertools import combinations

import numpy as np

from hclust.analysis.fragments import ELECTRON, StateEnergy, channels, couples, species_label
from hclust.species import allowed_multiplicities
from hclust.units import HARTREE_TO_EV

CORE_EV = 1.0  # covalent cores and their ligands
CLUSTER_EV = 0.013  # whole ion clusters; van der Waals units apart (see doc/Plan.md)
EQUIVALENT = 0.02  # bond-order sums closer than this are equally good atom assignments

Key = tuple[int, int, int]  # (m, charge, mult)


def key_label(key: Key) -> str:
    return species_label(*key)


@dataclass(frozen=True)
class Channel:
    parts: tuple[Key, ...]  # one fragment state, or two; detachment: (neutral,) + electron
    cost: float  # Eh, fragments minus the state
    electron: bool = False

    @property
    def label(self) -> str:
        return " + ".join([key_label(p) for p in self.parts] + ([ELECTRON] if self.electron else []))


class FragmentationTree:
    """Channels of every state, from the best energy of each computed state."""

    def __init__(self, states: list[StateEnergy]):
        self.energy = {(s.m, s.charge, s.mult): s.energy for s in states}
        self.channels = cache(self._channels)
        self._endpoints = cache(self._endpoints_uncached)

    def _channels(self, key: Key) -> tuple[Channel, ...]:
        """The cheapest spin-allowed fragment states of each binary split, cheapest first."""
        m, charge, mult = key
        if key not in self.energy:
            return ()
        out = []
        for first, second in channels(m, charge):
            best = None
            for m1 in allowed_multiplicities(first[0] - first[1]):
                for m2 in [2] if second is None else allowed_multiplicities(second[0] - second[1]):
                    a, b = (*first, m1), None if second is None else (*second, m2)
                    if not couples(m1, m2, mult) or a not in self.energy or (b is not None and b not in self.energy):
                        continue
                    cost = self.energy[a] + (0.0 if b is None else self.energy[b]) - self.energy[key]
                    if best is None or cost < best.cost:
                        best = Channel((a,) if b is None else (a, b), cost, electron=b is None)
            if best is not None:
                out.append(best)
        return tuple(sorted(out, key=lambda c: c.cost))

    def endpoints(self, key: Key, threshold_ev: float) -> tuple[tuple[Key, ...], ...]:
        """Every distinct set of units (sorted keys) reached by splitting below the threshold."""
        return self._endpoints(key, threshold_ev / HARTREE_TO_EV)

    def _endpoints_uncached(self, key: Key, threshold: float) -> tuple[tuple[Key, ...], ...]:
        cheap = [c for c in self.channels(key) if c.cost < threshold and not c.electron]
        if not cheap:
            return ((key,),)
        found = set()
        for c in cheap:
            a, b = (self._endpoints(p, threshold) for p in c.parts)
            for x in a:
                for y in b:
                    found.add(tuple(sorted(x + y, key=_unit_order)))
        return tuple(sorted(found, key=lambda e: (len(e), [_unit_order(k) for k in e])))

    def tree(self, key: Key, threshold_ev: float = CORE_EV) -> dict[str, list[dict]]:
        """The tree below `key` as a DAG: state label -> its channels, for every state reachable
        through channels cheaper than `threshold_ev` (the others are listed, not expanded)."""
        nodes: dict[str, list[dict]] = {}
        todo = [key]
        while todo:
            k = todo.pop()
            if key_label(k) in nodes:
                continue
            chans = self.channels(k)
            nodes[key_label(k)] = [{"split": c.label, "parts": [key_label(p) for p in c.parts],
                                    "electron": c.electron, "d_e": c.cost * HARTREE_TO_EV}
                                   for c in chans]
            todo += [p for c in chans if c.cost * HARTREE_TO_EV < threshold_ev for p in c.parts]
        return nodes


def _unit_order(key: Key) -> tuple:
    """Largest unit first, then by charge (cations first) and multiplicity."""
    return (-key[0], -key[1], key[2])


def units_label(units: tuple[Key, ...]) -> str:
    """'H3+ + 2 H2', 'H6+(4)', '4 H2 + H'."""
    counts: dict[Key, int] = {}
    for u in units:
        counts[u] = counts.get(u, 0) + 1
    return " + ".join(f"{n} {key_label(k)}" if n > 1 else key_label(k) for k, n in counts.items())


# --------------------------------------------------------------------------- atoms


@dataclass(frozen=True)
class Assignment:
    groups: tuple[tuple[int, ...], ...]  # atom indices of each unit, in the order of the units
    inside: float  # bond order kept inside units
    equivalent: int  # partitions as good as this one (1: unique)


def assign_atoms(units: tuple[Key, ...], weights: np.ndarray, charges: np.ndarray | None = None) -> Assignment:
    """The partition of the atoms into the units that keeps the most bond order (`weights`,
    symmetric) inside units; among equally sized units of different charge, the charge goes
    to the group whose atomic charges add up closest. Equivalent partitions are counted."""
    sizes = [u[0] for u in units]
    if sum(sizes) != len(weights):
        raise ValueError("units do not add up to the structure")
    scored = []
    for groups in _partitions(list(range(len(weights))), sizes):
        inside = sum(weights[i, j] for g in groups for i, j in combinations(g, 2))
        scored.append((inside, groups))
    best = max(s for s, _ in scored)
    good = [g for s, g in scored if s > best - EQUIVALENT]
    groups = next(g for s, g in scored if s == best)
    return Assignment(_label_groups(units, groups, charges), best, len(good))


def _partitions(atoms: list[int], sizes: list[int]) -> Iterator[tuple[tuple[int, ...], ...]]:
    """Every partition of `atoms` into groups of the given sizes, each once: the smallest atom
    left always starts the next group, which takes one of the distinct sizes left."""
    if not atoms:
        yield ()
        return
    first, others = atoms[0], atoms[1:]
    for size in sorted(set(sizes), reverse=True):
        rest = list(sizes)
        rest.remove(size)
        for chosen in combinations(others, size - 1):
            remaining = [a for a in others if a not in chosen]
            for tail in _partitions(remaining, rest):
                yield ((first, *chosen), *tail)


def _label_groups(units, groups, charges):
    """Order the groups like the units: by size, and by charge among equal sizes."""
    out, free = [], list(groups)
    order = sorted(range(len(units)), key=lambda i: -units[i][1])  # charged units choose first
    chosen: dict[int, tuple[int, ...]] = {}
    for i in order:
        size, charge = units[i][0], units[i][1]
        fits = [g for g in free if len(g) == size]
        if charges is not None and charge != 0:
            g = min(fits, key=lambda g: abs(sum(charges[a] for a in g) - charge))
        else:
            g = fits[0]
        free.remove(g)
        chosen[i] = g
    for i in range(len(units)):
        out.append(chosen[i])
    return tuple(out)
