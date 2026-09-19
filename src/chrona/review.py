"""Machine-readable review output derived from canonical Project data."""
from __future__ import annotations

from typing import Any

from .scheduler import schedule
from .validation import validate_project


def review_projects(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Produce a stable-ID semantic diff; this does not mutate either Project."""
    diagnostics = [item.as_dict() for project in (before, after) for item in validate_project(project)]
    if diagnostics:
        return {"status": "rejected", "diagnostics": diagnostics, "changes": []}
    changes: list[dict[str, Any]] = []
    before_objects, after_objects = before.get("objects", {}), after.get("objects", {})
    for object_id in sorted(set(before_objects) | set(after_objects)):
        if object_id not in before_objects:
            changes.append({"kind": "object", "id": object_id, "change": "added"})
        elif object_id not in after_objects:
            changes.append({"kind": "object", "id": object_id, "change": "removed"})
        elif before_objects[object_id] != after_objects[object_id]:
            changes.append({"kind": "object", "id": object_id, "change": "modified"})
    return {
        "status": "accepted",
        "diagnostics": [],
        "changes": changes,
        "beforeSchedule": schedule(before).placements,
        "afterSchedule": schedule(after).placements,
    }
