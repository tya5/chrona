"""Locations for source-tree and wheel-installed runtime resources."""
from __future__ import annotations

from functools import cache
from importlib.resources import files
from importlib.resources.abc import Traversable
import json
from typing import Any, Mapping

import yaml


_SAFE_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def safe_load(source: Any) -> Any:
    """Safely decode YAML, using JSON's fast path for JSON-subset resources."""
    if isinstance(source, bytes):
        stripped = source.lstrip()
        return json.loads(stripped) if stripped.startswith(b"{") else yaml.load(source, Loader=_SAFE_LOADER)
    elif isinstance(source, str):
        stripped = source.lstrip()
        return json.loads(stripped) if stripped.startswith("{") else yaml.load(source, Loader=_SAFE_LOADER)
    else:
        return yaml.load(source, Loader=_SAFE_LOADER)


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
