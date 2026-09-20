"""Locations for source-tree and wheel-installed runtime resources."""
from __future__ import annotations

from importlib.resources import files
from importlib.resources.abc import Traversable


def schema_resource(name: str) -> Traversable:
    """Return a schema from the wheel, or from the sole source-tree authority."""
    packaged = files(__package__).joinpath("schemas", name)
    if packaged.is_file():
        return packaged
    return files("schemas").joinpath(name)
