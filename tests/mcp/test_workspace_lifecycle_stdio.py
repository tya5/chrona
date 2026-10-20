"""An MCP-only client needs no shell call, command file or hand-read revision."""
import copy

import pytest
import yaml

pytest.importorskip("mcp.server", reason="optional chrona[mcp] is not installed")

from mcp import types  # noqa: E402
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
            rendered = await client.call_tool("render_workspace", {"workspace": path, "inline": "svg"})
            assert not rendered.is_error and rendered.structured_content["status"] == "ok"
            return created, replies, rendered
        return run()

    created, replies, rendered = session(root, scenario, allow_write=True)
    assert len(replies) == 2 and rendered.structured_content["byteLength"] > 0
    assert rendered.structured_content["format"] == "svg"
    assert [type(block) for block in rendered.content] == [types.TextContent, types.EmbeddedResource]
    svg = rendered.content[1].resource
    assert svg.mime_type == "image/svg+xml"
    assert svg.uri == f"chrona://render/{rendered.structured_content['contentIdentity']}.svg"
    assert svg.text.startswith("<svg") and len(svg.text.encode("utf-8")) == rendered.structured_content["byteLength"]
    raw = (root / created["workspace"]).read_text(encoding="utf-8")
    assert "初期タイトル" in raw and "日本語の計画" in raw and "\\u" not in raw
    project = yaml.safe_load(raw)["body"]["project"]
    assert list(project) == list(_project())
    assert project == _project()
    assert not list(root.rglob("command.yaml"))


def test_authoring_inline_and_path_forms_produce_the_same_revision_over_stdio(tmp_path):
    from tests.unit.chrona.app.test_agent_authoring import _command, _seed

    roots = (tmp_path / "inline-first", tmp_path / "path-first")
    originals = tuple(_seed(root, command_id="stdio-parity") for root in roots)
    commands = tuple(_command(original, command_id="stdio-parity") for original in originals)
    for root, command in zip(roots, commands, strict=True):
        (root / "command.yaml").write_text(yaml.safe_dump(command, sort_keys=False), encoding="utf-8")

    def scenario(command, inline_first):
        async def run(client, _init):
            inline_args = {"workspace": "workspace.yaml", "command": command}
            path_args = {"workspace": "workspace.yaml", "command": "command.yaml"}
            first_args, second_args = (inline_args, path_args) if inline_first else (path_args, inline_args)
            first = await client.call_tool("apply_authoring_command", first_args)
            second = await client.call_tool("apply_authoring_command", second_args)
            return first, second
        return run

    results = (
        session(roots[0], scenario(commands[0], True), allow_write=True),
        session(roots[1], scenario(commands[1], False), allow_write=True),
    )
    revisions = []
    for root, original, (first, second) in zip(roots, originals, results, strict=True):
        assert not first.is_error and not second.is_error
        first_result = first.structured_content["authoringResult"]
        second_result = second.structured_content["authoringResult"]
        assert first_result["status"] == "accepted"
        assert second_result == first_result
        assert (root / "workspace.yaml").read_bytes() != yaml.safe_dump(original, sort_keys=False).encode()
        revisions.append(first_result["resultRevision"])
    assert revisions[0] == revisions[1]
