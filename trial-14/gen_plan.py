import sys, yaml, os
out = sys.argv[1]
streams = {
 'ee':  ('Electronics', [('Schematic rev C',10),('Layout rev C',12),('EVT board bring-up',8),('Power integrity fixes',10),('DVT board spin',15),('DVT validation',10)]),
 'me':  ('Mechanical',  [('Enclosure CAD v2',10),('Thermal simulation',6),('Soft tooling',15),('Drop and ingress test',8),('Hard tooling kickoff',20),('T1 sample review',6)]),
 'fw':  ('Firmware',    [('Bootloader hardening',8),('Sensor driver port',10),('OTA update pipeline',15),('Power management',10),('Field diagnostics',8),('Release candidate 1',6)]),
 'mfg': ('Manufacturing',[('CM selection',10),('Line layout',8),('Test fixture design',12),('Pilot build 1',6),('Yield analysis',8),('Pilot build 2',6)]),
 'cert':('Certification',[('Pre-scan EMC',5),('FCC/CE test plan',6),('Safety file prep',10),('Lab EMC run',8),('Radio cert submission',5),('Cert review response',10)]),
}
# slip factors for current plan vs baseline (by task index)
slip = {('ee',3):5,('ee',4):5,('me',2):8,('fw',2):6,('mfg',3):3,('cert',3):4}
gates = [
 ('g-evt-exit','EVT exit',[('ee',2),('me',1)]),
 ('g-design-freeze','Design freeze',[('ee',3),('me',3)]),
 ('g-fw-feature','FW feature complete',[('fw',4)]),
 ('g-pilot','Pilot go/no-go',[('mfg',3)]),
 ('g-dvt-exit','DVT exit',[('ee',5),('me',5),('fw',5)]),
 ('g-cert','Cert submitted',[('cert',4)]),
]
def build(baseline):
    objs, rels = {}, []
    objs['kickoff'] = {'type':'gate','title':'Q4 kickoff','schedule':{'mode':'fixed-point','at':'2026-10-01'}}
    for s,(title,tasks) in streams.items():
        objs[s] = {'type':'group','title':title,'schedule':{'mode':'rollup'}}
        prev = ('kickoff','at')
        for i,(t,a) in enumerate(tasks):
            oid = f'{s}-{i+1}'
            amt = a + (0 if baseline else slip.get((s,i),0))
            objs[oid] = {'type':'task','title':t,'parent':s,'calendar':'office','fields':{'stream':title},
                         'schedule':{'mode':'scheduled','amount':f'{amt}wd'}}
            rels.append({'id':f'r-{oid}','type':'dependency','from':{'object':prev[0],'endpoint':prev[1]},'to':{'object':oid,'endpoint':'start'},'lag':'0d'})
            prev = (oid,'end')
    for gid,gt,preds in gates:
        objs[gid] = {'type':'gate','title':gt,'schedule':{'mode':'scheduled-point'}}
        for s,i in preds:
            rels.append({'id':f'r-{s}-{i+1}-{gid}','type':'dependency','from':{'object':f'{s}-{i+1}','endpoint':'end'},'to':{'object':gid,'endpoint':'at'},'lag':'0d'})
    objs['g-dvt-exit']['deadline'] = '2027-02-26'
    doc = {'version':'timeline/v0.7',
           'project':{'id':'atlas-q4','title':'Atlas sensor hub - Q4 portfolio review','calendar':'office'},
           'fieldRoles':{'responsible':'stream'},
           'calendars':{'office':{'working_days':['mon','tue','wed','thu','fri'],
               'exceptions':[{'date':'2026-11-26','working':False},{'date':'2026-11-27','working':False},
                             {'date':'2026-12-24','working':False},{'date':'2026-12-25','working':False},{'date':'2027-01-01','working':False}]}},
           'objects':objs,'relations':rels}
    if not baseline:
        doc['annotations'] = {
          'n1':{'kind':'note','text':'Ground-plane fix adds 5 wd','anchor':{'object':'ee-4'}},
          'n2':{'kind':'note','text':'Tooling vendor change','anchor':{'object':'me-3'}},
          'n3':{'kind':'risk','text':'OTA signing keys pending','anchor':{'object':'fw-3'}},
          'n4':{'kind':'note','text':'Board approval needed','anchor':{'object':'g-pilot'}},
        }
    return doc
yaml.safe_dump(build(False), open(os.path.join(out,'project.yaml'),'w'), sort_keys=False, allow_unicode=True)
yaml.safe_dump(build(True), open(os.path.join(out,'baseline.yaml'),'w'), sort_keys=False, allow_unicode=True)
