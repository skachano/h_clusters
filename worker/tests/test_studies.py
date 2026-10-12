"""Phase 8 studies: job planning and the fragment partition (no ORCA needed)."""

import numpy as np
import pytest

from hclust.analysis.fragments import Verdict
from hclust.analysis.verdicts import Reference, StateAnalysis
from hclust.engines import orca
from hclust.engines.orca import OrcaJob, Task
from hclust.geometry import Geometry
from hclust.levels import LEVELS
from hclust.species import State
from hclust.parse import atom_populations, bond_orders, printed_matrix
from hclust.studies import bonds, counterpoise, vertical
from hclust.studies.environment import fragments_of
from hclust.studies.field import longest_axis_along_z


@pytest.fixture(autouse=True)
def fixed_version(monkeypatch):
    monkeypatch.setattr(orca, "orca_version", lambda: "6.1.1")


def analysis(label_state: State, coords, channel: str, d_e: float = 0.01) -> StateAnalysis:
    g = Geometry.hydrogens(coords)
    ref = Reference(
        ref_job_id=1, structure_id=1, energy=-1.0, geometry_level="L1M", geometry_energy=-1.0,
        geometry=g, frequencies=None, point_group="C1", symmetry_number=1, homo=None, lumo=None, s2=None,
    )
    a = StateAnalysis(1, label_state, Verdict.BOUND, reference=ref)
    a.d = {"E": (d_e, channel)}
    return a


H3P = [[0, 0, 0], [0.87, 0, 0], [0.435, 0.753, 0]]  # H3+ triangle
H5P = H3P + [[0.435, 2.3, 0.38], [0.435, 2.3, -0.38]]  # + H2 on the C2 axis


def test_parse_part():
    assert counterpoise.parse_part("H3+") == (3, 1, 1)
    assert counterpoise.parse_part("H2(3)") == (2, 0, 3)
    assert counterpoise.parse_part("H-") == (1, -1, 1)
    assert counterpoise.parse_part("e-") is None


def test_h5_plus_splits_into_h3_plus_core_and_h2():
    plan = counterpoise.units_of(analysis(State(5, 1, 1), H5P, "H3+ + H2"))
    assert sorted((len(atoms), q, m) for atoms, q, m in plan) == [(2, 0, 1), (3, 1, 1)]
    core = next(atoms for atoms, q, _ in plan if q == 1)
    assert core == [0, 1, 2]


def test_neutral_h5_gives_away_the_lone_atom_and_keeps_h4():
    coords = [[0, 0, 0], [0.74, 0, 0], [0, 3.2, 0], [0.74, 3.2, 0], [0.37, 1.6, 3.0]]
    plan = counterpoise.units_of(analysis(State(5, 0, 2), coords, "H4 + H"))
    assert sorted(len(a) for a, _, _ in plan) == [1, 4]
    assert next(a for a, _, _ in plan if len(a) == 1) == [4]


def test_departing_h2_is_the_farthest_from_the_core():
    near, far = [[0.435, 2.0, 0.37], [0.435, 2.0, -0.37]], [[0.435, -3.5, 0.37], [0.435, -3.5, -0.37]]
    plan = counterpoise.units_of(analysis(State(7, 1, 1), H3P + near + far, "H5+ + H2"))
    leaving = next(a for a, q, _ in plan if len(a) == 2)
    assert leaving == [5, 6]


def test_no_partition_without_a_matching_core():
    # three H2 units cannot make H5+ + H (no H3 unit): the D2d H2-H2+-H2 case of H6+
    coords = [[0, 0, 0], [0.74, 0, 0], [0, 2, 0], [0.74, 2, 0], [0, 4, 0], [0.74, 4, 0]]
    assert counterpoise.units_of(analysis(State(6, 1, 2), coords, "H5+ + H")) is None
    assert counterpoise.units_of(analysis(State(4, -1, 4), H3P + [[0, 0, 2]], "H4(3) + e-")) is None


def test_counterpoise_jobs_put_ghosts_on_the_other_fragment():
    jobs = counterpoise.build([analysis(State(5, 1, 1), H5P, "H3+ + H2")])
    ghost = next(j for k, j in jobs.items() if k.endswith("|ghost") and j.state.charge == 1)
    assert ghost.ghosts == (3, 4)
    text = ghost.render()
    assert text.count("H:") == 2 and "* xyz 1 1" in text


