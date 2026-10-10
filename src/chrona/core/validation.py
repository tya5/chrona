from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml

from chrona.core.attachments import attachment_diagnostics
from chrona.core.diagnostics import Diagnostic
from chrona.core.periods import period_diagnostics
from chrona.core.temporal import (Calendar, TemporalError, as_date, is_scheduled_amount,
                       parse_amount, requires_working_calendar)
from chrona.resources import safe_load, schema_resource, schema_validator, validator_for_schema
from chrona.core.suggestions import unknown_id_message
from chrona.schema_diagnostics import explain_all_errors


SCHEMA_PATH = schema_resource("project-v0.7.schema.yaml")


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as stream:
        return safe_load(stream)


def validate_project(
    project: dict[str, Any],
    schema_path: Path = SCHEMA_PATH,
    extension_diagnostics: list[Diagnostic] | tuple[Diagnostic, ...] | None = None,
) -> list[Diagnostic]:
    """Run structural validation and Core rules over already-resolved inputs.

    Extension resolution belongs to an outer application/storage boundary.  That
    boundary may inject its deterministic diagnostics, but Core never imports a
    package registry or revision-store implementation.
    """
    diagnostics: list[Diagnostic] = []
    diagnostics.extend(_rollup_syntax_diagnostics(project))
    if diagnostics:
        return diagnostics
    validator = (
        schema_validator("project-v0.7.schema.yaml")
        if schema_path == SCHEMA_PATH
        else validator_for_schema(safe_load(schema_path.read_text(encoding="utf-8")))
    )
    # PyYAML resolves unquoted ISO dates to ``date`` objects, while JSON Schema
    # describes the canonical JSON-compatible representation as strings. Keep
    # the semantic value intact for scheduling, but validate its serialization.
    errors = tuple(validator.iter_errors(_schema_value(project)))
    failed_objects: frozenset[str] = frozenset()
    failed_relations: frozenset[int] = frozenset()
    if errors:
        # Every independent schema error, in pointer order (a union is reported as the one branch its `mode` selects),
        # then the Core rules for the parts that passed the schema when the errors are confined to objects and
        # relations (#1303).
        project_id = project.get("project", {}).get("id")
        violations = explain_all_errors(
            errors, resource_kind="project", resource_identity=project_id if isinstance(project_id, str) else None,
            select_branches=True, echo_values=True)
        diagnostics.extend(Diagnostic("E_SCHEMA", item.message, item.pointer) for item in violations)
        confined = _confined_failures(item.pointer for item in violations)
        if confined is None:
            return diagnostics
        failed_objects, failed_relations = confined
    calendars = project.get("calendars", {})
    objects = project.get("objects", {})
    children_by_parent = _validate_hierarchy(objects, diagnostics, skip=failed_objects)
    for calendar_id, raw in calendars.items():
        try:
            Calendar.from_mapping(raw)
        except (KeyError, TemporalError, ValueError) as exc:
            diagnostics.append(Diagnostic("E_SCHEMA", str(exc), f"/calendars/{calendar_id}"))

    project_calendar = project.get("project", {}).get("calendar")
    if project_calendar and project_calendar not in calendars:
        diagnostics.append(Diagnostic("E_REFERENCE", "Unknown project calendar", "/project/calendar"))

    for object_id, item in objects.items():
        if object_id in failed_objects:
            continue
        path = f"/objects/{object_id}"
        if item.get("calendar") and item["calendar"] not in calendars:
            diagnostics.append(Diagnostic("E_REFERENCE", "Unknown object calendar", path + "/calendar"))
        schedule = item["schedule"]
        mode = schedule["mode"]
        if "deadline" in item:
            try:
                as_date(item["deadline"])
            except TemporalError as exc:
                diagnostics.append(Diagnostic("E_SCHEMA", str(exc), path + "/deadline"))
        if mode == "fixed-span":
            try:
                if as_date(schedule["start"]) >= as_date(schedule["end"]):
                    diagnostics.append(Diagnostic("E_INVALID_SPAN", "Fixed span must satisfy start < end", path + "/schedule"))
            except TemporalError as exc:
                diagnostics.append(Diagnostic("E_SCHEMA", str(exc), path + "/schedule"))
        if mode == "scheduled":
            amount = schedule["amount"]
            if not is_scheduled_amount(amount):
                diagnostics.append(Diagnostic("E_INVALID_AMOUNT", "Scheduled spans allow only positive d, w, or wd", path + "/schedule/amount"))
            if requires_working_calendar(amount) and not _resolve_calendar_id(item, project):
                diagnostics.append(Diagnostic("E_CALENDAR_REQUIRED", "WorkPeriod schedule has no calendar", path))
        if mode == "scheduled-point":
            try:
                for bound in schedule.get("constraints", {}).get("at", {}).values():
                    as_date(bound)
            except TemporalError as exc:
                diagnostics.append(Diagnostic("E_SCHEMA", str(exc), path + "/schedule"))
                continue
        if mode == "scheduled-point" and not _has_derivation_source(object_id, schedule, project):
            diagnostics.append(Diagnostic("E_DERIVATION", "Scheduled point has no predecessor and no minimum date", path + "/schedule"))
        if mode == "rollup" and not children_by_parent.get(object_id):
            diagnostics.append(Diagnostic("E_ROLLUP_EMPTY", "Rollup must have scheduled descendants", path + "/schedule"))

    for index, relation in enumerate(project.get("relations", [])):
        if index in failed_relations:
            continue
        path = f"/relations/{index}"
        for side in ("from", "to"):
            ref = relation[side]
            if ref["object"] not in objects:
                diagnostics.append(Diagnostic("E_REFERENCE", unknown_id_message(f"{side} object", ref["object"], tuple(objects)),
                                              path + f"/{side}/object"))
            elif ref["object"] in failed_objects:
                continue  # its schedule failed the schema: no endpoint to check
            elif ref["endpoint"] not in _schedule_endpoints(objects[ref["object"]]["schedule"]):
                diagnostics.append(Diagnostic(
                    "E_ENDPOINT_MODE_MISMATCH",
                    f"Endpoint {ref['endpoint']} is unavailable on the referenced schedule",
                    path + f"/{side}/endpoint",
                ))
        lag = relation.get("lag")
        if lag:
            value = lag if isinstance(lag, str) else lag["value"]
            try:
                parse_amount(value)
                if requires_working_calendar(value):
                    lag_calendar = lag.get("calendar") if isinstance(lag, dict) else None
                    target = objects.get(relation["to"]["object"], {})
                    target = {} if relation["to"]["object"] in failed_objects else target
                    if lag_calendar and lag_calendar not in calendars:
                        diagnostics.append(Diagnostic("E_REFERENCE", "Unknown relation calendar", path + "/lag/calendar"))
                    elif not lag_calendar and not _resolve_calendar_id(target, project):
                        diagnostics.append(Diagnostic("E_CALENDAR_REQUIRED", "WorkPeriod lag has no calendar", path + "/lag"))
            except TemporalError as exc:
                diagnostics.append(Diagnostic("E_INVALID_AMOUNT", str(exc), path + "/lag"))
    if failed_objects or failed_relations:
        return diagnostics  # attachments and periods read whole objects: only for a Project that passed the schema
    diagnostics.extend(attachment_diagnostics(objects))
    diagnostics.extend(period_diagnostics(project, _schedule_endpoints))
    if any(isinstance(item, str) for item in project.get("extensions", [])):
        diagnostics.append(Diagnostic(
            "E_PACKAGE_RESOLUTION_REQUIRED",
            "Legacy extension identifiers require migration to immutable package references",
            "/extensions",
        ))
    elif extension_diagnostics:
        diagnostics.extend(extension_diagnostics)
    return diagnostics


