import json,glob,re,sys
sys.path.insert(0,'.')
from check import prims,box,pts
for f in sorted(glob.glob('r/*/*.scene.json')):
    s=json.load(open(f)); ps=[]; prims(s['surfaces'],ps)
    bars={p['sourceRef']:box(p) for p in ps if p['purpose']=='planned' and p['bounds']['inlineSize']>0}
    deps=[p for p in ps if p['purpose']=='dependency']
    n=0; ex=[]
    for d in deps:
        m=re.search(r'd-(s\d+t\d+)-(\w+)',d['sourceRef'])
        if not m: continue
        a,b=m.groups()
        if a not in bars or b not in bars: continue
        q=pts(d); minx=min(x for x,y in q)
        # left of both endpoints' starts by a large margin
        lim=min(bars[a][0],bars[b][0])
        if minx < lim-20: n+=1; ex.append(f'{a}->{b} minx={minx:.0f} predStart={bars[a][0]:.0f} succStart={bars[b][0]:.0f}')
    if n: print(f, f'{n}/{len(deps)}', ex[:2])
