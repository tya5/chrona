"""Axis lanes, cells and rule (#426 rows 5-9)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
PRESETS = [entry["id"] for entry in yaml.safe_load(
    (ROOT / "src/chrona/resources/presets/library.yaml").read_text(encoding="utf-8"))["entries"]]
HALCYON = "examples/halcyon-1/project.yaml"
HALCYON_ACTUAL = "examples/halcyon-1/actual.yaml"


def _render_preset(render_cache, preset_id: str) -> dict:
    return render_cache.render(HALCYON, HALCYON_ACTUAL, preset_id).scene["surfaces"][0]


@pytest.mark.parametrize("preset_id", PRESETS)
def test_catalogue_presets_draw_bounded_axis_cells_with_centred_labels(render_cache, preset_id):
    surface = _render_preset(render_cache, preset_id)
    primitives = {item["id"]: item for item in surface["primitives"]}
    axis = next(slot for slot in surface["slots"] if slot["id"] == "timeline-axis")["bounds"]
    bands = [item for key, item in primitives.items() if key.startswith("axis-band-rect:")]
    labels = [item for key, item in primitives.items() if key.startswith("axis-label:")]
    lanes = sorted({(round(band["bounds"]["block"], 3), round(band["bounds"]["blockSize"], 3)) for band in bands})
    assert len(lanes) == 2  # quarter and month lanes, each band filling exactly its lane
    assert lanes[0][0] == pytest.approx(axis["block"])
    assert lanes[1][0] == pytest.approx(lanes[0][0] + lanes[0][1])
    for label in labels:  # every label's line box is centred in its lane
        box = label["bounds"]
        lane = next(lane for lane in lanes if lane[0] - 0.01 <= box["block"] <= lane[0] + lane[1])
        assert box["block"] - lane[0] == pytest.approx(lane[0] + lane[1] - (box["block"] + box["blockSize"]), abs=0.01)
    by_lane: dict[float, list[dict]] = {}
    for band in bands:
        by_lane.setdefault(round(band["bounds"]["block"], 3), []).append(band["bounds"])
    for cells in by_lane.values():  # a visible gap between adjacent cells
        cells.sort(key=lambda bounds: bounds["inline"])
        assert all(right["inline"] - (left["inline"] + left["inlineSize"]) > 0.5 for left, right in zip(cells, cells[1:]))
    assert any(key.startswith("axis-separator:") for key in primitives)
    rule = primitives["axis-rule"]
    assert rule["visualRole"] == "axis-rule" and rule["bounds"]["block"] == pytest.approx(axis["block"] + axis["blockSize"])


def test_start_aligned_month_labels_are_inset_from_their_cell(render_cache):
    surface = _render_preset(render_cache, "mission-light")
    primitives = {item["id"]: item for item in surface["primitives"]}
    month_labels = [item for key, item in primitives.items()
                    if key.startswith("axis-label:") and item["text"] in {"Apr", "May", "Jun"}]
    month_cells = [item["bounds"] for key, item in primitives.items()
                   if key.startswith("axis-band-rect:3:")]
    assert month_labels
    for label in month_labels:
        cell = next(cell for cell in month_cells
                    if cell["inline"] - 2 <= label["bounds"]["inline"] <= cell["inline"] + cell["inlineSize"])
        assert label["bounds"]["inline"] - cell["inline"] > 3  # 0.5 em inset, not flush with the cell edge


def test_every_committed_timeline_slide_draws_the_axis_rule():
    for path in sorted(ROOT.glob("examples/*/generated/*.scene.json")):
        surface = json.loads(path.read_text(encoding="utf-8"))["surfaces"][0]
        if not any(slot["id"] == "timeline-axis" for slot in surface["slots"]):
            continue
        assert any(item["id"] == "axis-rule" for item in surface["primitives"]), path
