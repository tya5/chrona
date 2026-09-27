"""Point-to-span attachment: presentation metadata that never schedules (#486)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from chrona.core.diagnostics import Diagnostic


@dataclass(frozen=True)
class AttachmentWarning:
    """A point dated outside the planned span of the task it attaches to."""

    object_id: str
    host_id: str
    code: str = "W_PROJECT_ATTACHED_OUTSIDE_HOST"


def attachment_diagnostics(objects: dict[str, Any]) -> list[Diagnostic]:
    """Reject attachments that cannot name one span host for one point."""
    diagnostics: list[Diagnostic] = []
    for object_id, item in objects.items():
        host = item.get("attachesTo") if isinstance(item, dict) else None
        if host is None:
            continue
        path = f"/objects/{object_id}/attachesTo"
        if host == object_id:
            diagnostics.append(Diagnostic("E_PROJECT_ATTACH_SELF", "An object cannot attach to itself", path))
        elif host not in objects:
            diagnostics.append(Diagnostic("E_PROJECT_ATTACH_TARGET_UNKNOWN", f"Unknown attachment host {host}", path))
        elif _mode(item) != "fixed-point":
            diagnostics.append(Diagnostic("E_PROJECT_ATTACH_SOURCE_NOT_POINT", "Only a fixed-point object can attach to a span", path))
        elif _mode(objects[host]) == "fixed-point":
            diagnostics.append(Diagnostic("E_PROJECT_ATTACH_TARGET_NOT_SPAN", f"Attachment host {host} is not a span", path))
    return diagnostics


def attachment_warnings(project: dict[str, Any], placements: dict[str, dict[str, date]]) -> tuple[AttachmentWarning, ...]:
    """Name each attached point whose date falls outside its host's planned span."""
    warnings = []
    for object_id, item in project.get("objects", {}).items():
        host = item.get("attachesTo")
        point, span = placements.get(object_id, {}), placements.get(host, {}) if host else {}
        at, start, end = point.get("at"), span.get("start"), span.get("end")
        if at is not None and start is not None and end is not None and not start <= at <= end:
            warnings.append(AttachmentWarning(object_id, str(host)))
    return tuple(warnings)


def _mode(item: Any) -> object:
    schedule = item.get("schedule") if isinstance(item, dict) else None
    return schedule.get("mode") if isinstance(schedule, dict) else None
