"""The MCP binding over the in-process SDK client (#142, I142-S4).

Needs the optional ``chrona[mcp]`` extra; without it the whole module is skipped with that reason. The tool
semantics are tested SDK-free in ``tests/unit/chrona/app``; this module proves the binding moves them intact:
the tool list is the registry, a result becomes the right content blocks, ``isError`` is set only for ``failed``,
protocol errors come from the core's argument check, calls are serialized, and the guides are the packaged skill.
"""
from __future__ import annotations

import base64
import json
import threading
import time
from pathlib import Path

import pytest

pytest.importorskip("mcp.server", reason="the optional chrona[mcp] extra is not installed (a bare tests/mcp directory is only a namespace package)")

import anyio  # noqa: E402  (an SDK dependency, present whenever the extra is)
from mcp import Client, types  # noqa: E402
from mcp.shared.exceptions import MCPError  # noqa: E402

from chrona.app import agent_tools, mcp_server  # noqa: E402
from chrona.app.agent_tools import registry_document  # noqa: E402
from chrona.resources import skill_resource  # noqa: E402
from chrona.usecases.failure_report import StableFailure  # noqa: E402
from tests.support.store_workspace import StoreWorkspace  # noqa: E402

REPO = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
PROJECT = (REPO / "skills" / "chrona" / "examples" / "launch.yaml").read_text(encoding="utf-8")
CYCLE = """\
version: timeline/v0.7
project: {id: cyc, title: Cycle}
objects:
  a: {type: task, title: A, schedule: {mode: scheduled, amount: 3d}}
  b: {type: task, title: B, schedule: {mode: scheduled, amount: 3d}}
relations:
  - {id: r1, type: dependency, from: {object: a, endpoint: end}, to: {object: b, endpoint: start}, lag: 0d}
  - {id: r2, type: dependency, from: {object: b, endpoint: end}, to: {object: a, endpoint: start}, lag: 0d}
"""


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    root.mkdir()
    (root / "launch.yaml").write_text(PROJECT, encoding="utf-8")
    (root / "cycle.yaml").write_text(CYCLE, encoding="utf-8")
    return root


def run(workspace: Path, scenario, *, allow_write: bool = False):
    """Run ``scenario(client)`` against a fresh in-process server over ``workspace``."""
    async def go():
        async with Client(mcp_server.build_server(workspace, allow_write=allow_write)) as client:
            return await scenario(client)

    return anyio.run(go)


def test_the_tool_list_is_the_registry(workspace):
    listed = run(workspace, lambda client: client.list_tools()).tools
    document = registry_document()["tools"]
    assert [tool.name for tool in listed] == [tool["name"] for tool in document]
    for tool, expected in zip(listed, document, strict=True):
        assert tool.input_schema == expected["inputSchema"] and tool.output_schema == expected["outputSchema"]
        assert tool.description == expected["description"] and tool.title == expected["title"]
        annotations = expected["annotations"]
        assert (tool.annotations.read_only_hint, tool.annotations.destructive_hint, tool.annotations.idempotent_hint,
                tool.annotations.open_world_hint) == (annotations["readOnlyHint"], annotations["destructiveHint"],
                                                      annotations["idempotentHint"], annotations["openWorldHint"])
    by_name = {tool.name: tool.annotations for tool in listed}
    assert by_name["check_command"].read_only_hint is True and by_name["apply_command"].read_only_hint is False
    assert by_name["apply_command"].destructive_hint is True and by_name["schedule_project"].destructive_hint is False


def test_initialize_carries_the_name_the_instructions_and_no_prompt_capability(workspace):
    async def scenario(client):
        return client.server_info, client.instructions, client.server_capabilities

    info, instructions, capabilities = run(workspace, scenario)
    assert info.name == "chrona"
    assert len(mcp_server.INSTRUCTIONS.encode("utf-8")) < 1024
    assert instructions == mcp_server.INSTRUCTIONS
    for needle in ("schedule_project", "dependency cycles, no dates", "rejected", "chrona://guide/authoring"):
        assert needle in instructions
    assert capabilities.tools is not None and capabilities.resources is not None
    assert capabilities.prompts is None


