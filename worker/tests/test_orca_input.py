import pytest

from hclust.engines import orca
from hclust.engines.orca import OrcaJob, Task, job_hash
from hclust.geometry import Geometry
from hclust.levels import LEVELS
from hclust.species import State

H2 = Geometry.hydrogens([[0, 0, 0], [0, 0, 0.74]])
H = Geometry.hydrogens([[0, 0, 0]])


@pytest.fixture(autouse=True)
def fixed_version(monkeypatch):
    monkeypatch.setattr(orca, "orca_version", lambda: "6.1.1")


def test_render_closed_shell_dft_optfreq():
    job = OrcaJob(State(2, 0, 1), H2, LEVELS["L1V"], Task.OPTFREQ)
    assert job.render() == (
        "# hclust H2 (1) L1V optfreq\n"
        "! wB97M-V def2-TZVPPD TightOpt NumFreq TightSCF\n"
        "%maxcore 600\n"
        "* xyz 0 1\n"
        "H      0.0000000000     0.0000000000     0.0000000000\n"
        "H      0.0000000000     0.0000000000     0.7400000000\n"
        "*\n"
    )


def test_open_shell_uses_unrestricted_reference():
    assert "UKS" in OrcaJob(State(2, 1, 2), H2, LEVELS["L0"]).keywords()
    assert "UHF" in OrcaJob(State(2, -1, 2), H2, LEVELS["L2"]).keywords()


def test_one_electron_falls_back_to_hf():
    kw = OrcaJob(State(2, 1, 2), H2, LEVELS["L2"], Task.OPT).keywords()
    assert kw == "HF aug-cc-pVTZ UHF TightOpt TightSCF"


def test_ccsdt_optimization_uses_numerical_gradients():
    kw = OrcaJob(State(2, 0, 1), H2, LEVELS["L2"], Task.OPTFREQ).keywords()
    assert kw == "CCSD(T) aug-cc-pVTZ TightOpt NumGrad NumFreq TightSCF"


def test_single_atom_is_single_point():
    job = OrcaJob(State(1, 0, 2), H, LEVELS["L1"], Task.OPTFREQ)
    assert job.effective_task is Task.SP
    assert "Opt" not in job.keywords() and "Freq" not in job.keywords()


def test_rejects_bare_proton_and_wrong_geometry():
    with pytest.raises(ValueError, match="proton"):
        OrcaJob(State(1, 1, 1), H, LEVELS["L1"])
    with pytest.raises(ValueError, match="geometry"):
        OrcaJob(State(3, 1, 1), H2, LEVELS["L1"])


def test_hash_is_stable_and_sensitive():
    job = OrcaJob(State(2, 0, 1), H2, LEVELS["L1"])
    assert job.hash == OrcaJob(State(2, 0, 1), H2, LEVELS["L1"]).hash
    assert job.hash != OrcaJob(State(2, 0, 3), H2, LEVELS["L1"]).hash
    assert job.hash != OrcaJob(State(2, 0, 1), H2, LEVELS["L1"], Task.OPT).hash
    assert job_hash(job.render(), "6.1.1") != job_hash(job.render(), "6.1.2")


def test_retry_keywords_are_appended_and_change_the_hash():
    plain = OrcaJob(State(2, 0, 1), H2, LEVELS["L1"])
    slow = OrcaJob(State(2, 0, 1), H2, LEVELS["L1"], extra_keywords=("SlowConv",))
    assert slow.keywords() == "wB97X-D4 def2-TZVPPD TightSCF SlowConv"
    assert slow.hash != plain.hash


def test_goat_input():
    h3 = Geometry.hydrogens([[0, 0, 0], [0.9, 0, 0], [1.8, 0, 0]])
    job = OrcaJob(State(3, 1, 1), h3, LEVELS["XTB"], Task.GOAT)
    text = job.render()
    assert "! GOAT-EXPLORE XTB\n" in text
    assert "%goat\n  MaxEn 30\nend\n" in text
    # H2 has a single shape: GOAT degrades to an xTB optimization, with no UKS/UHF keyword.
    h2 = OrcaJob(State(2, 1, 2), H2, LEVELS["XTB"], Task.GOAT)
    assert h2.effective_task is Task.OPT
    assert h2.keywords() == "XTB TightOpt TightSCF"


