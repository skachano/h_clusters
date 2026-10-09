"""Cartesian geometries (Angstrom) and XYZ I/O."""

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class Geometry:
    symbols: tuple[str, ...]
    coords: np.ndarray = field(repr=False)  # (n, 3), Angstrom
    comment: str = ""

    def __post_init__(self) -> None:
        coords = np.asarray(self.coords, dtype=float).reshape(len(self.symbols), 3)
        object.__setattr__(self, "symbols", tuple(self.symbols))
        object.__setattr__(self, "coords", coords)

    @classmethod
    def hydrogens(cls, coords, comment: str = "") -> "Geometry":
        coords = np.asarray(coords, dtype=float).reshape(-1, 3)
        return cls(("H",) * len(coords), coords, comment)

    @classmethod
    def from_xyz(cls, text: str) -> "Geometry":
        lines = text.strip("\n").splitlines()
        n = int(lines[0])
        rows = [line.split() for line in lines[2 : 2 + n]]
        return cls(
            tuple(r[0] for r in rows),
            np.array([[float(x) for x in r[1:4]] for r in rows]),
            lines[1].strip(),
        )

    @classmethod
    def read(cls, path: Path) -> "Geometry":
        return cls.from_xyz(Path(path).read_text())

    def to_xyz(self) -> str:
        return f"{len(self)}\n{self.comment}\n{self.atom_block()}\n"

    def atom_block(self) -> str:
        """'H  x  y  z' lines, fixed precision so that rendering is deterministic."""
        return "\n".join(
            f"{s:<2} {x:16.10f} {y:16.10f} {z:16.10f}"
            for s, (x, y, z) in zip(self.symbols, self.coords)
        )

    def __len__(self) -> int:
        return len(self.symbols)

    def distance_matrix(self) -> np.ndarray:
        d = self.coords[:, None, :] - self.coords[None, :, :]
        return np.linalg.norm(d, axis=-1)

    def distances(self) -> np.ndarray:
        """Sorted unique interatomic distances."""
        i, j = np.triu_indices(len(self), k=1)
        return np.sort(self.distance_matrix()[i, j])
