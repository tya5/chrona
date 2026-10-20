#!/bin/sh
cd "$(dirname "$0")"
C=../venv/bin/chrona
sed -i '' 's/rowDistribution: pack/rowDistribution: fill/' executive-layout/layout.yaml
$C compile ../ja/plan.chrona --output ja-project.yaml 2>/dev/null
for proj in executive-project ja-project; do
  echo "$proj default: $($C render $proj.yaml --view executive-view.yaml --actual-placeholder 2>/dev/null | head -c 1)"
  $C render $proj.yaml --view executive-view.yaml --output $proj-default.png | head -c 300; echo
  $C render $proj.yaml --view executive-view.yaml --preset executive-light --output $proj-executive-light.png | head -c 300; echo
  $C render $proj.yaml --view executive-view.yaml --preset mission-light --layout executive-layout/layout.yaml --viewport 1600x900 --output $proj-mission-light.png | head -c 300; echo
done
$C render ja-project.yaml --view executive-view.yaml --locale ja-JP --actual ../ja/actual.yaml --output ja-project-default-ja.png | head -c 300; echo
