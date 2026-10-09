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
    assert s.seed_stage(s.seeds[0]).name == "pre"
    assert [c.name for c in s.children("pre")] == ["opt"]
    assert s.children("ref") == []
    assert s.upstream("ref") == {"pre", "opt", "ref"}
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
        ([{**STAGES[0], "from": "x"}] + STAGES[1:], "earlier stage"),
        ([STAGES[0], {**STAGES[1], "from": "ref"}, STAGES[2]], "earlier stage"),
        ([STAGES[0], STAGES[0]], "duplicate"),
        ([{**STAGES[0], "level": "L9"}], "unknown level"),
        ([{**STAGES[0], "task": "dance"}], "task"),
        ([STAGES[0], {"name": "s", "level": "L0", "select": {}, "from": "pre"}], "no level"),
        ([STAGES[0], {"name": "s", "select": {}, "from": ["pre", "pre"]}], "exactly one"),
        ([STAGES[0], {"name": "s", "select": {}, "from": "pre"},
          {"name": "t", "select": {}, "from": "s"}], "follow an ORCA stage"),
        ([STAGES[0], {"name": "lonely", "level": "L0", "task": "opt"}], "neither seeds"),
        ([{"name": "x"}], "level and a task"),
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


def test_search_dag_with_goat_and_select():
    s = CampaignSpec.model_validate({
        "name": "search",
        "species": {"states": [[3, 1, 1], [5, 1, 1]]},
        "seeds": [
            {"generator": "random", "params": {"count": 5}, "into": "pre"},
            {"generator": "sphere", "into": "goat"},
        ],
        "stages": [
            {"name": "goat", "level": "XTB", "task": "goat", "max_outputs": 10},
            {"name": "pre", "level": "L0", "task": "opt", "from": "goat"},
            {"name": "promote", "select": {"max_per_state": 4}, "from": "pre"},
            {"name": "opt", "level": "L1", "task": "optfreq", "from": "promote"},
        ],
    })
    assert [st.label for st in s.species.states()] == ["H3+ (1)", "H5+ (1)"]
    assert s.stage("promote").is_select
    assert s.upstream("promote") == {"goat", "pre", "promote"}
    assert [c.name for c in s.children("goat")] == ["pre"]


def test_seeds_cannot_go_into_a_select_stage():
    with pytest.raises(ValidationError, match="seeds must go into an ORCA stage"):
        CampaignSpec.model_validate(spec(
            seeds=[{"generator": "chain", "into": "s"}],
            stages=[STAGES[0], {"name": "s", "select": {}, "from": "pre"}],
        ))
