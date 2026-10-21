import asyncio, json, sys, os, base64
sys.path.insert(0, os.path.dirname(__file__))
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
OUT=os.path.dirname(os.path.abspath(__file__))
async def main():
    p=StdioServerParameters(command=sys.executable,args=["-m","chrona","mcp","--workspace",OUT+"/ws","--allow-write"])
    async with stdio_client(p) as (r,w):
        async with ClientSession(r,w) as s:
            await s.initialize()
            async def call(name,args,tag=None):
                try:
                    res=await s.call_tool(name,args)
                except Exception as e:
                    print("== EXC",name,tag,repr(e)[:400]); return {}
                txt=[c.text for c in res.content if c.type=="text"]
                for c in res.content:
                    if c.type=="image" and tag: open(f"{OUT}/s7-{tag}.png","wb").write(base64.b64decode(c.data))
                d=json.loads(txt[0]); print("==",name,tag,json.dumps(d,ensure_ascii=False)[:900]); return d
            ws="guided/workspace.yaml"
            rev=(await call("workspace_revision",{"workspace":ws}))["workspaceRevision"]
            def cmd(cid,typ,payload,base):
                cid="b-"+cid
                return {"version":"chrona/authoring-command/v0.1","commandId":cid,"type":typ,"target":{"kind":"authoring-workspace","path":"workspace.yaml"},"baseRevision":base,"payload":payload}
            acts=[("requirements","2027-01-04","2027-01-12"),("api-spec","2027-01-12","2027-01-19"),("ux-design","2027-01-04","2027-01-22")]
            rev0=rev
            for tid,a,b in acts:
                d=await call("apply_authoring_command",{"workspace":ws,"command":cmd("act-"+tid,"setWorkspaceActual",{"actual":{"taskId":tid,"actual":{"start":a,"finish":b},"progress":1}},rev)})
                rev=d["authoringResult"]["resultRevision"]
            # open task: try without finish
            d=await call("apply_authoring_command",{"workspace":ws,"command":cmd("act-auth-open","setWorkspaceActual",{"actual":{"taskId":"auth-api","actual":{"start":"2027-01-19"},"progress":0.1}},rev)})
            # mistaken edit: wrong actual for api-spec
            d=await call("apply_authoring_command",{"workspace":ws,"command":cmd("act-api-spec-mistake","setWorkspaceActual",{"actual":{"taskId":"api-spec","actual":{"start":"2027-01-12","finish":"2027-01-29"},"progress":1}},rev)})
            rev=d["authoringResult"]["resultRevision"]
            await call("render_workspace",{"workspace":ws,"locale":"ja-JP","format":"png"},"g2-mistake")
            # revert: inverse edit
            d=await call("apply_authoring_command",{"workspace":ws,"command":cmd("act-api-spec-revert","setWorkspaceActual",{"actual":{"taskId":"api-spec","actual":{"start":"2027-01-12","finish":"2027-01-19"},"progress":1}},rev)})
            rev2=d["authoringResult"]["resultRevision"]
            # replay same commandId (should be no-op)
            await call("apply_authoring_command",{"workspace":ws,"command":cmd("act-api-spec-revert","setWorkspaceActual",{"actual":{"taskId":"api-spec","actual":{"start":"2027-01-12","finish":"2027-01-19"},"progress":1}},rev)})
            await call("render_workspace",{"workspace":ws,"locale":"ja-JP","format":"png"},"g3-reverted")
            # risk note via override?
            await call("apply_authoring_command",{"workspace":ws,"command":cmd("risk-note","setPresentationOverride",{"overrides":{"annotations":{"x":1}}},rev2)})
asyncio.run(main())
