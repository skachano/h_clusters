"""Thermochemistry and shape descriptors, checked against ORCA's own 298.15 K output."""

import numpy as np
import pytest

from hclust.analysis.shape import principal_moments, radius_of_gyration, shape_class
from hclust.analysis.thermo import rrho
from hclust.geometry import Geometry
from hclust.parse import parse_orca


@pytest.mark.parametrize(("fixture", "mult", "ts_tolerance"), [
    ("h2p_optnumfreq_wb97mv", 2, 2e-6),  # linear, doublet: S_el = k ln 2
    ("h3p_optfreq_rimp2", 1, 2e-6),  # D3h, symmetry number 6
    # (H2)2: modes of 11-93 cm-1, where quasi-RRHO matters. ORCA's free-rotor entropy is
    # ~0.03 k per mode below 50 cm-1 lower than Grimme's published formula (Plan, Phase 5).
    ("h4_vdw_optfreq_rimp2", 1, 1.5e-4),
])
def test_rrho_reproduces_orca(orca_fixture, fixture, mult, ts_tolerance):
    r = parse_orca(orca_fixture(fixture), is_opt=True)
    t = rrho(r.geometry, r.frequencies, mult, r.symmetry_number)
    orca = r.thermo
    e_el = orca["elEnergy"]
    assert t.zpe == pytest.approx(orca["zpe"], abs=1e-7)
    assert e_el + t.u == pytest.approx(orca["innerEnergyU"], abs=1e-6)
    assert e_el + t.h == pytest.approx(orca["enthalpyH"], abs=1e-6)
    assert t.ts == pytest.approx(orca["entropyS"], abs=ts_tolerance)
    assert e_el + t.g == pytest.approx(orca["freeEnergyG"], abs=ts_tolerance)


def test_pressure_enters_only_through_translational_entropy(orca_fixture):
    r = parse_orca(orca_fixture("h3p_optfreq_rimp2"), is_opt=True)
    one, ten = (rrho(r.geometry, r.frequencies, 1, 6, pressure=p) for p in (1.0, 10.0))
    kt = 298.15 * 1.380649e-23 / 4.3597447222071e-18
    assert one.h == ten.h
    assert ten.g - one.g == pytest.approx(kt * np.log(10), rel=1e-9)


def test_atom_has_only_translation_and_spin():
    t = rrho(Geometry.hydrogens([[0, 0, 0]]), None, 2)
    kt = 298.15 * 1.380649e-23 / 4.3597447222071e-18
    assert t.zpe == 0 and t.thermal == pytest.approx(1.5 * kt)


def test_shape_classes():
    assert shape_class(Geometry.hydrogens([[0, 0, 0]])) == "atom"
    assert shape_class(Geometry.hydrogens([[0, 0, 0], [0, 0, 0.74], [0, 0, 3.0]])) == "linear"
    assert shape_class(Geometry.hydrogens([[0, 0, 0], [0.87, 0, 0], [0.435, 0.753, 0]])) == "planar"
    tetra = Geometry.hydrogens([[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]])
    assert shape_class(tetra) == "3D"
    assert principal_moments(tetra) == pytest.approx([8.064] * 3)
    assert radius_of_gyration(tetra) == pytest.approx(np.sqrt(3))


def regular_polygon(n: int, r: float = 1.0, z: float = 0.0) -> list[list[float]]:
    return [[r * np.cos(2 * np.pi * k / n), r * np.sin(2 * np.pi * k / n), z] for k in range(n)]


@pytest.mark.parametrize(("coords", "expected"), [
    ([[0, 0, 0]], ("Kh", 1)),
    ([[0, 0, 0], [0, 0, 0.74]], ("D∞h", 2)),
    ([[0, 0, 0], [0, 0, 0.74], [0, 0, 3.0]], ("C∞v", 1)),
    (regular_polygon(3, 0.5), ("D3h", 6)),
    # Phase 1: ORCA calls this C2v (one side 3e-4 A longer)
    ([[0, 0, 0], [0.8753, 0, 0], [0.43765, 0.75803, 0]], ("D3h", 6)),
    (regular_polygon(4), ("D4h", 8)),
    ([[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]], ("Td", 12)),
    ([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]], ("Oh", 24)),
    # H5+ proton-shared: two perpendicular H2 around a central H (D2d)
    ([[0, 0, 0], [1.1, 0, 0.37], [1.1, 0, -0.37], [-1.1, 0.37, 0], [-1.1, -0.37, 0]], ("D2d", 4)),
    # H3+.H2 (C2v): triangle plus an H2 along the C2 axis, perpendicular to the plane
    ([[0, 0, 0], [0.87, 0, 0], [0.435, 0.753, 0], [0.435, 2.3, 0.38], [0.435, 2.3, -0.38]], ("C2v", 2)),
    ([[0, 0, 0], [0.9, 0, 0], [1.6, 0.9, 0]], ("Cs", 1)),  # sides 0.90, 1.14, 1.84 A
    ([[0, 0, 0], [0.9, 0.1, 0.2], [1.5, 0.7, -0.3], [0.2, 1.1, 0.9]], ("C1", 1)),
])
def test_point_groups(coords, expected):
    from hclust.analysis.symmetry import point_group

    assert point_group(Geometry.hydrogens(coords)) == expected


def test_point_group_is_invariant_to_rotation_and_translation():
    from hclust.analysis.symmetry import point_group

    rng = np.random.default_rng(0)
    q, _ = np.linalg.qr(rng.normal(size=(3, 3)))
    tetra = np.array([[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]]) @ q.T + [3, -2, 5]
    assert point_group(Geometry.hydrogens(tetra)) == ("Td", 12)
