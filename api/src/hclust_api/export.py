"""Static snapshot of the API for the GitHub Pages site (doc/Plan.md, Phase 9).

    docker compose --profile serve run --rm --no-deps api \\
        python -m hclust_api.export --out /data/site/data --outputs /data/site/outputs.tar.xz

Every file is the API's own answer, fetched in-process through FastAPI's TestClient, so the
static site shows exactly what the live app shows. A request maps to a file by
`static_path` (mirrored in web/src/api/static.ts): the path after /api/, then the query as
one segment, with temperature and pressure replaced by their index in the conditions grid:

    /api/campaigns/baseline/grid?temperature=298.15&pressure=1&quantity=d_g
        -> campaigns/baseline/grid/c12-6,quantity-d_g.json

Responses that depend on T and p are exported at every grid point (each one also carries
D_G of the states it shows); the rest once. Missing resources (404) are simply absent.
Only the chosen campaigns are exported, and campaigns.json lists only those (the one file
that differs from the API's answer).
"""

import argparse
import io
import json
import os
import tarfile
import time
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import Session

from hclust.db import Job

from hclust_api.main import create_app

# Conditions grid: the static site's sliders snap to these. 20 temperatures log-spaced over
# the web app's slider range plus 298.15 K, and one pressure per decade (1 atm included).
TEMPERATURES = sorted({float(f"{10 * 300 ** (k / 19):.3g}") for k in range(20)} | {298.15})
PRESSURES = [10.0**k for k in range(-6, 4)]
DEFAULT_CONDITION = (TEMPERATURES.index(298.15), PRESSURES.index(1.0))

GRID_QUANTITIES = ("d_e", "d_0", "d_h", "d_g")
TREND_QUANTITIES = ("binding_per_atom", "d_e", "d_0", "d_g", "second_difference", "gap")
BENCHMARK_TESTS = ("L1", "L1M", "L1V", "L1b")
RAW_FILES = ("job.inp", "job.out")

MAX_FILE_BYTES = 25 * 2**20
MAX_TOTAL_BYTES = 200 * 2**20


def static_path(api_path: str, params: dict[str, str] | None = None,
                condition: tuple[int, int] | None = None) -> str:
    """File (relative to the data root) holding the answer to `api_path?params`."""
    if not api_path.startswith("/api/"):
        raise ValueError(f"not an API path: {api_path}")
    rel = api_path.removeprefix("/api/")
    segment = ([f"c{condition[0]}-{condition[1]}"] if condition else []) + [
        f"{k}-{v}" for k, v in sorted((params or {}).items())
    ]
    has_extension = "." in rel.rsplit("/", 1)[-1]
    return rel + ("/" + ",".join(segment) if segment else "") + ("" if has_extension else ".json")


class Exporter:
    def __init__(self, client: TestClient, out: Path, log=print):
        self.client, self.out, self.log = client, out, log
        self.files = self.bytes = self.missing = 0

    def get(self, api_path: str, params: dict[str, str] | None = None,
            condition: tuple[int, int] | None = None, keep=None):
        query = dict(params or {})
        if condition:
            query |= {"temperature": TEMPERATURES[condition[0]], "pressure": PRESSURES[condition[1]]}
        response = self.client.get(api_path, params=query)
        if response.status_code == 404:
            self.missing += 1
            return None
        response.raise_for_status()
        content = response.content
        if keep is not None:  # filter a JSON list
            content = json.dumps([x for x in response.json() if keep(x)], separators=(",", ":")).encode()
        target = self.out / static_path(api_path, params, condition)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        if len(content) > MAX_FILE_BYTES:
            raise RuntimeError(f"{target} is {len(content)} bytes")
        self.files += 1
        self.bytes += len(content)
        is_json = response.headers.get("content-type", "").startswith("application/json")
        return json.loads(content) if is_json else response.text

    def campaign(self, name: str) -> tuple[set[int], set[int]]:
        """Export one campaign; return the structures and the jobs its pages refer to."""
        base = f"/api/campaigns/{name}"
        states = self.get(f"{base}/states", condition=DEFAULT_CONDITION)
        keys = [(s["m"], s["charge"], s["mult"]) for s in states]
        structures, jobs = set(), set()
        conditions = [(i, j) for i in range(len(TEMPERATURES)) for j in range(len(PRESSURES))]
        start = time.monotonic()
        for n, condition in enumerate(conditions, 1):
            self.get(f"{base}/states", condition=condition)
            for q in GRID_QUANTITIES:
                self.get(f"{base}/grid", {"quantity": q}, condition)
            for q in TREND_QUANTITIES:
                self.get(f"{base}/trends", {"quantity": q}, condition)
            for m, charge, mult in keys:
                detail = self.get(f"{base}/states/{m}/{charge}/{mult}", condition=condition)
                if detail and condition == DEFAULT_CONDITION:
                    for isomer in detail["isomers"]:
                        structures.add(isomer["structure_id"])
                        jobs.add(isomer["ref_job_id"])
            if n % 30 == 0 or n == len(conditions):
                self.log(f"  {name}: {n}/{len(conditions)} conditions, {self.files} files, "
                         f"{self.bytes / 2**20:.1f} MB, {time.monotonic() - start:.0f} s")
        for test in BENCHMARK_TESTS:
            self.get(f"{base}/benchmark", {"test": test})
        summary = self.get(f"{base}/jobs/summary")
        jobs |= {f["job_id"] for f in (summary or {}).get("failures", [])}
        for study in self.get(f"{base}/studies") or []:
            self.get(f"{base}/studies/{study}")
        return structures, jobs

    def structure(self, structure_id: int) -> None:
        self.get(f"/api/structures/{structure_id}.xyz")
        self.get(f"/api/structures/{structure_id}/modes")
        self.get(f"/api/structures/{structure_id}/bonds")


