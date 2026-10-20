#!/bin/sh
cd "$(dirname "$0")"
for p in chrona-default-draft mission-light target-b technical-print editorial yuya; do
  echo "$p: $(../venv/bin/chrona render risk.chrona --preset $p --view net-view.yaml --viewport 1600x900 --output net-$p.png | head -c 400)"
done
