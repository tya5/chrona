"""``create_store`` and ``publish_resource``: the Store route end to end through ``call_tool`` only (#1892 row 2, item 6)."""
from __future__ import annotations

import copy
import json

import pytest
import yaml
from jsonschema import Draft202012Validator

from chrona.app.agent_tools import call_tool, tool_specs
from chrona.app.agent_workspace import WorkspaceScope

OUTPUT = {spec.name: Draft202012Validator(spec.output_schema) for spec in tool_specs()}
PROJECT = {
    "version": "timeline/v0.7",
    "project": {"id": "launch"},
    "objects": {"build": {"type": "task", "title": "Build", "schedule": {"mode": "fixed-span", "start": "2026-11-02", "end": "2026-11-06"}}},
}
ACTUAL = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "actuals", "body": {"observations": []}}
BATCH = {"version": "chrona/actual-intake-batch/v0.2", "kind": "actual-intake-batch", "id": "week-1",
         "body": {"source": {"system": "tracker", "contentIdentity": "sha256:" + "a" * 64},
                  "records": [{"externalKey": "42", "projectObjectId": "build", "actual": {"finish": "2026-11-07"}}]}}


def call(root, name, arguments, *, allow_write=True):
    result = call_tool(WorkspaceScope(root), name, arguments, allow_write=allow_write)
    assert not list(OUTPUT[name].iter_errors(result.structured)), result.structured
    return result


def codes(result):
    return [row["code"] for row in result.structured["diagnostics"]]


def publish(root, kind, document, **extra):
    return call(root, "publish_resource", {"kind": kind, "document": copy.deepcopy(document), **extra})


def command(command_id, kind, target, payload):
    return {"version": "chrona/command/v0.4", "commandId": command_id, "type": kind, "target": target,
            "baseRevision": target["revision"]["token"], "expectedContentIdentity": target["contentIdentity"], "payload": payload}


def test_publish_capture_intake_and_revert_complete_through_mcp_alone(tmp_path):
    assert call(tmp_path, "create_project", {"file": "project.yaml", "project": copy.deepcopy(PROJECT)}).structured["status"] == "ok"
    created = call(tmp_path, "create_store", {}).structured
    assert created == {"status": "ok", "diagnostics": [], "storeConfig": ".chrona/store.yaml", "store": "workspace"}
    assert (tmp_path / ".chrona" / "store").is_dir()

    project = call(tmp_path, "publish_resource", {"kind": "project", "path": "project.yaml"}).structured
    assert project["status"] == "ok" and "replayed" not in project and project["storeConfig"] == ".chrona/store.yaml"
    project_ref = project["reference"]
    assert project_ref["kind"] == "project" and project_ref["id"] == "launch" and project_ref["store"] == {"provider": "local", "identity": "workspace"}
    actual_ref = publish(tmp_path, "actual-set", ACTUAL).structured["reference"]
    batch_ref = publish(tmp_path, "actual-intake-batch", BATCH).structured["reference"]
    assert actual_ref["address"] == "actuals/actuals.yaml" and actual_ref["revision"]["token"].startswith("actual:1:")

    capture = command("snap-1", "captureSnapshot", project_ref,
                      {"snapshotId": "baseline-1", "registry": {"provider": "local", "identity": "workspace"}})
    checked = call(tmp_path, "check_command", {"command": capture}).structured
    assert checked["status"] == "ok", checked
    captured = call(tmp_path, "apply_command", {"command": capture}).structured
    assert captured["status"] == "ok", captured
    assert captured["automationResult"]["resultTarget"]["kind"] == "snapshot-ref"

    intake = command("intake-1", "applyActualIntakeBatch", actual_ref, {"batch": batch_ref, "project": project_ref})
    applied = call(tmp_path, "apply_command", {"command": intake}).structured
    assert applied["status"] == "ok", applied
    assert applied["automationResult"]["actualIntake"] == {"dispositions": ["inserted"]}
    after = applied["automationResult"]["resultTarget"]
    assert after["revision"]["token"].startswith("actual:2:")
    stored = yaml.safe_load((tmp_path / ".chrona" / "store" / ("revision-" + after["revision"]["token"].replace(":", "%3A"))
                             / "actuals" / "actuals.yaml").read_text(encoding="utf-8"))
    assert len(stored["body"]["observations"]) == 1

    reverted = call(tmp_path, "apply_command", {"command": command("undo-1", "revertActualCommand", after, {"commandId": "intake-1"})}).structured
    assert reverted["status"] == "ok", reverted
    restored = reverted["automationResult"]["resultTarget"]
    assert restored["revision"]["token"].startswith("actual:3:")
    back = yaml.safe_load((tmp_path / ".chrona" / "store" / ("revision-" + restored["revision"]["token"].replace(":", "%3A"))
                          / "actuals" / "actuals.yaml").read_text(encoding="utf-8"))
    assert back["body"]["observations"] == []
    replay = call(tmp_path, "apply_command", {"command": command("undo-1", "revertActualCommand", after, {"commandId": "intake-1"})}).structured
    assert replay["automationResult"]["replayed"] is True


