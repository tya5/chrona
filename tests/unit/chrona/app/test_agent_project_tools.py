"""The raw Project write tools: create_project and apply_project_command (#1892 row 1)."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from chrona.app.agent_tools import call_tool, registry_document
from chrona.app.agent_workspace import WorkspaceScope

PROJECT = {
    "version": "timeline/v0.7",
    "project": {"id": "launch", "title": "Launch", "calendar": "team"},
    "calendars": {"team": {"working_days": ["mon", "tue", "wed", "thu", "fri"]}},
    "objects": {"design": {"type": "task", "title": "Design",
                           "schedule": {"mode": "fixed-span", "start": "2026-11-02", "end": "2026-11-06"}}},
}


def _command(command_id: str, command_type: str, payload: dict, base: str, path: str = "project.yaml") -> dict:
    return {"version": "chrona/project-command/v0.1", "commandId": command_id, "type": command_type,
            "target": {"kind": "project", "path": path}, "baseRevision": base, "payload": payload}


def _call(root: Path, name: str, arguments: dict, *, write: bool = True):
    return call_tool(WorkspaceScope(root), name, arguments, allow_write=write)


def _created(root: Path, file: str = "project.yaml") -> str:
    result = _call(root, "create_project", {"file": file, "project": copy.deepcopy(PROJECT)})
    assert result.structured["status"] == "ok", result.structured
    return result.structured["projectRevision"]


def _apply(root: Path, command: dict, project: str = "project.yaml"):
    return _call(root, "apply_project_command", {"project": project, "command": command})


def _gate(at_least: str = "2026-11-10") -> dict:
    return {"type": "gate", "title": "Go live", "schedule": {"mode": "scheduled-point", "constraints": {"at": {"min": at_least}}}}


def test_registry_lists_both_tools_as_writers_with_closed_inputs():
    tools = {tool["name"]: tool for tool in registry_document()["tools"]}
    assert registry_document()["toolSet"] == "chrona/agent-tools/v0.9"
    for name in ("create_project", "apply_project_command"):
        assert tools[name]["annotations"] == {
            "readOnlyHint": False, "destructiveHint": True, "idempotentHint": True, "openWorldHint": False}
        assert tools[name]["inputSchema"]["additionalProperties"] is False
    assert tools["apply_project_command"]["inputSchema"]["required"] == ["project", "command"]
    assert tools["create_project"]["inputSchema"]["required"] == ["file", "project"]


def test_both_tools_are_refused_before_any_file_is_opened_without_the_write_gate(tmp_path):
    for name, arguments in (("create_project", {"file": "p.yaml", "project": PROJECT}),
                            ("apply_project_command", {"project": "missing.yaml", "command": "missing-command.yaml"})):
        result = _call(tmp_path, name, arguments, write=False)
        assert result.structured["status"] == "failed" and result.is_error
        assert result.structured["diagnostics"][0]["code"] == "E_MCP_WRITE_DISABLED"
    assert list(tmp_path.iterdir()) == []


def test_create_project_writes_a_valid_file_returns_its_revision_and_never_overwrites(tmp_path):
    (tmp_path / "plans").mkdir()
    revision = _created(tmp_path, "plans/project.yaml")
    written = yaml.safe_load((tmp_path / "plans/project.yaml").read_text(encoding="utf-8"))
    assert written == PROJECT
    validated = _call(tmp_path, "validate_project", {"project": "plans/project.yaml"}, write=False).structured
    assert validated["status"] == "ok" and validated["projectRevision"] == revision
    assert _call(tmp_path, "schedule_project", {"project": "plans/project.yaml"}, write=False).structured["status"] == "ok"
    before = (tmp_path / "plans/project.yaml").read_bytes()
    again = _call(tmp_path, "create_project", {"file": "plans/project.yaml", "project": PROJECT}).structured
    assert again["status"] == "failed"  # as create_workspace over an existing directory
    assert again["diagnostics"][0]["code"] == "E_PROJECT_EXISTS" and again["diagnostics"][0]["sourceRef"] == "/file"
    assert (tmp_path / "plans/project.yaml").read_bytes() == before
    assert sorted(path.name for path in (tmp_path / "plans").iterdir()) == ["project.yaml"]


def test_create_project_rejects_an_invalid_project_with_core_pointers_and_writes_nothing(tmp_path):
    broken = copy.deepcopy(PROJECT)
    broken["objects"]["design"]["schedule"] = {"mode": "scheduled", "amount": "3q"}
    result = _call(tmp_path, "create_project", {"file": "p.yaml", "project": broken}).structured
    assert result["status"] == "rejected"
    assert result["diagnostics"][0]["sourceRef"] == "/objects/design/schedule/amount"
    assert list(tmp_path.iterdir()) == []


def test_create_project_input_errors_name_the_node(tmp_path):
    for arguments, pointer in (({"file": "plan.txt", "project": PROJECT}, "/file"),
                               ({"file": "p.yaml", "project": {"project": {"id": "x"}}}, "/project")):
        result = _call(tmp_path, "create_project", arguments).structured
        assert result["status"] == "rejected" and result["diagnostics"][0]["code"] == "E_MCP_INPUT_INVALID"
        assert result["diagnostics"][0]["sourceRef"] == pointer
    assert list(tmp_path.iterdir()) == []


def test_set_object_adds_a_gate_a_working_day_task_and_a_deadline_and_the_plan_schedules(tmp_path):
    revision = _created(tmp_path)
    build = {"type": "task", "title": "Build", "deadline": "2026-11-20",
             "schedule": {"mode": "scheduled", "amount": "5wd", "constraints": {"end": {"max": "2026-11-27"}}}}
    first = _apply(tmp_path, _command("c1", "setObject", {"id": "build", "object": build}, revision)).structured
    assert first["status"] == "ok" and first["projectResult"]["status"] == "accepted"
    assert "replayed" not in first["projectResult"]
    second = _apply(tmp_path, _command("c2", "setObject", {"id": "go-live", "object": _gate()},
                                       first["projectResult"]["resultRevision"])).structured
    assert second["projectResult"]["projectRevision"] == first["projectResult"]["resultRevision"]
    saved = yaml.safe_load((tmp_path / "project.yaml").read_text(encoding="utf-8"))
    assert list(saved["objects"]) == ["design", "build", "go-live"]
    assert saved["objects"]["build"] == build and saved["objects"]["go-live"] == _gate()
    revalidated = _call(tmp_path, "validate_project", {"project": "project.yaml"}, write=False).structured
    assert revalidated["status"] == "ok" and revalidated["projectRevision"] == second["projectResult"]["resultRevision"]


def test_set_object_replaces_an_existing_id_in_place(tmp_path):
    revision = _created(tmp_path)
    replacement = {"type": "task", "title": "Design v2", "schedule": {"mode": "fixed-span", "start": "2026-11-03", "end": "2026-11-09"}}
    result = _apply(tmp_path, _command("c1", "setObject", {"id": "design", "object": replacement}, revision)).structured
    assert result["status"] == "ok"
    saved = yaml.safe_load((tmp_path / "project.yaml").read_text(encoding="utf-8"))
    assert saved["objects"] == {"design": replacement}


def test_a_schema_violation_in_the_object_is_rejected_at_its_command_pointer_and_writes_nothing(tmp_path):
    revision = _created(tmp_path)
    before = (tmp_path / "project.yaml").read_bytes()
    bad = {"type": "task", "colour": 1, "schedule": {"mode": "scheduled", "amount": "3q"}}
    result = _apply(tmp_path, _command("c1", "setObject", {"id": "build", "object": bad}, revision)).structured
    assert result["status"] == "rejected" and not result.get("projectResult", {}).get("resultRevision")
    pointers = {row["sourceRef"] for row in result["diagnostics"]}
    assert {"/payload/object", "/payload/object/schedule/amount"} <= pointers
    assert (tmp_path / "project.yaml").read_bytes() == before
    odd = _apply(tmp_path, _command("c2", "setObject", {"id": "build", "object": {"type": "task", "schedule": "5d"}}, revision)).structured
    assert odd["status"] == "rejected" and odd["diagnostics"][0]["sourceRef"] == "/payload/object/schedule"


def test_a_working_day_amount_without_a_calendar_is_a_core_rejection(tmp_path):
    project = copy.deepcopy(PROJECT)
    del project["calendars"], project["project"]["calendar"]
    created = _call(tmp_path, "create_project", {"file": "project.yaml", "project": project}).structured
    result = _apply(tmp_path, _command("c1", "setObject", {"id": "build", "object": {
        "type": "task", "schedule": {"mode": "scheduled", "amount": "5wd"}}}, created["projectRevision"])).structured
    assert result["status"] == "rejected"
    assert result["diagnostics"][0]["code"] == "E_CALENDAR_REQUIRED"
    assert result["diagnostics"][0]["sourceRef"] == "/payload/object"


def test_a_cycle_and_a_contradicted_date_are_not_write_errors_but_schedule_project_rejects_them(tmp_path):
    revision = _created(tmp_path)
    a = {"type": "task", "schedule": {"mode": "scheduled", "amount": "2d"}}
    one = _apply(tmp_path, _command("c1", "setObject", {"id": "x", "object": a}, revision)).structured
    two = _apply(tmp_path, _command("c2", "setObject", {"id": "y", "object": a}, one["projectResult"]["resultRevision"])).structured
    assert two["status"] == "ok"
    saved = yaml.safe_load((tmp_path / "project.yaml").read_text(encoding="utf-8"))
    saved["relations"] = [
        {"id": "r1", "type": "dependency", "from": {"object": "x", "endpoint": "end"}, "to": {"object": "y", "endpoint": "start"}},
        {"id": "r2", "type": "dependency", "from": {"object": "y", "endpoint": "end"}, "to": {"object": "x", "endpoint": "start"}},
    ]
    (tmp_path / "project.yaml").write_text(yaml.safe_dump(saved, sort_keys=False), encoding="utf-8")
    assert _call(tmp_path, "validate_project", {"project": "project.yaml"}, write=False).structured["status"] == "rejected"
    # a cycle already in the file does not stop an unrelated valid edit
    revision = yaml_revision(tmp_path)
    again = _apply(tmp_path, _command("c3", "setObject", {"id": "z", "object": a}, revision)).structured
    assert again["status"] == "ok"


def yaml_revision(root: Path) -> str:
    from chrona.core.identity import content_identity
    from chrona.resources import safe_load
    return content_identity(safe_load((root / "project.yaml").read_text(encoding="utf-8")))


def test_remove_object_deletes_an_unreferenced_object_and_refuses_unknown_or_referenced_ones(tmp_path):
    revision = _created(tmp_path)
    added = _apply(tmp_path, _command("c1", "setObject", {"id": "go-live", "object": {
        "type": "gate", "parent": "design", "schedule": {"mode": "scheduled-point"}}}, revision)).structured
    assert added["status"] == "rejected"  # a scheduled-point with no predecessor and no minimum date (Core E_DERIVATION)
    added = _apply(tmp_path, _command("c2", "setObject", {"id": "go-live", "object": {
        "type": "gate", "parent": "design", "schedule": _gate()["schedule"]}}, revision)).structured
    assert added["status"] == "ok"
    revision = added["projectResult"]["resultRevision"]
    saved = yaml.safe_load((tmp_path / "project.yaml").read_text(encoding="utf-8"))
    saved["relations"] = [{"id": "r1", "type": "dependency", "from": {"object": "design", "endpoint": "end"},
                           "to": {"object": "go-live", "endpoint": "at"}}]
    (tmp_path / "project.yaml").write_text(yaml.safe_dump(saved, sort_keys=False), encoding="utf-8")
    revision = yaml_revision(tmp_path)

    unknown = _apply(tmp_path, _command("c3", "removeObject", {"id": "nope"}, revision)).structured
    assert unknown["diagnostics"][0]["code"] == "E_PROJECT_OBJECT_MISSING" and unknown["diagnostics"][0]["sourceRef"] == "/payload/id"
    for target, expected in (("design", "relation 0 (from)"), ("go-live", "relation 0 (to)")):
        refused = _apply(tmp_path, _command(f"c4-{target}", "removeObject", {"id": target}, revision)).structured
        row = refused["diagnostics"][0]
        assert row["code"] == "E_PROJECT_OBJECT_REFERENCED" and expected in row["message"]
    assert "parent" in _apply(tmp_path, _command("c5", "removeObject", {"id": "design"}, revision)).structured["diagnostics"][0]["message"]

    saved["relations"] = []
    saved["objects"]["go-live"].pop("parent")
    (tmp_path / "project.yaml").write_text(yaml.safe_dump(saved, sort_keys=False), encoding="utf-8")
    removed = _apply(tmp_path, _command("c6", "removeObject", {"id": "go-live"}, yaml_revision(tmp_path))).structured
    assert removed["status"] == "ok"
    assert list(yaml.safe_load((tmp_path / "project.yaml").read_text(encoding="utf-8"))["objects"]) == ["design"]


def test_stale_base_revision_is_rejected_with_the_expected_revision_and_writes_nothing(tmp_path):
    revision = _created(tmp_path)
    before = (tmp_path / "project.yaml").read_bytes()
    stale = "sha256:" + "0" * 64
    result = _apply(tmp_path, _command("c1", "setObject", {"id": "g", "object": _gate()}, stale)).structured
    row = result["projectResult"]["diagnostics"][0]
    assert result["status"] == "rejected" and row["code"] == "E_AUTHORING_BASE_REVISION"
    assert row["expectedRevision"] == revision and row["receivedRevision"] == stale
    assert result["diagnostics"][0]["sourceRef"] == "/baseRevision" and "validate_project" in result["diagnostics"][0]["message"]
    assert (tmp_path / "project.yaml").read_bytes() == before


def test_replay_is_marked_and_id_reuse_says_the_first_command_applied(tmp_path):
    revision = _created(tmp_path)
    command = _command("c1", "setObject", {"id": "g", "object": _gate()}, revision)
    first = _apply(tmp_path, command).structured["projectResult"]
    written = (tmp_path / "project.yaml").read_bytes()
    replay = _apply(tmp_path, command).structured["projectResult"]
    assert replay == first | {"replayed": True, "revisionIsCurrent": True}
    assert (tmp_path / "project.yaml").read_bytes() == written
    later = _apply(tmp_path, _command("c2", "removeObject", {"id": "g"}, first["resultRevision"])).structured["projectResult"]
    stale_replay = _apply(tmp_path, command).structured["projectResult"]
    assert stale_replay["replayed"] is True and stale_replay["revisionIsCurrent"] is False
    assert stale_replay["resultRevision"] == first["resultRevision"] != later["resultRevision"]

    different = _command("c1", "setObject", {"id": "g", "object": _gate("2026-12-01")}, later["resultRevision"])
    reuse = _apply(tmp_path, different).structured
    row = reuse["projectResult"]["diagnostics"][0]
    assert row["code"] == "E_AUTHORING_COMMAND_ID_REUSE" and row["firstApplied"] is True
    assert row["appliedRevision"] == first["resultRevision"] and row["revisionIsCurrent"] is False
    assert "Project revision" in row["detail"] and "workspace" not in row["detail"]
    assert reuse["diagnostics"][0]["sourceRef"] == "/commandId"


def test_a_file_written_by_hand_with_unquoted_dates_has_the_revision_validate_project_reports(tmp_path):
    text = (
        "version: timeline/v0.7\n"
        "project: {id: hand, calendar: team}\n"
        "calendars: {team: {working_days: [mon, tue, wed, thu, fri]}}\n"
        "# a comment\n"
        "objects:\n  a: {type: task, schedule: {mode: fixed-span, start: 2026-11-02, end: 2026-11-06}}\n"
    )
    (tmp_path / "hand.yaml").write_text(text, encoding="utf-8")
    revision = _call(tmp_path, "validate_project", {"project": "hand.yaml"}, write=False).structured["projectRevision"]
    result = _apply(tmp_path, _command("c1", "setObject", {"id": "g", "object": _gate()}, revision, "hand.yaml"), "hand.yaml").structured
    assert result["status"] == "ok", result
    assert _call(tmp_path, "validate_project", {"project": "hand.yaml"}, write=False).structured["projectRevision"] \
        == result["projectResult"]["resultRevision"]
    assert _call(tmp_path, "schedule_project", {"project": "hand.yaml"}, write=False).structured["status"] == "ok"


def test_target_path_must_name_the_project_file(tmp_path):
    revision = _created(tmp_path)
    result = _apply(tmp_path, _command("c1", "setObject", {"id": "g", "object": _gate()}, revision, "other.yaml")).structured
    row = result["projectResult"]["diagnostics"][0]
    assert row["code"] == "E_AUTHORING_TARGET_MISMATCH" and "Project file name" in row["detail"]
    assert result["diagnostics"][0]["sourceRef"] == "/target/path"


def test_inline_command_breaking_the_schema_names_the_node_and_a_command_file_uses_the_same_schema(tmp_path):
    revision = _created(tmp_path)
    broken = _command("c1", "removeObject", {"id": "design", "extra": 1}, revision)
    result = _apply(tmp_path, broken).structured
    assert result["status"] == "rejected" and result["diagnostics"][0]["code"] == "E_MCP_INPUT_INVALID"
    assert result["diagnostics"][0]["sourceRef"].startswith("/command/payload")
    (tmp_path / "command.yaml").write_text(yaml.safe_dump(broken, sort_keys=False), encoding="utf-8")
    from_file = _call(tmp_path, "apply_project_command", {"project": "project.yaml", "command": "command.yaml"}).structured
    assert from_file["status"] == "failed" and from_file["diagnostics"][0]["code"] == "E_PROJECT_COMMAND_SCHEMA"
    assert from_file["diagnostics"][0]["sourceRef"] == "/command"
    (tmp_path / "command.yaml").write_text(yaml.safe_dump(
        _command("c2", "setObject", {"id": "g", "object": _gate()}, revision), sort_keys=False), encoding="utf-8")
    assert _call(tmp_path, "apply_project_command", {"project": "project.yaml", "command": "command.yaml"}).structured["status"] == "ok"


def test_validate_project_names_apply_project_command_for_a_command_document(tmp_path):
    command = _command("c1", "removeObject", {"id": "x"}, "sha256:" + "0" * 64)
    (tmp_path / "command.yaml").write_text(yaml.safe_dump(command, sort_keys=False), encoding="utf-8")
    result = _call(tmp_path, "validate_project", {"project": "command.yaml"}, write=False).structured
    assert result["diagnostics"][0]["code"] == "E_CLOSURE_KIND" and "apply_project_command" in result["diagnostics"][0]["message"]


def test_every_result_is_valid_against_the_result_schema_and_json_serialisable(tmp_path):
    from chrona.resources import schema_validator
    revision = _created(tmp_path)
    results = [
        _apply(tmp_path, _command("c1", "setObject", {"id": "g", "object": _gate()}, revision)).structured["projectResult"],
        _apply(tmp_path, _command("c2", "removeObject", {"id": "nope"}, revision)).structured["projectResult"],
        _apply(tmp_path, _command("c3", "removeObject", {"id": "nope"}, "sha256:" + "1" * 64)).structured["projectResult"],
    ]
    for result in results:
        assert not list(schema_validator("project-command-result-v0.1.schema.yaml").iter_errors(json.loads(json.dumps(result))))