def _confined_failures(pointers: Any) -> tuple[frozenset[str], frozenset[int]] | None:
    """The objects and relations holding schema errors, or None when an error lies elsewhere (no Core rules then)."""
    objects: set[str] = set()
    relations: set[int] = set()
    for pointer in pointers:
        parts = pointer.split("/")
        if len(parts) >= 3 and parts[1] == "objects":
            objects.add(parts[2].replace("~1", "/").replace("~0", "~"))
        elif len(parts) >= 3 and parts[1] == "relations" and parts[2].isdigit():
            relations.add(int(parts[2]))
        else:
            return None
    return frozenset(objects), frozenset(relations)


def _validate_hierarchy(objects: dict[str, Any], diagnostics: list[Diagnostic],
                        skip: frozenset[str] = frozenset()) -> dict[str, list[str]]:
    """Validate the single Project containment graph and return its ordered children.

    An object in `skip` failed the schema: it stays a known id but its own fields are not read."""
    children: dict[str, list[str]] = {object_id: [] for object_id in objects}
    for object_id, item in objects.items():
        if object_id in skip:
            continue
        parent = item.get("parent")
        if parent is None:
            continue
        path = f"/objects/{object_id}/parent"
        if parent not in objects:
            diagnostics.append(Diagnostic("E_PARENT_NOT_FOUND", unknown_id_message("parent object", parent, tuple(objects)), path))
            continue
        if parent == object_id:
            diagnostics.append(Diagnostic("E_SELF_PARENT", "Object cannot be its own parent", path))
            continue
        children[parent].append(object_id)

    codes: dict[str, str] = {}
    for object_id, item in objects.items():
        if object_id in skip:
            continue
        code = item.get("wbsCode")
        if code is None:
            continue
        if code in codes:
            diagnostics.append(Diagnostic("E_DUPLICATE_WBS_CODE", "Explicit WBS code must be unique", f"/objects/{object_id}/wbsCode"))
        else:
            codes[code] = object_id

    states: dict[str, int] = {}
    reported: set[str] = set()

    def visit(object_id: str) -> None:
        state = states.get(object_id, 0)
        if state == 1:
            if object_id not in reported:
                diagnostics.append(Diagnostic("E_PARENT_CYCLE", "Parent references must be acyclic", f"/objects/{object_id}/parent"))
                reported.add(object_id)
            return
        if state == 2:
            return
        states[object_id] = 1
        parent = None if object_id in skip else objects[object_id].get("parent")
        if parent in objects and parent != object_id:
            visit(parent)
        states[object_id] = 2

    for object_id in objects:
        visit(object_id)
    return children


