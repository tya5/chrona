"""Minimal stdio MCP client driving `chrona mcp --allow-write` like an agent would."""
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).resolve().parent
WS = HERE / "ws"
CHRONA = str(HERE.parent.parent / ".venv" / "bin" / "chrona")
LOG = HERE / "transcript.jsonl"


def short(result):
    out = []
    for c in result.content:
        if c.type == "text":
            out.append(c.text)
        elif c.type == "image":
            out.append(f"<image {c.mime_type} {len(c.data)} b64 chars>")
        else:
            out.append(f"<{c.type}>")
    return {"isError": result.is_error, "content": out, "structured": result.structured_content}


async def call(session, name, args, save_image=None):
    r = await session.call_tool(name, args)
    s = short(r)
    with LOG.open("a") as f:
        f.write(json.dumps({"tool": name, "args": args, "result": s}, ensure_ascii=False) + "\n")
    if save_image:
        import base64
        for c in r.content:
            if c.type == "image":
                (HERE / save_image).write_bytes(base64.b64decode(c.data))
    print(f"\n### {name} {json.dumps(args, ensure_ascii=False)}")
    txt = json.dumps(s["structured"] if s["structured"] else s["content"], ensure_ascii=False)
    print(txt[:2500])
    return s


def write(rel, text):
    (WS / rel).write_text(text, encoding="utf-8")


def struct(s):
    if s["structured"]:
        return s["structured"]
    for t in s["content"]:
        try:
            return json.loads(t)
        except Exception:
            pass
    return {}


async def main():
    LOG.write_text("")
    params = StdioServerParameters(command=CHRONA, args=["mcp", "--workspace", str(WS), "--allow-write"])
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as session:
            init = await session.initialize()
            print("server:", init.server_info, "\ninstructions:", (init.instructions or "")[:1500])
            res = await session.list_resources()
            print("resources:", [x.uri for x in res.resources])
            # 1) apply with a deliberately unknown base to learn the revision
            write("cmd-0.yaml", """version: chrona/authoring-command/v0.1
commandId: probe-0
type: setWorkspaceTask
target: {kind: authoring-workspace, path: workspace.yaml}
baseRevision: sha256:0000000000000000000000000000000000000000000000000000000000000000
payload:
  task: {id: design, title: 基本設計, planned: {start: '2026-11-16', finish: '2026-11-27'}}
""")
            s = await call(session, "apply_authoring_command", {"workspace": "workspace.yaml", "command": "cmd-0.yaml"})
            res0 = struct(s)
            ar = res0.get("authoringResult", res0)
            base = ar.get("workspaceRevision")
            print("learned base:", base)
            # 2) edit a task (rename + extend)
            write("cmd-1.yaml", f"""version: chrona/authoring-command/v0.1
commandId: edit-design
type: setWorkspaceTask
target: {{kind: authoring-workspace, path: workspace.yaml}}
baseRevision: {base}
payload:
  task: {{id: design, title: 基本設計・詳細設計, planned: {{start: '2026-11-16', finish: '2026-12-04'}}}}
""")
            s = await call(session, "apply_authoring_command", {"workspace": "workspace.yaml", "command": "cmd-1.yaml"})
            base = struct(s).get("authoringResult", {}).get("resultRevision", base)
            # 3) add a new task
            write("cmd-2.yaml", f"""version: chrona/authoring-command/v0.1
commandId: add-test
type: setWorkspaceTask
target: {{kind: authoring-workspace, path: workspace.yaml}}
baseRevision: {base}
payload:
  task: {{id: test, title: 受入テスト, planned: {{start: '2026-12-21', finish: '2027-01-08'}}}}
""")
            s = await call(session, "apply_authoring_command", {"workspace": "workspace.yaml", "command": "cmd-2.yaml"})
            base = struct(s).get("authoringResult", {}).get("resultRevision", base)
            # 4) record an actual
            write("cmd-3.yaml", f"""version: chrona/authoring-command/v0.1
commandId: actual-discovery
type: setWorkspaceActual
target: {{kind: authoring-workspace, path: workspace.yaml}}
baseRevision: {base}
payload:
  actual: {{taskId: discovery, actual: {{start: '2026-11-02', finish: '2026-11-17'}}, progress: 1}}
""")
            s = await call(session, "apply_authoring_command", {"workspace": "workspace.yaml", "command": "cmd-3.yaml"})
            base = struct(s).get("authoringResult", {}).get("resultRevision", base)
            # 5) revert the rename (write the old values back), as the spec says undo is a new revision
            write("cmd-4.yaml", f"""version: chrona/authoring-command/v0.1
commandId: revert-edit-design
type: setWorkspaceTask
target: {{kind: authoring-workspace, path: workspace.yaml}}
baseRevision: {base}
payload:
  task: {{id: design, title: 設計, planned: {{start: '2026-11-16', finish: '2026-11-27'}}}}
""")
            s = await call(session, "apply_authoring_command", {"workspace": "workspace.yaml", "command": "cmd-4.yaml"})
            # 6) replay same commandId: should be a no-op
            s = await call(session, "apply_authoring_command", {"workspace": "workspace.yaml", "command": "cmd-4.yaml"})
            # 7) try to render the workspace through render_draft
            await call(session, "render_draft", {"project": "workspace.yaml", "inline": "none"})
            await call(session, "validate_project", {"project": "workspace.yaml"})


asyncio.run(main())
