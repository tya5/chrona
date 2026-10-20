#!/bin/sh
cd "$(dirname "$0")"
C=../venv/bin/chrona
$C compile revised.chrona --output revised.yaml
for p in target-b yuya technical-print; do
for loc in en-US ja-JP; do
  $C render revised.yaml --actual ../ja/actual.yaml --snapshot baseline.yaml --preset $p --locale $loc --output cmp-$p-$loc.png > cmp-$p-$loc.json; echo "cmp $p $loc $?"
  $C render revised.yaml --actual ../ja/actual.yaml --snapshot baseline.yaml --preset $p --locale $loc --output cmp-$p-$loc.svg > /dev/null
  $C render revised.yaml --actual ../ja/actual.yaml --snapshot baseline.yaml --forecast --preset $p --locale $loc --output fc-$p-$loc.png > fc-$p-$loc.json; echo "fc $p $loc $?"
  $C render revised.yaml --actual ../ja/actual.yaml --snapshot baseline.yaml --forecast --preset $p --locale $loc --output fc-$p-$loc.svg > /dev/null
done
done
