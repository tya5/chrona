"""Opt-in scheduler for the `timeline/v0.2` DateTime Project successor."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from .diagnostics import Diagnostic
from .temporal_datetime import (
    DateTimeTemporalError,
    ZonedInstant,
    add_calendar_period,
    add_exact_duration,
    resolve_datetime,
    subtract_calendar_period,
)


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "timeline-design" / "docs" / "schemas" / "project-v0.2.schema.yaml"


@dataclass
class DateTimeScheduleResult:
    placements: dict[str, dict[str, ZonedInstant]]
    diagnostics: list[Diagnostic]

    @property
    def ok(self) -> bool:
        return not self.diagnostics


def schedule_datetime(project: dict[str, Any]) -> DateTimeScheduleResult:
    """Schedule the v0.2 acyclic subset without changing the Date-only scheduler."""
    diagnostics = _structural_diagnostics(project)
    if diagnostics:
        return DateTimeScheduleResult({}, diagnostics)
    objects = project["objects"]
    placements: dict[str, dict[str, ZonedInstant]] = {}
    pending = set(objects)
    for object_id, item in objects.items():
        raw = item["schedule"]
        if raw["mode"] == "fixed":
            placement = _fixed(raw, f"/objects/{object_id}/schedule", diagnostics)
            if placement:
                placements[object_id] = placement
                pending.remove(object_id)
        elif raw["mode"] == "recurrence":
            pending.remove(object_id)
    _relation_semantics(project, diagnostics)
    if diagnostics:
        return DateTimeScheduleResult(placements, diagnostics)
    while pending:
        progressed = False
        for object_id in list(pending):
            raw = objects[object_id]["schedule"]
            bounds, wait = _bounds(object_id, project, placements)
            if wait:
                continue
            placement = _scheduled(raw, bounds, f"/objects/{object_id}/schedule", diagnostics)
            if placement:
                placements[object_id] = placement
            pending.remove(object_id)
            progressed = True
        if not progressed:
            diagnostics.extend(Diagnostic("E_UNSUPPORTED_CYCLE", "DateTime reference scheduler supports an acyclic subset", f"/objects/{object_id}") for object_id in sorted(pending))
            break
    _validate_fixed_targets(project, placements, diagnostics)
    return DateTimeScheduleResult(placements, diagnostics)


def _structural_diagnostics(project: dict[str, Any]) -> list[Diagnostic]:
    schema = yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))
    return [Diagnostic("E_SCHEMA", error.message, "/" + "/".join(map(str, error.absolute_path)) or "/") for error in jsonschema.Draft202012Validator(schema).iter_errors(project)]


def _fixed(raw: dict[str, Any], path: str, diagnostics: list[Diagnostic]) -> dict[str, ZonedInstant] | None:
    try:
        if "at" in raw:
            return {"at": resolve_datetime(raw["at"])}
        placement = {"start": resolve_datetime(raw["start"]), "end": resolve_datetime(raw["end"])}
        if placement["start"].instant >= placement["end"].instant:
            diagnostics.append(Diagnostic("E_INVALID_SPAN", "Fixed span must satisfy start < end", path))
            return None
        return placement
    except DateTimeTemporalError as exc:
        diagnostics.append(Diagnostic(exc.diagnostic, "Invalid DateTime placement", path))
        return None


def _relation_semantics(project: dict[str, Any], diagnostics: list[Diagnostic]) -> None:
    for index, relation in enumerate(project["relations"]):
        path = f"/relations/{index}"
        for side in ("from", "to"):
            object_id, endpoint = relation[side]["object"], relation[side]["endpoint"]
            item = project["objects"].get(object_id)
            if item is None or item["schedule"]["mode"] == "recurrence":
                diagnostics.append(Diagnostic("E_DATETIME_ENDPOINT", "Dependency endpoint must name a non-recurrence object", path + f"/{side}"))
            elif endpoint not in _allowed_endpoints(item["schedule"]):
                diagnostics.append(Diagnostic("E_DATETIME_ENDPOINT", "Dependency endpoint is absent from object placement", path + f"/{side}/endpoint"))


def _allowed_endpoints(raw: dict[str, Any]) -> set[str]:
    return {"at"} if "at" in raw else {"start", "end"}


def _bounds(target: str, project: dict[str, Any], placements: dict[str, dict[str, ZonedInstant]]) -> tuple[dict[str, ZonedInstant], bool]:
    values: dict[str, ZonedInstant] = {}
    for relation in project["relations"]:
        if relation["to"]["object"] != target:
            continue
        source_id = relation["from"]["object"]
        if source_id not in placements:
            return {}, True
        source = placements[source_id][relation["from"]["endpoint"]]
        bound = _add(source, relation["lag"], "reject")
        endpoint = relation["to"]["endpoint"]
        if endpoint not in values or values[endpoint].instant < bound.instant:
            values[endpoint] = bound
    return values, False


def _add(value: ZonedInstant, amount: dict[str, str], policy: str) -> ZonedInstant:
    return add_exact_duration(value, amount["value"]) if amount["kind"] == "exactDuration" else add_calendar_period(value, amount["value"], policy)


def _subtract(value: ZonedInstant, amount: dict[str, str], policy: str) -> ZonedInstant:
    if amount["kind"] == "calendarPeriod":
        return subtract_calendar_period(value, amount["value"], policy)
    # Exact durations are ISO positive; derive the inverse at the instant level.
    result = add_exact_duration(value, amount["value"])
    return ZonedInstant(value.instant - (result.instant - value.instant), value.zone)


def _scheduled(raw: dict[str, Any], bounds: dict[str, ZonedInstant], path: str, diagnostics: list[Diagnostic]) -> dict[str, ZonedInstant] | None:
    anchor_name, anchor_value = next(iter(raw["anchor"].items()))
    try:
        anchor = resolve_datetime(anchor_value)
        policy = anchor_value.get("disambiguation", "reject")
        amount = raw["amount"]
        if anchor_name == "start":
            start, end = anchor, _add(anchor, amount, policy)
        else:
            end, start = anchor, _subtract(anchor, amount, policy)
        placement = {"start": start, "end": end}
        for endpoint, lower in bounds.items():
            if placement[endpoint].instant < lower.instant:
                diagnostics.append(Diagnostic("E_CONTRADICTORY_BOUNDS", "Authoritative anchor violates dependency lower bound", path + "/anchor"))
                return None
        return placement
    except DateTimeTemporalError as exc:
        diagnostics.append(Diagnostic(exc.diagnostic, "Invalid DateTime scheduled placement", path))
        return None


def _validate_fixed_targets(project: dict[str, Any], placements: dict[str, dict[str, ZonedInstant]], diagnostics: list[Diagnostic]) -> None:
    for index, relation in enumerate(project["relations"]):
        target_id, source_id = relation["to"]["object"], relation["from"]["object"]
        if target_id not in placements or source_id not in placements:
            continue
        if project["objects"][target_id]["schedule"]["mode"] != "fixed":
            continue
        required = _add(placements[source_id][relation["from"]["endpoint"]], relation["lag"], "reject")
        actual = placements[target_id][relation["to"]["endpoint"]]
        if actual.instant < required.instant:
            diagnostics.append(Diagnostic("E_FIXED_TARGET_VIOLATION", "Fixed target violates dependency lower bound", f"/relations/{index}"))
