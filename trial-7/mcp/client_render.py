"""Render the Japanese plan and schedule it through MCP render_draft / schedule_project."""
import asyncio, base64, json
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).resolve().parent
TRIAL = HERE.parent
CHRONA = str(TRIAL.parent / ".venv" / "bin" / "chrona")


async def main():
    params = StdioServerParameters(command=CHRONA, args=["mcp", "--workspace", str(TRIAL)])
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool("schedule_project", {"project": "ja/project.yaml"})
            st = res.structured_content or json.loads(res.content[0].text)
            print("schedule:", st.get("status"), [x["code"] for x in st.get("warnings", [])], st.get("analysis", {}).get("criticalObjectIds", [])[:5])
            res = await s.call_tool("render_draft", {"project": "ja/project.yaml", "actual": "ja/actual.yaml", "preset": "titlecard", "locale": "ja-JP"})
            for c in res.content:
                if c.type == "image":
                    (HERE / "mcp-titlecard-ja.png").write_bytes(base64.b64decode(c.data))
                    print("image bytes", len(base64.b64decode(c.data)))
                elif c.type == "text":
                    d = json.loads(c.text)
                    print("render:", d.get("status"), len(d.get("warnings", [])), d.get("byteLength"))
            g = await s.read_resource("chrona://guide/authoring")
            txt = g.contents[0].text
            print("guide mentions authoring-command:", "authoring-command" in txt, "setWorkspaceTask" in txt, "workspace revision" in txt)


asyncio.run(main())
