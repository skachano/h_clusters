"""FastAPI app: read-only endpoints over the results database (doc/Plan.md, section 4).

Run: `docker compose --profile serve up api`, then http://localhost:8000/docs
(uvicorn --factory hclust_api.main:create_app).
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse
from sqlmodel import Session

from hclust.db import default_db_path, get_readonly_engine
from hclust.engines.orca import default_jobs_root

from hclust_api import schemas, service

Temperature = Annotated[float, Query(gt=0, le=5000, description="K")]
Pressure = Annotated[float, Query(gt=0, le=1e6, description="atm")]


def create_app(db_path: Path | None = None, jobs_root: Path | None = None) -> FastAPI:
    app = FastAPI(
        title="hclust",
        version="0.1.0",
        description="Stability and shape of H_m^n clusters (m = 1-10, n = -1, 0, +1). Read-only.",
    )
    app.state.store = service.Store(get_readonly_engine(db_path or default_db_path()))
    app.state.jobs_root = jobs_root or default_jobs_root()

    def session(request: Request) -> Iterator[Session]:
        with Session(request.app.state.store.engine) as s:
            yield s

    def store(request: Request) -> service.Store:
        return request.app.state.store

    SessionDep = Annotated[Session, Depends(session)]
    StoreDep = Annotated[service.Store, Depends(store)]

    def campaign_or_404(session: Session, name: str) -> str:
        if not service.campaign_exists(session, name):
            raise HTTPException(404, f"no campaign named {name!r}")
        return name

    @app.get("/api/campaigns", response_model=list[schemas.CampaignOut])
    def campaigns(session: SessionDep):
        return service.campaigns(session)

    @app.get("/api/campaigns/{campaign}/grid", response_model=schemas.GridOut)
    def grid(session: SessionDep, store: StoreDep, campaign: str,
             temperature: Temperature = 298.15, pressure: Pressure = 1.0,
             quantity: schemas.Quantity = "d_e"):
        """One cell per species (m × charge): its ground state and the chosen dissociation energy."""
        return service.grid(store, session, campaign_or_404(session, campaign), temperature, pressure, quantity)

    @app.get("/api/campaigns/{campaign}/states", response_model=list[schemas.StateBrief])
    def states(session: SessionDep, store: StoreDep, campaign: str,
               temperature: Temperature = 298.15, pressure: Pressure = 1.0):
        analyses = store.analyses(session, campaign_or_404(session, campaign), temperature, pressure)
        return [service.brief(a) for a in analyses]

    @app.get("/api/campaigns/{campaign}/states/{m}/{charge}/{mult}", response_model=schemas.StateDetail)
    def state(session: SessionDep, store: StoreDep, campaign: str, m: int, charge: int, mult: int,
              temperature: Temperature = 298.15, pressure: Pressure = 1.0):
        detail = service.state_detail(store, session, campaign_or_404(session, campaign),
                                      m, charge, mult, temperature, pressure)
        if detail is None:
            raise HTTPException(404, f"no state H{m} charge {charge:+d} multiplicity {mult} in {campaign}")
        return detail

    @app.get("/api/campaigns/{campaign}/trends", response_model=schemas.TrendsOut)
    def trends(session: SessionDep, store: StoreDep, campaign: str, quantity: schemas.TrendQuantity,
               temperature: Temperature = 298.15, pressure: Pressure = 1.0):
        """One series per charge against m, from each species' ground state."""
        return service.trends(store, session, campaign_or_404(session, campaign), quantity, temperature, pressure)

    @app.get("/api/campaigns/{campaign}/benchmark", response_model=schemas.BenchmarkOut)
    def benchmark(session: SessionDep, store: StoreDep, campaign: str,
                  test: Annotated[str, Query(pattern="^(L1|L1M|L1V|L1b)$")] = "L1"):
        """D_e from the geometry level's own energies against CCSD(T) on the same structures."""
        return service.benchmark(store, session, campaign_or_404(session, campaign), test)

    @app.get("/api/campaigns/{campaign}/jobs/summary", response_model=schemas.JobsSummaryOut)
    def jobs_summary(session: SessionDep, campaign: str):
        return service.jobs_summary(session, campaign_or_404(session, campaign))

    @app.get("/api/campaigns/{campaign}/studies", response_model=list[str])
    def studies(session: SessionDep, request: Request, campaign: str):
        """Phase 8 studies with a saved report (python -m hclust study <name>)."""
        return service.study_names(request.app.state.jobs_root, campaign_or_404(session, campaign))

    @app.get("/api/campaigns/{campaign}/studies/{name}", response_model=schemas.StudyOut)
    def study(session: SessionDep, request: Request, campaign: str, name: str):
        out = service.study(request.app.state.jobs_root, campaign_or_404(session, campaign), name)
        if out is None:
            raise HTTPException(404, f"no report for study {name!r}")
        return out

    @app.get("/api/structures/{structure_id}.xyz", response_class=PlainTextResponse)
    def structure_xyz(session: SessionDep, structure_id: int):
        xyz = service.structure_xyz(session, structure_id)
        if xyz is None:
            raise HTTPException(404, "no such structure")
        return xyz

    @app.get("/api/structures/{structure_id}/modes", response_model=schemas.ModesOut)
    def structure_modes(session: SessionDep, structure_id: int):
        out = service.modes(session, structure_id)
        if out is None:
            raise HTTPException(404, "no frequency calculation produced this structure")
        return out

    @app.get("/api/structures/{structure_id}/bonds", response_model=schemas.BondsOut)
    def structure_bonds(session: SessionDep, structure_id: int):
        out = service.bonds(session, structure_id)
        if out is None:
            raise HTTPException(404, "no bond orders computed for this structure")
        return out

    @app.get("/api/jobs/{job_id}", response_model=schemas.JobOut)
    def job(session: SessionDep, request: Request, job_id: int):
        out = service.job_detail(session, job_id, request.app.state.jobs_root)
        if out is None:
            raise HTTPException(404, "no such job")
        return out

    @app.get("/api/jobs/{job_id}/files/{name}", response_class=FileResponse)
    def job_file(session: SessionDep, request: Request, job_id: int, name: str):
        """Raw ORCA files (input, output, property JSON, geometries)."""
        path = service.job_file(session, job_id, name, request.app.state.jobs_root)
        if path is None:
            raise HTTPException(404, f"no file {name!r} for job {job_id}")
        return FileResponse(path, media_type="text/plain" if not name.endswith(".json") else "application/json")

    return app

