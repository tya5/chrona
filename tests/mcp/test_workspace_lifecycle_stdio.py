"""An MCP-only client needs no shell call, command file or hand-read revision."""
import copy

import pytest
import yaml

pytest.importorskip("mcp.server", reason="optional chrona[mcp] is not installed")

from tests.mcp.test_mcp_stdio_e2e import session  # noqa: E402
from tests.unit.chrona.app.test_agent_workspace_lifecycle import _project  # noqa: E402


@pytest.mark.parametrize("preset", ["chrona-default-draft", "target-b"])
def test_mcp_only_client_creates_validates_edits_reverts_and_renders(tmp_path, preset):
    root = tmp_path / "server"
    root.mkdir()

    def scenario(client, _init):
        async def run():
            async def call(name, arguments):
                result = await client.call_tool(name, arguments)
                assert not result.is_error, result.structured_content
                assert result.structured_content["status"] == "ok", result.structured_content
                return result.structured_content

            created = await call("create_workspace", {"directory": "plan", "preset": preset, "project": _project()})
            path = created["workspace"]
            validated = await call("validate_workspace", {"workspace": path})
            queried = await call("workspace_revision", {"workspace": path})
            revision = queried["workspaceRevision"]
            assert revision == validated["workspaceRevision"] == created["workspaceRevision"]
            original = _project()["tasks"][0]
            changed = {**copy.deepcopy(original), "title": "変更後の日本語"}
            replies = []
            for command_id, task in (("edit", changed), ("inverse-edit", original)):
                command = {"version": "chrona/authoring-command/v0.1", "commandId": command_id,
                           "type": "setWorkspaceTask", "target": {"kind": "authoring-workspace", "path": "workspace.yaml"},
                           "baseRevision": revision, "payload": {"task": task}}
                result = await call("apply_authoring_command", {"workspace": path, "command": command})
                assert result["authoringResult"]["status"] == "accepted"
                revision = result["authoringResult"]["resultRevision"]
                replies.append(result)
            rendered = await call("render_workspace", {"workspace": path, "inline": "none"})
            return created, replies, rendered
        return run()

    created, replies, rendered = session(root, scenario, allow_write=True)
    assert len(replies) == 2 and rendered["byteLength"] > 0
    raw = (root / created["workspace"]).read_text(encoding="utf-8")
    assert "初期タイトル" in raw and "日本語の計画" in raw and "\\u" not in raw
    project = yaml.safe_load(raw)["body"]["project"]
    assert list(project) == list(_project())
    assert project == _project()
    assert not list(root.rglob("command.yaml"))
