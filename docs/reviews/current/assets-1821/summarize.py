import json,re,sys,collections
pat=re.compile(r'[+\-−]\d+')
for f in sys.argv[1:]:
    d=json.load(open(f))
    by=collections.defaultdict(collections.Counter)
    def walk(o):
        if isinstance(o,dict):
            if o.get('kind')=='Text' and isinstance(o.get('text'),str) and pat.search(o['text']):
                by[o.get('purpose')][o['text']]+=1
            for v in o.values(): walk(v)
        elif isinstance(o,list):
            for v in o: walk(v)
    walk(json.load(open(f)))
    print(f)
    for p,c in by.items(): print('  ',p,dict(sorted(c.items())))