def test_a_result_is_json_text_first_and_the_structured_content_equals_it(workspace):
    result = run(workspace, lambda client: client.call_tool("schedule_project", {"project": "launch.yaml"}))
    assert not result.is_error and [type(block) for block in result.content] == [types.TextContent]
    assert result.structured_content["status"] == "ok"
    assert json.loads(result.content[0].text) == result.structured_content
    assert list(result.structured_content["placements"]) == ["build", "design", "kickoff", "launch"]


def test_render_draft_returns_a_png_image_block_by_default(workspace):
    result = run(workspace, lambda client: client.call_tool("render_draft", {"project": "launch.yaml"}))
    assert not result.is_error and [type(block) for block in result.content] == [types.TextContent, types.ImageContent]
    image = result.content[1]
    assert image.mime_type == "image/png" and base64.b64decode(image.data).startswith(b"\x89PNG\r\n\x1a\n")


def test_render_draft_inline_svg_is_an_embedded_resource(workspace):
    result = run(workspace, lambda client: client.call_tool("render_draft", {"project": "launch.yaml", "inline": "svg"}))
    block = result.content[1]
    assert isinstance(block, types.EmbeddedResource)
    assert block.resource.mime_type == "image/svg+xml" and block.resource.text.startswith("<svg")
    assert block.resource.uri.startswith("chrona://render/sha256:") and block.resource.uri.endswith(".svg")


def test_is_error_is_set_only_for_failed(workspace):
    async def scenario(client):
        return (await client.call_tool("schedule_project", {"project": "cycle.yaml"}),
                await client.call_tool("validate_project", {"project": "../outside.yaml"}),
                await client.call_tool("validate_project", {"project": "launch.yaml"}))

    rejected, failed, ok = run(workspace, scenario)
    assert (rejected.structured_content["status"], rejected.is_error) == ("rejected", False)
    assert (failed.structured_content["status"], failed.is_error) == ("failed", True)
    assert failed.structured_content["diagnostics"][0]["code"] == "E_MCP_PATH_SYNTAX"
    assert (ok.structured_content["status"], ok.is_error) == ("ok", False)


@pytest.mark.parametrize(("name", "arguments"), [
    ("no_such_tool", {}), ("validate_project", {}), ("validate_project", {"project": 3}),
    ("validate_project", {"project": "launch.yaml", "extra": True}),
    ("render_draft", {"project": "launch.yaml", "format": "pdf"}),
])
def test_unknown_tools_and_malformed_arguments_are_protocol_errors_not_envelopes(workspace, name, arguments):
    async def scenario(client):
        with pytest.raises(MCPError) as raised:
            await client.call_tool(name, arguments)
        return raised.value

    error = run(workspace, scenario)
    assert error.code == types.INVALID_PARAMS and error.message


def test_the_guides_are_the_packaged_skill_text(workspace):
    async def scenario(client):
        listed = await client.list_resources()
        authoring = await client.read_resource("chrona://guide/authoring")
        diagnostics = await client.read_resource("chrona://guide/diagnostics")
        with pytest.raises(MCPError):
            await client.read_resource("chrona://guide/other")
        return listed, authoring, diagnostics

    listed, authoring, diagnostics = run(workspace, scenario)
    assert [resource.uri for resource in listed.resources] == ["chrona://guide/authoring", "chrona://guide/diagnostics"]
    skill = skill_resource()
    body = skill.joinpath("SKILL.md").read_text(encoding="utf-8").split("---", 2)[2].lstrip("\n")
    assert authoring.contents[0].text == body and not authoring.contents[0].text.startswith("---")
    assert diagnostics.contents[0].text == skill.joinpath("references", "diagnostics.md").read_text(encoding="utf-8")
    assert all(item.mime_type == "text/markdown" for item in (authoring.contents[0], diagnostics.contents[0]))


def test_calls_are_serialized(workspace, monkeypatch):
    active, peak, lock = [0], [0], threading.Lock()
    real = agent_tools.call_tool

    def slow(scope, name, arguments=None, **options):
        with lock:
            active[0] += 1
            peak[0] = max(peak[0], active[0])
        time.sleep(0.05)
        try:
            return real(scope, name, arguments, **options)
        finally:
            with lock:
                active[0] -= 1

    monkeypatch.setattr(mcp_server, "call_tool", slow)

    async def scenario(client):
        async with anyio.create_task_group() as group:
            for _ in range(6):
                group.start_soon(client.call_tool, "list_presets", {})

    run(workspace, scenario)
    assert peak[0] == 1


