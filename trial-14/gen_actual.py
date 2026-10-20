import json,sys,yaml,datetime as dt
p=json.load(open(sys.argv[1]))['placements']; proj=yaml.safe_load(open(sys.argv[2]))['objects']
asof=dt.date(2026,11,13); obs=[]; n=0
for oid,pl in p.items():
    o=proj[oid]
    if o['type']=='group': continue
    n+=1
    if 'at' in pl:
        d=dt.date.fromisoformat(pl['at'])
        if d<=asof: obs.append({'id':f'{oid}-1','sequence':1,'projectObjectId':oid,'actual':{'at':pl['at']}})
        continue
    s=dt.date.fromisoformat(pl['start']); e=dt.date.fromisoformat(pl['end'])
    if s>asof: continue
    shift = 2 if hash(oid)%3==0 else 0
    if e+dt.timedelta(days=shift)<=asof:
        obs.append({'id':f'{oid}-1','sequence':1,'projectObjectId':oid,'actual':{'start':pl['start'],'finish':str(e+dt.timedelta(days=shift)),'progress':1}})
    else:
        prog=round(max(0.05,min(0.9,(asof-s).days/max(1,(e-s).days)-0.1)),2)
        obs.append({'id':f'{oid}-1','sequence':1,'projectObjectId':oid,'actual':{'start':pl['start'],'openUntil':'asOf','progress':prog}})
doc={'version':'chrona/actual-set/v0.3','kind':'actual-set','id':'atlas-q4-observed','body':{'asOf':str(asof),'observations':obs}}
yaml.safe_dump(doc,open(sys.argv[3],'w'),sort_keys=False)
print(len(obs))
