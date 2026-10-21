import json,glob,collections
for f in sorted(glob.glob('r/*/*.json')):
    if f.endswith('scene.json'): continue
    d=json.load(open(f)); ds=d.get('warnings',[])+d.get('diagnostics',[])
    c=collections.Counter(x['code'] for x in ds)
    print(f[2:], d['status'], dict(c))
