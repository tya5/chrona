#!/bin/sh
# one.sh DESIGN CASE LOCALE   (CASE in A B C1 C2 C3 C4 D E)
cd "$(dirname "$0")"
P=$1; C=$2; L=$3; O=r/$P; mkdir -p $O
lang=en; [ $L = ja-JP ] && lang=ja
base=$(echo $C | cut -c1)
PR="--preset $P"; VP=""
case $C in C1) VP="--viewport 1280x720";; C2) VP="--viewport 1024x768";; C3) PR="--preset looks/$P/preset.yaml";; C4) VP="--viewport 900xauto";; esac
N=$O/$C-$L
s=$(python3 -c 'import time;print(time.time())')
../t14/.venv/bin/chrona render plan/$base-$lang-project.yaml --actual plan/$base-$lang-actual.yaml --snapshot plan/$base-$lang-baseline.yaml $PR $VP --locale $L --output $N.svg --emit-scene $N.scene.json > $N.json 2>$N.err
rc=$?
e=$(python3 -c 'import time;print(time.time())')
python3 -c "print('$P $C $L rc=$rc', round($e-$s,1))" >> times.txt
