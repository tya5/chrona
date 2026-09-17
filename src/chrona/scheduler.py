from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from .diagnostics import Diagnostic
from .temporal import Calendar, TemporalError, advance, as_date, retreat
from .validation import validate_project


@dataclass
class ScheduleResult:
    placements: dict[str, dict[str, date]]
    diagnostics: list[Diagnostic]

    @property
    def ok(self) -> bool:
        return not any(item.id.startswith("E_") for item in self.diagnostics)


def schedule(project: dict[str, Any]) -> ScheduleResult:
    """Reference scheduler for the acyclic Core v0.1 Date-only subset.

    It intentionally reports unresolved cyclic systems as capability diagnostics;
    a cycle is not thereby declared semantically invalid.
    """
    diagnostics = validate_project(project)
    if diagnostics:
        return ScheduleResult({}, diagnostics)
    calendars = {key: Calendar.from_mapping(value) for key, value in project.get("calendars", {}).items()}
    objects = project.get("objects", {})
    placements: dict[str, dict[str, date]] = {}
    pending = set(objects)

    # Fixed coordinates are authoritative and can always be made available.
    for object_id, item in objects.items():
        raw = item["schedule"]
        if raw["mode"] == "fixed":
            placements[object_id] = _fixed_placement(raw)
            pending.remove(object_id)

    while pending:
        progressed = False
        for object_id in list(pending):
            item = objects[object_id]
            raw = item["schedule"]
            if raw["mode"] != "scheduled":
                diagnostics.append(Diagnostic("E_DERIVATION", "Only fixed and scheduled objects are implemented", f"/objects/{object_id}"))
                pending.remove(object_id)
                continue
            bound, wait = _lower_bound(object_id, project, placements, calendars)
            if wait:
                continue
            try:
                placement, extra = _place_scheduled(object_id, item, raw, bound, project, calendars)
            except TemporalError as exc:
                diagnostics.append(Diagnostic("E_DERIVATION", str(exc), f"/objects/{object_id}/schedule"))
                pending.remove(object_id)
                continue
            diagnostics.extend(extra)
            placements[object_id] = placement
            pending.remove(object_id)
            progressed = True
        if not progressed:
            for object_id in sorted(pending):
                diagnostics.append(Diagnostic("E_UNSUPPORTED_CYCLE", "Unresolved dependency system; reference scheduler supports an acyclic subset", f"/objects/{object_id}"))
            break

    _validate_fixed_targets(project, placements, calendars, diagnostics)
    return ScheduleResult(placements, diagnostics)


def _fixed_placement(raw: dict[str, Any]) -> dict[str, date]:
    if "at" in raw:
        return {"at": as_date(raw["at"])}
    return {"start": as_date(raw["start"]), "end": as_date(raw["end"])}


def _lower_bound(target_id: str, project: dict, placements: dict, calendars: dict[str, Calendar]) -> tuple[dict[str, date], bool]:
    bounds: dict[str, date] = {}
    for relation in project.get("relations", []):
        if relation["to"]["object"] != target_id:
            continue
        source_id = relation["from"]["object"]
        if source_id not in placements:
            return {}, True
        source = placements[source_id]
        endpoint = relation["from"]["endpoint"]
        source_value = source[endpoint]
        lag = relation.get("lag", "0d")
        amount = lag if isinstance(lag, str) else lag["value"]
        calendar_id = (lag.get("calendar") if isinstance(lag, dict) else None) or project["objects"][target_id].get("calendar") or project.get("project", {}).get("calendar")
        cal = calendars.get(calendar_id) if amount.endswith("wd") else None
        bound = advance(source_value, amount, cal)
        target_endpoint = relation["to"]["endpoint"]
        bounds[target_endpoint] = max(bounds.get(target_endpoint, bound), bound)
    raw_constraints = project["objects"][target_id]["schedule"].get("constraints", {})
    for endpoint, value in raw_constraints.items():
        if "min" in value:
            candidate = as_date(value["min"])
            bounds[endpoint] = max(bounds.get(endpoint, candidate), candidate)
    return bounds, False


def _place_scheduled(object_id: str, item: dict, raw: dict, bounds: dict[str, date], project: dict, calendars: dict[str, Calendar]) -> tuple[dict[str, date], list[Diagnostic]]:
    amount = raw["amount"]
    calendar_id = item.get("calendar") or project.get("project", {}).get("calendar")
    calendar = calendars.get(calendar_id) if amount.endswith("wd") else None
    anchor = raw.get("anchor", {})
    diagnostics: list[Diagnostic] = []
    if "start" in anchor:
        start = as_date(anchor["start"])
        if "start" in bounds and start < bounds["start"]:
            return {}, [Diagnostic("E_CONTRADICTORY_BOUNDS", "Authoritative start anchor violates lower bound", f"/objects/{object_id}/schedule/anchor")]
    elif "end" in anchor:
        end = as_date(anchor["end"])
        if "end" in bounds and end < bounds["end"]:
            return {}, [Diagnostic("E_CONTRADICTORY_BOUNDS", "Authoritative end anchor violates lower bound", f"/objects/{object_id}/schedule/anchor")]
        start = retreat(end, amount, calendar)
    else:
        start = bounds.get("start")
        if start is None and "end" in bounds:
            start = retreat(bounds["end"], amount, calendar)
        if start is None:
            raise TemporalError("Scheduled object needs an anchor or resolved lower bound")
        if calendar is not None:
            start = calendar.next_working(start)
    end = advance(start, amount, calendar)
    if "end" in bounds and end < bounds["end"]:
        start = bounds["end"] if calendar is None else calendar.next_working(bounds["end"])
        end = advance(start, amount, calendar)
    for endpoint, value in raw.get("constraints", {}).items():
        if "max" in value and {"start": start, "end": end}[endpoint] > as_date(value["max"]):
            diagnostics.append(Diagnostic("E_CONTRADICTORY_BOUNDS", "Resolved endpoint exceeds maximum bound", f"/objects/{object_id}/schedule/constraints/{endpoint}/max"))
    return {"start": start, "end": end}, diagnostics


def _validate_fixed_targets(project: dict, placements: dict, calendars: dict[str, Calendar], diagnostics: list[Diagnostic]) -> None:
    for relation in project.get("relations", []):
        target_id = relation["to"]["object"]
        source_id = relation["from"]["object"]
        if target_id not in placements or source_id not in placements:
            continue
        target_raw = project["objects"][target_id]["schedule"]
        if target_raw["mode"] != "fixed":
            continue
        lag = relation.get("lag", "0d")
        amount = lag if isinstance(lag, str) else lag["value"]
        calendar_id = (lag.get("calendar") if isinstance(lag, dict) else None) or project["objects"][target_id].get("calendar") or project.get("project", {}).get("calendar")
        required = advance(placements[source_id][relation["from"]["endpoint"]], amount, calendars.get(calendar_id) if amount.endswith("wd") else None)
        actual = placements[target_id][relation["to"]["endpoint"]]
        if actual < required:
            diagnostics.append(Diagnostic("E_FIXED_TARGET_VIOLATION", "Fixed target violates dependency lower bound", f"/relations/{relation.get('id', target_id)}"))
