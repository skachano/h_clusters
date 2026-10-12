import numpy as np
import pytest

from hclust.parse import parse_orca


def test_open_shell_dft_opt_numfreq(orca_fixture):
    r = parse_orca(orca_fixture("h2p_optnumfreq_wb97mv"), is_opt=True)
    assert r.ok and r.opt_converged
    assert r.energy == pytest.approx(-0.5939771002979921, abs=1e-10)
    assert r.orca_version == "6.1.1"
    assert r.geometry.distances()[0] == pytest.approx(1.1369, abs=1e-4)
    np.testing.assert_allclose(r.frequencies, [1866.70176], atol=1e-3)
    assert r.n_imag == 0 and r.is_minimum
    assert r.s2 == pytest.approx(0.75, abs=1e-3)
    assert r.point_group == "D(inf)h" and r.symmetry_number == 2
    assert r.thermo["zpe"] == pytest.approx(0.004252659519975565)
    assert r.mulliken_charges == pytest.approx([0.5, 0.5])
    # One stretching mode along z; the two atoms move in opposite directions.
    assert r.modes.shape == (1, 2, 3)
    stretch = r.modes[0]
    np.testing.assert_allclose(stretch[:, :2], 0, atol=1e-8)
    assert stretch[0, 2] == pytest.approx(-stretch[1, 2])


def test_uhf_ccsdt_single_point(orca_fixture):
    r = parse_orca(orca_fixture("h2m_sp_uccsdt"))
    assert r.ok and r.opt_converged is None
    assert r.energy == pytest.approx(-1.1228076562602303, abs=1e-10)
    assert r.s2 == pytest.approx(0.750296)
    # The extra electron of H2- sits in an orbital with positive energy: it is not bound.
    assert r.homo == pytest.approx(0.052138)
    assert r.lumo == pytest.approx(0.156788)
    assert r.frequencies is None and r.n_imag is None


def test_rhf_ccsdt_single_point(orca_fixture):
    r = parse_orca(orca_fixture("h3p_sp_ccsdt"))
    assert r.ok
    assert r.energy == pytest.approx(-1.3417381083728672, abs=1e-10)
    assert r.s2 is None
    assert (r.homo, r.lumo) == pytest.approx((-1.207784, -0.198046))
    assert r.gap == pytest.approx(1.009738)
    assert sum(r.mulliken_charges) == pytest.approx(1.0)


def test_failed_job(orca_fixture):
    r = parse_orca(orca_fixture("h_fail_ccsdt"))
    assert not r.ok
    assert "Number of processes (1) in parallel calculation exceeds number of pairs" in r.error
    assert r.energy is None


def test_missing_output(tmp_path):
    r = parse_orca(tmp_path)
    assert r.status == "failed" and r.error == "no output"


def test_scf_failure_is_classified(orca_fixture):
    r = parse_orca(orca_fixture("scf_fail_wb97mv"))
    assert not r.ok and r.error_kind == "scf"
    assert "SCF has not converged" in r.error


def test_unconverged_optimization_keeps_last_geometry(orca_fixture):
    r = parse_orca(orca_fixture("opt_fail_r2scan"), is_opt=True)
    assert not r.ok and r.error_kind == "opt" and r.opt_converged is False
    assert len(r.geometry) == 3  # the restart point


def test_goat_ensemble(orca_fixture):
    r = parse_orca(orca_fixture("goat_h5p_xtb"), is_goat=True)
    assert r.ok
    assert len(r.ensemble) == len(r.ensemble_energies) == 1
    assert r.energy == pytest.approx(-1.9493849110)
    # GFN2-xTB's "global minimum" for H5+ is a chain, not the H3+.H2 complex.
    assert r.geometry.distances()[-1] == pytest.approx(3.963, abs=1e-3)


def test_cpscf_failure_is_classified_and_keeps_the_last_geometry(orca_fixture):
    r = parse_orca(orca_fixture("cpscf_fail_wb97xd4"), is_opt=True)
    assert not r.ok and r.error_kind == "cpscf"
    assert len(r.geometry) == 3  # the optimized structure, a restart point for NumFreq


def test_neb_path_frames(tmp_path):
    from hclust.parse import _frames

    (tmp_path / "job_MEP_trj.xyz").write_text(
        "2\nCoordinates from ORCA-job job_MEP E  -1.170000000000\nH 0 0 0\nH 0 0 0.74\n"
        "2\nCoordinates from ORCA-job job_MEP E  -1.100000000000\nH 0 0 0\nH 0 0 1.50\n"
    )
    geometries, energies = _frames(tmp_path / "job_MEP_trj.xyz")
    assert energies == [-1.17, -1.10]
    assert geometries[1].coords[1, 2] == pytest.approx(1.5)
    assert _frames(tmp_path / "missing.xyz") == ([], [])
