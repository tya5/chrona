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
    warnings: list[Diagnostic] = []
    completed: dict[str, bool] = {}
    reportable_targets = {(key, "at") for key, item in project["objects"].items()
                          if item["schedule"]["mode"] == "fixed-point"}
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
            if "at" in actual:
                reportable_targets.add((object_id, "at"))
            if raw["mode"] != "fixed-point":
                if "at" in actual:
                    item["schedule"] = {"mode": "fixed-point", "at": as_date(actual["at"])}
                else:
                    _floor(raw, "at", max(planned["at"], as_of))
            continue
        if "finish" in actual:
            reportable_targets.add((object_id, "end"))
            if "start" in actual:
                reportable_targets.add((object_id, "start"))
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
            reportable_targets.add((object_id, "start"))
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
        return _failure(tuple(diagnostics), tuple(findings), unmatched, tuple(warnings))

    scheduled = scheduler.schedule(effective)
    for diagnostic in scheduled.diagnostics:
        details = diagnostic.details or {}
        if (diagnostic.id == "E_FIXED_TARGET_VIOLATION"
                and (details.get("object"), details.get("endpoint")) in reportable_targets):
            target_id, endpoint = details.get("object"), details.get("endpoint")
            actual = (latest.get(target_id) or {}).get("actual", {}) if isinstance(target_id, str) else {}
            if endpoint == "start" and isinstance(actual, Mapping) and "start" in actual:
                warning = _observed_start_bound_warning(
                    diagnostic, project, scheduled.placements, latest, as_date(actual["start"]),
                )
                if warning is None:
                    # Do not turn malformed or incomplete Scheduler evidence into a
                    # guessed warning; this target exception requires proof.
                    diagnostics.append(diagnostic)
                else:
                    warnings.append(warning)
            else:
                findings.append(diagnostic)
        else:
            diagnostics.append(diagnostic)
    for object_id, planned in ordinary.placements.items():
        placement = scheduled.placements.get(object_id)
        expected = {"at"} if "at" in planned else {"start", "end"}
        if (placement is None or set(placement) != expected
                or any(type(value) is not date for value in placement.values())):
            diagnostics.append(Diagnostic("E_DERIVATION", "Forecast placement is missing or has the wrong endpoint kind", f"/objects/{object_id}/schedule"))
    for object_id in scheduled.placements.keys() - objects.keys():
        diagnostics.append(Diagnostic("E_DERIVATION", "Forecast placement has no source Project object", f"/objects/{object_id}"))
    if diagnostics:
        return _failure(tuple(diagnostics), tuple(findings), unmatched, tuple(warnings))

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
                           moved_count=moved, analysis=scheduled.analysis, warnings=tuple(warnings))


def _failure(diagnostics: tuple[Diagnostic, ...], findings: tuple[Diagnostic, ...] = (),
             unmatched=(), warnings: tuple[Diagnostic, ...] = ()) -> ForecastOutcome:
    return ForecastOutcome(MappingProxyType({}), diagnostics=diagnostics, findings=findings,
                           unmatched_actual_ids=tuple(sorted(unmatched)), warnings=warnings)


def _observed_start_bound_warning(
    diagnostic: Diagnostic,
    project: Mapping[str, Any],
    placements: Mapping[str, Mapping[str, date]],
    latest: Mapping[str, Mapping[str, Any]],
    observed_start: date,
) -> Diagnostic | None:
    """Translate only a proved observed-start relation miss into a forecast warning.

    Scheduler details remain the date authority. Project relations and selected
    Actuals are checked as provenance, not used to solve the dependency again.
    """
    details = diagnostic.details
    if not isinstance(details, Mapping):
        return None
    target_id = details.get("object")
    relation_key = details.get("relation")
    placed = _detail_date(details.get("placed"))
    required = _detail_date(details.get("required"))
    source = details.get("from")
    if (not isinstance(target_id, str) or not isinstance(relation_key, str)
            or details.get("endpoint") != "start" or placed != observed_start
            or required is None or required <= placed or not isinstance(source, Mapping)):
        return None
    source_id, source_endpoint = source.get("object"), source.get("endpoint")
    source_date = _detail_date(source.get("value"))
    if (not isinstance(source_id, str) or source_endpoint not in {"start", "end", "at"}
            or source_date is None):
        return None
    source_placement = placements.get(source_id)
    if (source_placement is None or source_endpoint not in source_placement
            or source_placement[source_endpoint] != source_date):
        return None

    relation = None
    for index, candidate in enumerate(project.get("relations", ())):
        candidate_key = candidate.get("id") or f"/relations/{index}"
        if candidate_key == relation_key:
            relation = candidate
            break
    if relation is None:
        return None
    source_ref = relation.get("from", {})
    target_ref = relation.get("to", {})
    if (source_ref.get("object") != source_id or source_ref.get("endpoint") != source_endpoint
            or target_ref.get("object") != target_id or target_ref.get("endpoint") != "start"
            or details.get("lag") != relation.get("lag", "0d")):
        return None
    target_observation = latest.get(target_id)
    target_actual = (target_observation or {}).get("actual", {})
    if (not isinstance(target_actual, Mapping) or "start" not in target_actual
            or _detail_date(target_actual["start"]) != observed_start):
        return None

    source_observation = latest.get(source_id)
    source_actual = (source_observation or {}).get("actual", {})
    actual_endpoint = {"start": "start", "end": "finish", "at": "at"}[source_endpoint]
    source_basis = ("observed" if isinstance(source_actual, Mapping)
                    and _detail_date(source_actual.get(actual_endpoint)) == source_date else "forecast")
    before_bound_days = (required - placed).days
    evidence = dict(details)
    evidence["beforeBoundDays"] = before_bound_days
    evidence["sourceDateBasis"] = source_basis
    overlap_days = ((source_date - placed).days
                    if source_endpoint == "end" and source_date > placed else 0)
    if overlap_days > 0:
        evidence["overlapDays"] = overlap_days
        basis_text = "observed" if source_basis == "observed" else "forecast"
        message = (f"Work on {target_id} started on {placed.isoformat()}, {overlap_days} calendar day(s) "
                   f"before predecessor {source_id}'s {basis_text} finish on {source_date.isoformat()}; "
                   f"relation {relation_key} requires "
                   f"{required.isoformat()} after lag {details['lag']}. The observed start is retained.")
    else:
        source_label = (f"predecessor {source_id}'s {source_basis} finish"
                        if source_endpoint == "end" else f"{source_id}.{source_endpoint}")
        message = (f"Observed start of {target_id} on {placed.isoformat()} misses dependency bound for "
                   f"relation {relation_key}: {source_label} on {source_date.isoformat()} with lag "
                   f"{details['lag']} requires {required.isoformat()} "
                   f"({before_bound_days} calendar day(s) before the bound). The observed start is retained.")
    return Diagnostic("W_FORECAST_OBSERVED_START_BEFORE_BOUND", message, diagnostic.path,
                      details=evidence)


def _detail_date(value: Any) -> date | None:
    try:
        return as_date(value)
    except (TypeError, ValueError):
        return None


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
