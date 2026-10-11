"""Declarative campaign definition (campaigns/*.yaml): species, seeds, stage DAG, resources."""

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from hclust.engines.orca import Task
from hclust.levels import LEVELS
from hclust.species import State, enumerate_states
from hclust.structures import GENERATORS


class _Spec(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class SpeciesSpec(_Spec):
    m: tuple[int, int] = (1, 10)  # inclusive range
    charges: list[int] = [-1, 0, 1]
    n_mult: int = Field(2, ge=1)
    # Explicit (m, charge, mult) list; overrides the ranges above.
    states_: list[tuple[int, int, int]] | None = Field(None, alias="states")

    def states(self) -> list[State]:
        """All states with at least one electron (H+ is a bare proton, E = 0)."""
        if self.states_ is not None:
            states = [State(*s) for s in self.states_]
        else:
            lo, hi = self.m
            states = enumerate_states(range(lo, hi + 1), tuple(self.charges), self.n_mult)
        return [s for s in states if s.n_electrons > 0]


class SeedSpec(_Spec):
    generator: str
    params: dict[str, Any] = {}
    into: str | None = None  # stage that receives these seeds; default: the first stage

    @field_validator("generator")
    @classmethod
    def _known(cls, v: str) -> str:
        if v not in GENERATORS:
            raise ValueError(f"unknown generator {v!r}; known: {sorted(GENERATORS)}")
        return v


class SelectSpec(_Spec):
    """Per-state barrier: deduplicate the source stage's structures and promote the best."""

    energy_window_kcal: float = 15.0
    max_per_state: int = Field(8, ge=1)
    dedup_energy_kcal: float = 0.1
    dedup_distance: float = 0.05  # RMS of sorted-distance fingerprints, Angstrom
    # Only promote true minima (requires a source stage with frequencies).
    minima_only: bool = False


class StageSpec(_Spec):
    """Either an ORCA stage (level + task) or a selection stage (select)."""

    name: str
    level: str | None = None
    task: Task | None = None
    select: SelectSpec | None = None
    from_: list[str] = Field([], alias="from")
    # "minimum": only continue from parents whose frequencies are all real.
    when: Literal["ok", "minimum"] = "ok"
    # GOAT: pass on at most this many ensemble structures (lowest energy first).
    max_outputs: int | None = Field(None, ge=1)

    @field_validator("from_", mode="before")
    @classmethod
    def _listify(cls, v):
        return [v] if isinstance(v, str) else v

    @field_validator("level")
    @classmethod
    def _known(cls, v: str | None) -> str | None:
        if v is not None and v not in LEVELS:
            raise ValueError(f"unknown level {v!r}; known: {sorted(LEVELS)}")
        return v

    @model_validator(mode="after")
    def _kind(self) -> "StageSpec":
        if self.select is not None:
            if self.level or self.task:
                raise ValueError(f"select stage {self.name!r} takes no level or task")
            if len(self.from_) != 1:
                raise ValueError(f"select stage {self.name!r} needs exactly one 'from'")
        elif not (self.level and self.task):
            raise ValueError(f"stage {self.name!r} needs a level and a task (or select)")
        return self

    @property
    def is_select(self) -> bool:
        return self.select is not None


class Resources(_Spec):
    workers: int = Field(16, ge=1)
    maxcore_mb: int = 600
    timeout_min: float = 120
    # Total estimated scratch of running jobs stays below this (see Level.scratch_gb_m10).
    scratch_budget_gb: float = 150


class CampaignSpec(_Spec):
    name: str
    species: SpeciesSpec = SpeciesSpec()
    seeds: list[SeedSpec]
    stages: list[StageSpec]
    resources: Resources = Resources()
    # Structures whose pieces are all farther apart than this (Angstrom) have dissociated.
    dissociation_cutoff: float = 3.5

    @model_validator(mode="after")
    def _check_dag(self) -> "CampaignSpec":
        if not self.stages:
            raise ValueError("a campaign needs at least one stage")
        seen: dict[str, StageSpec] = {}
        for stage in self.stages:
            if stage.name in seen:
                raise ValueError(f"duplicate stage {stage.name!r}")
            for source in stage.from_:
                if source not in seen:
                    raise ValueError(f"stage {stage.name!r} must start from an earlier stage")
            if stage.is_select and seen[stage.from_[0]].is_select:
                raise ValueError(f"select stage {stage.name!r} must follow an ORCA stage")
            seen[stage.name] = stage
        for seed in self.seeds:
            target = seen.get(seed.into or self.stages[0].name)
            if target is None or target.is_select:
                raise ValueError(f"seeds must go into an ORCA stage, not {seed.into!r}")
        fed = {seed.into or self.stages[0].name for seed in self.seeds}
        for stage in self.stages:
            if not stage.from_ and stage.name not in fed:
                raise ValueError(f"stage {stage.name!r} has neither seeds nor 'from'")
        return self

    @classmethod
    def load(cls, path: Path) -> "CampaignSpec":
        return cls.model_validate(yaml.safe_load(Path(path).read_text()))

    def stage(self, name: str) -> StageSpec:
        return next(s for s in self.stages if s.name == name)

    def seed_stage(self, seed: SeedSpec) -> StageSpec:
        return self.stage(seed.into or self.stages[0].name)

    def children(self, stage: str) -> list[StageSpec]:
        return [s for s in self.stages if stage in s.from_]

    def upstream(self, stage: str) -> set[str]:
        """All stages whose jobs can lead to jobs of `stage`, including itself."""
        found, todo = set(), [stage]
        while todo:
            name = todo.pop()
            if name not in found:
                found.add(name)
                todo.extend(self.stage(name).from_)
        return found
