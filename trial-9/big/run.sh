#!/bin/sh
# Time 150-task renders; capture stderr to see when the cost warning appears.
cd "$(dirname "$0")"
C=../venv/bin/chrona
for p in chrona-default-draft target-b; do
  s=$(date +%s)
  $C render big.chrona --preset $p --output big-$p.png > big-$p.json 2> big-$p.err
  e=$(date +%s)
  echo "$p exit=$? seconds=$((e - s)) cost=$(grep -c W_LAYOUT_ROUTING_COST big-$p.json) err_cost=$(grep -c W_LAYOUT_ROUTING_COST big-$p.err)"
done
s=$(date +%s)
$C render big.chrona --preset target-b --relations none --output big-target-b-norel.png > big-norel.json 2> big-norel.err
e=$(date +%s)
echo "target-b --relations none seconds=$((e - s))"
