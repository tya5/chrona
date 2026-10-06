"""#1148: render authored radius tokens into completed Scene geometry."""
from datetime import date

import pytest

from tests.support import synthetic_review as sr


@pytest.mark.parametrize("radius", [3.0, "capsule"])
def test_radius_token_is_completed_in_scene_for_different_mark_heights(tmp_path, radius):
    observed = []
    for index, ratio in enumerate((0.5, 0.75)):
        directory = tmp_path / str(index)
        directory.mkdir()
        parts = sr.bundle()
        body = parts["theme"]["body"]
        body["values"].update({
            "physical-radius": {"type": "radius", "value": radius},
            "mark-height": {"type": "number", "value": ratio},
            "mark-offset": {"type": "number", "value": 0},
        })
        body["roles"]["planned"].update(cornerRadius="physical-radius", markHeight="mark-height",
                                           markOffset="mark-offset")
        rendered = sr.render(directory, sr.project({
            "a": sr.span("a", date(2026, 2, 2), 30),
        }), presentation=parts)
        marks = [p for p in rendered.surface.primitives if p.kind == "Rect" and p.source_ref == "a"
                 and p.scene_id.startswith("planned:")]
        assert len(marks) == 1
        mark = marks[0]
        expected = min(mark.bounds[2:]) / 2 if radius == "capsule" else radius
        assert mark.corner_radius == expected
        observed.append(mark.bounds[3])
    assert observed[0] != observed[1]


def test_physical_chip_radius_does_not_scale_with_text_height(tmp_path):
    heights = []
    for index, size in enumerate((11, 16)):
        directory = tmp_path / str(index)
        directory.mkdir()
        parts = sr.bundle()
        body = parts["theme"]["body"]
        body["values"].update({
            "physical-radius": {"type": "radius", "value": 3},
            "chip-padding": {"type": "number", "value": 0.2},
            "chip-text-size": {"type": "number", "value": size},
        })
        body["roles"]["as-of-label"] = {
            **{key: value for key, value in body["roles"]["text"].items() if key not in {"iconScale", "iconGap"}},
            "fontSize": "chip-text-size",
        }
        body["roles"]["as-of-label-chip"] = {
            "backgroundTreatment": "fill", "chipPadding": "chip-padding", "cornerRadius": "physical-radius",
        }
        body["colorBindings"]["as-of-label-chip.fill"] = "warning"
        rendered = sr.render(directory, sr.project({
            "a": sr.span("a", date(2026, 2, 2), 30),
        }), presentation=parts, actual={
            "version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
            "body": {"asOf": "2026-02-20", "observations": []},
        })
        chips = [p for p in rendered.surface.primitives if p.scene_id == "chip:as-of-label"]
        assert len(chips) == 1
        assert chips[0].corner_radius == 3.0
        heights.append(chips[0].bounds[3])
    assert heights[0] != heights[1]
