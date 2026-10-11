"""Fragmentation channels, spin-allowed asymptotes, verdicts, and the database loader."""

import pytest
from sqlmodel import Session

from hclust.analysis.fragments import (
    Asymptotes, StateEnergy, Verdict, channels, couples, judge, species_label,
)
from hclust.analysis.thermo import Thermo
from hclust.campaign import CampaignSpec
from hclust.db import get_engine
from hclust.engines import orca
from hclust.results import Result
from hclust.runner import Runner


def test_channels_of_a_cation_and_an_anion():
    assert channels(1, 0) == []
    assert channels(2, 1) == [((1, 0), (1, 1))]  # H + H+, listed once
    assert set(channels(3, 1)) == {((1, 0), (2, 1)), ((1, 1), (2, 0))}
    assert ((2, 0), None) in channels(2, -1)  # electron detachment
    # symmetric splits are listed once: H2 + H2+ but not also H2+ + H2
    assert channels(4, 1).count(((2, 0), (2, 1))) + channels(4, 1).count(((2, 1), (2, 0))) == 1


def test_spin_coupling_rules():
    assert couples(2, 2, 1) and couples(2, 2, 3) and not couples(2, 2, 5)
    assert couples(3, 2, 2) and couples(3, 2, 4) and not couples(3, 2, 3)
    assert couples(1, 1, 1) and not couples(1, 1, 3)


def test_labels():
    assert species_label(1, -1) == "H-" and species_label(3, 1) == "H3+"
    assert species_label(2, 0, 3) == "H2(3)" and species_label(2, 0, 1) == "H2"


def atoms(*extra: StateEnergy) -> list[StateEnergy]:
    return [StateEnergy(1, 0, 2, -0.5), StateEnergy(1, 1, 1, 0.0), StateEnergy(1, -1, 1, -0.527), *extra]


def test_dissociation_goes_to_the_lowest_spin_allowed_limit():
    h2 = StateEnergy(2, 0, 1, -1.174)
    h3 = StateEnergy(3, 0, 2, -1.670)  # above H2 + H (-1.674): falls apart
    asym = Asymptotes(atoms(h2, h3))
    d, channel = asym.dissociation(h2, "E")
    assert d == pytest.approx(0.174) and channel == "H + H"
    d, channel = asym.dissociation(h3, "E")
    assert d == pytest.approx(-0.004) and channel == "H2 + H"


def test_high_spin_state_cannot_fall_into_low_spin_fragments():
    h2 = StateEnergy(2, 0, 1, -1.174)
    quartet = StateEnergy(3, 0, 4, -1.4)  # lies far below H + H + H (-1.5 is not reachable)
    asym = Asymptotes(atoms(h2, quartet))
    d, channel = asym.dissociation(quartet, "E")
    assert channel == "H + H + H"  # H2 (singlet) + H cannot make a quartet
    assert d == pytest.approx(-0.1)


def test_anion_detachment_and_multi_fragment_limits():
    hm = StateEnergy(1, -1, 1, -0.527)
    asym = Asymptotes(atoms())
    assert asym.dissociation(hm, "E") == (pytest.approx(0.027), "H + e-")
    # H2+ is not computed: its lowest limit is H + H+
    assert asym.lowest((2, 1), 2, "E").label == "H + H+"


def test_thermal_quantities_use_each_fragment_correction():
    t = lambda zpe: Thermo(298.15, 1.0, zpe, 0.0, 0.0)  # noqa: E731
    h = StateEnergy(1, 0, 2, -0.5, t(0.0))
    h2 = StateEnergy(2, 0, 1, -1.174, t(0.01))
    asym = Asymptotes([h, h2])
    assert asym.dissociation(h2, "E0")[0] == pytest.approx(0.164)
    assert asym.dissociation(StateEnergy(2, 0, 1, -1.174), "E0") is None  # no frequencies


@pytest.mark.parametrize(("kwargs", "verdict"), [
    ({"m": 1, "charge": 0}, Verdict.ATOM),
    ({"charge": -1, "all_unbound": True}, Verdict.UNBOUND_ELECTRON),
    ({"has_intact": True}, Verdict.NOT_A_MINIMUM),
    ({}, Verdict.DISSOCIATES),
    ({"best": True, "d_e": -0.1}, Verdict.METASTABLE),
    ({"best": True, "d_e": 0.1, "d_0": -0.01}, Verdict.BOUND),
    ({"best": True, "d_e": 0.1, "d_0": 0.05}, Verdict.BOUND_WITH_ZPE),
])
def test_judge(kwargs, verdict):
    args = {"m": 3, "charge": 0, "has_intact": False, "all_unbound": False, "has_minimum": False}
    best = StateEnergy(3, 0, 2, -1.0) if kwargs.pop("best", False) else None
    d_e, d_0 = kwargs.pop("d_e", None), kwargs.pop("d_0", None)
    assert judge(best, d_e, d_0, **(args | kwargs)) is verdict


def test_verdicts_from_a_campaign(tmp_path, monkeypatch):
    """H, H2 and an unbound H2- through the runner (fake ORCA), then analyze()."""
    from hclust.analysis.verdicts import analyze, store
    from hclust.db import VerdictRow
    from hclust.units import HARTREE_TO_EV

    from test_runner import FakeOrca, ok

    monkeypatch.setattr(orca, "orca_version", lambda: "6.1.1")
    spec = CampaignSpec.model_validate({
        "name": "mini", "species": {"states": [[1, 0, 2], [2, 0, 1], [2, -1, 2]]},
        "seeds": [{"generator": "chain", "params": {"spacing": 0.74}}],
        "stages": [
            {"name": "opt", "level": "L1", "task": "optfreq"},
            {"name": "ref", "level": "L2", "task": "sp", "from": "opt", "when": "minimum"},
        ],
    })
    energies = {(1, 0): -0.5, (2, 0): -1.17, (2, -1): -1.15}

    def script(job, n):
        r: Result = ok(job, energy=energies[(job.state.m, job.state.charge)])
        r.homo = 0.04 if job.state.charge == -1 else -0.5  # +1.1 eV: the anion is unbound
        return r

    with Session(get_engine(tmp_path / "t.sqlite")) as session:
        Runner(session, spec, execute=FakeOrca(script), log=lambda _: None).run()
        analyses = {a.state.label: a for a in analyze(session, "mini")}
        h2 = analyses["H2 (1)"]
        assert h2.verdict is Verdict.BOUND_WITH_ZPE
        assert h2.d["E"][0] == pytest.approx(0.17) and h2.d["E"][1] == "H + H"
        assert h2.d["E0"][0] < h2.d["E"][0]  # ZPE of the 1000 cm-1 fake mode
        assert analyses["H (2)"].verdict is Verdict.ATOM
        assert analyses["H2- (2)"].verdict is Verdict.UNBOUND_ELECTRON
        assert h2.ionization == pytest.approx(0.67)  # to H + H+ + e- (no H2+ computed)
        store(session, "mini", list(analyses.values()))
        row = session.get(VerdictRow, 1)
        assert row is not None and row.verdict in {v.value for v in Verdict}
        assert h2.d["E"][0] * HARTREE_TO_EV == pytest.approx(4.63, abs=0.01)
