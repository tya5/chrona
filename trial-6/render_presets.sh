#!/bin/bash
# Render the imported plan with every preset to PNG and summarise warnings.
cd "$(dirname "$0")"
C=../.venv/bin/chrona
for p in ${PRESETS:-mission-light control-room-dark print-mono executive-light elevated-light editorial technical-print marquee sunday target-b titlecard yuya muted-executive wallboard-dark}; do
  out=out/${PREFIX:-preset}-$p
  rm -f $out.${EXT:-png}
  $C render ${INPUT:-project.yaml} $EXTRA --preset $p --output $out.${EXT:-png} > $out.json 2>$out.err
  rc=$?
  python3 summarise.py $out.json $rc $p
done
