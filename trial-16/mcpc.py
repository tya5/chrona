import asyncio, json, sys, base64, time, os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
OUT=os.path.dirname(os.path.abspath(__file__))
PY=sys.executable
async def main(calls_file, tag):
    calls=json.load(open(calls_file))
    params=StdioServerParameters(command=PY,args=["-m","chrona","mcp","--workspace",os.path.join(OUT,"ws"),"--allow-write"])
    async with stdio_client(params) as (r,w):
        async with ClientSession(r,w) as s:
            init=await s.initialize()
            log=[]
            for i,c in enumerate(calls):
                t=time.time()
                if c["tool"]=="__list__":
                    res=await s.list_tools()
                    d=[{"name":x.name,"description":x.description,"inputSchema":x.input_schema} for x in res.tools]
                    json.dump(d,open(f"{OUT}/{tag}-tools.json","w"),ensure_ascii=False,indent=1)
                    print("tools:",[x["name"] for x in d]); continue
                if c["tool"]=="__resources__":
                    res=await s.list_resources(); print([str(x.uri) for x in res.resources])
                    for x in res.resources:
                        rr=await s.read_resource(x.uri)
                        open(f"{OUT}/{tag}-res-{str(x.uri).split('/')[-1]}.md","w").write(rr.contents[0].text)
                    continue
                try:
                    res=await s.call_tool(c["tool"],c.get("args",{}))
                except Exception as e:
                    print(f'== [{i}] EXC',repr(e)); continue
                dt=time.time()-t
                parts=[]
                for j,ct in enumerate(res.content):
                    if ct.type=="text":
                        parts.append(ct.text)
                    elif ct.type=="image":
                        fn=f"{OUT}/{tag}-{i}-{c.get('name',c['tool'])}.png"
                        open(fn,"wb").write(base64.b64decode(ct.data)); parts.append(f"<image {fn}>")
                    else: parts.append(f"<{ct.type}>")
                sc=getattr(res,"structured_content",None)
                rec={"i":i,"tool":c["tool"],"sec":round(dt,2),"isError":res.is_error,"content":parts,"structured":sc}
                log.append(rec)
                txt="\n".join(parts)
                print(f"== [{i}] {c['tool']} {dt:.2f}s isError={res.is_error}\n{txt[:c.get('max',3000)]}")
            json.dump(log,open(f"{OUT}/{tag}-log.json","w"),ensure_ascii=False,indent=1,default=str)
asyncio.run(main(sys.argv[1],sys.argv[2]))
