import json,glob,sys
def prims(o,out):
    if isinstance(o,dict):
        if 'bounds' in o and 'purpose' in o and isinstance(o['bounds'],dict) and 'inline' in o['bounds']:
            out.append(o)
        for v in o.values(): prims(v,out)
    elif isinstance(o,list):
        for v in o: prims(v,out)
def box(p):
    b=p['bounds']; return b['inline'],b['block'],b['inline']+b['inlineSize'],b['block']+b['blockSize']
def inter(a,b):
    return max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
MARK={'planned','actual','snapshot','progress-fill'}
for f in sorted(glob.glob('r/*/w*-*.scene.json')):
    s=json.load(open(f)); ps=[]; prims(s['surfaces'],ps)
    boxes=[p for p in ps if p['purpose']=='annotation-box']
    texts=[p for p in ps if p.get('kind')=='Text']
    hits=[]
    for bx in boxes:
        B=box(bx)
        for m in ps:
            if m['purpose'] in MARK and m.get('sourceRef')!=bx['sourceRef'].split('-')[0]:
                a=inter(B,box(m))
                if a>0.3*m['bounds']['inlineSize']*m['bounds']['blockSize']: hits.append(f"box {bx['sourceRef']} covers {m['purpose']}:{m['sourceRef']}")
    # text-text overlaps
    for i,a in enumerate(texts):
        for b in texts[i+1:]:
            if inter(box(a),box(b))>4 and a.get('sourceRef')!=b.get('sourceRef'):
                hits.append(f"text {a['id']} x {b['id']}")
    if hits: print(f, len(hits)); [print('   ',h) for h in hits[:12]]
