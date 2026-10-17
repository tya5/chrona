import sys, yaml
d = sys.argv[1]; points = sys.argv[2] if len(sys.argv) > 2 else None
th = yaml.safe_load(open(f'{d}/theme.yaml'))
th['body'].setdefault('colorScales', {})['risk'] = {'slots': {'low': 'riskLow', 'medium': 'riskMedium', 'high': 'riskHigh'}}
yaml.safe_dump(th, open(f'{d}/theme.yaml', 'w'), sort_keys=False, allow_unicode=True)
sc = yaml.safe_load(open(f'{d}/scheme.yaml'))
sc['body'].setdefault('categories', {}).update({'riskLow': '#9FD8C2', 'riskMedium': '#F3C77A', 'riskHigh': '#E5786D'})
yaml.safe_dump(sc, open(f'{d}/scheme.yaml', 'w'), sort_keys=False, allow_unicode=True)
v = yaml.safe_load(open(f'{d}/view.yaml'))
b = v['body']
b['colorEncoding'] = {'scale': 'risk', 'target': 'planned', 'source': {'field': 'risk'}, 'domain': ['low', 'medium', 'high']}
b['deadlines'] = {'show': 'all'}
if points:
    b.setdefault('rows', {})['points'] = points
    if points == 'key-row':
        b['rows']['keyRow'] = {'title': 'Milestones'}
yaml.safe_dump(v, open(f'{d}/view.yaml', 'w'), sort_keys=False, allow_unicode=True)
