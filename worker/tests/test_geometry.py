import numpy as np

from hclust.geometry import Geometry


def test_xyz_roundtrip():
    g = Geometry.hydrogens([[0, 0, 0], [0, 0, 0.74]], comment="H2")
    back = Geometry.from_xyz(g.to_xyz())
    assert back.symbols == ("H", "H")
    assert back.comment == "H2"
    np.testing.assert_allclose(back.coords, g.coords)


def test_distances_sorted():
    g = Geometry.hydrogens([[0, 0, 0], [1, 0, 0], [0, 2, 0]])
    np.testing.assert_allclose(g.distances(), [1.0, 2.0, np.sqrt(5)])
