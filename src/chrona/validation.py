from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from .diagnostics import Diagnostic
from .temporal import Calendar, TemporalError, as_date, is_scheduled_amount, parse_amount


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "timeline-design" / "docs" / "schemas" / "project-v0.1.schema.yaml"


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def validate_project(project: dict[str, Any], schema_path: Path = SCHEMA_PATH) -> list[Diagnostic]:
    """Run structural validation first, then Core rules which Schema cannot express."""
    diagnostics: list[Diagnostic] = []
    schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    for error in jsonschema.Draft202012Validator(schema).iter_errors(project):
        path = "/" + "/".join(str(part) for part in error.absolute_path)
        diagnostics.append(Diagnostic("E_SCHEMA", error.message, path or "/"))
    if diagnostics:
        return diagnostics

    calendars = project.get("calendars", {})
    objects = project.get("objects", {})
    for calendar_id, raw in calendars.items():
        try:
            Calendar.from_mapping(raw)
        except (KeyError, TemporalError, ValueError) as exc:
            diagnostics.append(Diagnostic("E_SCHEMA", str(exc), f"/calendars/{calendar_id}"))

    project_calendar = project.get("project", {}).get("calendar")
    if project_calendar and project_calendar not in calendars:
        diagnostics.append(Diagnostic("E_REFERENCE", "Unknown project calendar", "/project/calendar"))

    for object_id, item in objects.items():
        path = f"/objects/{object_id}"
        if item.get("calendar") and item["calendar"] not in calendars:
            diagnostics.append(Diagnostic("E_REFERENCE", "Unknown object calendar", path + "/calendar"))
        schedule = item["schedule"]
        mode = schedule["mode"]
        if mode == "fixed" and "start" in schedule:
            try:
                if as_date(schedule["start"]) >= as_date(schedule["end"]):
                    diagnostics.append(Diagnostic("E_INVALID_SPAN", "Fixed span must satisfy start < end", path + "/schedule"))
            except TemporalError as exc:
                diagnostics.append(Diagnostic("E_SCHEMA", str(exc), path + "/schedule"))
        if mode == "scheduled":
            amount = schedule["amount"]
            if not is_scheduled_amount(amount):
                diagnostics.append(Diagnostic("E_INVALID_AMOUNT", "Scheduled spans allow only positive d, w, or wd", path + "/schedule/amount"))
            if amount.endswith("wd") and not _resolve_calendar_id(item, project):
                diagnostics.append(Diagnostic("E_CALENDAR_REQUIRED", "WorkPeriod schedule has no calendar", path))

    for index, relation in enumerate(project.get("relations", [])):
        path = f"/relations/{index}"
        for side in ("from", "to"):
            ref = relation[side]
            if ref["object"] not in objects:
                diagnostics.append(Diagnostic("E_REFERENCE", f"Unknown {side} object", path + f"/{side}/object"))
        lag = relation.get("lag")
        if lag:
            value = lag if isinstance(lag, str) else lag["value"]
            try:
                parse_amount(value)
                if value.endswith("wd"):
                    lag_calendar = lag.get("calendar") if isinstance(lag, dict) else None
                    target = objects.get(relation["to"]["object"], {})
                    if lag_calendar and lag_calendar not in calendars:
                        diagnostics.append(Diagnostic("E_REFERENCE", "Unknown relation calendar", path + "/lag/calendar"))
                    elif not lag_calendar and not _resolve_calendar_id(target, project):
                        diagnostics.append(Diagnostic("E_CALENDAR_REQUIRED", "WorkPeriod lag has no calendar", path + "/lag"))
            except TemporalError as exc:
                diagnostics.append(Diagnostic("E_INVALID_AMOUNT", str(exc), path + "/lag"))
    return diagnostics


def _resolve_calendar_id(item: dict[str, Any], project: dict[str, Any]) -> str | None:
    return item.get("calendar") or project.get("project", {}).get("calendar")
