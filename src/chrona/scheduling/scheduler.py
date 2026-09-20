from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from chrona.core.diagnostics import Diagnostic
from chrona.core.temporal import (Calendar, TemporalError, advance, as_date, parse_amount,
                       requires_working_calendar, retreat)
from chrona.core.validation import validate_project


@dataclass
class ScheduleResult:
    placements: dict[str, dict[str, date]]
    diagnostics: list[Diagnostic]

    @property
    def ok(self) -> bool:
        return not self.diagnostics


def schedule(project: dict[str, Any], package_manifests: dict[str, dict[str, Any]] | None = None, package_reader=None) -> ScheduleResult:
    """Reference scheduler for the acyclic Core v0.1 Date-only subset.

    It intentionally reports unresolved cyclic systems as capability diagnostics;
    a cycle is not thereby declared semantically invalid.
    """
    diagnostics = validate_project(project, package_manifests=package_manifests, package_reader=package_reader)
    if diagnostics:
        return ScheduleResult({}, diagnostics)
    calendars = {key: Calendar.from_mapping(value) for key, value in project.get("calendars", {}).items()}
    objects = project.get("objects", {})
    placements: dict[str, dict[str, date]] = {}
    pending = list(objects)

    # Fixed coordinates are authoritative and can always be made available.
    for object_id, item in objects.items():
        raw = item["schedule"]
        if raw["mode"] == "fixed":
            placements[object_id] = _fixed_placement(raw)
            pending.remove(object_id)

    while pending:
        progressed = False
        for object_id in tuple(pending):
            item = objects[object_id]
            raw = item["schedule"]
            if raw["mode"] != "scheduled":
                diagnostics.append(Diagnostic("E_DERIVATION", "Only fixed and scheduled objects are implemented", f"/objects/{object_id}"))
                pending.remove(object_id)
                continue
            bound, wait, bound_diagnostics = _lower_bound(object_id, project, placements, calendars)
            if bound_diagnostics:
                diagnostics.extend(bound_diagnostics)
                pending.remove(object_id)
                progressed = True
                continue
            if wait:
                continue
            try:
                placement, extra = _place_scheduled(object_id, item, raw, bound, project, calendars)
            except TemporalError as exc:
                diagnostics.append(Diagnostic("E_DERIVATION", str(exc), f"/objects/{object_id}/schedule"))
                pending.remove(object_id)
                continue
            diagnostics.extend(extra)
            if placement:
                placements[object_id] = placement
            pending.remove(object_id)
            progressed = True
        if not progressed:
            positive_cycle = _has_positive_dependency_cycle(project)
            diagnostic_id = "E_UNSATISFIABLE_DEPENDENCIES" if positive_cycle else "E_UNSUPPORTED_CYCLE"
            message = "Dependency system has no feasible solution" if positive_cycle else "Unresolved dependency system; reference scheduler supports an acyclic subset"
            for object_id in pending:
                diagnostics.append(Diagnostic(diagnostic_id, message, f"/objects/{object_id}"))
            break

    _validate_fixed_targets(project, placements, calendars, diagnostics)
    ordered = {object_id: placements[object_id] for object_id in objects if object_id in placements}
    return ScheduleResult(ordered, diagnostics)


def _fixed_placement(raw: dict[str, Any]) -> dict[str, date]:
    if "at" in raw:
        return {"at": as_date(raw["at"])}
    return {"start": as_date(raw["start"]), "end": as_date(raw["end"])}


def _lower_bound(target_id: str, project: dict, placements: dict,
                 calendars: dict[str, Calendar]) -> tuple[dict[str, date], bool, list[Diagnostic]]:
    bounds: dict[str, date] = {}
    for relation in project.get("relations", []):
        if relation["to"]["object"] != target_id:
            continue
        source_id = relation["from"]["object"]
        if source_id not in placements:
            return {}, True, []
        source = placements[source_id]
        endpoint = relation["from"]["endpoint"]
        if endpoint not in source:
            return {}, False, [Diagnostic(
                "E_ENDPOINT_MODE_MISMATCH",
                "Dependency source endpoint is unavailable on resolved placement",
                f"/relations/{relation.get('id', source_id)}/from/endpoint",
            )]
        source_value = source[endpoint]
        lag = relation.get("lag", "0d")
        amount = lag if isinstance(lag, str) else lag["value"]
        calendar_id = (lag.get("calendar") if isinstance(lag, dict) else None) or project["objects"][target_id].get("calendar") or project.get("project", {}).get("calendar")
        cal = calendars.get(calendar_id) if requires_working_calendar(amount) else None
        bound = advance(source_value, amount, cal)
        target_endpoint = relation["to"]["endpoint"]
        bounds[target_endpoint] = max(bounds.get(target_endpoint, bound), bound)
    raw_constraints = project["objects"][target_id]["schedule"].get("constraints", {})
    for endpoint, value in raw_constraints.items():
        if "min" in value:
            candidate = as_date(value["min"])
            bounds[endpoint] = max(bounds.get(endpoint, candidate), candidate)
    return bounds, False, []


