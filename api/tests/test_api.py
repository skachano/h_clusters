"""The API over a small campaign run with a fake ORCA (no ORCA needed)."""

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from hclust.campaign import CampaignSpec
from hclust.db import get_engine
from hclust.engines import orca
from hclust.geometry import Geometry
from hclust.results import Result
from hclust.runner import Runner
from hclust_api.main import create_app

ENERGIES = {(1, 0): -0.5, (2, 0): -1.17, (2, 1): -0.60, (3, 1): -1.34, (2, -1): -1.15, (1, -1): -0.527}
HOMO_EH = {-1: 0.04}  # +1.1 eV: H2- is unbound; H- gets the default below


def fake_orca(job, timeout_s):
    g = job.geometry
    task = job.effective_task
    if task.optimizes:
        g = Geometry(g.symbols, g.coords * 0.9)
    key = (job.state.m, job.state.charge)
    r = Result(status="ok", energy=ENERGIES[key], geometry=g, opt_converged=True,
               homo=HOMO_EH.get(job.state.charge, -0.5) if key != (1, -1) else -0.05, lumo=0.1,
               s2=0.75 if job.state.mult == 2 else None)
    if task.has_freq and len(g) > 1:
        n_vib = max(3 * len(g) - 5, 1) if len(g) == 2 else 3 * len(g) - 6
        r.frequencies = np.array([1000.0 + 100 * i for i in range(n_vib)])
        r.modes = np.ones((n_vib, len(g), 3))
    return r


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("api")
    orca.orca_version = lambda: "6.1.1"
    spec = CampaignSpec.model_validate({
        "name": "mini",
        "species": {"states": [[1, 0, 2], [1, -1, 1], [2, 0, 1], [2, 1, 2], [2, -1, 2], [3, 1, 1]]},
        "seeds": [{"generator": "ring", "params": {"side": 0.87}}, {"generator": "chain", "params": {"spacing": 0.74}}],
        "stages": [
            {"name": "opt", "level": "L1", "task": "optfreq"},
            {"name": "ref", "level": "L2", "task": "sp", "from": "opt", "when": "minimum"},
        ],
    })
    with Session(get_engine(tmp / "hclust.sqlite")) as session:
        Runner(session, spec, execute=fake_orca, log=lambda _: None).run()
    jobs = tmp / "jobs"
    with TestClient(create_app(tmp / "hclust.sqlite", jobs)) as c:
        c.jobs_root = jobs
        yield c


def test_campaigns(client):
    [c] = client.get("/api/campaigns").json()
    assert c["name"] == "mini" and c["n_states"] == 6


def test_grid_has_one_cell_per_species(client):
    grid = client.get("/api/campaigns/mini/grid", params={"quantity": "d_e"}).json()
    cells = {(c["m"], c["charge"]): c for c in grid["cells"]}
    assert set(cells) == {(1, 0), (1, -1), (2, 0), (2, 1), (2, -1), (3, 1)}
    h2 = cells[(2, 0)]
    assert h2["ground"]["verdict"] == "bound_with_zpe"
    assert h2["value"] == pytest.approx(0.17 * 27.211386, rel=1e-6) and h2["survives"]
    assert cells[(2, -1)]["ground"]["verdict"] == "unbound_electron"
    assert cells[(1, 0)]["ground"]["verdict"] == "atom"


def test_grid_free_energy_depends_on_temperature(client):
    cold, hot = (client.get("/api/campaigns/mini/grid", params={"quantity": "d_g", "temperature": t}).json()
                 for t in (50, 3000))
    value = lambda g: next(c["value"] for c in g["cells"] if (c["m"], c["charge"]) == (3, 1))  # noqa: E731
    assert value(hot) < value(cold)  # entropy favours the fragments


def test_state_detail(client):
    s = client.get("/api/campaigns/mini/states/3/1/1").json()
    assert s["label"] == "H3+ (1)" and s["verdict"] == "bound_with_zpe"
    assert s["channels"][0]["limit"] == "H2 + H+"  # -1.17 Eh, below H2+ + H (-1.10)
    assert min(c["d_e"] for c in s["channels"]) == pytest.approx(s["d_e"])
    assert s["isomers"] and s["isomers"][0]["relative"] == 0
    assert s["xyz"].startswith("3\n")
    assert [x["mult"] for x in s["multiplicities"]] == [1]
    assert client.get("/api/campaigns/mini/states/3/1/3").status_code == 404
    assert client.get("/api/campaigns/nope/states/3/1/1").status_code == 404


def test_structure_xyz_and_modes(client):
    s = client.get("/api/campaigns/mini/states/2/0/1").json()
    xyz = client.get(f"/api/structures/{s['structure_id']}.xyz")
    assert xyz.status_code == 200 and xyz.text.startswith("2\n")
    modes = client.get(f"/api/structures/{s['structure_id']}/modes").json()
    assert modes["frequencies"] == [1000.0] and np.array(modes["modes"]).shape == (1, 2, 3)


def test_trends(client):
    t = client.get("/api/campaigns/mini/trends", params={"quantity": "binding_per_atom"}).json()
    neutral = next(s for s in t["series"] if s["charge"] == 0)
    h2 = next(p for p in neutral["points"] if p["m"] == 2)
    assert h2["value"] == pytest.approx(0.17 * 27.211386 / 2, rel=1e-6)
    assert t["unit"] == "eV/atom"


def test_benchmark_compares_geometry_level_with_ccsdt(client):
    b = client.get("/api/campaigns/mini/benchmark", params={"test": "L1"}).json()
    assert b["n"] > 0 and b["mae"] == pytest.approx(0)  # the fake gives both levels one energy
    assert client.get("/api/campaigns/mini/benchmark", params={"test": "XTB"}).status_code == 422


def test_jobs_summary_and_files(client):
    summary = client.get("/api/campaigns/mini/jobs/summary").json()
    assert summary["counts"]["done"] > 0 and summary["failures"] == []
    assert [s["stage"] for s in summary["stages"]] == ["opt", "ref"]
    job = client.get("/api/jobs/1").json()
    (client.jobs_root / job["hash"]).mkdir(parents=True)
    (client.jobs_root / job["hash"] / "job.out").write_text("ORCA TERMINATED NORMALLY")
    assert client.get("/api/jobs/1").json()["files"] == ["job.out"]
    assert client.get("/api/jobs/1/files/job.out").text == "ORCA TERMINATED NORMALLY"
    assert client.get("/api/jobs/1/files/..%2Fhclust.sqlite").status_code == 404


def test_openapi_schema_is_complete(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/campaigns/{campaign}/grid" in paths and "/api/structures/{structure_id}/modes" in paths


def test_committed_openapi_schema_is_up_to_date(client):
    """api/openapi.json feeds the web app's generated client: regenerate it after API changes."""
    import json

    from hclust_api.openapi import SCHEMA_PATH

    assert json.loads(SCHEMA_PATH.read_text()) == client.app.openapi()
