"""Reproducible Project loading from immutable Revision Store resources."""
from __future__ import annotations

from typing import Any

from chrona.core.ports import SnapshotReadError, SnapshotReader
from chrona.resources import safe_load


def load_project(reference: dict[str, Any], reader: SnapshotReader) -> dict[str, Any]:
    """Load one pinned Project; callers cannot supply a filesystem path fallback."""
    if reference.get("kind") != "project":
        raise SnapshotReadError("E_STORE_REFERENCE", f"expected reference kind=project; received kind={reference.get('kind')!r}")
    loaded = safe_load(reader.read(reference))
    if not isinstance(loaded, dict):
        raise SnapshotReadError("E_STORE_REFERENCE", f"expected Project object at address={reference.get('address')!r}; received {type(loaded).__name__}")
    return loaded
