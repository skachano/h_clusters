"""Regression against exactly known H, H-, H2, H2+ and H3+ results (doc/Plan.md, 1.2).

L1 (wB97M-V) optimizes and computes frequencies; L2 (CCSD(T)/aug-cc-pVTZ) computes
single points at the L1 geometries. Results are cached in $HCLUST_DATA/jobs, so a
rerun only parses.
"""

from functools import cache

import numpy as np
import pytest

from hclust.engines.orca import ORCA_DIR, OrcaJob, Task, run_orca
from hclust.geometry import Geometry
from hclust.levels import LEVELS
from hclust.results import Result
from hclust.species import State
from hclust.units import HARTREE_TO_EV

pytestmark = [
    pytest.mark.orca,
    pytest.mark.skipif(not (ORCA_DIR / "orca").exists(), reason="ORCA not mounted"),
]

# Non-relativistic, clamped-nuclei exact energies (Eh) and equilibrium distances (Angstrom).
E_H = -0.5
E_H_MINUS = -0.527751016544  # Pekeris / Frankowski-Pekeris
E_H2 = -1.174475714  # Kolos-Wolniewicz, r = 1.4011 bohr
E_H2_PLUS = -0.602634214  # r = 1.9972 bohr
E_H3_PLUS = -1.343835625  # Pavanello et al., JCP 136, 184303 (2012)
R_H2, R_H2_PLUS, R_H3_PLUS = 0.74144, 1.0569, 0.8736
OMEGA_H2 = 4401.2  # harmonic wavenumber, cm^-1

STATES = {
    "H": State(1, 0, 2),
    "H-": State(1, -1, 1),
    "H2": State(2, 0, 1),
    "H2+": State(2, 1, 2),
    "H3+": State(3, 1, 1),
}
STARTS = {
    "H": [[0, 0, 0]],
    "H-": [[0, 0, 0]],
    "H2": [[0, 0, 0], [0, 0, 0.78]],
    "H2+": [[0, 0, 0], [0, 0, 1.00]],
    # Deliberately distorted; must relax to the D3h triangle.
    "H3+": [[0, 0, 0], [0.90, 0, 0], [0.40, 0.85, 0]],
}

ENERGY_TOL_EV = 0.05
DISTANCE_TOL = 0.01


@cache
def l1(name: str) -> Result:
    job = OrcaJob(STATES[name], Geometry.hydrogens(STARTS[name]), LEVELS["L1"], Task.OPTFREQ)
    result = run_orca(job)
    assert result.ok, result.error
    return result


@cache
def l2(name: str) -> Result:
    result = run_orca(OrcaJob(STATES[name], l1(name).geometry, LEVELS["L2"]))
    assert result.ok, result.error
    return result


def ev(hartree: float) -> float:
    return hartree * HARTREE_TO_EV


@pytest.mark.parametrize(
    "name, r_ref",
    [
        ("H2", R_H2),
        pytest.param(
            "H2+", R_H2_PLUS,
            marks=pytest.mark.xfail(strict=True, reason="DFT self-interaction error stretches H2+ by ~0.08 A"),
        ),
        ("H3+", R_H3_PLUS),
    ],
)
def test_l1_bond_length(name, r_ref):
    np.testing.assert_allclose(l1(name).geometry.distances(), r_ref, atol=DISTANCE_TOL)


@pytest.mark.parametrize("name", ["H2", "H2+", "H3+"])
def test_l1_structure_is_minimum(name):
    assert l1(name).opt_converged
    assert l1(name).n_imag == 0


def test_l1_h3_plus_is_equilateral():
    # ORCA's own point-group detection is too strict for a TightOpt residual and
    # reports C2v here; tolerant symmetry detection is our job (analysis/symmetry.py).
    h3 = l1("H3+")
    assert np.ptp(h3.geometry.distances()) < 1e-3
    bend = sorted(h3.frequencies)[:2]  # the degenerate e' pair
    assert bend[1] - bend[0] < 5


def test_l1_h2_harmonic_frequency():
    assert l1("H2").frequencies == pytest.approx([OMEGA_H2], rel=0.02)


def test_l2_hydrogen_atom():
    # One electron: L2 falls back to HF, exact up to basis-set incompleteness.
    assert ev(l2("H").energy - E_H) == pytest.approx(0, abs=ENERGY_TOL_EV)


def test_l2_electron_affinity_of_h():
    ea = l2("H").energy - l2("H-").energy
    assert ev(ea) == pytest.approx(ev(E_H - E_H_MINUS), abs=ENERGY_TOL_EV)


def test_l2_h2_dissociation_energy():
    de = 2 * l2("H").energy - l2("H2").energy
    assert ev(de) == pytest.approx(ev(2 * E_H - E_H2), abs=ENERGY_TOL_EV)


def test_l2_h2_plus_dissociation_energy():
    de = l2("H").energy - l2("H2+").energy  # H2+ -> H + H+, E(H+) = 0
    assert ev(de) == pytest.approx(ev(E_H - E_H2_PLUS), abs=ENERGY_TOL_EV)


def test_l2_h3_plus_proton_detachment_energy():
    de = l2("H2").energy - l2("H3+").energy  # H3+ -> H2 + H+
    assert ev(de) == pytest.approx(ev(E_H2 - E_H3_PLUS), abs=ENERGY_TOL_EV)
