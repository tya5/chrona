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
        if stripped.startswith(b"{"):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                pass
        return yaml.load(source, Loader=_SAFE_LOADER)
    elif isinstance(source, str):
        stripped = source.lstrip()
        if stripped.startswith("{"):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                pass
        return yaml.load(source, Loader=_SAFE_LOADER)
    else:
        return yaml.load(source, Loader=_SAFE_LOADER)


def schema_resource(name: str) -> Traversable:
    """Return a schema from the wheel, or from the sole source-tree authority."""
    packaged = files(__package__).joinpath("schemas", name)
    if packaged.is_file():
        return packaged
    return files("schemas").joinpath(name)


def template_resource(name: str) -> Traversable:
    """Return one supported init template from the wheel or development authority."""
    packaged = files(__package__).joinpath("examples", name)
    if packaged.is_dir() and packaged.joinpath("manifest.yaml").is_file():
        return packaged
    source = files("examples").joinpath(name)
    if source.is_dir() and source.joinpath("manifest.yaml").is_file():
        return source
    raise ValueError("E_INIT_EXAMPLE")


def default_preset_resource() -> Traversable:
    """Return the wheel-owned draft default preset without repository lookup."""
    resource = files(__package__).joinpath("presets", "default.yaml")
    if not resource.is_file():
        raise ValueError("E_DRAFT_DEFAULT_PRESET")
    return resource


def default_preset_root() -> Traversable:
    """Return the one explicit resource root declared by the bundled default."""
    packaged = files(__package__).joinpath("examples", "halcyon-1")
    if packaged.joinpath("project.yaml").is_file():
        return packaged
    return files("examples").joinpath("halcyon-1")


@cache
def schema_document(name: str) -> Mapping[str, Any]:
    """Decode one immutable schema resource once per process."""
    value = safe_load(schema_resource(name).read_bytes())
    if not isinstance(value, Mapping):
        raise ValueError(f"E_SCHEMA_RESOURCE: {name}")
    return value
