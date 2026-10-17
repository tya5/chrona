"""Explicit, non-persistent forecast evaluation through the injected Scheduler."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from types import MappingProxyType
from typing import Any, Mapping

from chrona.core.diagnostics import Diagnostic
from chrona.core.figures import working_days_in
from chrona.core.forecast import ForecastItem, ForecastOutcome
from chrona.core.hierarchy import children_by_parent, normalize_hierarchy
from chrona.core.observations import latest_observations
from chrona.core.ports import ScheduleOutcome, Scheduler
from chrona.core.temporal import Calendar, advance, as_date, requires_working_calendar


def forecast_schedule(
    project: Mapping[str, Any], ordinary: ScheduleOutcome,
    actual_set: Mapping[str, Any] | None, scheduler: Scheduler,
) -> ForecastOutcome:
    """Evaluate Spec04 §17.1 after ordinary plan/Actual resource validation.

    No View, Snapshot, geometry, storage write or alternate dependency solver is
    involved. Source objects and observations are never mutated.
    """
    if not ordinary.ok:
        return _failure(tuple(ordinary.diagnostics))
    if actual_set is None:
        return _failure((Diagnostic("E_FORECAST_ACTUAL_REQUIRED", "Forecast requires an Actual Set", "/body/actual"),))
    body = actual_set.get("body", actual_set)
    if body.get("asOf") is None:
        return _failure((Diagnostic("E_FORECAST_ASOF_REQUIRED", "Forecast requires an explicit Actual asOf", "/body/asOf"),))
    as_of = as_date(body["asOf"])
    latest, unmatched = latest_observations(body.get("observations", ()), ordinary.placements)
    observation_indices = {observation["id"]: index for index, observation in enumerate(body.get("observations", ()))}
    effective = deepcopy(dict(project))
    objects = effective["objects"]
    children = children_by_parent(normalize_hierarchy(project))
    diagnostics: list[Diagnostic] = []
    findings: list[Diagnostic] = []
    completed: dict[str, bool] = {}
    for object_id, item in objects.items():
        planned = ordinary.placements.get(object_id)
        if planned is None:
            diagnostics.append(Diagnostic("E_DERIVATION", "Ordinary placement is missing", f"/objects/{object_id}/schedule"))
            continue
        raw = item["schedule"]
        observation = latest.get(object_id)
        actual = (observation or {}).get("actual", {})
        is_point = "at" in planned
        if ((is_point and any(key in actual for key in ("start", "finish")))
                or (not is_point and "at" in actual)):
            diagnostics.append(_observation_diagnostic("E_FORECAST_ACTUAL_KIND", "Actual occurrence kind differs from the planned object", observation,
                                                       observation_indices[observation["id"]]))
            continue
        completed[object_id] = ("at" in actual) if is_point else ("finish" in actual)
        if raw["mode"] == "rollup":
            continue
        if is_point:
            if raw["mode"] != "fixed-point":
                if "at" in actual:
                    item["schedule"] = {"mode": "fixed-point", "at": as_date(actual["at"])}
                else:
                    _floor(raw, "at", max(planned["at"], as_of))
            continue
        if "finish" in actual:
            start = as_date(actual["start"]) if "start" in actual else planned["start"]
            end = as_date(actual["finish"])
            if "start" not in actual:
                findings.append(_observation_diagnostic("I_FORECAST_START_UNOBSERVED", "Forecast retains planned start; Actual start is unobserved", observation,
                                                         observation_indices[observation["id"]]))
            item["schedule"] = {"mode": "fixed-span", "start": start, "end": end}
            diagnostics.extend(_retained_bounds(object_id, raw, {"start": start, "end": end}))
            continue
        amount, calendar = _effort(project, object_id, planned)
        if amount is None:
            diagnostics.append(Diagnostic("E_FORECAST_DURATION_UNAVAILABLE", "Fixed span has no positive inferred work effort", f"/objects/{object_id}/schedule"))
            continue
        if "start" in actual:
            start = as_date(actual["start"])
            arithmetic_start = calendar.next_working(start) if calendar is not None else start
            end = max(advance(arithmetic_start, amount, calendar), as_of)
            # Keep literal observed coordinates while Scheduler validates all
            # relations into the effective fixed span and derives successors.
            item["schedule"] = {"mode": "fixed-span", "start": start, "end": end}
            diagnostics.extend(_retained_bounds(object_id, raw, {"start": start, "end": end}))
        else:
            item["schedule"] = {"mode": "scheduled", "amount": amount,
                                "constraints": deepcopy(raw.get("constraints", {}))}
            _floor(item["schedule"], "start", max(planned["start"], as_of))
    if diagnostics:
        return _failure(tuple(diagnostics), tuple(findings), unmatched)

    scheduled = scheduler.schedule(effective)
    fixed_points = {key for key, item in project["objects"].items() if item["schedule"]["mode"] == "fixed-point"}
    for diagnostic in scheduled.diagnostics:
        details = diagnostic.details or {}
        if (diagnostic.id == "E_FIXED_TARGET_VIOLATION"
                and details.get("object") in fixed_points and details.get("endpoint") == "at"):
            findings.append(diagnostic)
        else:
            diagnostics.append(diagnostic)
    for object_id, planned in ordinary.placements.items():
        placement = scheduled.placements.get(object_id)
        expected = {"at"} if "at" in planned else {"start", "end"}
        if (placement is None or set(placement) != expected
                or any(type(value) is not date for value in placement.values())):
            diagnostics.append(Diagnostic("E_DERIVATION", "Forecast placement is missing or has the wrong endpoint kind", f"/objects/{object_id}/schedule"))
    if diagnostics:
        return _failure(tuple(diagnostics), tuple(findings), unmatched)

    for entry in reversed(normalize_hierarchy(project)):
        if objects[entry.object_id]["schedule"]["mode"] != "rollup":
            continue
        completed[entry.object_id] = all(completed[child] for child in children[entry.object_id])
        observation = latest.get(entry.object_id)
        actual = (observation or {}).get("actual", {})
        placement = scheduled.placements[entry.object_id]
        if any(key in actual and as_date(actual[key]) != placement[endpoint]
               for key, endpoint in (("start", "start"), ("finish", "end"))):
            findings.append(_observation_diagnostic("I_FORECAST_ROLLUP_OBSERVATION_CONFLICT", "Group Actual contradicts the forecast children envelope; children win", observation,
                                                     observation_indices[observation["id"]]))
    items = MappingProxyType({key: ForecastItem(MappingProxyType(dict(value)), completed[key])
                              for key, value in scheduled.placements.items()})
    moved = sum(item.placement != ordinary.placements[key] for key, item in items.items())
    findings.append(Diagnostic("I_FORECAST_MOVED", f"Forecast moved {moved} Project objects", "/objects", details={"count": moved}))
    return ForecastOutcome(items, findings=tuple(findings), unmatched_actual_ids=tuple(sorted(unmatched)),
                           moved_count=moved, analysis=scheduled.analysis)


def _failure(diagnostics: tuple[Diagnostic, ...], findings: tuple[Diagnostic, ...] = (),
             unmatched=()) -> ForecastOutcome:
    return ForecastOutcome(MappingProxyType({}), diagnostics, findings, tuple(sorted(unmatched)))


def _observation_diagnostic(code: str, message: str, observation: Mapping[str, Any], index: int) -> Diagnostic:
    return Diagnostic(code, message, f"/body/observations/{index}/actual",
                      details={"object": observation["projectObjectId"], "observation": observation["id"]})


def _floor(raw: dict, endpoint: str, value: date) -> None:
    bounds = raw.setdefault("constraints", {}).setdefault(endpoint, {})
    bounds["min"] = max(value, as_date(bounds["min"])) if "min" in bounds else value


def _effort(project: Mapping[str, Any], object_id: str,
            planned: Mapping[str, date]) -> tuple[str | None, Calendar | None]:
    item = project["objects"][object_id]
    calendar_id = item.get("calendar") or project.get("project", {}).get("calendar")
    calendar = Calendar.from_mapping(project["calendars"][calendar_id]) if calendar_id else None
    amount = item["schedule"].get("amount")
    if amount is None:
        count = (working_days_in(planned["start"], planned["end"], calendar) if calendar is not None
                 else (planned["end"] - planned["start"]).days)
        if count <= 0:
            return None, calendar
        amount = f"{count}{'wd' if calendar is not None else 'd'}"
    return amount, calendar if requires_working_calendar(amount) else None


def _retained_bounds(object_id: str, raw: Mapping[str, Any], placement: Mapping[str, date]) -> list[Diagnostic]:
    """Observed coordinates stay fixed; source constraints remain feasibility checks.

    Fixed-span syntax cannot carry bounds, so preserve their checks explicitly
    rather than dropping them during non-persistent normalization.
    """
    result = []
    for endpoint, bounds in raw.get("constraints", {}).items():
        for bound, value in bounds.items():
            violated = placement[endpoint] < as_date(value) if bound == "min" else placement[endpoint] > as_date(value)
            if violated:
                result.append(Diagnostic("E_CONTRADICTORY_BOUNDS", "Observed forecast endpoint violates retained bound",
                                         f"/objects/{object_id}/schedule/constraints/{endpoint}/{bound}"))
    return result
