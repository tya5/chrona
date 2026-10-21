#!/bin/sh
# one.sh DESIGN WEEK LOCALE
cd "$(dirname "$0")"
P=$1; W=$2; L=$3; O=r/$P; mkdir -p $O
A=""; [ $W -gt 0 ] && A="--actual plan/w$W-actual.yaml"
s=$(python3 -c 'import time;print(time.time())')
../t14/.venv/bin/chrona render plan/w$W-project.yaml $A --snapshot plan/baseline.yaml --preset $P --locale $L --output $O/w$W-$L.svg --emit-scene $O/w$W-$L.scene.json > $O/w$W-$L.json 2>$O/w$W-$L.err
rc=$?
e=$(python3 -c 'import time;print(time.time())')
python3 -c "print('$P w$W $L rc=$rc', round($e-$s,1),'s')" | tee -a times.txt
