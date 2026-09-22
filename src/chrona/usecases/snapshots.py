"""Validate or schedule one pinned Project snapshot, extensions included."""
from __future__ import annotations

from typing import Any

from chrona.core.ports import SnapshotReader
from chrona.core.validation import validate_project
from chrona.extensions.profiles import resolve_profile_diagnostics
from chrona.scheduling.scheduler import ScheduleResult, schedule
from chrona.storage.loader import load_project


def validate_snapshot(reference: dict[str, Any], reader: SnapshotReader):
    project = load_project(reference, reader)
    return validate_project(project, extension_diagnostics=resolve_profile_diagnostics(project, reader))


def schedule_snapshot(reference: dict[str, Any], reader: SnapshotReader) -> ScheduleResult:
    project = load_project(reference, reader)
    return schedule(project, extension_diagnostics=resolve_profile_diagnostics(project, reader))
