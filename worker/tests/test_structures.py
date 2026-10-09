import numpy as np
import pytest

from hclust.geometry import Geometry
from hclust.structures import (
    GENERATORS, composition, fragments, is_dissociated, random_clusters, same_structure, templates,
)


def min_distance(g: Geometry) -> float:
    return g.distances().min() if len(g) > 1 else np.inf


@pytest.mark.parametrize("m", range(1, 11))
def test_templates_have_m_atoms_and_no_clashes(m):
    gs = templates(m)
    assert gs, f"no template for m={m}"
    for g in gs:
        assert len(g) == m
        assert min_distance(g) > 0.7, g.comment


def test_template_menu_grows_with_m():
    names = lambda m: [g.comment.split()[0] for g in templates(m)]
    assert names(2) == ["chain"]
    assert names(3) == ["chain", "ring"]
    assert names(5) == ["chain", "ring", "sphere", "h2_units", "h3_core"]


def test_h3_core_motif():
    (g,) = GENERATORS["h3_core"](5)
    assert composition(g) == "H3·H2"
    assert not is_dissociated(g)


@pytest.mark.parametrize("m", [2, 5, 10])
def test_random_clusters_are_connected_reproducible_and_distinct(m):
    a = random_clusters(m, count=10, seed=7)
    assert len(a) == 10
    for g in a:
        assert len(g) == m and min_distance(g) >= 0.6
        assert len(fragments(g, 1.6)) == 1
    b = random_clusters(m, count=10, seed=7)
    assert all(np.allclose(x.coords, y.coords) for x, y in zip(a, b))
    c = random_clusters(m, count=10, seed=8)
    assert not np.allclose(a[0].coords, c[0].coords)


def test_fragments_and_composition():
    h2_pair = Geometry.hydrogens([[0, 0, 0], [0, 0, 0.74], [0, 3, 0], [0, 3, 0.74]])
    assert fragments(h2_pair) == [[0, 1], [2, 3]]
    assert is_dissociated(h2_pair)
    assert not is_dissociated(h2_pair, cutoff=3.5)
    assert composition(h2_pair) == "H2·H2"
    assert composition(Geometry.hydrogens([[0, 0, 0], [0, 0, 0.74], [0, 0, 3]])) == "H2·H"


def test_same_structure_ignores_permutation_rotation_translation():
    rng = np.random.default_rng(1)
    g = random_clusters(5, count=1, seed=3)[0]
    q, _ = np.linalg.qr(rng.normal(size=(3, 3)))
    moved = Geometry(g.symbols, (g.coords @ q.T + [1.0, -2.0, 0.5])[rng.permutation(5)])
    assert same_structure(g, moved)
    stretched = Geometry(g.symbols, g.coords * 1.1)
    assert not same_structure(g, stretched)