def _place_scheduled(object_id: str, item: dict, raw: dict, bounds: dict[str, date], project: dict, calendars: dict[str, Calendar]) -> tuple[dict[str, date], list[Diagnostic]]:
    amount = raw["amount"]
    calendar_id = item.get("calendar") or project.get("project", {}).get("calendar")
    calendar = calendars.get(calendar_id) if requires_working_calendar(amount) else None
    anchor = raw.get("anchor", {})
    diagnostics: list[Diagnostic] = []
    if "start" in anchor:
        start = as_date(anchor["start"])
        if calendar is not None and not calendar.is_working(start):
            return {}, [Diagnostic("E_NON_WORKING_ANCHOR", "Explicit WorkPeriod start anchor is not a working date", f"/objects/{object_id}/schedule/anchor/start")]
        if "start" in bounds and start < bounds["start"]:
            return {}, [Diagnostic("E_CONTRADICTORY_BOUNDS", "Authoritative start anchor violates lower bound", f"/objects/{object_id}/schedule/anchor")]
    elif "end" in anchor:
        end = as_date(anchor["end"])
        if "end" in bounds and end < bounds["end"]:
            return {}, [Diagnostic("E_CONTRADICTORY_BOUNDS", "Authoritative end anchor violates lower bound", f"/objects/{object_id}/schedule/anchor")]
        start = retreat(end, amount, calendar)
    else:
        candidates = []
        if "start" in bounds:
            candidates.append(bounds["start"])
        if "end" in bounds:
            candidates.append(retreat(bounds["end"], amount, calendar))
        start = max(candidates) if candidates else None
        if start is None:
            raise TemporalError("Scheduled object needs an anchor or resolved lower bound")
        if calendar is not None:
            start = calendar.next_working(start)
    end = advance(start, amount, calendar)
    if "end" in bounds and end < bounds["end"]:
        if anchor:
            return {}, [Diagnostic("E_CONTRADICTORY_BOUNDS", "Authoritative anchor violates opposite endpoint lower bound", f"/objects/{object_id}/schedule/anchor")]
        raise TemporalError("Resolved end lower bound is inconsistent")
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
        required = advance(placements[source_id][relation["from"]["endpoint"]], amount, calendars.get(calendar_id) if requires_working_calendar(amount) else None)
        actual = placements[target_id][relation["to"]["endpoint"]]
        if actual < required:
            diagnostics.append(Diagnostic("E_FIXED_TARGET_VIOLATION", "Fixed target violates dependency lower bound", f"/relations/{relation.get('id', target_id)}"))


def _has_positive_dependency_cycle(project: dict) -> bool:
    """Prove an unsatisfiable cycle for calendar-day constraints only.

    WorkPeriod edges depend on a calendar and are intentionally left to the
    acyclic reference subset. A positive calendar-day cycle, however, is
    contradictory regardless of an anchor and has a normative diagnostic.
    """
    edges: list[tuple[tuple[str, str], tuple[str, str], int]] = []
    nodes: set[tuple[str, str]] = set()
    for relation in project.get("relations", []):
        lag = relation.get("lag", "0d")
        amount = lag if isinstance(lag, str) else lag["value"]
        try:
            parts = parse_amount(amount)
        except TemporalError:
            continue
        if any(unit == "wd" for _, unit in parts):
            continue
        weight = sum(number * (7 if unit == "w" else 1) for number, unit in parts)
        source = (relation["from"]["object"], relation["from"]["endpoint"])
        target = (relation["to"]["object"], relation["to"]["endpoint"])
        nodes.update((source, target))
        edges.append((source, target, weight))

    distance = {node: 0 for node in nodes}
    for _ in range(len(nodes)):
        changed = False
        for source, target, weight in edges:
            if distance[target] < distance[source] + weight:
                distance[target] = distance[source] + weight
                changed = True
        if not changed:
            return False
    return bool(edges)
