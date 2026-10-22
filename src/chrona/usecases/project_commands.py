"""Typed commands on a raw Project file (``project.yaml``) above the shared transaction port (#1892 row 1).

``apply_authoring_command`` edits the compact guided workspace. This module is the same revision-bound command
family for the file the skill, ``validate_project``, ``schedule_project`` and ``render_draft`` read: one command is
prepared against the parsed Project, the candidate is validated by the Project schema and the Core rules, and only
a valid candidate is handed to the locked transaction (compare-and-set, receipt ledger, atomic replace). A date
that contradicts a dependency and a dependency cycle are not write-time errors: ``schedule_project`` owns them.
The file is rewritten as canonical YAML, so comments and flow style in it are not kept.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from chrona.core.diagnostics import Diagnostic
from chrona.core.identity import content_identity
from chrona.core.validation import validate_project
from chrona.extensions.profiles import check_project_extensions
from chrona.storage.file_transaction import PreparedFileMutation

COMMAND_VERSION = "chrona/project-command/v0.1"
RESULT_VERSION = "chrona/project-command-result/v0.1"
MAX_ROWS = 8


def parse_project_command(path: Path) -> dict[str, Any]:
    """Read a command file and refuse it with the schema's pointer when it breaks ``project-command/v0.1``."""
    from chrona.resources import safe_load, schema_validator
    from chrona.schema_diagnostics import explain_errors
    value = safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("E_PROJECT_COMMAND_SCHEMA: expected object")
    errors = tuple(schema_validator("project-command-v0.1.schema.yaml").iter_errors(value))
    if errors:
        violation = explain_errors(
            errors, resource_kind="project-command",
            resource_identity=value.get("commandId") if isinstance(value.get("commandId"), str) else None,
        )
        raise ValueError(f"E_PROJECT_COMMAND_SCHEMA: {violation.pointer}: {violation.message}")
    return value


def project_revision(project: Mapping[str, Any]) -> str:
    """The CAS precondition of a parsed Project: its canonical content identity (dates and strings alike)."""
    return content_identity(project)


def apply_project_command(project_path: Path, command: dict[str, Any], *, transact: Any) -> dict[str, Any]:
    """Prepare source intent and delegate all publication to the shared transaction."""
    def prepare(canonical_path: Path, current: dict[str, Any]) -> PreparedFileMutation:
        return prepare_project_command(canonical_path, current, command)

    def reject(code: str, observed_identity: str, detail: str = "", **fields: Any) -> dict[str, Any]:
        # The shared transaction words its refusals for a workspace; this file is a Project.
        detail = detail.replace("workspace revision", "Project revision").replace("canonical workspace filename", "Project file name")
        return _rejected(command, code, observed_identity, detail=detail, fields=fields)

    return transact(project_path, command, prepare=prepare, reject=reject, verify_receipt=verify_project_receipt)


def prepare_project_command(
    canonical_path: Path, current: dict[str, Any], command: dict[str, Any],
) -> PreparedFileMutation:
    """Return complete validated bytes and the exact result without any canonical write."""
    base = project_revision(current)
    if command["target"]["path"] != canonical_path.name:
        return _prepared_rejection(command, "E_AUTHORING_TARGET_MISMATCH", base,
                                   detail=f"target path must name the Project file {canonical_path.name!r}")
    if command["baseRevision"] != base:
        return _prepared_rejection(command, "E_AUTHORING_BASE_REVISION", base)
    candidate = deepcopy(current)
    refusal = _apply(candidate, command)
    if refusal is not None:
        code, details = refusal
        return PreparedFileMutation(files={}, result_revision=None, result=_rejected(command, code, base, details=details))
    found = _candidate_diagnostics(candidate, command, canonical_path.parent)
    if found:
        return PreparedFileMutation(files={}, result_revision=None, result=_rejected_rows(command, base, found))
    next_revision = project_revision(candidate)
    payload = yaml.safe_dump(candidate, allow_unicode=True, sort_keys=False).encode("utf-8")
    result = {
        "version": RESULT_VERSION, "status": "accepted", "commandId": command["commandId"],
        "commandBaseRevision": command["baseRevision"], "projectRevision": base,
        "resultRevision": next_revision, "diagnostics": [],
    }
    return PreparedFileMutation(files={canonical_path.name: payload}, result_revision=next_revision, result=result)


