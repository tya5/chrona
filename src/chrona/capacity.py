"""M11-1 Date-only capacity validation and derived overload reporting."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from .diagnostics import Diagnostic
from .scheduler import schedule
from .temporal import as_date


@dataclass(frozen=True)
class CapacityResult:
    diagnostics: tuple[Diagnostic, ...]
    overloads: tuple[dict[str, Any], ...]

    @property
    def ok(self) -> bool:
        return not self.diagnostics


def evaluate_capacity(project: dict[str, Any], capacity: dict[str, Any]) -> CapacityResult:
    """Derive daily overloads without changing the Project or schedule."""
    scheduled = schedule(project)
    diagnostics = list(scheduled.diagnostics)
    if diagnostics:
        return CapacityResult(tuple(diagnostics), ())
    resources = {item.get("id"): item for item in capacity.get("resources", [])}
    availability: dict[tuple[str, object], float] = {}
    for index, item in enumerate(capacity.get("availability", [])):
        key = (item.get("resourceId"), item.get("date"))
        if key in availability:
            diagnostics.append(Diagnostic("E_CAPACITY_AVAILABILITY", "Duplicate resource/day availability", f"/availability/{index}"))
            continue
        availability[key] = item.get("amount", 0)
    demand: dict[tuple[str, object], float] = defaultdict(float)
    for index, assignment in enumerate(capacity.get("assignments", [])):
        resource = resources.get(assignment.get("resourceId"))
        object_id = assignment.get("objectId")
        if resource is None or object_id not in scheduled.placements:
            diagnostics.append(Diagnostic("E_REFERENCE", "Assignment reference is unavailable", f"/assignments/{index}")); continue
        if resource.get("unit") != assignment.get("unit"):
            diagnostics.append(Diagnostic("E_RESOURCE_UNIT_MISMATCH", "Assignment and resource units differ", f"/assignments/{index}/unit")); continue
        placement = scheduled.placements[object_id]
        if "start" not in placement or "end" not in placement:
            continue
        day = placement["start"]
        while day < placement["end"]:
            demand[(resource["id"], day)] += assignment["demand"]
            day += timedelta(days=1)
    overloads = tuple({"resourceId": resource_id, "date": day.isoformat(), "demand": amount, "availability": availability.get((resource_id, day.isoformat()), 0)} for (resource_id, day), amount in sorted(demand.items()) if amount > availability.get((resource_id, day.isoformat()), 0))
    if overloads:
        diagnostics.append(Diagnostic("E_CAPACITY_OVERLOAD", "Capacity demand exceeds explicit availability"))
    return CapacityResult(tuple(diagnostics), overloads)
