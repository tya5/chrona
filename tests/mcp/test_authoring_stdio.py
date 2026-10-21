"""The durable authoring writer over real MCP stdio (#902 item 2)."""
from __future__ import annotations

import pytest
import yaml

pytest.importorskip("mcp.server", reason="the optional chrona[mcp] extra is not installed")

from tests.mcp.test_mcp_stdio_e2e import session, tree  # noqa: E402
from tests.unit.chrona.app.test_agent_authoring import _command, _seed, _workspace  # noqa: E402


def test_authoring_stdio_write_gate_containment_replay_and_no_overwrite(tmp_path):
    root = tmp_path / "ws"
    _seed(root)
    outside = tmp_path / "outside.yaml"
    outside.write_text("outside sentinel", encoding="utf-8")
    before = tree(root)

    def disabled_scenario(client, init):
        async def run():
            return await client.call_tool("apply_authoring_command", {
                "workspace": "missing.yaml", "command": "missing-command.yaml"})
        return run()

    disabled = session(root, disabled_scenario)
    assert disabled.is_error and disabled.structured_content["status"] == "failed"
    assert disabled.structured_content["diagnostics"][0]["code"] == "E_MCP_WRITE_DISABLED"
    assert "Nothing was read or written" in disabled.structured_content["diagnostics"][0]["message"]
    assert tree(root) == before

    def writer_scenario(client, init):
        async def run():
            escaped = await client.call_tool("apply_authoring_command", {
                "workspace": "../outside.yaml", "command": "command.yaml"})
            accepted = await client.call_tool("apply_authoring_command", {
                "workspace": "workspace.yaml", "command": "command.yaml"})
            replay = await client.call_tool("apply_authoring_command", {
                "workspace": "workspace.yaml", "command": "command.yaml"})
            receipt_dirs = tuple(root.glob(".chrona-authoring-receipts-*"))
            accepted_receipts = {path.name: path.read_bytes() for directory in receipt_dirs for path in directory.glob("*.json")}
            accepted_workspace = (root / "workspace.yaml").read_bytes()
            stale = _command(_workspace(), command_id="stale-1")
            (root / "command.yaml").write_text(yaml.safe_dump(stale, sort_keys=False), encoding="utf-8")
            stale_result = await client.call_tool("apply_authoring_command", {
                "workspace": "workspace.yaml", "command": "command.yaml"})
            assert (root / "workspace.yaml").read_bytes() == accepted_workspace
            # Alter only the request file after acceptance to prove an ID collision cannot replace its receipt.
            changed = _command(_workspace(), command_id="agent-1")
            changed["payload"]["task"]["title"] = "Different request"
            (root / "command.yaml").write_text(yaml.safe_dump(changed, sort_keys=False), encoding="utf-8")
            collision = await client.call_tool("apply_authoring_command", {
                "workspace": "workspace.yaml", "command": "command.yaml"})
            return escaped, accepted, replay, stale_result, collision, accepted_receipts
        return run()

    escaped, accepted, replay, stale, collision, accepted_receipts = session(root, writer_scenario, allow_write=True)
    assert escaped.is_error and escaped.structured_content["diagnostics"][0]["code"] == "E_MCP_PATH_SYNTAX"
    assert escaped.structured_content["diagnostics"][0]["sourceRef"] == "/workspace"
    assert "outside.yaml" not in escaped.content[0].text and outside.read_text(encoding="utf-8") == "outside sentinel"
    assert not accepted.is_error and accepted.structured_content["status"] == "ok"
    assert accepted.structured_content["authoringResult"]["status"] == "accepted"
    assert "replayed" not in accepted.structured_content["authoringResult"]
    assert replay.structured_content["authoringResult"] == accepted.structured_content["authoringResult"] | {
        "replayed": True, "revisionIsCurrent": True}
    assert stale.structured_content["status"] == "rejected" and not stale.is_error
    assert stale.structured_content["authoringResult"]["diagnostics"][0]["code"] == "E_AUTHORING_BASE_REVISION"
    assert stale.structured_content["diagnostics"][0]["sourceRef"] == "/baseRevision"
    assert collision.structured_content["status"] == "rejected" and not collision.is_error
    assert collision.structured_content["authoringResult"]["diagnostics"][0]["code"] == "E_AUTHORING_COMMAND_ID_REUSE"
    assert collision.structured_content["diagnostics"][0]["sourceRef"] == "/commandId"
    final = tree(root)
    assert yaml.safe_load((root / "workspace.yaml").read_text(encoding="utf-8"))["body"]["project"]["tasks"][0]["title"] == "Agent edit"
    assert accepted_receipts
    after_receipts = {path.name: path.read_bytes() for directory in root.glob(".chrona-authoring-receipts-*")
                      for path in directory.glob("*.json")}
    assert after_receipts == accepted_receipts
    assert final["command.yaml"] != before["command.yaml"]


def test_authoring_stdio_lists_truthful_writer_annotations(tmp_path):
    root = tmp_path / "ws"
    _seed(root)

    def scenario(client, init):
        async def run():
            return await client.list_tools()
        return run()

    tools = session(root, scenario).tools
    authoring, = [tool for tool in tools if tool.name == "apply_authoring_command"]
    assert authoring.annotations.read_only_hint is False
    assert authoring.annotations.destructive_hint is True
    assert authoring.annotations.idempotent_hint is True
    assert set(authoring.input_schema["properties"]) == {"workspace", "command"}
