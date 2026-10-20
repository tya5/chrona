#!/bin/sh
# usage: render.sh PRESET OUTNAME
cd "$(dirname "$0")"
mkdir -p out
P=${1:-nordic/preset.yaml}; N=${2:-nordic}
C=venv/bin/chrona
$C render plan/plan-en.yaml --actual plan/actual-en.yaml --snapshot plan/baseline-en.yaml --preset "$P" --locale en-US --output out/$N-en.png --emit-scene out/$N-en.scene.json.tmp > out/$N-en.json; echo "en exit $?"
$C render plan/plan-ja.yaml --actual plan/actual-ja.yaml --snapshot plan/baseline-ja.yaml --preset "$P" --locale ja-JP --output out/$N-ja.png > out/$N-ja.json; echo "ja exit $?"
rm -f out/$N-en.scene.json.tmp
python3 -c "
import json,sys,collections
for l in ('en','ja'):
    d=json.load(open('out/$N-'+l+'.json'))
    print(l, d.get('status'), [ (x['code'],x.get('count',1)) for x in d.get('diagnostics',[])+d.get('warnings',[])])
"
