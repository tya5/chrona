"""Locations for source-tree and wheel-installed runtime resources."""
from __future__ import annotations

from functools import cache
from importlib.resources import files
from importlib.resources.abc import Traversable
from typing import Any, Mapping

from chrona.yaml_codec import safe_load


def schema_resource(name: str) -> Traversable:
    """Return a schema from the wheel, or from the sole source-tree authority."""
    packaged = files(__package__).joinpath("schemas", name)
    if packaged.is_file():
        return packaged
    return files("schemas").joinpath(name)


@cache
def schema_document(name: str) -> Mapping[str, Any]:
    """Decode one immutable schema resource once per process."""
    value = safe_load(schema_resource(name).read_bytes())
    if not isinstance(value, Mapping):
        raise ValueError(f"E_SCHEMA_RESOURCE: {name}")
    return value
