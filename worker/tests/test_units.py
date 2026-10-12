"""Units from fragmentation thresholds, and their atoms."""

import numpy as np
import pytest

from hclust.analysis.fragments import StateEnergy
from hclust.analysis.units import CLUSTER_EV, CORE_EV, FragmentationTree, _partitions, assign_atoms, units_label
from hclust.units import HARTREE_TO_EV

EV = 1 / HARTREE_TO_EV
H, H2, H3P = -0.5, -1.17, -1.34


def tree() -> FragmentationTree:
    states = [
        StateEnergy(1, 0, 2, H), StateEnergy(1, 1, 1, 0.0), StateEnergy(1, -1, 1, H - 0.75 * EV),
        StateEnergy(2, 0, 1, H2), StateEnergy(2, 1, 2, -0.60), StateEnergy(3, 1, 1, H3P),
        StateEnergy(4, 0, 1, 2 * H2 - 0.005 * EV),  # (H2)2, van der Waals
        StateEnergy(5, 1, 1, H3P + H2 - 0.37 * EV),  # H3+ . H2
        StateEnergy(7, 1, 1, H3P + 2 * H2 - 0.59 * EV),  # H5+ + H2 at 0.22 eV
        StateEnergy(3, -1, 1, H - 0.75 * EV + H2 - 0.05 * EV),  # H- . H2
    ]
    return FragmentationTree(states)


def test_core_and_cluster_units():
    t = tree()
    assert [units_label(e) for e in t.endpoints((7, 1, 1), CORE_EV)] == ["H3+ + 2 H2"]
    assert [units_label(e) for e in t.endpoints((7, 1, 1), CLUSTER_EV)] == ["H7+"]
    assert [units_label(e) for e in t.endpoints((4, 0, 1), CLUSTER_EV)] == ["2 H2"]  # van der Waals apart
    assert [units_label(e) for e in t.endpoints((3, -1, 1), CORE_EV)] == ["H2 + H-"]
    # covalent cores stay whole, and electron detachment (0.75 eV) never splits H-
    for key in ((2, 0, 1), (3, 1, 1), (1, -1, 1)):
        assert t.endpoints(key, CORE_EV) == ((key,),)


def test_channels_and_tree():
    t = tree()
    first = t.channels((5, 1, 1))[0]
    assert first.label == "H2 + H3+" and first.cost * HARTREE_TO_EV == pytest.approx(0.37)
    detach = [c for c in t.channels((1, -1, 1)) if c.electron]
    assert detach and detach[0].label == "H + e-" and detach[0].cost * HARTREE_TO_EV == pytest.approx(0.75)
    nodes = t.tree((7, 1, 1))
    # expanded below 1 eV: H7+ -> H3+ + H4 costs 0.585 eV, so H4 is reached too
    assert set(nodes) == {"H7+", "H5+", "H4", "H3+", "H2"}
    assert nodes["H7+"][0]["split"] == "H2 + H5+" and nodes["H7+"][0]["d_e"] == pytest.approx(0.22)


def test_every_order_of_splitting_is_followed():
    # two cheap channels ending in different pieces: both alternatives are kept
    t = FragmentationTree([
        StateEnergy(1, 0, 2, H), StateEnergy(1, 1, 1, 0.0), StateEnergy(2, 0, 1, H2),
        StateEnergy(2, 1, 2, H2 + 0.2 * EV), StateEnergy(3, 1, 1, H3P),
        StateEnergy(4, 1, 2, H3P + H - 0.1 * EV),  # -> H3+ + H at 0.1 eV
    ])
    t.energy[(2, 1, 2)] = H3P + H - H2 - 0.1 * EV + 0.05 * EV  # H2+ + H2 at 0.15 eV
    t.channels.cache_clear()
    labels = [units_label(e) for e in t.endpoints((4, 1, 2), CORE_EV)]
    assert set(labels) == {"H3+ + H", "H2+ + H2"}


def test_partitions_are_complete_and_unique():
    parts = list(_partitions(list(range(5)), [3, 2]))
    assert len(parts) == 10 and len({frozenset(map(frozenset, p)) for p in parts}) == 10
    assert len(list(_partitions(list(range(6)), [2, 2, 2]))) == 15
    assert len(list(_partitions(list(range(6)), [3, 2, 1]))) == 60


def test_atom_assignment_and_delocalisation():
    # H5+: a triangle 0-1-2 and an H2 3-4, weakly linked
    w = np.zeros((5, 5))
    for i, j, v in ((0, 1, 0.44), (0, 2, 0.44), (1, 2, 0.44), (3, 4, 0.9), (2, 3, 0.1)):
        w[i, j] = w[j, i] = v
    a = assign_atoms(((3, 1, 1), (2, 0, 1)), w)
    assert a.groups == ((0, 1, 2), (3, 4)) and a.equivalent == 1
    # H6+ like ours: two equivalent triangles share the bond 0-3
    w = np.zeros((6, 6))
    for i, j, v in ((1, 2, 0.55), (4, 5, 0.55), (0, 3, 0.39), (0, 4, 0.35), (0, 5, 0.35), (3, 1, 0.35), (3, 2, 0.35)):
        w[i, j] = w[j, i] = v
    a = assign_atoms(((3, 1, 1), (2, 0, 1), (1, 0, 2)), w)
    assert a.equivalent == 2 and len(a.groups[0]) == 3 and len(a.groups[2]) == 1
    # equal sizes, different charges: the charge follows the atomic charges
    w = np.zeros((4, 4))
    w[0, 1] = w[1, 0] = w[2, 3] = w[3, 2] = 0.8
    charges = np.array([0.0, 0.0, 0.5, 0.5])
    a = assign_atoms(((2, 1, 2), (2, 0, 1)), w, charges)
    assert a.groups == ((2, 3), (0, 1))