def verify_project_receipt(
    request: dict[str, Any], result: dict[str, Any], before_identity: str, after_identity: str,
) -> None:
    """Validate persisted replay data before the transaction returns it as authoritative."""
    from chrona.resources import schema_validator

    request_errors = tuple(schema_validator("project-command-v0.1.schema.yaml").iter_errors(request))
    result_errors = tuple(schema_validator("project-command-result-v0.1.schema.yaml").iter_errors(result))
    if request_errors or result_errors:
        raise ValueError("E_AUTHORING_REPLAY_UNAVAILABLE: retained request or result violates its schema")
    if (
        result["status"] != "accepted"
        or result["commandId"] != request["commandId"]
        or result["commandBaseRevision"] != request["baseRevision"]
        or result["projectRevision"] != before_identity
        or result["resultRevision"] != after_identity
    ):
        raise ValueError("E_AUTHORING_REPLAY_UNAVAILABLE: retained result identities do not match the accepted request")


# --- the commands --------------------------------------------------------------------------------------------

_MAPPING_MEMBERS = {
    "setObject": ("objects", "object"), "setCalendar": ("calendars", "calendar"),
    "setEntity": ("entities", "entity"), "setFieldRole": ("fieldRoles", "binding"),
}
"""Command type -> (Project member it upserts into, payload key that holds the value)."""


def _key(command: dict[str, Any]) -> str:
    """The key a mapping-member command writes: the field role for ``setFieldRole``, the ``id`` otherwise."""
    return command["payload"]["role" if command["type"] == "setFieldRole" else "id"]


def _apply(candidate: dict[str, Any], command: dict[str, Any]) -> tuple[str, list[str]] | None:
    """Edit ``candidate`` in place; return ``(code, details)`` when the command itself is refused."""
    payload, command_type = command["payload"], command["type"]
    if command_type in _MAPPING_MEMBERS:
        member, value_key = _MAPPING_MEMBERS[command_type]
        table = candidate.get(member)
        if table is None:
            table = candidate[member] = {}
        if not isinstance(table, dict):
            return "E_PROJECT_COMMAND", [f"/payload: the Project's {member} member is not a mapping; fix the file first"]
        table[_key(command)] = deepcopy(payload[value_key])
        return None
    if command_type == "setRelation":
        relations = candidate.get("relations")
        if relations is None:
            relations = candidate["relations"] = []
        if not isinstance(relations, list):
            return "E_PROJECT_COMMAND", ["/payload: the Project's relations member is not a list; fix the file first"]
        relation = deepcopy(payload["relation"])
        index = _relation_index(relations, relation)
        if index is None:
            relations.append(relation)
        else:
            relations[index] = relation
        return None
    if command_type == "removeRelation":
        relations, relation_id = candidate.get("relations"), payload["id"]
        if not isinstance(relations, list) or _relation_index(relations, {"id": relation_id}) is None:
            known = ", ".join(str(item["id"]) for item in (relations if isinstance(relations, list) else ())
                              if isinstance(item, dict) and isinstance(item.get("id"), str))
            return "E_PROJECT_RELATION_MISSING", [
                f"/payload/id: the Project has no relation with id {relation_id!r}"
                + (f"; its relation ids are {known[:200]}" if known else "; only a relation that declares an id can be removed")]
        relations[:] = [item for item in relations if not (isinstance(item, dict) and item.get("id") == relation_id)]
        if not relations:
            del candidate["relations"]
        return None
    if command_type == "removeCalendar":
        calendars, calendar_id = candidate.get("calendars"), payload["id"]
        if not isinstance(calendars, dict) or calendar_id not in calendars:
            known = ", ".join(sorted(map(str, calendars))[:10]) if isinstance(calendars, dict) else ""
            return "E_PROJECT_CALENDAR_MISSING", [
                f"/payload/id: the Project has no calendar {calendar_id!r}" + (f"; its calendars include {known}" if known else "")]
        users = _calendar_users(candidate, calendar_id)
        if users:
            return "E_PROJECT_CALENDAR_REFERENCED", [
                f"/payload/id: calendar {calendar_id!r} is still used by {'; '.join(users[:MAX_ROWS])}; "
                "point those at another calendar first"]
        del calendars[calendar_id]
        return None
    objects = candidate.get("objects")
    if command_type == "removeObject":
        object_id = payload["id"]
        if not isinstance(objects, dict) or object_id not in objects:
            known = ", ".join(sorted(map(str, objects))[:10]) if isinstance(objects, dict) else ""
            return "E_PROJECT_OBJECT_MISSING", [
                f"/payload/id: the Project has no object {object_id!r}" + (f"; its objects include {known}" if known else "")]
        users = _referrers(candidate, object_id)
        if users:
            return "E_PROJECT_OBJECT_REFERENCED", [
                f"/payload/id: object {object_id!r} is still named by {'; '.join(users[:MAX_ROWS])}; "
                "remove or change those first"]
        del objects[object_id]
        return None
    return "E_PROJECT_COMMAND", [f"/type: unsupported command type {command_type!r}"]


