"""Keep the packaged-axis evidence checker sensitive to actual geometry (#1294)."""
from copy import deepcopy
from datetime import date

import pytest

from tests.support.preset_checks import (
    check_bounded_axis_cells, check_centered_fixed_axis_labels, check_start_aligned_month_labels,
)
from tests.support.legacy_axis import use_legacy_six_tier_axis
from tests.support import synthetic_review as sr
from chrona.presentation.scene.serialization import scene_document


def _scene():
    axis = {"inline": 100, "block": 20, "inlineSize": 200, "blockSize": 40}
    return {"surfaces": [{"slots": [{"id": "timeline-axis", "bounds": axis}],
                          "primitives": [
        {"id": "axis-band-rect:0:0", "bounds": {**axis, "inlineSize": 99}},
        {"id": "axis-band-rect:0:1", "bounds": {**axis, "inline": 201, "inlineSize": 99}},
        {"id": "axis-label:2:0", "hostPlacementId": "axis-band-rect:0:0",
         "bounds": {"inline": 120, "block": 35, "inlineSize": 50, "blockSize": 10}},
        {"id": "axis-separator:0:1"},
        {"id": "axis-rule", "visualRole": "axis-rule", "bounds": {**axis, "block": 60}},
    ]}]}


def test_one_year_band_lane_with_a_centered_hosted_auto_label_passes():
    check_bounded_axis_cells(_scene())


def test_the_checker_accepts_the_actual_packaged_auto_axis(tmp_path):
    parts = sr.bundle("executive-light")
    parts["view"]["body"]["window"] = {
        "mode": "explicit", "start": "2026-01-01", "end": "2028-01-01",
    }
    rendered = sr.render(tmp_path, sr.project({"a": sr.span("a", date(2026, 2, 1), 40)}),
                         presentation=parts)
    check_bounded_axis_cells(scene_document(rendered.scene))


def test_fixed_axis_centering_remains_covered_with_explicit_legacy_declarations(tmp_path):
    parts = use_legacy_six_tier_axis(sr.bundle("executive-light"))
    rendered = sr.render(tmp_path, sr.project({"a": sr.span("a", date(2026, 2, 1), 120)}),
                         presentation=parts)
    check_centered_fixed_axis_labels(scene_document(rendered.scene))


def test_start_aligned_month_insets_remain_covered_with_explicit_legacy_declarations(tmp_path):
    parts = use_legacy_six_tier_axis(sr.bundle("mission-light"))
    parts["view"]["body"]["window"] = {
        "mode": "explicit", "start": "2026-04-01", "end": "2026-07-01",
    }
    rendered = sr.render(tmp_path, sr.project({"a": sr.span("a", date(2026, 4, 5), 40)}),
                         presentation=parts)
    check_start_aligned_month_labels(scene_document(rendered.scene))


def test_the_fixed_axis_centering_checker_rejects_an_off_center_label():
    scene = _scene()
    scene["surfaces"][0]["primitives"][2]["bounds"]["block"] = 30
    with pytest.raises(AssertionError):
        check_centered_fixed_axis_labels(scene)


@pytest.mark.parametrize("defect", ["outside", "no-gap", "outside-host", "wrong-host", "missing-rule"])
def test_the_checker_rejects_geometry_regressions(defect):
    scene = deepcopy(_scene())
    items = scene["surfaces"][0]["primitives"]
    if defect == "outside":
        items[1]["bounds"]["inlineSize"] = 100
    elif defect == "no-gap":
        items[1]["bounds"]["inline"] = 199
    elif defect == "outside-host":
        items[2]["bounds"]["block"] = 15
    elif defect == "wrong-host":
        items[2]["hostPlacementId"] = "axis-rule"
    else:
        items[-1]["visualRole"] = "axis-grid"
    with pytest.raises(AssertionError):
        check_bounded_axis_cells(scene)
