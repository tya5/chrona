#!/bin/sh
# Render plan.chrona with every bundled preset in ja-JP (and en-US for comparison).
cd "$(dirname "$0")"
C=../venv/bin/chrona
mkdir -p out
for p in mission-light control-room-dark print-mono executive-light elevated-light editorial technical-print chrona-default-draft marquee sunday target-b titlecard yuya muted-executive wallboard-dark; do
  for loc in ja-JP en-US; do
    $C render plan.chrona --actual actual.yaml --preset $p --locale $loc --output out/$p-$loc.svg > out/$p-$loc.json 2> out/$p-$loc.err
    echo "$p $loc exit=$? $(head -c 200 out/$p-$loc.json)"
  done
  $C render plan.chrona --actual actual.yaml --preset $p --locale ja-JP --output out/$p-ja-JP.png > /dev/null 2>&1
done
