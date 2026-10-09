"""Results database (SQLite). The orchestrator is its only writer; the API reads it."""

import os
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from sqlalchemy import JSON, Column, UniqueConstraint, event
from sqlalchemy.engine import Engine
from sqlmodel import Field, SQLModel, create_engine

from hclust.species import State


def _now() -> datetime:
    return datetime.now(UTC)


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class StateRow(SQLModel, table=True):
    __tablename__ = "state"
    __table_args__ = (UniqueConstraint("m", "charge", "mult"),)

    id: int | None = Field(default=None, primary_key=True)
    m: int
    charge: int
    mult: int
    n_electrons: int

    def to_state(self) -> State:
        return State(self.m, self.charge, self.mult)


class Campaign(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    spec: dict = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)


class Structure(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    state_id: int = Field(foreign_key="state.id", index=True)
    origin: str  # "seed:<generator>" or the stage whose job produced it
    parent_job_id: int | None = Field(default=None, foreign_key="job.id")
    xyz: str
    created_at: datetime = Field(default_factory=_now)


class Job(SQLModel, table=True):
    """One node of the stage DAG for one input structure. Retries reuse the row."""

    __table_args__ = (UniqueConstraint("campaign_id", "stage", "input_structure_id"),)

    id: int | None = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="campaign.id", index=True)
    state_id: int = Field(foreign_key="state.id", index=True)
    stage: str
    level: str
    task: str
    parent_id: int | None = Field(default=None, foreign_key="job.id")
    input_structure_id: int = Field(foreign_key="structure.id")
    # What the next attempt starts from; differs from the input after a restart or displacement.
    start_structure_id: int = Field(foreign_key="structure.id")
    modifiers: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    status: str = Field(default=JobStatus.PENDING, index=True)  # a JobStatus value
    attempts: int = 0
    hash: str | None = None
    error: str | None = None
    error_kind: str | None = None
    wall_s: float | None = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class Attempt(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id", index=True)
    n: int
    hash: str | None
    modifiers: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    start_structure_id: int = Field(foreign_key="structure.id")
    status: str
    error: str | None = None
    error_kind: str | None = None
    action: str | None = None  # what the runner did next: retry reason or None
    cached: bool = False
    wall_s: float | None = None
    finished_at: datetime = Field(default_factory=_now)


class JobResult(SQLModel, table=True):
    __tablename__ = "result"

    job_id: int = Field(foreign_key="job.id", primary_key=True)
    energy: float
    final_structure_id: int = Field(foreign_key="structure.id")
    s2: float | None = None
    homo: float | None = None
    lumo: float | None = None
    mulliken_charges: list[float] | None = Field(default=None, sa_column=Column(JSON))
    frequencies: list[float] | None = Field(default=None, sa_column=Column(JSON))
    modes: list | None = Field(default=None, sa_column=Column(JSON))
    thermo: dict | None = Field(default=None, sa_column=Column(JSON))
    n_imag: int | None = None
    point_group: str | None = None
    symmetry_number: int | None = None
    opt_converged: bool | None = None
    orca_version: str | None = None


def default_db_path() -> Path:
    return Path(os.environ.get("HCLUST_DATA", "data")) / "hclust.sqlite"


def get_engine(path: Path | None = None) -> Engine:
    path = Path(path or default_db_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path}")

    @event.listens_for(engine, "connect")
    def _pragmas(dbapi_conn, _record) -> None:
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")  # readers (the API) never block the writer
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    SQLModel.metadata.create_all(engine)
    return engine
