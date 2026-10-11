"""A small campaign run with a fake ORCA (no ORCA needed), shared by the API tests."""

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
