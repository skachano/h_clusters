"""Seed geometries for the structure search (templates and random generators come in Phase 3)."""

from collections.abc import Callable

from hclust.geometry import Geometry


def chain(m: int, spacing: float = 0.9) -> list[Geometry]:
    """A linear chain along z: the simplest seed that exists for every m."""
    return [Geometry.hydrogens([[0.0, 0.0, i * spacing] for i in range(m)], f"chain {spacing}")]


GENERATORS: dict[str, Callable[..., list[Geometry]]] = {
    "chain": chain,
}