def _relation_index(relations: list[Any], relation: Mapping[str, Any]) -> int | None:
    """Index of the relation a set command replaces: the first with the same declared ``id``, or, for a relation
    without an id, an identical one (so resending it does not duplicate the edge)."""
    declared = relation.get("id")
    for index, item in enumerate(relations):
        if not isinstance(item, dict):
            continue
        if isinstance(declared, str) and declared:
            if item.get("id") == declared:
                return index
        elif item == relation:
            return index
    return None


def _calendar_users(project: Mapping[str, Any], calendar_id: str) -> list[str]:
    """What still names a calendar: the Project default, an object's ``calendar`` and a relation's ``lag.calendar``."""
    found: list[str] = []
    meta = project.get("project")
    if isinstance(meta, dict) and meta.get("calendar") == calendar_id:
        found.append("the Project default calendar (project.calendar)")
    for object_id, item in (project.get("objects") or {}).items():
        if isinstance(item, dict) and item.get("calendar") == calendar_id:
            found.append(f"object {object_id!r} (calendar)")
    relations = project.get("relations")
    for index, relation in enumerate(relations if isinstance(relations, list) else ()):
        lag = relation.get("lag") if isinstance(relation, dict) else None
        if isinstance(lag, dict) and lag.get("calendar") == calendar_id:
            found.append(f"relation {index} (lag.calendar)")
    return found


def _referrers(project: Mapping[str, Any], object_id: str) -> list[str]:
    """What still names an object: relation endpoints, ``parent`` and ``attachesTo`` of other objects."""
    found: list[str] = []
    relations = project.get("relations")
    for index, relation in enumerate(relations if isinstance(relations, list) else ()):
        for side in ("from", "to"):
            endpoint = relation.get(side) if isinstance(relation, dict) else None
            if isinstance(endpoint, dict) and endpoint.get("object") == object_id:
                found.append(f"relation {index} ({side})")
    for other_id, other in (project.get("objects") or {}).items():
        if other_id == object_id or not isinstance(other, dict):
            continue
        for member in ("parent", "attachesTo"):
            if other.get(member) == object_id:
                found.append(f"object {other_id!r} ({member})")
    return found


# --- validation of the candidate -----------------------------------------------------------------------------

def validate_project_candidate(project: dict[str, Any], base_dir: Path | None = None) -> list[Diagnostic]:
    """The Project schema and Core rules, without the dependency-cycle and scheduling checks (those stay with
    ``validate_project`` and ``schedule_project``)."""
    if not isinstance(project, dict):
        return [Diagnostic("E_SCHEMA", "a Project must be a YAML mapping with version, project and objects", "/")]
    extensions = (check_project_extensions(project, base_dir=base_dir)
                  if base_dir is not None and isinstance(project.get("extensions"), list) else None)
    return list(validate_project(project, extension_diagnostics=extensions))


