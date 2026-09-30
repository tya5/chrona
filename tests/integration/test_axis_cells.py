"""Axis lanes, cells and rule (#426 rows 5-9).

The catalogue-preset axis-cell and start-aligned-label checks on the HALCYON board live in
`tests/support/preset_checks.py` and run once per preset in `test_halcyon_preset_renders.py`.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_every_committed_timeline_slide_draws_the_axis_rule():
    for path in sorted(ROOT.glob("examples/*/generated/*.scene.json")):
        surface = json.loads(path.read_text(encoding="utf-8"))["surfaces"][0]
        if not any(slot["id"] == "timeline-axis" for slot in surface["slots"]):
            continue
        assert any(item["id"] == "axis-rule" for item in surface["primitives"]), path
