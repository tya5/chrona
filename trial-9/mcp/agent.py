"""Drive `chrona mcp --allow-write` as an agent would: create, edit, revert, render."""
import asyncio
import base64
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = os.path.dirname(os.path.abspath(__file__))
CHRONA = os.path.join(HERE, "..", "venv", "bin", "chrona")
LOG = []


async def call(s, name, args):
    r = await s.call_tool(name, args)
    out = None
    for c in r.content:
        if c.type == "text":
            try:
                out = json.loads(c.text)
            except Exception:
                out = c.text
        elif c.type == "image":
            path = os.path.join(HERE, f"{name}-{len(LOG)}.png")
            open(path, "wb").write(base64.b64decode(c.data))
            print("   image ->", path)
    short = json.dumps(out, ensure_ascii=False)[:900]
    print(f"## {name} isError={r.is_error}\n   {short}")
    LOG.append((name, args, out))
    return out


def cmd(cid, typ, base, payload):
    return {"version": "chrona/authoring-command/v0.1", "commandId": cid, "type": typ,
            "target": {"kind": "authoring-workspace", "path": "workspace.yaml"},
            "baseRevision": base, "payload": payload}


async def main():
    params = StdioServerParameters(command=CHRONA, args=["mcp", "--workspace", HERE, "--allow-write"])
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            await call(s, "list_presets", {})
            created = await call(s, "create_workspace", {
                "directory": "plan", "preset": "target-b",
                "project": {"id": "launch", "title": "公開計画", "tasks": [
                    {"id": "design", "title": "設計", "planned": {"start": "2026-12-14", "finish": "2026-12-25"}},
                    {"id": "build", "title": "実装", "planned": {"start": "2026-12-28", "finish": "2027-01-22"}},
                    {"id": "test", "title": "試験", "planned": {"start": "2027-01-25", "finish": "2027-02-05"}},
                ]}})
            ws = created.get("workspace", "plan/workspace.yaml")
            rev0 = created.get("workspaceRevision")
            await call(s, "validate_workspace", {"workspace": ws})
            await call(s, "render_workspace", {"workspace": ws, "format": "png", "locale": "ja-JP"})
            # edit: move build later
            r1 = await call(s, "apply_authoring_command", {"workspace": ws, "command": cmd(
                "c1-move-build", "setWorkspaceTask", rev0,
                {"task": {"id": "build", "title": "実装（延長）", "planned": {"start": "2026-12-28", "finish": "2027-02-05"}}})})
            rev1 = (r1.get("authoringResult") or {}).get("resultRevision")
            # add a new task
            r2 = await call(s, "apply_authoring_command", {"workspace": ws, "command": cmd(
                "c2-add-docs", "setWorkspaceTask", rev1,
                {"task": {"id": "docs", "title": "文書", "planned": {"start": "2027-01-11", "finish": "2027-01-29"}}})})
            rev2 = (r2.get("authoringResult") or {}).get("resultRevision")
            # actual
            r3 = await call(s, "apply_authoring_command", {"workspace": ws, "command": cmd(
                "c3-actual", "setWorkspaceActual", rev2,
                {"actual": {"taskId": "design", "actual": {"start": "2026-12-14", "finish": "2026-12-28"}, "progress": 1}})})
            rev3 = (r3.get("authoringResult") or {}).get("resultRevision")
            await call(s, "render_workspace", {"workspace": ws, "format": "png", "locale": "ja-JP"})
            # stale base
            await call(s, "apply_authoring_command", {"workspace": ws, "command": cmd(
                "c4-stale", "setWorkspaceTask", rev0,
                {"task": {"id": "test", "title": "試験", "planned": {"start": "2027-02-08", "finish": "2027-02-19"}}})})
            # replay c1 exactly
            await call(s, "apply_authoring_command", {"workspace": ws, "command": cmd(
                "c1-move-build", "setWorkspaceTask", rev0,
                {"task": {"id": "build", "title": "実装（延長）", "planned": {"start": "2026-12-28", "finish": "2027-02-05"}}})})
            # revert c1 by inverse at current revision
            r5 = await call(s, "apply_authoring_command", {"workspace": ws, "command": cmd(
                "c5-revert-build", "setWorkspaceTask", rev3,
                {"task": {"id": "build", "title": "実装", "planned": {"start": "2026-12-28", "finish": "2027-01-22"}}})})
            rev5 = (r5.get("authoringResult") or {}).get("resultRevision")
            # revert the added task? (no delete operation documented)
            await call(s, "workspace_revision", {"workspace": ws})
            await call(s, "validate_workspace", {"workspace": ws})
            await call(s, "render_workspace", {"workspace": ws, "format": "png", "locale": "ja-JP"})
            await call(s, "render_workspace", {"workspace": ws, "format": "png", "locale": "en-US"})
            # switch preset
            await call(s, "apply_authoring_command", {"workspace": ws, "command": cmd(
                "c6-preset", "selectPresentationPreset", rev5,
                {"preset": {"id": "marquee", "version": "1", "path": "preset/preset.yaml"}})})
    json.dump([(n, a, o) for n, a, o in LOG], open(os.path.join(HERE, "transcript.json"), "w"), ensure_ascii=False, indent=1)


asyncio.run(main())
