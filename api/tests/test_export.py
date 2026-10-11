"""The static-site export: file naming, completeness, and equality with the live API."""

import json
import tarfile

import pytest

from hclust_api import export as ex


def test_static_path_folds_the_query_into_the_path():
    # the same examples as web/src/api/static.test.ts: the two sides must agree
    assert ex.static_path("/api/campaigns") == "campaigns.json"
    assert ex.static_path("/api/campaigns/baseline/grid", {"quantity": "d_g"}, (12, 6)) == \
        "campaigns/baseline/grid/c12-6,quantity-d_g.json"
    assert ex.static_path("/api/campaigns/baseline/states/5/1/1", condition=(0, 9)) == \
        "campaigns/baseline/states/5/1/1/c0-9.json"
    assert ex.static_path("/api/campaigns/baseline/benchmark", {"test": "L1M"}) == \
        "campaigns/baseline/benchmark/test-L1M.json"
    assert ex.static_path("/api/structures/3094.xyz") == "structures/3094.xyz"
    with pytest.raises(ValueError):
        ex.static_path("/other")


def test_conditions_grid_spans_the_slider_and_contains_the_default():
    assert ex.TEMPERATURES[0] == 10 and ex.TEMPERATURES[-1] == 3000 and 298.15 in ex.TEMPERATURES
    assert ex.PRESSURES[0] == pytest.approx(1e-6) and ex.PRESSURES[-1] == pytest.approx(1e3)
    assert (ex.TEMPERATURES[ex.DEFAULT_CONDITION[0]], ex.PRESSURES[ex.DEFAULT_CONDITION[1]]) == (298.15, 1.0)


@pytest.fixture(scope="module")
def exported(client, tmp_path_factory, monkeypatch_module):
    # a coarser grid keeps the test fast; the logic is the same
    monkeypatch_module.setattr(ex, "TEMPERATURES", [100.0, 298.15, 1000.0])
    monkeypatch_module.setattr(ex, "PRESSURES", [0.1, 1.0])
    monkeypatch_module.setattr(ex, "DEFAULT_CONDITION", (1, 1))
    out = tmp_path_factory.mktemp("site") / "data"
    root = client.jobs_root.parent
    manifest = ex.export(out, ["mini"], outputs=out.parent / "outputs.tar.xz",
                         db_path=root / "hclust.sqlite", jobs_root=client.jobs_root, log=lambda _: None)
    return out, manifest


@pytest.fixture(scope="module")
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


def test_every_page_request_has_a_file(exported, client):
    out, manifest = exported
    assert manifest["campaigns"] == ["mini"] and manifest["conditions"]["temperatures"] == [100.0, 298.15, 1000.0]
    assert json.loads((out / "manifest.json").read_text())["files"] == manifest["files"]
    states = client.get("/api/campaigns/mini/states").json()
    for i in range(3):
        for j in range(2):
            for q in ex.GRID_QUANTITIES:
                assert (out / ex.static_path("/api/campaigns/mini/grid", {"quantity": q}, (i, j))).is_file()
            for s in states:
                path = f"/api/campaigns/mini/states/{s['m']}/{s['charge']}/{s['mult']}"
                assert (out / ex.static_path(path, condition=(i, j))).is_file(), path
    detail = client.get("/api/campaigns/mini/states/3/1/1").json()
    for isomer in detail["isomers"]:
        assert (out / f"structures/{isomer['structure_id']}.xyz").is_file()
    assert (out / "campaigns/mini/jobs/summary.json").is_file()


def test_files_are_the_api_answers(exported, client):
    out, _ = exported
    live = client.get("/api/campaigns/mini/grid", params={"temperature": 1000.0, "pressure": 0.1, "quantity": "d_g"})
    assert (out / "campaigns/mini/grid/c2-0,quantity-d_g.json").read_bytes() == live.content
    detail = client.get("/api/campaigns/mini/states/3/1/1", params={"temperature": 298.15, "pressure": 1.0})
    assert (out / "campaigns/mini/states/3/1/1/c1-1.json").read_bytes() == detail.content


def test_missing_resources_stay_missing(exported, client):
    out, _ = exported
    structure = client.get("/api/campaigns/mini/states/3/1/1").json()["structure_id"]
    assert client.get(f"/api/structures/{structure}/bonds").status_code == 404  # no bonds study here
    assert not (out / f"structures/{structure}/bonds.json").exists()
    assert (out / f"structures/{structure}.xyz").exists()


def test_outputs_archive_holds_the_linked_jobs(exported, client):
    out, manifest = exported
    detail = client.get("/api/campaigns/mini/states/3/1/1").json()
    with tarfile.open(out.parent / "outputs.tar.xz") as tar:
        names = set(tar.getnames())
    assert manifest["outputs"]["files"] == len(names)
    # the fake ORCA writes no files, so the archive may be empty; its layout is what matters
    assert all(n.startswith("outputs/") and n.count("/") == 2 for n in names)
    assert detail["isomers"][0]["ref_job_id"] > 0
