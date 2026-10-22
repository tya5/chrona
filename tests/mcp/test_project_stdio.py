"""create_project and apply_project_command over real MCP stdio (#1892 row 1)."""
from __future__ import annotations

import copy
import json

import pytest
import yaml

pytest.importorskip("mcp.server", reason="the optional chrona[mcp] extra is not installed")

from tests.mcp.test_mcp_stdio_e2e import session, tree  # noqa: E402
from tests.unit.chrona.app.test_agent_project_tools import PROJECT, _command, _gate  # noqa: E402


def test_project_tools_create_edit_replay_and_schedule_over_stdio(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()

    def disabled(client, init):
        async def run():
            return await client.call_tool("create_project", {"file": "project.yaml", "project": PROJECT})
        return run()

    refused = session(root, disabled)
    assert refused.is_error and refused.structured_content["diagnostics"][0]["code"] == "E_MCP_WRITE_DISABLED"
    assert tree(root) == {}

    def scenario(client, init):
        async def run():
            created = await client.call_tool("create_project", {"file": "project.yaml", "project": copy.deepcopy(PROJECT)})
            revision = created.structured_content["projectRevision"]
            command = _command("c1", "setObject", {"id": "go-live", "object": _gate()}, revision)
            applied = await client.call_tool("apply_project_command", {"project": "project.yaml", "command": command})
            replay = await client.call_tool("apply_project_command", {"project": "project.yaml", "command": command})
            malformed = await client.call_tool("apply_project_command", {"project": "project.yaml", "command": {"type": "setObject"}})
            bad = await client.call_tool("apply_project_command", {"project": "project.yaml", "command": _command(
                "c2", "setObject", {"id": "x", "object": {"type": "task", "schedule": {"mode": "scheduled", "amount": "3q"}}},
                applied.structured_content["projectResult"]["resultRevision"])})
            schedule = await client.call_tool("schedule_project", {"project": "project.yaml"})
            return created, applied, replay, malformed, bad, schedule
        return run()

    created, applied, replay, malformed, bad, schedule = session(root, scenario, allow_write=True)
    assert created.structured_content["status"] == "ok" and not created.is_error
    result = applied.structured_content["projectResult"]
    assert applied.structured_content["status"] == "ok" and result["status"] == "accepted" and "replayed" not in result
    assert replay.structured_content["projectResult"] == result | {"replayed": True, "revisionIsCurrent": True}
    assert malformed.structured_content["status"] == "rejected" and not malformed.is_error
    assert malformed.structured_content["diagnostics"][0]["code"] == "E_MCP_INPUT_INVALID"
    assert bad.structured_content["status"] == "rejected" and not bad.is_error
    assert bad.structured_content["diagnostics"][0]["sourceRef"] == "/payload/object/schedule/amount"
    assert schedule.structured_content["status"] == "ok"
    assert schedule.structured_content["placements"]["go-live"] == {"at": "2026-11-10"}
    saved = yaml.safe_load((root / "project.yaml").read_text(encoding="utf-8"))
    assert list(saved["objects"]) == ["design", "go-live"]
    assert json.loads(applied.content[0].text) == applied.structured_content


def test_an_accepted_edit_is_reverted_through_mcp_alone_by_its_inverse(tmp_path):
    """#1892 row 2 item 4: create, edit, remove, then revert both with the returned inverse; no file or shell access."""
    root = tmp_path / "ws"
    root.mkdir()

    def scenario(client, init):
        async def run():
            call = lambda command: client.call_tool("apply_project_command", {"project": "project.yaml", "command": command})  # noqa: E731
            created = await client.call_tool("create_project", {"file": "project.yaml", "project": copy.deepcopy(PROJECT)})
            start = created.structured_content["projectRevision"]
            added = (await call(_command("c1", "setObject", {"id": "go-live", "object": _gate()}, start))).structured_content["projectResult"]
            removed = (await call(_command("c2", "removeObject", {"id": "design"}, added["resultRevision"]))).structured_content["projectResult"]
            undo_remove = (await call(removed["inverse"])).structured_content["projectResult"]
            undo_add = (await call(added["inverse"])).structured_content["projectResult"]
            return start, undo_remove, undo_add
        return run()

    start, undo_remove, undo_add = session(root, scenario, allow_write=True)
    assert undo_remove["status"] == "accepted"
    assert undo_add["status"] == "accepted" and undo_add["resultRevision"] == start
    saved = yaml.safe_load((root / "project.yaml").read_text(encoding="utf-8"))
    assert saved == PROJECT
