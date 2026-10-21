import yaml, os, datetime as dt, copy
OUT = os.path.dirname(os.path.abspath(__file__)) + '/plan'
os.makedirs(OUT, exist_ok=True)
D = dt.date
W = dt.timedelta(weeks=1); d1 = dt.timedelta(days=1)
streams = {
 'plat': ('Platform', D(2026,10,5), [('arch','Architecture spike',2),('gw','API gateway',4),('auth','Auth service',3),('bill','Billing service',4),('load','Load testing',2),('hard','Hardening',3),('relops','Release ops',2)]),
 'mob':  ('Mobile app', D(2026,10,5), [('ux','UX research',3),('ds','Design system',3),('ios','iOS app shell',5),('and','Android app shell',5),('sync','Offline sync',3),('store','Store submission',2)]),
 'data': ('Data', D(2026,10,5), [('evt','Event schema',2),('pipe','Pipeline MVP',4),('wh','Warehouse model',3),('dash','Dashboards',3),('ml','ML scoring pilot',4),('dqa','Data QA',2)]),
 'gtm':  ('Go-to-market', D(2026,10,26), [('mkt','Market sizing',2),('price','Pricing study',3),('beta','Beta recruitment',4),('web','Partner webinar',2),('camp','Launch campaign',4),('enab','Sales enablement',3)]),
}
gates = [('g1','Design review',D(2026,11,6)),('g2','Alpha',D(2026,12,11)),('g3','Beta start',D(2027,1,29)),('g4','Launch readiness',D(2027,3,5)),('g5','GA',D(2027,3,31))]
# per-week plan edits: extra days on a task's duration (shifts successors)
def plan(week):
    extra = {}
    if week >= 2: extra['gw'] = 21          # API gateway slips 3 weeks
    if week >= 1: extra['evt'] = 2          # event schema finished late (+2d) -> pipeline starts later
    removed = {'web'} if week >= 3 else set()
    objs, rels = {}, []
    for sid,(title,start,tasks) in streams.items():
        objs[sid] = {'type':'group','title':title,'schedule':{'mode':'rollup'}}
        cur = start; prev = None
        for tid,tt,wk in tasks:
            if tid in removed: continue
            end = cur + wk*W + dt.timedelta(days=extra.get(tid,0))
            objs[tid] = {'type':'task','title':tt,'parent':sid,'fields':{'stream':title},
                         'schedule':{'mode':'fixed-span','start':str(cur),'end':str(end)}}
            if prev: rels.append({'id':f'{prev}-{tid}','type':'dependency','from':{'object':prev,'endpoint':'end'},'to':{'object':tid,'endpoint':'start'},'lag':'0d'})
            prev = tid; cur = end
    if week >= 2:
        objs['pen'] = {'type':'task','title':'Security pen test','parent':'plat','fields':{'stream':'Platform'},
                       'schedule':{'mode':'fixed-span','start':'2026-11-16','end':'2026-12-07'}}
    for gid,gt,at in gates:
        objs[gid] = {'type':'gate','title':gt,'schedule':{'mode':'fixed-point','at':str(at)}}
    doc = {'version':'timeline/v0.7',
           'project':{'id':'nova','title':'Nova app launch plan','calendar':'office'},
           'fieldRoles':{'responsible':'stream'},
           'calendars':{'office':{'working_days':['mon','tue','wed','thu','fri'],
               'exceptions':[{'date':'2026-11-26','working':False},{'date':'2026-12-25','working':False},{'date':'2027-01-01','working':False}]}},
           'objects':objs,'relations':rels}
    ann = {}
    if week >= 1: ann['n1'] = {'kind':'note','text':'Schema review took 2 extra days','anchor':{'object':'evt'}}
    if week >= 2: ann['r1'] = {'kind':'risk','text':'Vendor rate limits block gateway','anchor':{'object':'gw'}}
    if week >= 3: ann['n2'] = {'kind':'note','text':'Early finish frees one engineer','anchor':{'object':'pipe'}}
    if week >= 3: ann['r2'] = {'kind':'risk','text':'Design review missed: sign-off pending','anchor':{'object':'g1'}}
    if ann: doc['annotations'] = ann
    return doc
asof = {1:'2026-10-26',2:'2026-11-02',3:'2026-11-09'}
obs_by_week = {
 1: [('arch',{'start':'2026-10-05','finish':'2026-10-16','progress':1}),   # early (planned 10-19)
     ('gw',{'start':'2026-10-16','openUntil':'asOf','progress':0.15}),
     ('ux',{'start':'2026-10-05','openUntil':'asOf','progress':0.9}),
     ('evt',{'start':'2026-10-05','finish':'2026-10-21','progress':1}),    # late (+2d)
     ('pipe',{'start':'2026-10-21','openUntil':'asOf','progress':0.1}),
     ('mkt',{'start':'2026-10-26','openUntil':'asOf','progress':0.0})],
 2: [('gw',{'start':'2026-10-16','openUntil':'asOf','progress':0.25}),
     ('ux',{'start':'2026-10-05','finish':'2026-10-28','progress':1}),     # late 2d
     ('ds',{'start':'2026-10-28','openUntil':'asOf','progress':0.2}),
     ('pipe',{'start':'2026-10-21','openUntil':'asOf','progress':0.4}),
     ('mkt',{'start':'2026-10-26','openUntil':'asOf','progress':0.5})],
 3: [('gw',{'start':'2026-10-16','openUntil':'asOf','progress':0.35}),
     ('ds',{'start':'2026-10-28','openUntil':'asOf','progress':0.5}),
     ('pipe',{'start':'2026-10-21','finish':'2026-11-06','progress':1}),   # early (planned 11-20)
     ('wh',{'start':'2026-11-06','openUntil':'asOf','progress':0.1}),
     ('mkt',{'start':'2026-10-26','finish':'2026-11-06','progress':1}),    # early (planned 11-09)
     ('price',{'start':'2026-11-06','openUntil':'asOf','progress':0.1})],
}
base = plan(0)
yaml.safe_dump(base, open(f'{OUT}/baseline.yaml','w'), sort_keys=False)
for w in range(4):
    yaml.safe_dump(plan(w), open(f'{OUT}/w{w}-project.yaml','w'), sort_keys=False)
    if w == 0: continue
    obs = []; seq = {}
    for ww in range(1, w+1):
        for oid,a in obs_by_week[ww]:
            seq[oid] = seq.get(oid,0)+1
            obs.append({'id':f'{oid}-{seq[oid]}','sequence':seq[oid],'projectObjectId':oid,'actual':a})
    doc = {'version':'chrona/actual-set/v0.3','kind':'actual-set','id':'nova-observed','body':{'asOf':asof[w],'observations':obs}}
    yaml.safe_dump(doc, open(f'{OUT}/w{w}-actual.yaml','w'), sort_keys=False)
print(sum(1 for o in base['objects'].values() if o['type']=='task'), 'tasks')
