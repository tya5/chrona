#!/bin/bash
C=../rv/.venv/bin/chrona
A=(render plan.yaml --snapshot baseline.yaml --actual actual-b-day-before.yaml --forecast --view view-no-format.yaml)
cells(){ python3 - "$1" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); out=[]
def w(o):
    if isinstance(o,dict):
        if o.get('kind')=='Text' and o.get('tableColumnId')=='Delta' and o.get('purpose')=='table-cell': out.append(o['text'])
        for v in o.values(): w(v)
    elif isinstance(o,list):
        for v in o: w(v)
w(d); print('  Delta cells:', ' '.join(out))
PY
}
echo '$ git -C ../rv rev-parse --short HEAD'; git -C ../rv rev-parse --short HEAD
echo '$ sed -n 8p src/chrona/resources/presets/bundles/editorial-readable-default/layout.yaml'; sed -n 8p ../rv/src/chrona/resources/presets/bundles/editorial-readable-default/layout.yaml
echo; echo "# bundled default preset (no --preset = chrona-default-draft, Layout editorial-readable-default); View column has no format"
echo "\$ chrona ${A[*]} --output default.svg --emit-scene default.json"
$C "${A[@]}" --output default.svg --emit-scene default.json | python3 -c "import json,sys; d=json.load(sys.stdin); print('  status', d['status'], *[x['code'] for x in d.get('diagnostics',[])])"
cells default.json
for p in mission-light control-room-dark print-mono executive-light elevated-light technical-print muted-executive wallboard-dark editorial; do
  echo "\$ chrona ${A[*]} --preset $p --output $p.svg --emit-scene $p.json"
  $C "${A[@]}" --preset $p --output $p.svg --emit-scene $p.json | python3 -c "import json,sys; d=json.load(sys.stdin); print('  status', d['status'], *[x['code'] for x in d.get('diagnostics',[])])"
  [ -f $p.json ] && cells $p.json
done
echo; echo "# mission-light, control-room-dark and print-mono reject --forecast (E_FORECAST_PRESENTATION_REQUIRED: no legend slot), so they are rendered without it"
B=(render plan.yaml --snapshot baseline.yaml --actual actual-b-day-before.yaml --view view-no-format.yaml)
for p in mission-light control-room-dark print-mono; do
  echo "\$ chrona ${B[*]} --preset $p --output $p-noforecast.svg --emit-scene $p-noforecast.json"
  $C "${B[@]}" --preset $p --output $p-noforecast.svg --emit-scene $p-noforecast.json | python3 -c "import json,sys; d=json.load(sys.stdin); print('  status', d['status'], *[x['code'] for x in d.get('diagnostics',[])])"
  cells $p-noforecast.json
done
