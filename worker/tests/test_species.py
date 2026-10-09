import pytest

from hclust.species import State, allowed_multiplicities, enumerate_states


def test_electron_count_and_label():
    s = State(3, 1, 1)
    assert s.n_electrons == 2
    assert s.label == "H3+ (1)"
    assert State(1, -1, 1).label == "H- (1)"
    assert State(2, 0, 3).n_unpaired == 2


@pytest.mark.parametrize(
    "n, expected",
    [(0, [1]), (1, [2]), (2, [1, 3]), (3, [2, 4]), (11, [2, 4, 6, 8, 10, 12])],
)
def test_allowed_multiplicities(n, expected):
    assert allowed_multiplicities(n) == expected


@pytest.mark.parametrize("args", [(2, 0, 2), (1, 2, 1), (0, 0, 1), (2, 0, 5)])
def test_invalid_states_rejected(args):
    with pytest.raises(ValueError):
        State(*args)


def test_enumeration_counts():
    lowest = enumerate_states(n_mult=1)
    assert len(lowest) == 30
    assert sum(s.n_electrons > 0 for s in lowest) == 29
    baseline = enumerate_states(n_mult=2)
    # Two spin states each, except the 0- and 1-electron species H+, H and H2+.
    assert len(baseline) == 2 * 30 - 3
    assert [s.mult for s in baseline if (s.m, s.charge) == (2, 1)] == [2]
