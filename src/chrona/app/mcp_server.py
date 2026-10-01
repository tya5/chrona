"""The MCP binding: the one module that imports the SDK (the optional ``chrona[mcp]`` extra).

It registers the SDK-free tool core (``chrona.app.agent_tools``) with the SDK's low-level
``Server`` and serves it over stdio. It adds no behavior: a ``tools/list`` is the tool registry,
a ``tools/call`` is ``call_tool`` with its result moved into content blocks, and the two
resources are the packaged skill's own text. The tool core owns the input schemas, so the
binding passes the registry's schemas to the SDK and maps the core's two protocol errors
(unknown tool, malformed arguments) to ``INVALID_PARAMS``; a ``rejected`` or ``failed`` tool
result is a result, and the SDK's error flag is set only for ``failed``.

Nothing here prints: the protocol owns standard output (the SDK also points file descriptor 1
at standard error while serving), and logging goes to standard error. Calls are serialized
by a lock because a render cannot be cancelled and the use cases are not written for
concurrent calls; a call runs in a worker thread so the transport stays responsive. SDK API
verified against ``mcp`` 2.x: ``mcp.server.Server`` (constructor-registered handlers),
``mcp.server.stdio.stdio_server``, ``mcp.types`` and ``mcp.shared.exceptions.MCPError``.
"""
from __future__ import annotations

import base64
import logging
import sys
import threading
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import anyio
import anyio.to_thread
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import MCPError

from chrona.app.agent_tools import InvalidArgumentsError, ToolResult, UnknownToolError, call_tool, tool_specs
from chrona.app.agent_workspace import WorkspaceScope
from chrona.resources import skill_resource

SERVER_NAME = "chrona"
AUTHORING_URI = "chrona://guide/authoring"
DIAGNOSTICS_URI = "chrona://guide/diagnostics"
INSTRUCTIONS = (
    "Chrona turns a YAML plan into computed dates and a deterministic picture: edit the plan file, never the "
    "picture. Tools: validate_project (structure only; it does NOT detect dependency cycles), schedule_project "
    "(computed placements; it rejects cycles and contradictory fixed dates, so run it before calling a plan valid), "
    "render_draft (a PNG preview by default, SVG on request) and list_presets. Paths are relative to the workspace "
    "root. A result's status is ok, rejected (the plan is refused: read each diagnostic's code and sourceRef) or "
    "failed (the call could not run); a rejection is a normal result, so read status, not only isError. The "
    f"resources {AUTHORING_URI} and {DIAGNOSTICS_URI} explain the model and every diagnostic code."
)
_LOG = logging.getLogger("chrona.mcp")
_FRONT_MATTER = "---"


def _server_version() -> str:
    try:
        return version("chrona")
    except PackageNotFoundError:  # a source tree without installed metadata
        return "0+unknown"


def _tools() -> list[types.Tool]:
    tools = []
    for spec in tool_specs():
        document = spec.document()
        tools.append(types.Tool(
            name=document["name"], title=document["title"], description=document["description"],
            input_schema=document["inputSchema"], output_schema=document["outputSchema"],
            annotations=types.ToolAnnotations(
                read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False),
        ))
    return tools


def _content(result: ToolResult) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Block 0 is always the structured result as JSON text; an attachment follows it."""
    blocks: list[types.TextContent | types.ImageContent | types.EmbeddedResource] = [types.TextContent(text=result.text())]
    for attachment in result.attachments:
        if attachment.kind == "image":
            blocks.append(types.ImageContent(
                data=base64.b64encode(attachment.data).decode("ascii"), mime_type=attachment.media_type))
        else:
            blocks.append(types.EmbeddedResource(resource=types.TextResourceContents(
                uri=str(attachment.uri), mime_type=attachment.media_type, text=attachment.data.decode("utf-8"))))
    return blocks


def _guides() -> dict[str, tuple[str, str, str]]:
    """``uri -> (name, description, text)`` of the two guides, read from the packaged skill, or empty without it."""
    try:
        root = skill_resource()
        skill = root.joinpath("SKILL.md").read_text(encoding="utf-8")
        diagnostics = root.joinpath("references", "diagnostics.md").read_text(encoding="utf-8")
    except (OSError, ModuleNotFoundError, ValueError) as error:
        _LOG.warning("the packaged skill is unavailable, so no guide resource is served: %s", type(error).__name__)
        return {}
    if skill.startswith(_FRONT_MATTER):
        skill = skill.split(_FRONT_MATTER, 2)[2].lstrip("\n")
    return {
        AUTHORING_URI: ("authoring", "The chrona authoring model, the loop and the rules that cost the most when broken.", skill),
        DIAGNOSTICS_URI: ("diagnostics", "Every diagnostic code an agent meets and what to change for each.", diagnostics),
    }


def build_server(workspace: str | Path) -> Server:
    """The MCP server over one workspace; raises ``StableFailure`` for a workspace the scope refuses."""
    scope = WorkspaceScope(workspace)
    lock = threading.Lock()
    guides = _guides()

    def locked_call(name: str, arguments: Any) -> ToolResult:
        with lock:
            return call_tool(scope, name, arguments)

    async def on_list_tools(ctx: Any, params: Any) -> types.ListToolsResult:
        return types.ListToolsResult(tools=_tools())

    async def on_call_tool(ctx: Any, params: types.CallToolRequestParams) -> types.CallToolResult:
        try:
            result = await anyio.to_thread.run_sync(locked_call, params.name, params.arguments)
        except UnknownToolError as error:
            raise MCPError(types.INVALID_PARAMS, f"unknown tool: {error}") from None
        except InvalidArgumentsError as error:
            raise MCPError(types.INVALID_PARAMS, str(error)) from None
        return types.CallToolResult(content=_content(result), structured_content=result.structured,
                                    is_error=result.is_error)

    async def on_list_resources(ctx: Any, params: Any) -> types.ListResourcesResult:
        return types.ListResourcesResult(resources=[
            types.Resource(uri=uri, name=name, description=description, mime_type="text/markdown")
            for uri, (name, description, _text) in guides.items()
        ])

    async def on_read_resource(ctx: Any, params: types.ReadResourceRequestParams) -> types.ReadResourceResult:
        entry = guides.get(params.uri)
        if entry is None:
            raise MCPError(types.INVALID_PARAMS, f"unknown resource: {params.uri}")
        return types.ReadResourceResult(contents=[
            types.TextResourceContents(uri=params.uri, mime_type="text/markdown", text=entry[2])])

    handlers: dict[str, Any] = {"on_list_tools": on_list_tools, "on_call_tool": on_call_tool}
    if guides:
        handlers |= {"on_list_resources": on_list_resources, "on_read_resource": on_read_resource}
    return Server(SERVER_NAME, version=_server_version(), instructions=INSTRUCTIONS, **handlers)


async def _serve(server: Server) -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def serve(workspace: str | Path) -> None:
    """Run the server over standard input and output until the client closes the stream."""
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr, format="%(name)s: %(message)s")
    anyio.run(_serve, build_server(workspace))
