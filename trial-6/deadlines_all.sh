#!/bin/bash
# Which presets can draw deadlines? Copy each, add `deadlines: {show: all}` to its View, render.
cd "$(dirname "$0")"
C=../.venv/bin/chrona
mkdir -p looks-dl out/dl
for p in target-b marquee sunday titlecard yuya executive-light mission-light technical-print muted-executive wallboard-dark chrona-default-draft; do
  rm -rf looks-dl/$p
  $C preset copy $p --output looks-dl/$p > /dev/null
  sed -i '' 's/^  surface: table-timeline/  surface: table-timeline\n  deadlines: {show: all}/' looks-dl/$p/view.yaml
  $C render plan.yaml --actual actual-week2.yaml --snapshot baseline.yaml --preset looks-dl/$p/preset.yaml \
    --output out/dl/$p.png > out/dl/$p.json 2>/dev/null
  python3 -c "
import json,sys
d=json.load(open('out/dl/$p.json'))
print('$p', d['status'], [(x['code'], x.get('sourceRef'), x['message'][:90]) for x in d.get('diagnostics',[])])"
done
