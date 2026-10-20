"""Inline and workspace-path Store Command Requests use the same MCP dispatch (#902 item 4)."""
from __future__ import annotations

import pytest

pytest.importorskip("mcp.server", reason="the optional chrona[mcp] extra is not installed")

from tests.mcp.test_mcp_stdio_e2e import session  # noqa: E402
from tests.support.store_workspace import StoreWorkspace  # noqa: E402


def test_inline_and_path_store_commands_check_and_replay_with_identical_revisions_over_stdio(tmp_path):
    inline_work = StoreWorkspace(tmp_path / "inline-first")
    path_work = StoreWorkspace(tmp_path / "path-first")
    works = (inline_work, path_work)
    paths = []
    commands = []
    for work in works:
        batch = work.batch("same-batch")
        command = work.intake("same-command", batch)
        commands.append(command)
        paths.append(work.write_command("same-command.yaml", command))

    async def run_one(client, command, path, inline_first):
        inline_args = {"command": command}
        path_args = {"command": path}
        checked_inline = await client.call_tool("check_command", inline_args)
        checked_path = await client.call_tool("check_command", path_args)
        assert not checked_inline.is_error and not checked_path.is_error
        assert checked_inline.structured_content["status"] == "ok"
        assert checked_path.structured_content["status"] == "ok"
        assert checked_inline.structured_content["automationResult"] == checked_path.structured_content["automationResult"]

        first_args, replay_args = (inline_args, path_args) if inline_first else (path_args, inline_args)
        first = await client.call_tool("apply_command", first_args)
        assert not first.is_error and first.structured_content["status"] == "ok"
        replay = await client.call_tool("apply_command", replay_args)
        assert not replay.is_error and replay.structured_content["status"] == "ok"
        return checked_inline, checked_path, first, replay

    async def inline_first_scenario(client, _init):
        return await run_one(client, commands[0], paths[0], True)

    async def path_first_scenario(client, _init):
        return await run_one(client, commands[1], paths[1], False)

    results = (
        session(inline_work.root, inline_first_scenario, allow_write=True),
        session(path_work.root, path_first_scenario, allow_write=True),
    )
    accepted_targets = []
    for work, (checked_inline, checked_path, first, replay) in zip(works, results, strict=True):
        first_result = first.structured_content["automationResult"]
        replay_result = replay.structured_content["automationResult"]
        assert first_result["resultTarget"] == replay_result["resultTarget"]
        assert replay_result["replayed"] is True
        assert first_result.get("replayed", False) is False
        assert checked_inline.structured_content["automationResult"] == checked_path.structured_content["automationResult"]
        assert work.tip()["counter"] == 2
        accepted_targets.append(first_result["resultTarget"])
    assert accepted_targets[0] == accepted_targets[1]
