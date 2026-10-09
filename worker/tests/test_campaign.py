import pytest
from pydantic import ValidationError

from hclust.campaign import CampaignSpec

STAGES = [
    {"name": "pre", "level": "L0", "task": "opt"},
    {"name": "opt", "level": "L1", "task": "optfreq", "from": "pre"},
    {"name": "ref", "level": "L2", "task": "sp", "from": "opt", "when": "minimum"},
]


def spec(**overrides) -> dict:
    return {"name": "t", "seeds": [{"generator": "chain"}], "stages": STAGES} | overrides


def test_valid_spec_and_dag():
    s = CampaignSpec.model_validate(spec(species={"m": [1, 2], "charges": [0, 1]}))
    assert s.root.name == "pre"
    assert [c.name for c in s.children("pre")] == ["opt"]
    assert s.children("ref") == []
    # H+ (no electrons) is not a calculation.
    assert [st.label for st in s.species.states()] == ["H (2)", "H2 (1)", "H2 (3)", "H2+ (2)"]


def test_demo_campaign_file_is_valid():
    from pathlib import Path

    path = Path(__file__).parents[2] / "campaigns" / "demo.yaml"
    if not path.exists():
        pytest.skip("campaigns/ not mounted")
    assert CampaignSpec.load(path).name == "demo"


@pytest.mark.parametrize(
    "stages, message",
    [
        ([{**STAGES[0], "from": "x"}] + STAGES[1:], "first stage"),
        ([STAGES[0], {**STAGES[1], "from": "ref"}, STAGES[2]], "earlier stage"),
        ([STAGES[0], STAGES[0]], "duplicate"),
        ([{**STAGES[0], "level": "L9"}], "unknown level"),
        ([{**STAGES[0], "task": "dance"}], "task"),
    ],
)
def test_invalid_dag(stages, message):
    with pytest.raises(ValidationError, match=message):
        CampaignSpec.model_validate(spec(stages=stages))


def test_unknown_generator_and_extra_keys():
    with pytest.raises(ValidationError, match="unknown generator"):
        CampaignSpec.model_validate(spec(seeds=[{"generator": "magic"}]))
    with pytest.raises(ValidationError, match="Extra inputs"):
        CampaignSpec.model_validate(spec(colour="blue"))
