"""Locations for source-tree and wheel-installed runtime resources."""
from __future__ import annotations

from functools import cache
from importlib.resources import files
from importlib.resources.abc import Traversable
import json
from pathlib import PurePosixPath
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


@cache
def example_registry() -> Mapping[str, Mapping[str, str]]:
    """Return the initialisable examples by id, validated against the registry schema."""
    from jsonschema import Draft202012Validator

    value = safe_load(files(__package__).joinpath("example-registry.yaml").read_bytes())
    if not isinstance(value, Mapping) or tuple(Draft202012Validator(schema_document("example-registry-v0.1.schema.yaml")).iter_errors(value)):
        raise ValueError("E_EXAMPLE_REGISTRY")
    return {entry["id"]: entry for entry in value["examples"]}


def example_ids() -> tuple[str, ...]:
    """Return the ids `chrona init --example` accepts."""
    return tuple(example_registry())


def template_resource(name: str) -> Traversable:
    """Return one registered init example from the wheel or development authority."""
    entry = example_registry().get(name)
    if entry is None:
        raise ValueError(f"E_INIT_EXAMPLE: {name!r} is not registered; available: {', '.join(example_ids())}")
    parts = PurePosixPath(entry["path"]).parts
    packaged = files(__package__).joinpath(*parts)
    if packaged.is_dir() and packaged.joinpath("manifest.yaml").is_file():
        return packaged
    source = files(parts[0]).joinpath(*parts[1:])
    if source.is_dir() and source.joinpath("manifest.yaml").is_file():
        return source
    raise ValueError("E_INIT_EXAMPLE")


def minimal_template_resource() -> Traversable:
    """Return the wheel-owned editable starter template, not a corpus example."""
    resource = files(__package__).joinpath("templates", "minimal")
    required = ("project.yaml", "actual.yaml", "README.md")
    if not resource.is_dir() or any(not resource.joinpath(name).is_file() for name in required):
        raise ValueError("E_INIT_TEMPLATE")
    return resource


def default_preset_resource() -> Traversable:
    """Return the wheel-owned draft default preset without repository lookup."""
    resource = files(__package__).joinpath("presets", "default.yaml")
    if not resource.is_file():
        raise ValueError("E_DRAFT_DEFAULT_PRESET")
    return resource


def builtin_preset_library_resource() -> Traversable:
    """Return the finite wheel-owned builtin preset catalogue."""
    resource = files(__package__).joinpath("presets", "library.yaml")
    if not resource.is_file():
        raise ValueError("E_BUILTIN_PRESET_LIBRARY")
    return resource


def axis_name_tables_resource() -> Traversable:
    """Return the finite, wheel-owned axis vocabulary catalog."""
    resource = files(__package__).joinpath("axis-name-tables-v0.1.yaml")
    if not resource.is_file():
        raise ValueError("E_AXIS_NAME_TABLE_RESOURCE")
    return resource


def builtin_preset_source_root(address: str) -> Traversable:
    """Resolve one safe builtin-library source root in wheel or source authority."""
    path = PurePosixPath(address)
    if (not address or path.is_absolute() or address != path.as_posix()
            or any(part in {"", ".", ".."} for part in path.parts)):
        raise ValueError("E_BUILTIN_PRESET_LIBRARY")
    packaged = files(__package__).joinpath(*path.parts)
    if path.parts == ("icons",) and packaged.is_dir():
        return packaged
    if packaged.is_dir() and (
        packaged.joinpath("project.yaml").is_file()
        or path.parts[:2] == ("presets", "bundles")
    ):
        return packaged
    raise ValueError("E_BUILTIN_PRESET_RESOURCE")


def default_preset_root() -> Traversable:
    """Return the packaged presets root that every path of the bundled default is relative to."""
    root = files(__package__).joinpath("presets")
    if not root.joinpath("default.yaml").is_file():
        raise ValueError("E_DRAFT_DEFAULT_PRESET")
    return root


@cache
def schema_document(name: str) -> Mapping[str, Any]:
    """Decode one immutable schema resource once per process."""
    value = safe_load(schema_resource(name).read_bytes())
    if not isinstance(value, Mapping):
        raise ValueError(f"E_SCHEMA_RESOURCE: {name}")
    return value