def test_vertical_targets_are_spin_allowed():
    a = analysis(State(3, -1, 1), H3P, "H2 + H-")
    a.best = None
    jobs = vertical.build([a])
    assert set(jobs) == {"H3- (1)|+0|2"}  # singlet anion -> doublet neutral only
    quartet = analysis(State(4, -1, 4), H3P + [[0, 0, 2]], "H4(3) + e-")
    assert set(vertical.build([quartet])) == {"H4- (4)|+0|3", "H4- (4)|+0|5"}


def test_environment_fragments_skip_proton_and_electron_channels():
    assert fragments_of(analysis(State(3, 1, 1), H3P, "H2 + H+")) is None
    assert fragments_of(analysis(State(4, -1, 4), H3P + [[0, 0, 2]], "H4(3) + e-")) is None
    assert [f.label for f in fragments_of(analysis(State(5, 1, 1), H5P, "H3+ + H2"))] == ["H3+ (1)", "H2 (1)"]


def test_longest_axis_goes_along_z():
    g = longest_axis_along_z(Geometry.hydrogens([[0, 0, 0], [3.0, 0.1, 0], [1.5, 0.2, 0.05]]))
    spread = np.ptp(g.coords, axis=0)
    assert spread[2] == max(spread)
    assert np.allclose(g.coords.mean(axis=0), 0)


def test_ghost_atoms_render_and_keep_old_inputs_unchanged():
    g = Geometry.hydrogens([[0, 0, 0], [0, 0, 0.74], [0, 0, 3.3]])
    job = OrcaJob(State(2, 0, 1), g, LEVELS["L2"], Task.SP, ghosts=(2,))
    lines = job.render().splitlines()
    assert lines[-2].startswith("H:") and not lines[-3].startswith("H:")
    plain = OrcaJob(State(2, 0, 1), Geometry.hydrogens([[0, 0, 0], [0, 0, 0.74]]), LEVELS["L2"])
    assert "H:" not in plain.render() and "%" not in plain.render().split("%maxcore")[1]
    with pytest.raises(ValueError):
        OrcaJob(State(2, 0, 1), g, LEVELS["L2"])  # three real atoms for H2


BOND_ORDER_OUTPUT = """
LOEWDIN BOND ORDERS (THRESH 0.001000)
---------------------------------
B(  0-H ,  1-H ) :   0.4218 B(  0-H ,  2-H ) :   0.4190 B(  0-H ,  3-H ) :   0.0639 
B(  3-H ,  4-H ) :   0.6691 


  4 H      0.9262     1.0000     0.0738     0.9897     0.9897     0.0000

  Mayer bond orders larger than 0.001000
B(  0-H ,  1-H ) :   0.5534 B(  0-H ,  3-H ) :  -0.0250 
B(  4-H ,  3-H ) :   0.8627 

-------
TIMINGS
"""


def test_bond_orders_read_both_blocks():
    orders = bond_orders(BOND_ORDER_OUTPUT)
    assert orders["loewdin"] == [(0, 1, 0.4218), (0, 2, 0.419), (0, 3, 0.0639), (3, 4, 0.6691)]
    assert orders["mayer"] == [(0, 1, 0.5534), (0, 3, -0.025), (3, 4, 0.8627)]  # i < j
    assert bond_orders("no population analysis") == {}


def test_bond_summary_splits_units_from_links():
    g = Geometry.hydrogens(H5P)
    loewdin = [[0, 1, 0.42], [0, 2, 0.42], [1, 2, 0.41], [2, 3, 0.25], [2, 4, 0.25], [3, 4, 0.67]]
    s = bonds.summary(g, loewdin)
    assert s == {"units": 2, "weakest_in_unit": 0.41, "strongest_in_unit": 0.67, "strongest_link": 0.25}


def test_loewdin_index_counts_the_spin_density_of_one_electron_bonds():
    # one function per atom, overlap s; sigma = (a + b) / sqrt(2 + 2s)
    s = 0.6
    overlap = np.array([[1, s], [s, 1]])
    sigma = np.array([1, 1]) / np.sqrt(2 + 2 * s)
    one = np.outer(sigma, sigma)
    assert bonds.loewdin_bond_orders(overlap, 2 * one, None, 2, 2)[0][2] == pytest.approx(1.0)  # H2
    assert bonds.loewdin_bond_orders(overlap, one, one, 2, 1)[0][2] == pytest.approx(0.5)  # H2+
    # UKS triplet H2 (one alpha electron in sigma, one in sigma*): ORCA prints the alpha density
    star = np.array([1, -1]) / np.sqrt(2 - 2 * s)
    alpha = one + np.outer(star, star)
    assert bonds.loewdin_bond_orders(overlap, alpha, alpha, 2, 2)[0][2] == pytest.approx(0.0, abs=1e-12)
    # an H2 pair next to an unpaired electron elsewhere keeps its full bond
    three = np.zeros((3, 3))
    three[:2, :2] = overlap
    three[2, 2] = 1
    pair = np.zeros((3, 3))
    pair[:2, :2] = one
    radical = np.zeros((3, 3))
    radical[2, 2] = 1
    orders = bonds.loewdin_bond_orders(three, pair + radical, radical, 3, 3)  # alpha density, as ORCA
    assert orders[0][2] == pytest.approx(1.0) and orders[1][2] == pytest.approx(0.0, abs=1e-12)
    with pytest.raises(ValueError):
        bonds.loewdin_bond_orders(overlap, 2 * one, None, 2, 3)


