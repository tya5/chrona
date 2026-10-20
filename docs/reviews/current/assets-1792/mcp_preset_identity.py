"""Row 2 evidence: the trial-9 marquee-over-target-b call against a real `chrona mcp` stdio server.

Usage: python mcp_preset_identity.py <scratch-dir>   (needs PYTHONPATH=<worktree>/src)
"""
import asyncio
import hashlib
import json
import os
import pathlib
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = pathlib.Path(sys.argv[1]).resolve()
HERE.mkdir(parents=True, exist_ok=True)


def cmd(cid, base, preset):
    return {"version": "chrona/authoring-command/v0.1", "commandId": cid, "type": "selectPresentationPreset",
            "target": {"kind": "authoring-workspace", "path": "workspace.yaml"}, "baseRevision": base,
            "payload": {"preset": preset}}


async def call(s, name, args):
    r = await s.call_tool(name, args)
    text = next(c.text for c in r.content if c.type == "text")
    return json.loads(text)


def digest(path):
    return hashlib.sha256((HERE / path).read_bytes()).hexdigest()[:16]


async def main():
    params = StdioServerParameters(command=sys.executable, args=["-m", "chrona", "mcp", "--workspace", str(HERE), "--allow-write"], env=dict(os.environ))
    out = []
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            created = await call(s, "create_workspace", {"directory": "plan", "preset": "target-b", "project": {
                "id": "launch", "title": "Launch plan", "tasks": [
                    {"id": "design", "title": "Design", "planned": {"start": "2026-12-14", "finish": "2026-12-25"}},
                    {"id": "build", "title": "Build", "planned": {"start": "2026-12-28", "finish": "2027-01-22"}}]}})
            ws, rev = created["workspace"], created["workspaceRevision"]
            before = digest(ws)
            out.append({"step": "create_workspace(target-b)", "workspaceRevision": rev, "workspace.yaml sha256[:16]": before})
            # The trial-9 call, verbatim: id "marquee" over the copied target-b preset file.
            refused = await call(s, "apply_authoring_command", {"workspace": ws, "command": cmd(
                "c6-preset", rev, {"id": "marquee", "version": "1", "path": "preset/preset.yaml"})})
            out.append({"step": "selectPresentationPreset marquee over target-b path", "status": refused["status"],
                        "diagnostic": refused["authoringResult"]["diagnostics"][0]})
            now = (await call(s, "workspace_revision", {"workspace": ws}))["workspaceRevision"]
            out.append({"step": "workspace_revision after refusal", "workspaceRevision": now, "unchanged": now == rev,
                        "workspace.yaml sha256[:16]": digest(ws), "bytes unchanged": digest(ws) == before})
            rendered = await call(s, "render_workspace", {"workspace": ws, "format": "svg", "inline": "none"})
            out.append({"step": "render_workspace after refusal", "status": rendered["status"]})
            same = await call(s, "apply_authoring_command", {"workspace": ws, "command": cmd(
                "c7-preset", rev, {"id": "chrona-builtin-target-b", "version": "1", "path": "preset/preset.yaml"})})
            out.append({"step": "matching re-pin chrona-builtin-target-b", "status": same["status"],
                        "resultRevision": same["authoringResult"]["resultRevision"]})
    print(json.dumps(out, indent=2, ensure_ascii=False))

asyncio.run(main())