def _rollup_syntax_diagnostics(project: dict[str, Any]) -> list[Diagnostic]:
    """Name malformed rollup declarations instead of leaking a generic schema error."""
    diagnostics: list[Diagnostic] = []
    objects = project.get("objects", {})
    if not isinstance(objects, dict):
        return diagnostics
    for object_id, item in objects.items():
        if not isinstance(item, dict):
            continue
        schedule = item.get("schedule")
        if not isinstance(schedule, dict) or schedule.get("mode") != "rollup":
            continue
        if set(schedule) != {"mode"}:
            diagnostics.append(Diagnostic("E_ROLLUP_SCHEDULE", "Rollup schedule only permits mode: rollup", f"/objects/{object_id}/schedule"))
    return diagnostics


def _resolve_calendar_id(item: dict[str, Any], project: dict[str, Any]) -> str | None:
    return item.get("calendar") or project.get("project", {}).get("calendar")


def _has_derivation_source(object_id: str, schedule: dict[str, Any], project: dict[str, Any]) -> bool:
    """A derived point needs something to derive from: a relation into its `at` or a minimum date."""
    if "min" in schedule.get("constraints", {}).get("at", {}):
        return True
    return any(relation["to"]["object"] == object_id and relation["to"]["endpoint"] == "at"
               for relation in project.get("relations", []))


def _schedule_endpoints(schedule: dict[str, Any]) -> frozenset[str]:
    if schedule.get("mode") in {"fixed-point", "scheduled-point"}:
        return frozenset({"at"})
    return frozenset({"start", "end"})


def _schema_value(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _schema_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_schema_value(item) for item in value]
    return value
