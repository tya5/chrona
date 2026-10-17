import sys, yaml
src = yaml.safe_load(open('looks/exec/theme.yaml'))['body']
d = sys.argv[1]
th = yaml.safe_load(open(f'{d}/theme.yaml'))
b = th['body']
for k in ('deadline-mark-width', 'deadline-mark-reach', 'deadline-mark-order'):
    b['values'][k] = src['values'][k]
b['roles']['deadline-mark'] = src['roles']['deadline-mark']
b['colorBindings']['deadline-mark.stroke'] = 'negative'
yaml.safe_dump(th, open(f'{d}/theme.yaml', 'w'), sort_keys=False, allow_unicode=True)
