"""Results database (SQLite). The orchestrator is its only writer; the API reads it."""

import os
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from sqlalchemy import JSON, Column, UniqueConstraint, event, inspect, text
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
    DISSOCIATED = "dissociated"  # the optimization drifted apart into fragments


TERMINAL = (JobStatus.DONE, JobStatus.FAILED, JobStatus.DISSOCIATED)


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
    unbound: bool | None = None  # anion without its extra electron (Level.anion_unbound)


class Candidate(SQLModel, table=True):
    """One structure seen by a select stage: the record of dedup and promotion decisions."""

    __table_args__ = (UniqueConstraint("campaign_id", "stage", "job_id"),)

    id: int | None = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="campaign.id", index=True)
    stage: str  # the select stage
    state_id: int = Field(foreign_key="state.id", index=True)
    job_id: int = Field(foreign_key="job.id")  # source job
    structure_id: int = Field(foreign_key="structure.id")
    energy: float
    source: str  # where the search started: "seed:random", "seed:templates", "goat", ...
    composition: str  # bonded units, e.g. "H3·H2"
    dissociated: bool
    unbound: bool | None = None  # anion without its extra electron: never selected
    n_imag: int | None = None  # from the source job's frequencies, if it computed them
    duplicate_of: int | None = Field(default=None, foreign_key="candidate.id")
    rank: int | None = None  # among unique, intact structures; 0 = lowest energy
    selected: bool = False


class VerdictRow(SQLModel, table=True):
    """Stability analysis of one state (hclust.analysis.verdicts), redone by `analyze`.

    Energies in Eh. D_q = lowest fragmentation channel minus the state: positive = bound.
    """

    __tablename__ = "verdict"
    __table_args__ = (UniqueConstraint("campaign_id", "state_id"),)

    id: int | None = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="campaign.id", index=True)
    state_id: int = Field(foreign_key="state.id", index=True)
    verdict: str
    temperature: float  # K, for d_h and d_g
    pressure: float  # atm, for d_g
    ref_job_id: int | None = Field(default=None, foreign_key="job.id")  # best CCSD(T) energy
    structure_id: int | None = Field(default=None, foreign_key="structure.id")
    geometry_level: str | None = None  # level that optimized the best structure
    energy: float | None = None
    zpe: float | None = None
    d_e: float | None = None
    d_0: float | None = None
    d_h: float | None = None
    d_g: float | None = None
    channel: str | None = None  # lowest channel for D_e, e.g. "H3+ + H2"
    channel_g: str | None = None  # lowest channel for D_g (can differ)
    spin_gap: float | None = None  # E - lowest E over the species' multiplicities
    detachment: float | None = None  # anions: E(lowest neutral limit) - E, adiabatic
    ionization: float | None = None  # E(lowest cation limit) - E, adiabatic
    homo: float | None = None  # of the reference (HF) wave function
    s2: float | None = None
    spin_contaminated: bool | None = None  # <S^2> off by more than 10 % of S(S+1)
    point_group: str | None = None
    shape: str | None = None  # atom | linear | planar | 3D
    composition: str | None = None  # bonded units, e.g. "H3·H2"
    n_candidates: int = 0  # reference energies considered for this state


class StudyResult(SQLModel, table=True):
    """One ORCA run of a Phase 8 study (hclust.studies), keyed within its study.

    Studies run outside the stage DAG (other charges, ghost atoms, fields, ...); the ORCA
    files are content-addressed under data/jobs/<hash> like every campaign job.
    """

    __tablename__ = "study_result"
    __table_args__ = (UniqueConstraint("study", "key"),)

    id: int | None = Field(default=None, primary_key=True)
    study: str = Field(index=True)
    key: str  # e.g. "H3-(1)|vde|0|2"
    hash: str
    status: str  # ok | failed
    energy: float | None = None
    error: str | None = None
    wall_s: float | None = None
    data: dict | None = Field(default=None, sa_column=Column(JSON))  # study-specific details
    updated_at: datetime = Field(default_factory=_now)


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
    _add_missing_columns(engine)
    return engine


def get_readonly_engine(path: Path | None = None) -> Engine:
    """For readers (the API): SQLite refuses writes, and no schema changes are attempted.

    The directory must still be writable: WAL readers need the -shm file (Plan, Phase 6).
    """
    path = Path(path or default_db_path()).resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    return create_engine(
        f"sqlite:///file:{path}?mode=ro&uri=true", connect_args={"check_same_thread": False}
    )


def _add_missing_columns(engine: Engine) -> None:
    """Minimal migration: new nullable columns are added to existing tables."""
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table in SQLModel.metadata.tables.values():
            existing = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name not in existing:
                    kind = column.type.compile(engine.dialect)
                    conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {kind}'))