def test_analytic_and_numerical_frequencies():
    assert "Freq" in OrcaJob(State(2, 0, 1), H2, LEVELS["L1"], Task.FREQ).keywords().split()
    assert "NumFreq" in OrcaJob(State(2, 0, 1), H2, LEVELS["L1M"], Task.FREQ).keywords().split()
    assert OrcaJob(State(2, 0, 1), H2, LEVELS["L1M"]).keywords() == (
        "RI-MP2 RIJK aug-cc-pVTZ aug-cc-pVTZ/C aug-cc-pVTZ/JK TightSCF"
    )


def test_screening_level_uses_loose_opt_with_more_cycles():
    h3 = Geometry.hydrogens([[0, 0, 0], [0.9, 0, 0], [0.45, 0.8, 0]])
    text = OrcaJob(State(3, 1, 1), h3, LEVELS["L0"], Task.OPT).render()
    assert "! r2SCAN-3c Opt TightSCF\n" in text
    assert "%geom\n  MaxIter 150\nend\n" in text
    # L1 keeps TightOpt but also gets more cycles; L2 and single points have no %geom.
    l1 = OrcaJob(State(3, 1, 1), h3, LEVELS["L1"], Task.OPT).render()
    assert "TightOpt" in l1 and "MaxIter 150" in l1
    assert "%geom" not in OrcaJob(State(3, 1, 1), h3, LEVELS["L2"], Task.OPT).render()
    assert "%geom" not in OrcaJob(State(3, 1, 1), h3, LEVELS["L0"]).render()


def test_numfreq_modifier_replaces_the_analytic_hessian():
    job = OrcaJob(State(2, 0, 1), H2, LEVELS["L1"], Task.OPTFREQ, extra_keywords=("NumFreq",))
    assert job.keywords().split().count("NumFreq") == 1
    assert "Freq" not in job.keywords().split()


def test_neb_input_carries_its_end_point():
    h3 = Geometry.hydrogens([[0, 0, 0], [0.9, 0, 0], [0.45, 0.8, 0]])
    end = Geometry.hydrogens([[0, 0, 0], [0.9, 0, 0], [0.45, 3.0, 0]])
    job = OrcaJob(State(3, 1, 1), h3, LEVELS["L1M"], Task.NEB, end_geometry=end, neb_images=8)
    text = job.render()
    assert "! RI-MP2 RIJK aug-cc-pVTZ aug-cc-pVTZ/C aug-cc-pVTZ/JK NEB-CI TightSCF\n" in text
    assert '%neb\n  NEB_End_XYZFile "end.xyz"\n  NImages 8\n  PreOpt false\nend\n' in text
    assert job.files == {"end.xyz": end.to_xyz()}
    other = Geometry.hydrogens([[0, 0, 0], [0.9, 0, 0], [0.45, 3.1, 0]])
    assert job.hash != OrcaJob(State(3, 1, 1), h3, LEVELS["L1M"], Task.NEB, end_geometry=other, neb_images=8).hash
    with pytest.raises(ValueError, match="NEB"):
        OrcaJob(State(3, 1, 1), h3, LEVELS["L1M"], Task.NEB)
    with pytest.raises(ValueError, match="NEB"):
        OrcaJob(State(3, 1, 1), h3, LEVELS["L1M"], Task.OPT, end_geometry=end)
    # every other job has no extra files and hashes its input text alone, as before
    plain = OrcaJob(State(3, 1, 1), h3, LEVELS["L1M"], Task.OPT)
    assert plain.files == {} and plain.hash == job_hash(plain.render(), "6.1.1")


def test_transition_state_search_starts_from_a_computed_hessian():
    h3 = Geometry.hydrogens([[0, 0, 0], [0.9, 0, 0], [0.45, 0.8, 0]])
    text = OrcaJob(State(3, 1, 1), h3, LEVELS["L1M"], Task.TS).render()
    assert "OptTS NumFreq TightSCF\n" in text and "TightOpt" not in text
    assert "%geom\n  Calc_Hess true\n  NumHess true\n  MaxIter 150\nend\n" in text
