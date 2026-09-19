from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from .diagnostics import Diagnostic
from .profiles import resolve_package_manifests, validate_profiles
from .extension_registry import PackageRegistry, resolve_evaluation_packages
from .revision_store import LocalSnapshotReader
from .temporal import Calendar, TemporalError, as_date, is_scheduled_amount, parse_amount


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "timeline-design" / "docs" / "schemas" / "project-v0.1.schema.yaml"


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def validate_project(project: dict[str, Any], schema_path: Path = SCHEMA_PATH, package_manifests: dict[str, dict[str, Any]] | None = None, package_reader: LocalSnapshotReader | None = None, package_registry: PackageRegistry | None = None, package_references: list[dict[str, Any]] | None = None) -> list[Diagnostic]:
    """Run structural validation first, then Core rules which Schema cannot express."""
    diagnostics: list[Diagnostic] = []
    schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    # PyYAML resolves unquoted ISO dates to ``date`` objects, while JSON Schema
    # describes the canonical JSON-compatible representation as strings. Keep
    # the semantic value intact for scheduling, but validate its serialization.
    for error in jsonschema.Draft202012Validator(schema).iter_errors(_schema_value(project)):
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
    if package_reader is not None:
        package_manifests, resolution_diagnostics = resolve_package_manifests(project, package_reader)
        diagnostics.extend(resolution_diagnostics)
    if package_registry is not None and package_references is not None:
        package_manifests, registry_diagnostics = resolve_evaluation_packages(package_registry, package_references, project["version"])
        diagnostics.extend(Diagnostic(item, "Extension lifecycle resolution failed", "/extensions") for item in registry_diagnostics)
    diagnostics.extend(validate_profiles(project, package_manifests))
    return diagnostics


def _resolve_calendar_id(item: dict[str, Any], project: dict[str, Any]) -> str | None:
    return item.get("calendar") or project.get("project", {}).get("calendar")


def _schema_value(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _schema_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_schema_value(item) for item in value]
    return value
