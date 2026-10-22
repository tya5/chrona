"""Relation, calendar, entity and field-role commands of apply_project_command (#1892 row 1, item 2)."""
from __future__ import annotations

import copy
from pathlib import Path

import yaml

from chrona.app.agent_tools import call_tool
from chrona.app.agent_workspace import WorkspaceScope
from chrona.resources import schema_validator

PROJECT = {
    "version": "timeline/v0.7",
    "project": {"id": "launch", "calendar": "team"},
    "calendars": {"team": {"working_days": ["mon", "tue", "wed", "thu", "fri"]},
                  "ops": {"working_days": ["mon", "tue", "wed", "thu", "fri", "sat"]}},
    "objects": {
        "design": {"type": "task", "schedule": {"mode": "fixed-span", "start": "2026-11-02", "end": "2026-11-06"}},
        "build": {"type": "task", "schedule": {"mode": "scheduled", "amount": "5wd"}},
        "audit": {"type": "task", "calendar": "ops", "schedule": {"mode": "scheduled", "amount": "3wd"}},
    },
}


def _call(root: Path, name: str, arguments: dict):
    return call_tool(WorkspaceScope(root), name, arguments, allow_write=True)


def _created(root: Path, project: dict | None = None) -> str:
    result = _call(root, "create_project", {"file": "project.yaml", "project": copy.deepcopy(project or PROJECT)})
    assert result.structured["status"] == "ok", result.structured
    return result.structured["projectRevision"]


def _apply(root: Path, command_id: str, command_type: str, payload: dict, base: str):
    return _call(root, "apply_project_command", {"project": "project.yaml", "command": {
        "version": "chrona/project-command/v0.1", "commandId": command_id, "type": command_type,
        "target": {"kind": "project", "path": "project.yaml"}, "baseRevision": base, "payload": payload}}).structured


def _saved(root: Path) -> dict:
    return yaml.safe_load((root / "project.yaml").read_text(encoding="utf-8"))


def _relation(**extra) -> dict:
    return {"type": "dependency", "from": {"object": "design", "endpoint": "end"},
            "to": {"object": "build", "endpoint": "start"}, **extra}


def test_set_relation_appends_replaces_by_id_and_the_plan_schedules(tmp_path):
    revision = _created(tmp_path)
    first = _apply(tmp_path, "r1", "setRelation", {"relation": _relation(id="d-b")}, revision)
    assert first["status"] == "ok" and first["projectResult"]["status"] == "accepted"
    second = _apply(tmp_path, "r2", "setRelation", {"relation": _relation(id="d-b", lag="2d")},
                    first["projectResult"]["resultRevision"])
    assert second["status"] == "ok"
    assert _saved(tmp_path)["relations"] == [_relation(id="d-b", lag="2d")]
    third = _apply(tmp_path, "r3", "setRelation", {"relation": {**_relation(), "to": {"object": "audit", "endpoint": "start"}}},
                   second["projectResult"]["resultRevision"])
    assert len(_saved(tmp_path)["relations"]) == 2
    # an identical id-less relation is not duplicated
    again = _apply(tmp_path, "r4", "setRelation", {"relation": {**_relation(), "to": {"object": "audit", "endpoint": "start"}}},
                   third["projectResult"]["resultRevision"])
    assert again["status"] == "ok" and len(_saved(tmp_path)["relations"]) == 2
    assert _call(tmp_path, "schedule_project", {"project": "project.yaml"}).structured["status"] == "ok"


def test_set_relation_with_a_dangling_endpoint_is_rejected_at_the_relation_pointer_and_writes_nothing(tmp_path):
    revision = _created(tmp_path)
    before = (tmp_path / "project.yaml").read_bytes()
    bad = _relation(id="x")
    bad["to"] = {"object": "ship", "endpoint": "start"}
    result = _apply(tmp_path, "r1", "setRelation", {"relation": bad}, revision)
    assert result["status"] == "rejected"
    row = result["diagnostics"][0]
    assert row["code"] == "E_REFERENCE" and row["sourceRef"] == "/payload/relation/to/object"
    assert "ship" in row["message"]
    assert (tmp_path / "project.yaml").read_bytes() == before


def test_set_relation_schema_violation_names_the_payload_node(tmp_path):
    revision = _created(tmp_path)
    bad = _relation()
    bad["type"] = "blocks"
    result = _apply(tmp_path, "r1", "setRelation", {"relation": bad}, revision)
    assert result["status"] == "rejected"
    assert result["diagnostics"][0]["sourceRef"].startswith("/payload/relation")


def test_remove_relation_by_id_and_its_refusals(tmp_path):
    revision = _created(tmp_path)
    added = _apply(tmp_path, "r1", "setRelation", {"relation": _relation(id="d-b")}, revision)["projectResult"]["resultRevision"]
    unknown = _apply(tmp_path, "r2", "removeRelation", {"id": "nope"}, added)
    assert unknown["diagnostics"][0]["code"] == "E_PROJECT_RELATION_MISSING"
    assert unknown["diagnostics"][0]["sourceRef"] == "/payload/id" and "d-b" in unknown["diagnostics"][0]["message"]
    removed = _apply(tmp_path, "r3", "removeRelation", {"id": "d-b"}, added)
    assert removed["status"] == "ok" and "relations" not in _saved(tmp_path)
    assert _apply(tmp_path, "r4", "removeRelation", {"id": "d-b"}, removed["projectResult"]["resultRevision"]
                  )["diagnostics"][0]["code"] == "E_PROJECT_RELATION_MISSING"


