"""Reproducible Project loading from immutable Revision Store resources."""
from __future__ import annotations

from typing import Any

import yaml

from chrona.storage.revision_store import LocalSnapshotReader, SnapshotReadError
from chrona.scheduling.scheduler import ScheduleResult, schedule
from chrona.core.validation import validate_project
from chrona.extensions.profiles import resolve_profile_diagnostics


def load_project(reference: dict[str, Any], reader: LocalSnapshotReader) -> dict[str, Any]:
    """Load one pinned Project; callers cannot supply a filesystem path fallback."""
    if reference.get("kind") != "project":
        raise SnapshotReadError("E_STORE_REFERENCE")
    loaded = yaml.safe_load(reader.read(reference))
    if not isinstance(loaded, dict):
        raise SnapshotReadError("E_STORE_REFERENCE")
    return loaded


def validate_snapshot(reference: dict[str, Any], reader: LocalSnapshotReader):
    project = load_project(reference, reader)
    return validate_project(project, extension_diagnostics=resolve_profile_diagnostics(project, reader))


def schedule_snapshot(reference: dict[str, Any], reader: LocalSnapshotReader) -> ScheduleResult:
    project = load_project(reference, reader)
    return schedule(project, extension_diagnostics=resolve_profile_diagnostics(project, reader))
