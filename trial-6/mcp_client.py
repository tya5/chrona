"""Drive `chrona mcp` once over stdio, as an MCP host would, and save the render preview."""
import asyncio
import base64
import json
import pathlib
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = pathlib.Path(__file__).resolve().parent
CHRONA = str(HERE.parent / ".venv" / "bin" / "chrona")


def show(name, result):
    texts = [c.text for c in result.content if getattr(c, "type", "") == "text"]
    images = [c for c in result.content if getattr(c, "type", "") == "image"]
    print(f"--- {name}: isError={getattr(result, "is_error", None)} texts={len(texts)} images={len(images)}")
    for t in texts:
        print(t[:600])
    return texts, images


async def main():
    params = StdioServerParameters(command=CHRONA, args=["mcp", "--workspace", str(HERE)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("tools:", [t.name for t in tools.tools])
            show("validate_project", await session.call_tool("validate_project", {"project": "plan.yaml"}))
            texts, _ = show("schedule_project", await session.call_tool("schedule_project", {"project": "plan.yaml"}))
            show("schedule_project outside", await session.call_tool("schedule_project", {"project": "../README.md"}))
            texts, images = show(
                "render_draft",
                await session.call_tool(
                    "render_draft",
                    {"project": "plan.yaml", "actual": "actual-week2.yaml", "snapshot": "baseline.yaml",
                     "forecast": True, "preset": "target-b"},
                ),
            )
            for i, img in enumerate(images):
                out = HERE / "out" / f"mcp-render-{i}.png"
                out.write_bytes(base64.b64decode(img.data))
                print("wrote", out)
            res = await session.list_resources()
            print("resources:", [str(r.uri) for r in res.resources])


asyncio.run(main())
