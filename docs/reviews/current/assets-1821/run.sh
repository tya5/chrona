#!/bin/bash
C=../rv/.venv/bin/chrona
r(){ echo "\$ chrona $*"; $C "$@" | head -c 400; echo; }
A=(render revised.yaml --actual actual.yaml --snapshot baseline.yaml --forecast --preset yuya)
r "${A[@]}" --locale en-US --output yuya-en-US.png --emit-scene yuya-en-US.json
r "${A[@]}" --locale ja-JP --output yuya-ja-JP.png --emit-scene yuya-ja-JP.json
r "${A[@]}" --view view-override-wd.yaml --locale en-US --output yuya-en-US-override.png --emit-scene yuya-en-US-override.json
r "${A[@]}" --view view-override-営.yaml --locale ja-JP --output yuya-ja-JP-override.png --emit-scene yuya-ja-JP-override.json
# bar labels: the yuya design places its labels in the table; the View moves them to plot + table (placement: both)
r "${A[@]}" --view view-both.yaml --locale ja-JP --output yuya-ja-JP-both.png --emit-scene yuya-ja-JP-both.json
r "${A[@]}" --view view-override-wd-both.yaml --locale en-US --output yuya-en-US-override-both.png --emit-scene yuya-en-US-override-both.json
r "${A[@]}" --view view-override-営-both.yaml --locale ja-JP --output yuya-ja-JP-override-both.png --emit-scene yuya-ja-JP-override-both.json
