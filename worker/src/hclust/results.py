"""Engine-independent result of one calculation."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np

from hclust.geometry import Geometry

# Imaginary frequencies smaller than this are numerical noise (doc/Plan.md, 2.2).
IMAG_FREQ_TOLERANCE_CM = 20.0

ErrorKind = Literal["scf", "opt", "timeout", "other"]


@dataclass
class Result:
    status: Literal["ok", "failed"]
    error: str | None = None
    error_kind: ErrorKind | None = None
    energy: float | None = None  # Eh, final single-point energy (highest level in the job)
    geometry: Geometry | None = None  # final geometry
    s2: float | None = None  # <S^2> of the UHF/UKS reference; None for restricted runs
    homo: float | None = None  # Eh
    lumo: float | None = None  # Eh
    mulliken_charges: list[float] | None = None
    frequencies: np.ndarray | None = field(default=None, repr=False)  # cm^-1, vibrations only; imaginary < 0
    modes: np.ndarray | None = field(default=None, repr=False)  # (n_vib, n_atoms, 3)
    thermo: dict[str, float] | None = None  # ORCA RRHO terms at 298.15 K, Eh
    point_group: str | None = None
    symmetry_number: int | None = None
    opt_converged: bool | None = None  # None when the job did not optimize
    wall_time_s: float | None = None
    orca_version: str | None = None
    workdir: Path | None = None
    cached: bool = False  # returned from an earlier identical run without running ORCA

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    @property
    def n_imag(self) -> int | None:
        if self.frequencies is None:
            return None
        return int(np.sum(self.frequencies < -IMAG_FREQ_TOLERANCE_CM))

    @property
    def gap(self) -> float | None:
        if self.homo is None or self.lumo is None:
            return None
        return self.lumo - self.homo

    @property
    def is_minimum(self) -> bool | None:
        return None if self.n_imag is None else self.n_imag == 0
