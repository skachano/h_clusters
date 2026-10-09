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

    def states(self) -> list[State]:
        """All states with at least one electron (H+ is a bare proton, E = 0)."""
        lo, hi = self.m
        states = enumerate_states(range(lo, hi + 1), tuple(self.charges), self.n_mult)
        return [s for s in states if s.n_electrons > 0]


class SeedSpec(_Spec):
    generator: str
    params: dict[str, Any] = {}

    @field_validator("generator")
    @classmethod
    def _known(cls, v: str) -> str:
        if v not in GENERATORS:
            raise ValueError(f"unknown generator {v!r}; known: {sorted(GENERATORS)}")
        return v


class StageSpec(_Spec):
    name: str
    level: str
    task: Task
    from_: str | None = Field(None, alias="from")
    # "minimum": only continue from parents whose frequencies are all real.
    when: Literal["ok", "minimum"] = "ok"

    @field_validator("level")
    @classmethod
    def _known(cls, v: str) -> str:
        if v not in LEVELS:
            raise ValueError(f"unknown level {v!r}; known: {sorted(LEVELS)}")
        return v


class Resources(_Spec):
    workers: int = Field(16, ge=1)
    maxcore_mb: int = 600
    timeout_min: float = 120


class CampaignSpec(_Spec):
    name: str
    species: SpeciesSpec = SpeciesSpec()
    seeds: list[SeedSpec]
    stages: list[StageSpec]
    resources: Resources = Resources()

    @model_validator(mode="after")
    def _check_dag(self) -> "CampaignSpec":
        seen: set[str] = set()
        for i, stage in enumerate(self.stages):
            if stage.name in seen:
                raise ValueError(f"duplicate stage {stage.name!r}")
            if i == 0 and stage.from_ is not None:
                raise ValueError("the first stage starts from the seeds and has no 'from'")
            if i > 0 and stage.from_ not in seen:
                raise ValueError(f"stage {stage.name!r} must start from an earlier stage")
            seen.add(stage.name)
        return self

    @classmethod
    def load(cls, path: Path) -> "CampaignSpec":
        return cls.model_validate(yaml.safe_load(Path(path).read_text()))

    @property
    def root(self) -> StageSpec:
        return self.stages[0]

    def children(self, stage: str) -> list[StageSpec]:
        return [s for s in self.stages if s.from_ == stage]