def _own_location(candidate: Mapping[str, Any], command: dict[str, Any]) -> tuple[str, str] | None:
    """``(Project pointer, command pointer)`` of the value a set command wrote, so a finding inside it leads with the payload."""
    command_type = command["type"]
    if command_type == "setRelation":
        relations = candidate.get("relations")
        index = _relation_index(relations, command["payload"]["relation"]) if isinstance(relations, list) else None
        return (f"/relations/{index}", "/payload/relation") if index is not None else None
    if command_type in _MAPPING_MEMBERS:
        member, value_key = _MAPPING_MEMBERS[command_type]
        return f"/{member}/{_key(command)}", f"/payload/{value_key}"
    return None


def _candidate_diagnostics(candidate: dict[str, Any], command: dict[str, Any], base_dir: Path) -> list[tuple[str, str, str]]:
    """``(code, command pointer, message)`` for each finding; a finding outside the command's own value keeps its Project pointer."""
    location = _own_location(candidate, command)
    rows: list[tuple[str, str, str]] = []
    for item in validate_project_candidate(candidate, base_dir):
        path = item.path or "/"
        if location is not None and (path == location[0] or path.startswith(location[0] + "/")):
            rows.append((item.id, location[1] + path[len(location[0]):], item.message))
        else:
            rows.append((item.id, "/payload", f"Project {path}: {item.message}"))
    return rows


# --- results --------------------------------------------------------------------------------------------------

def _prepared_rejection(command: dict[str, Any], code: str, base: str, *, detail: str = "") -> PreparedFileMutation:
    return PreparedFileMutation(files={}, result_revision=None, result=_rejected(command, code, base, detail=detail))


def _rejected_rows(command: dict[str, Any], base: str, rows: list[tuple[str, str, str]]) -> dict[str, Any]:
    return _result(command, base, [{"code": code, "detail": f"{pointer}: {message}"} for code, pointer, message in rows[:MAX_ROWS]])


def _rejected(command: dict[str, Any], code: str, base: str, detail: str = "",
              details: list[str] | None = None, fields: dict[str, Any] | None = None) -> dict[str, Any]:
    code, _, inline_detail = code.partition(":")
    detail = detail or inline_detail.strip()
    diagnostic: dict[str, Any] = {"code": code}
    if detail:
        diagnostic["detail"] = detail
    if code == "E_AUTHORING_BASE_REVISION":
        diagnostic |= {
            "expectedRevision": base, "receivedRevision": command.get("baseRevision"),
            "detail": (f"Project revision expected {base}; command declared {command.get('baseRevision')}; "
                       "read the current revision with validate_project (projectRevision) and retry"),
        }
    diagnostic |= fields or {}
    rows = [{"code": code, "detail": item} for item in details] if details else [diagnostic]
    return _result(command, base, rows)


def _result(command: dict[str, Any], base: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "version": RESULT_VERSION, "status": "rejected",
        "commandId": command.get("commandId"), "commandBaseRevision": command.get("baseRevision"),
        "projectRevision": base, "resultRevision": None, "diagnostics": rows,
    }


# --- create_project -------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class NewProject:
    """A validated Project ready for exclusive publication: its canonical bytes and revision."""

    payload: bytes
    revision: str


def prepare_new_project(project: Mapping[str, Any]) -> NewProject | tuple[Diagnostic, ...]:
    """Validate a complete Project mapping and return its bytes, or the diagnostics that refuse it."""
    value = deepcopy(dict(project)) if isinstance(project, Mapping) else project
    found = validate_project_candidate(value)
    if found:
        return tuple(found)
    return NewProject(yaml.safe_dump(value, allow_unicode=True, sort_keys=False).encode("utf-8"), project_revision(value))
