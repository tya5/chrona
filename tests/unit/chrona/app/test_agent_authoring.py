"""Agent-tool boundary tests for the shared durable authoring command (#902 item 2)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

from chrona.app.agent_tools import call_tool, registry_document
from chrona.app.agent_workspace import WorkspaceScope
from chrona.app.cli import main
from chrona.core.identity import content_identity


def _workspace() -> dict:
    return {
        "version": "chrona/authoring-workspace/v0.1", "kind": "authoring-workspace", "id": "workspace",
        "body": {
            "project": {"id": "project", "tasks": [{"id": "one", "title": "One",
                         "planned": {"start": "2026-01-01", "finish": "2026-01-02"}}]},
            "presentation": {"mode": "guided", "binding": {"preset": {
                "id": "starter", "version": "1", "path": "preset.yaml"}}},
        },
    }


def _command(workspace: dict, *, command_id: str = "agent-1", base: str | None = None) -> dict:
    return {
        "version": "chrona/authoring-command/v0.1", "commandId": command_id,
        "type": "setWorkspaceTask", "target": {"kind": "authoring-workspace", "path": "workspace.yaml"},
        "baseRevision": base or content_identity(workspace),
        "payload": {"task": {"id": "one", "title": "Agent edit",
                    "planned": {"start": "2026-01-03", "finish": "2026-01-04"}}},
    }


def _seed(root: Path, *, command_id: str = "agent-1") -> dict:
    root.mkdir(parents=True)
    workspace = _workspace()
    (root / "workspace.yaml").write_text(yaml.safe_dump(workspace, sort_keys=False), encoding="utf-8")
    (root / "command.yaml").write_text(yaml.safe_dump(_command(workspace, command_id=command_id), sort_keys=False), encoding="utf-8")
    return workspace


def _tree(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


def test_agent_authoring_tool_has_write_truth_and_closed_two_path_input(tmp_path):
    tool, = [item for item in registry_document()["tools"] if item["name"] == "apply_authoring_command"]
    assert tool["inputSchema"]["required"] == ["workspace", "command"]
    assert set(tool["inputSchema"]["properties"]) == {"workspace", "command"}
    assert tool["inputSchema"]["additionalProperties"] is False
    assert tool["annotations"] == {
        "readOnlyHint": False, "destructiveHint": True, "idempotentHint": True, "openWorldHint": False,
    }

    # Neither missing input is opened when the server was not started with the write gate.
    root = tmp_path / "ws"
    root.mkdir()
    result = call_tool(WorkspaceScope(root), "apply_authoring_command",
                       {"workspace": "missing.yaml", "command": "also-missing.yaml"})
    assert result.structured["status"] == "failed" and result.is_error
    assert result.structured["diagnostics"][0]["code"] == "E_MCP_WRITE_DISABLED"
    assert "Nothing was read or written" in result.structured["diagnostics"][0]["message"]
    assert _tree(root) == {}


def test_agent_authoring_metadata_matches_command_version_and_path_forms(tmp_path):
    tool, = [item for item in registry_document()["tools"] if item["name"] == "apply_authoring_command"]
    command = tool["inputSchema"]["properties"]["command"]
    inline_schema = next(option for option in command["oneOf"] if option.get("type") == "object")
    version = inline_schema["properties"]["version"]["const"]

    assert version == "chrona/authoring-command/v0.1"
    for description in (command["description"], tool["description"]):
        assert f"version: {version}" in description
        assert "workspace: guided/workspace.yaml" in description
        assert "{kind: authoring-workspace, path: workspace.yaml}" in description
        assert "file name, not its outer path" in description

    root = tmp_path / "ws"
    workspace = _seed(root / "guided")
    before = _tree(root)
    valid = _command(workspace)
    wrong_version = json.loads(json.dumps(valid))
    wrong_version["version"] = "authoring-command/v0.1"
    rejected = call_tool(WorkspaceScope(root), "apply_authoring_command",
                         {"workspace": "guided/workspace.yaml", "command": wrong_version}, allow_write=True)
    assert rejected.structured["status"] == "rejected" and not rejected.is_error
    assert rejected.structured["diagnostics"][0]["sourceRef"] == "/command/version"
    assert _tree(root) == before

    wrong_target = json.loads(json.dumps(valid))
    wrong_target["target"]["path"] = "guided/workspace.yaml"
    rejected = call_tool(WorkspaceScope(root), "apply_authoring_command",
                         {"workspace": "guided/workspace.yaml", "command": wrong_target}, allow_write=True)
    assert rejected.structured["status"] == "rejected"
    assert rejected.structured["diagnostics"][0]["sourceRef"].startswith("/command/target/path")
    assert _tree(root) == before

    accepted = call_tool(WorkspaceScope(root), "apply_authoring_command",
                         {"workspace": "guided/workspace.yaml", "command": valid}, allow_write=True)
    assert accepted.structured["status"] == "ok"
    assert accepted.structured["authoringResult"]["status"] == "accepted"


def test_agent_authoring_tool_containment_and_diagnostic_source_are_honest(tmp_path):
    root = tmp_path / "ws"
    _seed(root)
    outside = tmp_path / "outside.yaml"
    outside.write_text("not opened", encoding="utf-8")
    before = _tree(root)
    result = call_tool(WorkspaceScope(root), "apply_authoring_command",
                       {"workspace": "../outside.yaml", "command": "command.yaml"}, allow_write=True)
    assert result.structured["status"] == "failed" and result.is_error
    assert result.structured["diagnostics"][0]["code"] == "E_MCP_PATH_SYNTAX"
    assert result.structured["diagnostics"][0]["sourceRef"] == "/workspace"
    assert "outside.yaml" not in result.text()
    assert _tree(root) == before and outside.read_text(encoding="utf-8") == "not opened"


def test_agent_authoring_tool_blocks_symlink_escape_before_reading(tmp_path):
    root = tmp_path / "ws"
    _seed(root)
    outside = tmp_path / "outside.yaml"
    outside.write_text("sensitive outside bytes", encoding="utf-8")
    try:
        (root / "escape.yaml").symlink_to(outside)
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"symlinks unavailable: {error}")
    before = _tree(root)
    result = call_tool(WorkspaceScope(root), "apply_authoring_command",
                       {"workspace": "escape.yaml", "command": "command.yaml"}, allow_write=True)
    assert result.structured["status"] == "failed" and result.is_error
    assert result.structured["diagnostics"][0]["code"] == "E_MCP_PATH_CONTAINMENT"
    assert result.structured["diagnostics"][0]["sourceRef"] == "/workspace"
    assert "sensitive outside bytes" not in result.text()
    assert _tree(root) == before


def test_agent_authoring_tool_maps_canonical_symlink_and_refuses_alias_target(tmp_path):
    root = tmp_path / "ws"
    _seed(root)
    alias = root / "workspace-alias.yaml"
    try:
        alias.symlink_to(root / "workspace.yaml")
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"symlinks unavailable: {error}")

    # A path alias resolves to the canonical workspace for identity and target validation.
    accepted = call_tool(WorkspaceScope(root), "apply_authoring_command",
                         {"workspace": "workspace-alias.yaml", "command": "command.yaml"}, allow_write=True)
    assert accepted.structured["status"] == "ok"
    assert accepted.structured["authoringResult"]["status"] == "accepted"

    workspace = _workspace()
    alias_command = _command(workspace, command_id="alias-target")
    alias_command["target"]["path"] = "workspace-alias.yaml"
    (root / "command.yaml").write_text(yaml.safe_dump(alias_command, sort_keys=False), encoding="utf-8")
    before = _tree(root)
    refused = call_tool(WorkspaceScope(root), "apply_authoring_command",
                        {"workspace": "workspace-alias.yaml", "command": "command.yaml"}, allow_write=True)
    assert refused.structured["status"] == "rejected" and not refused.is_error
    assert refused.structured["authoringResult"]["diagnostics"][0]["code"] == "E_AUTHORING_TARGET_MISMATCH"
    assert refused.structured["diagnostics"][0]["sourceRef"] == "/target/path"
    assert _tree(root) == before


def test_agent_authoring_tool_separates_bad_command_and_corrupt_receipt_failures(tmp_path):
    root = tmp_path / "ws"
    _seed(root)
    (root / "command.yaml").write_text("broken: [\n", encoding="utf-8")
    malformed = call_tool(WorkspaceScope(root), "apply_authoring_command",
                          {"workspace": "workspace.yaml", "command": "command.yaml"}, allow_write=True)
    assert malformed.structured["status"] == "failed" and malformed.is_error
    assert malformed.structured["diagnostics"][0]["sourceRef"] == "/command"
    assert "authoringResult" not in malformed.structured

    # Recreate the original request, accept it, then damage its sole replay authority.
    workspace = _workspace()
    (root / "command.yaml").write_text(yaml.safe_dump(_command(workspace), sort_keys=False), encoding="utf-8")
    accepted = call_tool(WorkspaceScope(root), "apply_authoring_command",
                         {"workspace": "workspace.yaml", "command": "command.yaml"}, allow_write=True)
    assert accepted.structured["status"] == "ok"
    receipt = next(next(root.glob(".chrona-authoring-receipts-*")).glob("*.json"))
    receipt.write_text("corrupt receipt", encoding="utf-8")
    unavailable = call_tool(WorkspaceScope(root), "apply_authoring_command",
                            {"workspace": "workspace.yaml", "command": "command.yaml"}, allow_write=True)
    assert unavailable.structured["status"] == "failed" and unavailable.is_error
    assert unavailable.structured["diagnostics"][0]["sourceRef"] == "/workspace"
    assert "authoringResult" not in unavailable.structured


def test_agent_authoring_tool_cli_parity_replay_stale_and_id_reuse(tmp_path, monkeypatch, capsys):
    tool_root, cli_root = tmp_path / "tool", tmp_path / "cli"
    _seed(tool_root)
    _seed(cli_root)
    cli_result_path = cli_root / "result.json"

    # The SDK-free tool and CLI share the same durable operation and emit the same result contract.
    tool_result = call_tool(WorkspaceScope(tool_root), "apply_authoring_command",
                            {"workspace": "workspace.yaml", "command": "command.yaml"}, allow_write=True)
    monkeypatch.chdir(cli_root)
    monkeypatch.setattr(sys, "argv", ["chrona", "authoring-command-apply", "--workspace", "workspace.yaml",
                                       "--command", "command.yaml", "--result", "result.json"])
    try:
        main()
    except SystemExit as error:
        assert error.code == 0
    cli_result = json.loads(cli_result_path.read_text(encoding="utf-8"))
    assert tool_result.structured["status"] == "ok" and not tool_result.is_error
    assert tool_result.structured["authoringResult"] == cli_result
    assert cli_result["status"] == "accepted"

    after_first = _tree(tool_root)
    replay = call_tool(WorkspaceScope(tool_root), "apply_authoring_command",
                       {"workspace": "workspace.yaml", "command": "command.yaml"}, allow_write=True)
    first_result = tool_result.structured["authoringResult"]
    assert "replayed" not in first_result and "revisionIsCurrent" not in first_result
    assert replay.structured["authoringResult"] == first_result | {"replayed": True, "revisionIsCurrent": True}
    assert _tree(tool_root) == after_first

    # Same command identity with altered canonical request is refusal, and does not overwrite the receipt.
    altered = _command(_workspace(), command_id="agent-1")
    altered["payload"]["task"]["title"] = "Different request"
    (tool_root / "command.yaml").write_text(yaml.safe_dump(altered, sort_keys=False), encoding="utf-8")
    before_conflict = _tree(tool_root)
    conflict = call_tool(WorkspaceScope(tool_root), "apply_authoring_command",
                         {"workspace": "workspace.yaml", "command": "command.yaml"}, allow_write=True)
    assert conflict.structured["status"] == "rejected" and not conflict.is_error
    assert conflict.structured["authoringResult"]["diagnostics"][0]["code"] == "E_AUTHORING_COMMAND_ID_REUSE"
    assert conflict.structured["diagnostics"][0]["sourceRef"] == "/commandId"
    reuse_row = conflict.structured["authoringResult"]["diagnostics"][0]
    assert reuse_row["firstApplied"] is True and reuse_row["revisionIsCurrent"] is True
    assert reuse_row["appliedRevision"] == first_result["resultRevision"]
    assert "was applied" in conflict.structured["diagnostics"][0]["message"]
    assert _tree(tool_root) == before_conflict

    # A fresh command based on old bytes is stale; it must not modify the accepted workspace.
    fresh = _command(_workspace(), command_id="stale-1")
    (tool_root / "command.yaml").write_text(yaml.safe_dump(fresh, sort_keys=False), encoding="utf-8")
    before_stale = _tree(tool_root)
    stale = call_tool(WorkspaceScope(tool_root), "apply_authoring_command",
                      {"workspace": "workspace.yaml", "command": "command.yaml"}, allow_write=True)
    assert stale.structured["status"] == "rejected" and not stale.is_error
    assert stale.structured["authoringResult"]["diagnostics"][0]["code"] == "E_AUTHORING_BASE_REVISION"
    assert stale.structured["diagnostics"][0]["sourceRef"] == "/baseRevision"
    assert _tree(tool_root) == before_stale
    assert "traceback" not in capsys.readouterr().err.lower()


def _apply(root: Path, command: dict):
    return call_tool(WorkspaceScope(root), "apply_authoring_command",
                     {"workspace": "guided/workspace.yaml", "command": command}, allow_write=True)


def test_authoring_input_rejections_carry_the_pointer_and_expected_shape(tmp_path):
    root = tmp_path / "ws"
    workspace = _seed(root / "guided")
    before = _tree(root)

    open_actual = _command(workspace)
    open_actual["type"] = "setWorkspaceActual"
    open_actual["payload"] = {"actual": {"taskId": "one", "actual": {"start": "2026-01-01"}}}
    result = _apply(root, open_actual)
    row = result.structured["diagnostics"][0]
    assert (result.structured["status"], result.is_error) == ("rejected", False)
    assert row["sourceRef"] == "/command/payload/actual/actual" and "missing required property 'finish'" in row["message"]

    misplaced = _command(workspace)
    misplaced["payload"]["task"]["constraints"] = {"at": {"min": "2026-01-02"}}
    row = _apply(root, misplaced).structured["diagnostics"][0]
    assert row["sourceRef"] == "/command/payload/task/constraints"
    assert "permitted properties: id, title, planned" in row["message"] and "not accepted anywhere" in row["message"]

    wrong_level = _command(workspace)
    wrong_level["payload"]["task"]["planned"]["start"] = "2026-01-03"
    wrong_level["payload"]["start"] = "2026-01-03"
    row = _apply(root, wrong_level).structured["diagnostics"][0]
    assert row["sourceRef"] == "/command/payload/start" and "is permitted at /command/payload/task/planned" in row["message"]
    assert _tree(root) == before


@pytest.mark.parametrize(("overrides", "pointer", "words"), [
    ({"theme": {"surprise": 1}}, "/payload/overrides/theme/surprise", "permitted properties: colorScheme"),
    ({"layout": {}}, "/payload/overrides/layout", "permitted properties: view, theme"),
    ({"theme": 3}, "/payload/overrides/theme", "expected type object"),
])
def test_a_bad_presentation_override_names_the_node_in_the_payload(tmp_path, overrides, pointer, words):
    root = tmp_path / "ws"
    workspace = _seed(root / "guided")
    before = (root / "guided" / "workspace.yaml").read_bytes()
    command = _command(workspace)
    command["type"] = "setPresentationOverride"
    command["payload"] = {"overrides": overrides}
    result = _apply(root, command)
    assert (result.structured["status"], result.is_error) == ("rejected", False)
    row = result.structured["diagnostics"][0]
    assert row["code"] == "E_RESOURCE_SCHEMA" and row["sourceRef"] == pointer and words in row["message"]
    assert "expected one permitted form" not in row["message"]
    assert result.structured["authoringResult"]["diagnostics"][0]["detail"].startswith(pointer + ": ")
    assert (root / "guided" / "workspace.yaml").read_bytes() == before