def test_set_calendar_adds_and_replaces_and_a_bad_calendar_names_its_pointer(tmp_path):
    revision = _created(tmp_path)
    added = _apply(tmp_path, "c1", "setCalendar", {"id": "jp", "calendar": {
        "title": "Japan", "working_days": ["mon", "tue"], "exceptions": [{"date": "2026-11-03", "working": False}]}}, revision)
    assert added["status"] == "ok" and _saved(tmp_path)["calendars"]["jp"]["title"] == "Japan"
    replaced = _apply(tmp_path, "c2", "setCalendar", {"id": "jp", "calendar": {"working_days": ["fri"]}},
                      added["projectResult"]["resultRevision"])
    assert replaced["status"] == "ok" and _saved(tmp_path)["calendars"]["jp"] == {"working_days": ["fri"]}
    bad = _apply(tmp_path, "c3", "setCalendar", {"id": "jp", "calendar": {"working_days": []}},
                 replaced["projectResult"]["resultRevision"])
    assert bad["status"] == "rejected" and bad["diagnostics"][0]["sourceRef"].startswith("/payload/calendar")
    assert _saved(tmp_path)["calendars"]["jp"] == {"working_days": ["fri"]}


def test_remove_calendar_is_refused_while_the_project_an_object_or_a_lag_uses_it(tmp_path):
    project = copy.deepcopy(PROJECT)
    project["calendars"]["lagcal"] = {"working_days": ["mon"]}
    project["calendars"]["spare"] = {"working_days": ["tue"]}
    project["relations"] = [_relation(lag={"value": "1wd", "calendar": "lagcal"})]
    revision = _created(tmp_path, project)
    before = (tmp_path / "project.yaml").read_bytes()
    for index, (name, expect) in enumerate((("team", "project.calendar"), ("ops", "object 'audit'"), ("lagcal", "relation 0"))):
        refused = _apply(tmp_path, f"x{index}", "removeCalendar", {"id": name}, revision)
        row = refused["diagnostics"][0]
        assert refused["status"] == "rejected" and row["code"] == "E_PROJECT_CALENDAR_REFERENCED", refused
        assert row["sourceRef"] == "/payload/id" and expect in row["message"]
    assert (tmp_path / "project.yaml").read_bytes() == before
    missing = _apply(tmp_path, "x3", "removeCalendar", {"id": "nope"}, revision)
    assert missing["diagnostics"][0]["code"] == "E_PROJECT_CALENDAR_MISSING" and "spare" in missing["diagnostics"][0]["message"]
    removed = _apply(tmp_path, "x4", "removeCalendar", {"id": "spare"}, revision)
    assert removed["status"] == "ok" and "spare" not in _saved(tmp_path)["calendars"]


def test_set_entity_and_set_field_role_upsert_and_validate(tmp_path):
    revision = _created(tmp_path)
    entity = _apply(tmp_path, "e1", "setEntity", {"id": "ana", "entity": {"type": "person", "title": "Ana", "fields": {"team": "core"}}}, revision)
    assert entity["status"] == "ok"
    role = _apply(tmp_path, "f1", "setFieldRole", {"role": "responsible", "binding": "owner"}, entity["projectResult"]["resultRevision"])
    assert role["status"] == "ok"
    saved = _saved(tmp_path)
    assert saved["entities"]["ana"]["title"] == "Ana" and saved["fieldRoles"] == {"responsible": "owner"}
    rebound = _apply(tmp_path, "f2", "setFieldRole", {"role": "responsible", "binding": "lead"}, role["projectResult"]["resultRevision"])
    assert rebound["status"] == "ok" and _saved(tmp_path)["fieldRoles"] == {"responsible": "lead"}
    bad_entity = _apply(tmp_path, "e2", "setEntity", {"id": "ana", "entity": {"title": "no type"}}, rebound["projectResult"]["resultRevision"])
    assert bad_entity["status"] == "rejected" and bad_entity["diagnostics"][0]["sourceRef"].startswith("/payload/entity")
    unknown_role = _apply(tmp_path, "f3", "setFieldRole", {"role": "boss", "binding": "x"}, rebound["projectResult"]["resultRevision"])
    assert unknown_role["status"] == "rejected" and unknown_role["diagnostics"][0]["code"] == "E_MCP_INPUT_INVALID"
    assert unknown_role["diagnostics"][0]["sourceRef"] == "/command/payload/role"


def test_new_results_replay_and_validate_against_the_result_schema(tmp_path):
    revision = _created(tmp_path)
    first = _apply(tmp_path, "r1", "setRelation", {"relation": _relation(id="d-b")}, revision)
    again = _apply(tmp_path, "r1", "setRelation", {"relation": _relation(id="d-b")}, revision)
    assert again["projectResult"]["replayed"] is True
    validator = schema_validator("project-command-result-v0.1.schema.yaml")
    assert not list(validator.iter_errors(first["projectResult"]))
    rejected = _apply(tmp_path, "r2", "removeCalendar", {"id": "team"}, first["projectResult"]["resultRevision"])
    assert not list(validator.iter_errors(rejected["projectResult"]))