def pack_outputs(engine, jobs_root: Path, job_ids: set[int], archive: Path) -> dict:
    """ORCA input and output of every job the site links to, as outputs/<job id>/<file>."""
    archive.parent.mkdir(parents=True, exist_ok=True)
    packed = 0
    with Session(engine) as session, tarfile.open(archive, "w:xz") as tar:
        for job_id in sorted(job_ids):
            job = session.get(Job, job_id)
            if job is None or not job.hash:
                continue
            for name in RAW_FILES:
                path = jobs_root / job.hash / name
                if path.is_file():
                    tar.add(path, arcname=f"outputs/{job_id}/{name}")
                    packed += 1
    return {"file": archive.name, "files": packed, "bytes": archive.stat().st_size}


def export(out: Path, campaigns: list[str], outputs: Path | None = None, db_path: Path | None = None,
           jobs_root: Path | None = None, log=print) -> dict:
    app = create_app(db_path, jobs_root)
    out.mkdir(parents=True, exist_ok=True)
    with TestClient(app) as client:
        ex = Exporter(client, out, log)
        listed = ex.get("/api/campaigns", keep=lambda c: c["name"] in campaigns)
        unknown = set(campaigns) - {c["name"] for c in listed}
        if unknown:
            raise SystemExit(f"no such campaign: {', '.join(sorted(unknown))}")
        structures, jobs = set(), set()
        for name in campaigns:
            s, j = ex.campaign(name)
            structures |= s
            jobs |= j
        for structure_id in sorted(structures):
            ex.structure(structure_id)
    if ex.bytes > MAX_TOTAL_BYTES:
        raise RuntimeError(f"export is {ex.bytes / 2**20:.0f} MB, over {MAX_TOTAL_BYTES / 2**20:.0f} MB")
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "commit": os.environ.get("GIT_COMMIT"),
        "conditions": {"temperatures": TEMPERATURES, "pressures": PRESSURES, "default": list(DEFAULT_CONDITION)},
        "campaigns": campaigns,
        "files": ex.files,
        "bytes": ex.bytes,
        "structures": len(structures),
        "outputs": None,
    }
    if outputs is not None:
        manifest["outputs"] = pack_outputs(app.state.store.engine, app.state.jobs_root, jobs, outputs)
        manifest["outputs"]["jobs"] = len(jobs)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    log(f"{ex.files} files, {ex.bytes / 2**20:.1f} MB ({ex.missing} absent); "
        f"{len(structures)} structures, {len(jobs)} linked jobs")
    return manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, required=True, help="data directory of the site")
    parser.add_argument("--campaign", action="append", help="campaign to export (repeatable; default: baseline)")
    parser.add_argument("--outputs", type=Path, help="also pack the linked ORCA files (.tar.xz)")
    args = parser.parse_args(argv)
    manifest = export(args.out, args.campaign or ["baseline"], args.outputs)
    if manifest["outputs"]:
        o = manifest["outputs"]
        print(f"outputs: {o['files']} files of {o['jobs']} jobs, {o['bytes'] / 2**20:.1f} MB -> {args.outputs}")


if __name__ == "__main__":
    main()
