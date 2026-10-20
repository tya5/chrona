#!/bin/sh
# usage: render.sh OUTDIR LOCALE EXT [extra args]
cd "$(dirname "$0")"
D=$1; L=$2; E=$3; shift 3; mkdir -p $D
../t14/.venv/bin/chrona render plan/project.yaml --actual plan/actual.yaml --snapshot plan/baseline.yaml --preset looks/board-mono/preset.yaml --viewport ${VP:-1684x1191} --locale $L --output $D/$L.$E "$@" > $D/$L.$E.json 2>/dev/null
echo "exit=$?"
python3 -c "
import json,sys;d=json.load(open('$D/$L.$E.json'));print(d['status'])
for w in d.get('warnings',[])+d.get('diagnostics',[]): print(w['code'], '|', w.get('sourceRef'),'|', w.get('message','')[:260])"