def test_create_store_is_idempotent_and_never_rewrites_a_different_configuration(tmp_path):
    first = call(tmp_path, "create_store", {"identity": "plans"}).structured
    again = call(tmp_path, "create_store", {"identity": "plans"}).structured
    assert again["replayed"] is True and "replayed" not in first
    other = call(tmp_path, "create_store", {"identity": "other"})
    assert other.structured["status"] == "failed" and codes(other) == ["E_STORE_CONFIG_EXISTS"]
    assert yaml.safe_load((tmp_path / ".chrona" / "store.yaml").read_text(encoding="utf-8"))["stores"][0]["identity"] == "plans"


def test_the_written_configuration_is_one_contained_required_local_store(tmp_path):
    call(tmp_path, "create_store", {})
    config = yaml.safe_load((tmp_path / ".chrona" / "store.yaml").read_text(encoding="utf-8"))
    assert config == {"version": "chrona/store-config/v0.1",
                      "stores": [{"provider": "local", "identity": "workspace", "root": "store", "integrity": "required"}]}


def test_a_symlinked_chrona_directory_is_refused(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "ws"
    root.mkdir()
    (root / ".chrona").symlink_to(outside, target_is_directory=True)
    result = call(root, "create_store", {})
    assert codes(result) == ["E_STORE_DIRECTORY"] and not list(outside.iterdir())


def test_publishing_the_same_bytes_replays_and_changed_bytes_are_a_new_revision(tmp_path):
    call(tmp_path, "create_store", {})
    first = publish(tmp_path, "project", PROJECT).structured
    again = publish(tmp_path, "project", PROJECT).structured
    assert again["replayed"] is True and again["reference"] == first["reference"]
    changed = copy.deepcopy(PROJECT)
    changed["objects"]["build"]["title"] = "Build it"
    second = publish(tmp_path, "project", changed).structured
    assert "replayed" not in second and second["reference"]["revision"] != first["reference"]["revision"]
    assert second["reference"]["contentIdentity"] != first["reference"]["contentIdentity"]


def test_an_actual_set_is_published_once_and_changes_only_by_command(tmp_path):
    call(tmp_path, "create_store", {})
    first = publish(tmp_path, "actual-set", ACTUAL).structured
    again = publish(tmp_path, "actual-set", ACTUAL).structured
    assert again["replayed"] is True and again["reference"] == first["reference"]
    changed = copy.deepcopy(ACTUAL)
    changed["body"]["observations"] = [{"id": "o1", "sequence": 1, "projectObjectId": "build", "actual": {"finish": "2026-11-07"}}]
    refused = publish(tmp_path, "actual-set", changed)
    assert codes(refused) == ["E_STORE_RESOURCE_EXISTS"] and refused.structured["status"] == "failed"


def test_input_rejections_name_the_node(tmp_path):
    call(tmp_path, "create_store", {})
    cases = [
        ({"kind": "project"}, "E_MCP_INPUT_INVALID", "/"),
        ({"kind": "project", "path": "project.yaml", "document": PROJECT}, "E_MCP_INPUT_INVALID", "/"),
        ({"kind": "actual-set", "document": PROJECT}, "E_STORE_RESOURCE_INVALID", "/kind"),
        ({"kind": "actual-set", "document": {**ACTUAL, "id": "a/b"}}, "E_STORE_RESOURCE_INVALID", "/"),
        ({"kind": "actual-intake-batch", "document": {**BATCH, "body": {**BATCH["body"], "records": "x"}}}, "E_SCHEMA", "/body/records"),
        ({"kind": "project", "document": {"version": "timeline/v0.7", "project": {"id": "p"}, "objects": 3}}, None, None),
        ({"kind": "project", "document": PROJECT, "store": "nope"}, "E_STORE_SELECTION", "/store"),
        ({"kind": "bogus", "document": PROJECT}, "E_MCP_INPUT_INVALID", "/kind"),
    ]
    for arguments, code, pointer in cases:
        result = call(tmp_path, "publish_resource", arguments)
        assert result.structured["status"] in {"rejected", "failed"}, (arguments, result.structured)
        row = result.structured["diagnostics"][0]
        if code:
            assert (row["code"], row["sourceRef"]) == (code, pointer), (arguments, row)
    assert not any((tmp_path / ".chrona" / "store").iterdir())


def test_a_missing_store_configuration_names_the_path_and_writes_nothing(tmp_path):
    result = call(tmp_path, "publish_resource", {"kind": "project", "document": PROJECT})
    assert result.structured["status"] == "failed" and result.structured["diagnostics"][0]["sourceRef"] == "/storeConfig"
    assert not (tmp_path / ".chrona").exists()


@pytest.mark.parametrize("name,arguments", [("create_store", {}), ("publish_resource", {"kind": "project", "document": PROJECT})])
def test_both_tools_need_the_write_gate_and_write_nothing_without_it(tmp_path, name, arguments):
    result = call(tmp_path, name, arguments, allow_write=False)
    assert codes(result) == ["E_MCP_WRITE_DISABLED"] and not (tmp_path / ".chrona").exists()


def test_the_store_root_in_the_configuration_must_stay_inside_the_workspace(tmp_path):
    root = tmp_path / "ws"
    (root / ".chrona").mkdir(parents=True)
    (root / ".chrona" / "store.yaml").write_text(json.dumps({
        "version": "chrona/store-config/v0.1",
        "stores": [{"provider": "local", "identity": "x", "root": "../../elsewhere"}]}), encoding="utf-8")
    result = call(root, "publish_resource", {"kind": "project", "document": PROJECT})
    assert codes(result) == ["E_MCP_PATH_CONTAINMENT"] and not (tmp_path / "elsewhere").exists()
