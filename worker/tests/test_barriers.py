import numpy as np
import pytest

from hclust.geometry import Geometry
from hclust.studies import barriers

# H5+ (C2v, H3+.H2) as in the baseline: atom 0 is the apex, 1-2 the base, 3-4 the H2.
H5 = Geometry.hydrogens([
    [0.9702, 0.0, 0.0], [-0.3337, 0.3807, 0.0], [-0.3337, -0.3807, 0.0],
    [1.8509, 0.0, 0.4054], [1.8509, 0.0, -0.4054],
])


def distances(x):
    r = np.linalg.norm(x[:, None] - x[None], axis=-1)
    return np.sort(r[np.triu_indices(len(x), 1)])


def turn(angle):
    c, s = np.cos(angle), np.sin(angle)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def test_align_recovers_a_turned_and_renumbered_fragment():
    triangle = H5.coords[:3]
    moved = (triangle @ turn(0.7).T + [3, -1, 2])[[2, 0, 1]]
    placed = barriers.align(moved, triangle)
    assert placed == pytest.approx(triangle, abs=1e-9)
    assert barriers.align(np.zeros((1, 3)), np.array([[1.0, 2.0, 3.0]])) == pytest.approx(np.array([[1.0, 2.0, 3.0]]))


def test_partitions_and_symmetry_copies():
    assert len(list(barriers.ordered_partitions(6, [1, 5]))) == 6
    assert len(list(barriers.ordered_partitions(6, [3, 3]))) == 20
    # the two base atoms of H5+ are symmetry copies; the apex is not
    fp = lambda g: barriers.fingerprint(H5.coords, g)  # noqa: E731
    assert fp(((1,), (0, 2, 3, 4))) == fp(((2,), (0, 1, 3, 4)))
    assert fp(((0,), (1, 2, 3, 4))) != fp(((1,), (0, 2, 3, 4)))


def test_product_end_pulls_the_neutral_fragment_out():
    h2 = np.array([[0, 0, 0], [0, 0, 0.7416]])
    h3p = np.array([[0, 0, 0], [0.87, 0, 0], [0.435, 0.753, 0]])
    paths = barriers.channel_paths(H5, [("H2", 0, h2), ("H3+", 1, h3p)])
    groups, end = paths[0]
    assert len(paths) == 2 and paths[0][0] != paths[1][0]
    h2_atoms, rest = list(groups[0]), list(groups[1])
    gap = np.linalg.norm(end.coords[h2_atoms][:, None] - end.coords[rest][None], axis=-1).min()
    assert gap == pytest.approx(barriers.SEPARATION, abs=1e-6)
    # each fragment keeps its own shape
    assert distances(end.coords[h2_atoms]) == pytest.approx([0.7416], abs=1e-6)
    assert distances(end.coords[rest]) == pytest.approx(distances(h3p), abs=1e-6)
    assert barriers.describe(groups, ["H2", "H3+"]).startswith("H2 {")


def test_proton_hop_end_is_the_mirror_minimum():
    end = barriers.hop_end(H5)
    x = end.coords
    assert distances(x) == pytest.approx(distances(H5.coords), abs=1e-6)  # the same structure
    assert x[0] == pytest.approx(H5.coords[0])  # the apex stays
    # the old H2 (3, 4) is now bonded to the apex as the triangle's base, the old base is H2
    r = lambda i, j: np.linalg.norm(x[i] - x[j])  # noqa: E731
    assert r(0, 3) == pytest.approx(np.linalg.norm(H5.coords[0] - H5.coords[1]), abs=1e-6)
    assert r(1, 2) == pytest.approx(np.linalg.norm(H5.coords[3] - H5.coords[4]), abs=1e-6)
    # the shortest way: no H2 turns end over end, so no atom moves as far as a bond length
    assert np.linalg.norm(x - H5.coords, axis=1).max() < 0.6


def test_zpe_skips_the_imaginary_mode():
    assert barriers.zpe([-500.0, 1000.0, 3000.0]) == pytest.approx(2000.0 / 219474.6313632)
    assert barriers.zpe(None) is None


def test_ts_must_stay_near_its_starting_image():
    moved = Geometry(H5.symbols, H5.coords + 0.05)
    assert barriers.on_path(H5, moved)  # a rigid shift changes no distance
    stretched = Geometry(H5.symbols, H5.coords * [1.0, 1.0, 1.5])
    assert not barriers.on_path(H5, stretched)
