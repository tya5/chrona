import json,glob,re,sys
REQ={'A':(1600,None),'B':(1600,None),'D':(1600,None),'E':(1600,None),'C1':(1280,720),'C2':(1024,768),'C3':(1123,794),'C4':(900,None)}
def prims(o,out):
    if isinstance(o,dict):
        if 'purpose' in o and 'kind' in o: out.append(o)
        for v in o.values(): prims(v,out)
    elif isinstance(o,list):
        for v in o: prims(v,out)
def box(p):
    b=p['bounds']; return (b['inline'],b['block'],b['inline']+b['inlineSize'],b['block']+b['blockSize'])
def inter(a,b): return max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
def pts(p):
    if 'points' in p: return [tuple(x) for x in p['points']]
    out=[]
    for c in p.get('pathCommands',[]):
        out+= [tuple(x) for x in c['points']][-1:] if c['kind']=='quadratic' else [tuple(x) for x in c['points']]
    return out
def segs(p):
    q=pts(p); return list(zip(q,q[1:]))
def seg_box(s,b,shrink=0.5):
    (x1,y1),(x2,y2)=s; b=(b[0]+shrink,b[1]+shrink,b[2]-shrink,b[3]-shrink)
    if abs(y1-y2)<1e-6: return b[1]<y1<b[3] and max(min(x1,x2),b[0])<min(max(x1,x2),b[2])
    if abs(x1-x2)<1e-6: return b[0]<x1<b[2] and max(min(y1,y2),b[1])<min(max(y1,y2),b[3])
    # diagonal: sample
    for i in range(1,40):
        t=i/40; x=x1+(x2-x1)*t; y=y1+(y2-y1)*t
        if b[0]<x<b[2] and b[1]<y<b[3]: return True
    return False
def cross(s,t):
    (a,b),(c,d)=s,t
    def o(p,q,r): return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
    d1,d2,d3,d4=o(c,d,a),o(c,d,b),o(a,b,c),o(a,b,d)
    return d1*d2<-1e-6 and d3*d4<-1e-6
def main():
  files=sorted(glob.glob('r/*/*.scene.json'))
  if len(sys.argv)>1: files=[f for f in files if any(a in f for a in sys.argv[1:])]
  for f in files:
      m=re.match(r'r/([^/]+)/([A-Z]\d?)-(\w\w-\w\w)',f); d,c,l=m.groups()
      s=json.load(open(f)); ps=[]; prims(s['surfaces'],ps)
      W,H=s['viewport']['inlineSize'],s['viewport']['blockSize']
      rw,rh=REQ[c]; out=[]
      if W>rw+0.5: out.append(f'canvas width {W:.0f} > requested {rw}')
      if rh and H>rh+0.5: out.append(f'canvas height {H:.0f} > requested {rh}')
      texts=[p for p in ps if p['kind']=='Text']
      for p in ps:
          if p['kind'] in('Text','Rect') and p['bounds']['inlineSize']>0:
              b=box(p)
              if b[2]>W+1 or b[3]>H+1 or b[0]<-1 or b[1]<-1: out.append(f"off-canvas {p['purpose']} {p['id'][:50]} {tuple(round(x) for x in b)}")
      tt=0; ex=[]
      for i,a in enumerate(texts):
          for b in texts[i+1:]:
              if a.get('sourceRef')==b.get('sourceRef') and a['purpose']==b['purpose']: continue
              ar=inter(box(a),box(b))
              if ar>0.15*min(a['bounds']['inlineSize']*a['bounds']['blockSize'],b['bounds']['inlineSize']*b['bounds']['blockSize']) and ar>4:
                  tt+=1; ex.append(f"{a['purpose']}:{a['id'][:40]} x {b['purpose']}:{b['id'][:40]}")
      if tt: out.append(f'text-text overlaps {tt}: '+' | '.join(ex[:4]))
      bars=[p for p in ps if p['purpose'] in('planned','actual') and p['kind'] in('Rect','Symbol') and p['bounds']['inlineSize']>0]
      deps=[p for p in ps if p['purpose']=='dependency']
      nthru=0; ex=[]
      for dp in deps:
          ends=set(re.findall(r':(s\d+t\d+|g\d+)',dp['id']))
          for sg in segs(dp):
              for b in bars:
                  if b.get('sourceRef') in ends: continue
                  if seg_box(sg,box(b),1.0): nthru+=1; ex.append(f"{dp['sourceRef']}->{b['sourceRef']}"); break
      if nthru: out.append(f'dependency segments through other bars {nthru}/{len(deps)} deps: '+', '.join(ex[:5]))
      dt=0
      for dp in deps:
          for sg in segs(dp):
              if any(seg_box(sg,box(t),1.0) for t in texts if t['purpose'] not in('axis-label',)): dt+=1; break
      if dt: out.append(f'dependency through text {dt}')
      leaders=[p for p in ps if p['purpose']=='annotation-leader']
      boxes={p['sourceRef']:p for p in ps if p['purpose']=='annotation-box'}
      lc=0
      for i,a in enumerate(leaders):
          for b in leaders[i+1:]:
              if any(cross(x,y) for x in segs(a) for y in segs(b)): lc+=1
      if lc: out.append(f'annotation leaders crossing each other: {lc} pairs')
      # rail order inversion: anchor y (leader first point) vs box top
      pairs=[]
      for L in leaders:
          q=pts(L)
          if q and L['sourceRef'] in boxes: pairs.append((q[0][1],box(boxes[L['sourceRef']])[1],L['sourceRef']))
      inv=sum(1 for i,a in enumerate(pairs) for b in pairs[i+1:] if (a[0]-b[0])*(a[1]-b[1])<0 and abs(a[0]-b[0])>2)
      if inv: out.append(f'annotation order inversions (anchor vs box) {inv}')
      lb=0; ex=[]
      for L in leaders:
          for sg in segs(L):
              for b in bars:
                  if b.get('sourceRef') and b['sourceRef'] in L['sourceRef']: continue
                  if seg_box(sg,box(b),1.0): lb+=1; ex.append(f"{L['sourceRef']}->{b['sourceRef']}"); break
      if lb: out.append(f'leader segments through bars {lb}: '+', '.join(ex[:4]))
      cov=[]
      for k,bx in boxes.items():
          for b in bars:
              if inter(box(bx),box(b))>0.2*b['bounds']['inlineSize']*max(b['bounds']['blockSize'],1): cov.append(f"{k} covers {b['sourceRef']}")
          for t in texts:
              if t['purpose'] not in('annotation-text','annotation-kind-label','annotation-title') and not t['id'].startswith('annotation') and inter(box(bx),box(t))>4: cov.append(f"{k} covers text {t['purpose']}:{t['id'][:30]}")
      if cov: out.append(f'annotation boxes covering marks/text {len(cov)}: '+', '.join(cov[:5]))
      print(f'== {d} {c} {l}  canvas {W:.0f}x{H:.0f}')
      for o in out: print('   ',o)

if __name__=='__main__': main()
