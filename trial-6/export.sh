#!/bin/bash
# Export the forecast comparison in every output format.
cd "$(dirname "$0")"
mkdir -p export
for f in svg png pdf typ tex; do
  ../.venv/bin/chrona render plan.yaml --actual actual-week2.yaml --snapshot baseline.yaml --forecast \
    --preset ${PRESET:-target-b} --output export/forecast-${PRESET:-target-b}.$f \
    > export/forecast-${PRESET:-target-b}-$f.json 2> export/forecast-${PRESET:-target-b}-$f.err
  python3 summarise.py export/forecast-${PRESET:-target-b}-$f.json $? $f
done
ls -la export
