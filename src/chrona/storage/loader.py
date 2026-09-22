"""Reproducible Project loading from immutable Revision Store resources."""
from __future__ import annotations

from typing import Any

import yaml

from chrona.core.ports import SnapshotReadError, SnapshotReader


def load_project(reference: dict[str, Any], reader: SnapshotReader) -> dict[str, Any]:
    """Load one pinned Project; callers cannot supply a filesystem path fallback."""
    if reference.get("kind") != "project":
        raise SnapshotReadError("E_STORE_REFERENCE")
    loaded = yaml.safe_load(reader.read(reference))
    if not isinstance(loaded, dict):
        raise SnapshotReadError("E_STORE_REFERENCE")
    return loaded