def test_a_filesystem_root_workspace_is_refused_before_serving(tmp_path):
    with pytest.raises(StableFailure) as raised:
        mcp_server.build_server(Path(tmp_path.anchor))
    assert raised.value.code == "E_MCP_WORKSPACE_TOO_BROAD"


def test_without_the_packaged_skill_the_server_still_serves_tools_and_omits_resources(workspace, monkeypatch):
    def missing():
        raise FileNotFoundError("no skill")

    monkeypatch.setattr(mcp_server, "skill_resource", missing)

    async def scenario(client):
        assert client.server_capabilities.resources is None
        return await client.call_tool("list_presets", {})

    assert run(workspace, scenario).structured_content["status"] == "ok"


# --- the write start option (#813) ------------------------------------------------------------------------------

def test_without_allow_write_apply_command_is_refused_over_the_binding_and_check_command_still_works(tmp_path):
    work = StoreWorkspace(tmp_path / "ws")
    path = work.write_command("c1.yaml", work.intake("c1", work.batch("b1")))
    before = work.snapshot()

    async def scenario(client):
        return (await client.call_tool("apply_command", {"command": path}),
                await client.call_tool("check_command", {"command": path}), client.instructions)

    applied, checked, instructions = run(work.root, scenario)

    assert applied.is_error and applied.structured_content["status"] == "failed"
    assert [row["code"] for row in applied.structured_content["diagnostics"]] == ["E_MCP_WRITE_DISABLED"]
    assert not checked.is_error and checked.structured_content["status"] == "ok"
    assert instructions == mcp_server.INSTRUCTIONS and "Writes are off" in instructions
    assert work.snapshot() == before


def test_with_allow_write_apply_command_writes_a_new_store_revision_and_a_replay_is_a_no_op(tmp_path):
    work = StoreWorkspace(tmp_path / "ws")
    path = work.write_command("c1.yaml", work.intake("c1", work.batch("b1")))

    async def scenario(client):
        return (await client.call_tool("apply_command", {"command": path}),
                await client.call_tool("apply_command", {"command": path}), client.instructions)

    first, second, instructions = run(work.root, scenario, allow_write=True)

    assert not first.is_error and first.structured_content["status"] == "ok"
    assert second.structured_content["automationResult"]["replayed"] is True
    assert work.tip()["counter"] == 2
    assert instructions == mcp_server.WRITE_INSTRUCTIONS and "no approval step" in instructions
    assert len(mcp_server.WRITE_INSTRUCTIONS.encode("utf-8")) < 1024
    assert json.loads(first.content[0].text) == first.structured_content


def test_a_rejected_command_is_a_result_and_not_a_tool_error(tmp_path):
    work = StoreWorkspace(tmp_path / "ws")
    path = work.write_command("c1.yaml", work.intake("c1", work.batch("b1"), base="actual:0:stale"))

    result = run(work.root, lambda client: client.call_tool("apply_command", {"command": path}), allow_write=True)

    assert not result.is_error and result.structured_content["status"] == "rejected"
    assert result.structured_content["automationResult"]["status"] == "rejected"


def test_a_server_built_without_the_option_refuses_writes_and_the_option_defaults_off(tmp_path):
    import inspect

    work = StoreWorkspace(tmp_path / "ws")
    path = work.write_command("c1.yaml", work.intake("c1", work.batch("b1")))
    before = work.snapshot()

    async def go():
        async with Client(mcp_server.build_server(work.root)) as client:  # no allow_write argument at all
            return await client.call_tool("apply_command", {"command": path})

    result = anyio.run(go)

    assert result.is_error and result.structured_content["diagnostics"][0]["code"] == "E_MCP_WRITE_DISABLED"
    assert work.snapshot() == before
    for function in (mcp_server.build_server, mcp_server.serve):
        assert inspect.signature(function).parameters["allow_write"].default is False
