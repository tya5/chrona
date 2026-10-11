"""Keep the packaged-axis evidence checker sensitive to actual geometry (#1294)."""
from copy import deepcopy
from datetime import date
from pathlib import Path

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


def _two_lane_scene():
    scene = _scene()
    items = scene["surfaces"][0]["primitives"]
    for band in items[:2]:
        band["bounds"]["blockSize"] = 20
    items[2]["bounds"]["block"] = 25
    for band in deepcopy(items[:2]):
        band["id"] = band["id"].replace(":0:", ":3:")
        band["bounds"]["block"] = 40
        items.append(band)
    return scene


def test_decorative_second_band_can_coexist_with_hosted_auto_labels():
    check_bounded_axis_cells(_two_lane_scene())


def test_band_lanes_need_not_fill_an_explicitly_larger_axis_slot():
    scene = _two_lane_scene()
    surface = scene["surfaces"][0]
    surface["slots"][0]["bounds"]["blockSize"] = 60
    next(item for item in surface["primitives"] if item["id"] == "axis-rule")["bounds"]["block"] = 80
    check_bounded_axis_cells(scene)


def test_band_lanes_cannot_overflow_the_axis_slot():
    scene = _two_lane_scene()
    scene["surfaces"][0]["slots"][0]["bounds"]["blockSize"] = 30
    with pytest.raises(AssertionError):
        check_bounded_axis_cells(scene)


@pytest.mark.parametrize("shift", [-1, 1])
def test_the_checker_rejects_gaps_and_overlaps_between_band_lanes(shift):
    scene = _two_lane_scene()
    for item in scene["surfaces"][0]["primitives"]:
        if item["id"].startswith("axis-band-rect:3:"):
            item["bounds"]["block"] += shift
    with pytest.raises(AssertionError):
        check_bounded_axis_cells(scene)


@pytest.mark.parametrize("preset", ["executive-light", "technical-print"])
def test_the_checker_accepts_the_actual_packaged_auto_axis(tmp_path, preset):
    parts = sr.bundle(preset)
    parts["view"]["body"]["window"] = {
        "mode": "explicit", "start": "2026-01-01", "end": "2028-01-01",
    }
    catalogs = ((Path(__file__).resolve().parents[4] /
                 "src/chrona/resources/icons/chrona-theme-starter-v2026-10-09.yaml",)
                if preset == "technical-print" else ())
    rendered = sr.render(tmp_path, sr.project({"a": sr.span("a", date(2026, 2, 1), 40)}),
                         presentation=parts, icon_catalogs=catalogs)
    scene = scene_document(rendered.scene)
    assert any(item["id"].startswith("axis-label:")
               for item in scene["surfaces"][0]["primitives"])
    check_bounded_axis_cells(scene)


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
