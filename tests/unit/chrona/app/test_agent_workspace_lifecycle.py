"""The guided workspace lifecycle stays inside the server's declared root."""
import pytest

from chrona.app.agent_tools import call_tool, registry_document
from chrona.app.agent_workspace import WorkspaceScope


def _project():
    return {"title": "日本語の計画", "id": "plan", "tasks": [
        {"id": "one", "title": "初期タイトル", "planned": {"start": "2026-01-05", "finish": "2026-01-09"}},
    ]}


@pytest.mark.parametrize("preset", ["chrona-default-draft", "target-b"])
def test_workspace_tools_create_validate_query_and_render_copied_presets(tmp_path, preset):
    scope = WorkspaceScope(tmp_path)
    created = call_tool(scope, "create_workspace", {"directory": "plan", "project": _project(), "preset": preset},
                        allow_write=True).structured
    assert created["status"] == "ok", created
    assert created["workspace"] == "plan/workspace.yaml"
    workspace = {"workspace": created["workspace"]}
    validated = call_tool(scope, "validate_workspace", workspace).structured
    queried = call_tool(scope, "workspace_revision", workspace).structured
    assert validated["status"] == queried["status"] == "ok"
    assert validated["workspaceRevision"] == queried["workspaceRevision"] == created["workspaceRevision"]
    rendered = call_tool(scope, "render_workspace", {**workspace, "inline": "svg"})
    assert rendered.structured["status"] == "ok", rendered.structured
    assert rendered.structured["byteLength"] > 0
    assert rendered.attachments[0].kind == "svg"


@pytest.mark.parametrize("directory,code", [
    ("../outside", "E_MCP_PATH_SYNTAX"), ("NUL", "E_MCP_PATH_SYNTAX"),
    ("missing/new", "E_INPUT_IO"), ("existing", "E_AUTHORING_WORKSPACE_EXISTS"),
])
def test_creation_rejects_unsafe_missing_parent_and_existing_destinations(tmp_path, directory, code):
    (tmp_path / "existing").mkdir()
    sentinel = tmp_path / "existing" / "keep.txt"
    sentinel.write_text("preserve", encoding="utf-8")
    result = call_tool(WorkspaceScope(tmp_path), "create_workspace",
                       {"directory": directory, "project": _project()}, allow_write=True)
    assert result.is_error and result.structured["diagnostics"][0]["code"] == code
    assert sentinel.read_text() == "preserve"
    assert set(tmp_path.iterdir()) == {tmp_path / "existing"}


def test_create_write_gate_precedes_destination_and_preset_reads(tmp_path):
    result = call_tool(WorkspaceScope(tmp_path), "create_workspace",
                       {"directory": "../outside", "project": _project(), "preset": "unknown"})
    assert result.is_error
    assert result.structured["diagnostics"][0]["code"] == "E_MCP_WRITE_DISABLED"
    assert list(tmp_path.iterdir()) == []


def test_creation_refuses_an_in_root_symlink_parent_without_touching_its_target(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is not available")
    result = call_tool(WorkspaceScope(tmp_path), "create_workspace",
                       {"directory": "alias/new", "project": _project()}, allow_write=True)
    assert result.is_error and result.structured["diagnostics"][0]["code"] == "E_MCP_PATH_CONTAINMENT"
    assert list(real.iterdir()) == [] and alias.is_symlink()


def test_lifecycle_registry_exposes_commands_payloads_and_truthful_write_annotations():
    registry = registry_document()
    assert registry["toolSet"] == "chrona/agent-tools/v0.7"
    tools = {tool["name"]: tool for tool in registry["tools"]}
    for name in ("create_workspace", "validate_workspace", "workspace_revision", "render_workspace"):
        assert tools[name]["inputSchema"]["additionalProperties"] is False
        assert tools[name]["annotations"]["readOnlyHint"] == (name != "create_workspace")
    description = tools["apply_authoring_command"]["description"]
    for operation in ("setWorkspaceTask", "setWorkspaceActual", "selectPresentationPreset",
                      "setPresentationOverride", "materializePresentationPreset"):
        assert operation in description
    assert "baseRevision" in description and "payload" in description


def _select_preset(scope, workspace, revision, preset_id, version="1", command_id="select-1"):
    return call_tool(scope, "apply_authoring_command", {
        "workspace": workspace,
        "command": {"version": "chrona/authoring-command/v0.1", "commandId": command_id,
                    "type": "selectPresentationPreset",
                    "target": {"kind": "authoring-workspace", "path": "workspace.yaml"},
                    "baseRevision": revision,
                    "payload": {"preset": {"id": preset_id, "version": version, "path": "preset/preset.yaml"}}},
    }, allow_write=True).structured


def test_select_preset_refuses_a_binding_the_pinned_preset_cannot_render(tmp_path):
    scope = WorkspaceScope(tmp_path)
    created = call_tool(scope, "create_workspace", {"directory": "plan", "project": _project(), "preset": "target-b"},
                        allow_write=True).structured
    workspace, revision = created["workspace"], created["workspaceRevision"]
    before = (tmp_path / workspace).read_bytes()

    for preset_id, version in (("marquee", "1"), ("chrona-builtin-target-b", "2")):
        refused = _select_preset(scope, workspace, revision, preset_id, version)
        diagnostic = refused["authoringResult"]["diagnostics"][0]
        assert refused["status"] == "rejected"
        assert diagnostic["code"] == "E_AUTHORING_PRESET_IDENTITY"
        assert "create_workspace" in diagnostic["detail"]
        assert (tmp_path / workspace).read_bytes() == before
        assert call_tool(scope, "workspace_revision", {"workspace": workspace}).structured["workspaceRevision"] == revision
    assert call_tool(scope, "render_workspace", {"workspace": workspace}).structured["status"] == "ok"

    same = _select_preset(scope, workspace, revision, "chrona-builtin-target-b", command_id="select-2")
    assert same["status"] == "ok"
    assert same["authoringResult"]["resultRevision"] == revision