PRINTED = """
--------------
OVERLAP MATRIX
--------------
                  0          1    
      0       1.000000   0.600000
      1       0.600000   1.000000
                  2    
      0       0.100000
      1      -0.200000

-------
DENSITY
-------
"""


def test_printed_matrix_reads_column_groups():
    m = printed_matrix(PRINTED, "OVERLAP MATRIX")
    assert m.shape == (3, 3) and m[1, 2] == -0.2 and m[0, 1] == 0.6
    assert printed_matrix(PRINTED, "SPIN DENSITY") is None


POPULATIONS = """
LOEWDIN ATOMIC CHARGES AND SPIN POPULATIONS
-------------------------------------------
   0 H :    0.002609    0.000620
   1 H :   -0.008971    0.009302
   2 H :    0.006362    0.990078

----------------------------------------------------
  ATOM       NA         ZA         QA         VA         BVA        FA
  0 H      0.9570     1.0000     0.0430     1.0056     1.0055     0.0001
  1 H      1.0464     1.0000    -0.0464     1.0020     1.0020     0.0001
  2 H      0.9966     1.0000     0.0034     1.0006     0.0083     0.9924

  Mayer bond orders larger than 0.001000
"""


def test_atom_populations_open_and_closed_shell():
    atoms = atom_populations(POPULATIONS)
    assert len(atoms) == 3
    assert atoms[2] == {"charge": 0.006362, "spin": 0.990078, "valence": 1.0006, "free_valence": 0.9924}
    closed = atom_populations("LOEWDIN ATOMIC CHARGES\n----------------------\n   0 H :    0.070791\n   1 H :   -0.070791\n\n")
    assert closed == [{"charge": 0.070791, "spin": None, "valence": None, "free_valence": None},
                      {"charge": -0.070791, "spin": None, "valence": None, "free_valence": None}]
    assert atom_populations("nothing") is None


def test_dmc_scan_jobs_are_valid_counterpoise_triples():
    from hclust.studies import dmc as study

    jobs = study.scan_jobs()
    n_r = len(study.DISTANCES)
    assert len(jobs) == n_r * (4 + 3) * 3
    ab, a, b = (jobs[f"HH|T|3.40|{p}"] for p in ("AB", "A", "B"))
    assert ab.geometry.coords.shape == a.geometry.coords.shape == (4, 3)
    assert a.ghosts == (2, 3) and b.ghosts == (0, 1) and ab.ghosts == ()
    assert "VeryTightSCF" in ab.render() and "STol 1e-7" in ab.render()
    h = jobs["H|1|3.40|B"]
    assert h.state.mult == 2 and h.ghosts == (0, 1)
    assert "%mdci" not in h.render() and "! HF " in h.render()  # one electron: HF, no MDCI
    # the H2 bond is the vibrationally averaged length in every geometry
    c = ab.geometry.coords
    assert np.linalg.norm(c[0] - c[1]) == pytest.approx(study.R_H2) and np.linalg.norm(c[2] - c[3]) == pytest.approx(study.R_H2)


def test_dmc_isotropic_averages():
    from hclust.studies import dmc as study

    energies = {}
    for name, v in zip(study.H2H2, (1.0, 2.0, 3.0, 4.0)):  # L, T, H, X interaction energies
        energies |= {f"HH|{name}|3.40|AB": v, f"HH|{name}|3.40|A": 0.0, f"HH|{name}|3.40|B": 0.0}
    for i in range(3):
        energies |= {f"H|{i}|3.40|AB": -1.0, f"H|{i}|3.40|A": -0.5, f"H|{i}|3.40|B": -0.25}
    curves = study.averaged_curves(energies)
    assert curves["H2-H2"] == [(3.4, pytest.approx((1 + 4 * 2 + 2 * 3 + 2 * 4) / 9))]
    assert curves["H-H2"] == [(3.4, pytest.approx(-0.25))]  # weights sum to one
    assert sum(w for _, w in study.COS_THETA) == pytest.approx(1)
