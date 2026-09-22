"""Presentation-free compare-and-set persistence for authoring workspace bytes."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from chrona.operational.resources import OperationalResourceError, content_identity


def read_authoring_workspace(path: Path) -> dict[str, Any]:
    """Read untyped source bytes for an application use case to validate."""
    return _load_workspace(path)


def cas_write_authoring_workspace(path: Path, expected_identity: str, candidate: dict[str, Any]) -> str | None:
    """Persist application-validated source only if its content identity still matches."""
    try:
        _atomic_yaml_write(path, candidate, expected_identity)
    except FileExistsError:
        return None
    return content_identity(candidate)


def _load_workspace(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise OperationalResourceError("E_AUTHORING_WORKSPACE_SCHEMA")
    return value


def _atomic_yaml_write(path: Path, candidate: dict[str, Any], expected_identity: str) -> None:
    if content_identity(_load_workspace(path)) != expected_identity:
        raise FileExistsError
    temporary = path.with_name(f".{path.name}.authoring.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            yaml.safe_dump(candidate, handle, sort_keys=False)
            handle.flush()
        if content_identity(_load_workspace(path)) != expected_identity:
            raise FileExistsError
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
