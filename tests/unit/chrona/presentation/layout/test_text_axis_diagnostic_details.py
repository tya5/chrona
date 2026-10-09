from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.asof_label import find_asof_label_candidate
from chrona.presentation.layout.axis import (
    axis_label_fits,
    format_axis_tier_label,
    thinning_schedule,
)
from chrona.presentation.layout.labels import LabelRect, _candidate, place_label, place_member_name
from chrona.presentation.layout.mark_aware_scale import PointMarkFootprint
from chrona.presentation.layout.model import geometry_sum
from chrona.presentation.layout.obstacles import SurfaceObstacleIndex
from chrona.presentation.layout.text import place_text, wrap_text


def test_label_candidate_input_names_measurements():
    with pytest.raises(ValueError) as bad_candidate:
        _candidate(LabelRect(1, 2, 8, 6), (0, 3), "above", 2)
    assert str(bad_candidate.value).startswith("E_PRESENTATION_LABEL_INPUT:")
    assert "size=(0, 3)" in str(bad_candidate.value)
    assert "side='above'" in str(bad_candidate.value)

    with pytest.raises(ValueError) as invalid_request:
        place_label(LabelRect(0, 0, 10, 10), (3, 3), ("above",),
                    bounds=LabelRect(0, 0, 20, 20), maximum_side_gap=-1)
    assert str(invalid_request.value).startswith("E_PRESENTATION_LABEL_INPUT:")
    assert "maximum_side_gap=-1" in str(invalid_request.value)


def test_inside_label_unplaceable_error_names_measured_sizes():
    with pytest.raises(ValueError) as inside:
        _candidate(LabelRect(0, 0, 2, 2), (4, 5), "inside", 0)
    assert str(inside.value).startswith("E_PRESENTATION_LABEL_UNPLACEABLE:")
    assert "anchor_size=(2, 2)" in str(inside.value)
    assert "size=(4, 5)" in str(inside.value)


def test_member_name_request_error_names_invalid_terminal_options():
    with pytest.raises(ValueError) as caught:
        place_member_name(LabelRect(1, 2, 10, 4), (5, 3), ("end",),
                          own_mark_right=float("nan"), overflow="suppress")
    assert str(caught.value).startswith("E_PRESENTATION_LABEL_INPUT:")
    assert "own_mark_right=nan" in str(caught.value)
    assert "sides=('end',)" in str(caught.value)


def test_axis_thinning_error_names_tier_fit_results():
    with pytest.raises(ValueError) as overflow:
        thinning_schedule((False, False, False))
    assert str(overflow.value).startswith("E_PRESENTATION_AXIS_OVERFLOW:")
    assert "candidate_count=3" in str(overflow.value)
    assert "fit_results=(False, False, False)" in str(overflow.value)

def test_axis_format_error_names_level_and_requested_form():
    from chrona.presentation.axis_intervals import axis_intervals

    interval = axis_intervals(date(2026, 3, 1), date(2026, 4, 1), "month")[0]
    table = SimpleNamespace()
    with pytest.raises(ValueError) as form:
        format_axis_tier_label(interval, "quarter", table)
    assert str(form.value).startswith("E_PRESENTATION_AXIS_FORMAT:")
    assert "level='month'" in str(form.value)
    assert "form='quarter'" in str(form.value)


def test_axis_label_orientation_error_names_measurement_context():
    with pytest.raises(ValueError) as caught:
        axis_label_fits(content="Mar", available_inline=8, font_size=10,
                        font_metrics=SimpleNamespace(width=lambda text, size: 12),
                        orientation="diagonal")
    assert str(caught.value).startswith("E_PRESENTATION_TEXT_ORIENTATION:")
    assert "orientation='diagonal'" in str(caught.value)
    assert "available_inline=8" in str(caught.value)


def test_asof_label_geometry_error_names_actual_inputs():
    with pytest.raises(ValueError) as geometry:
        find_asof_label_candidate(LabelRect(0, 0, 0, 10), (4, 3), rule_x=2, gap=1,
                                  rule_host_id="rule-alpha", obstacles=SurfaceObstacleIndex(),
                                  obstacle_classes=("mark",))
    assert str(geometry.value).startswith("E_LAYOUT_ASOF_LABEL_GEOMETRY:")
    assert "footprint=(4, 3)" in str(geometry.value)
    assert "rule_x=2" in str(geometry.value)

def test_asof_label_rule_host_error_names_missing_identifier():
    with pytest.raises(ValueError) as host:
        find_asof_label_candidate(LabelRect(0, 0, 20, 20), (4, 3), rule_x=2, gap=1,
                                  rule_host_id="", obstacles=SurfaceObstacleIndex(),
                                  obstacle_classes=("mark",))
    assert str(host.value).startswith("E_LAYOUT_ASOF_LABEL_RULE_HOST:")
    assert "rule_host_id=''" in str(host.value)


def test_text_wrapping_error_names_available_width():
    with pytest.raises(ValueError) as wrap:
        wrap_text("short words", available_inline=0, font_size=10,
                  font_metrics=SimpleNamespace(width=lambda text, size: len(text) * size))
    assert str(wrap.value).startswith("E_PRESENTATION_WRAP_INPUT:")
    assert "available_inline=0" in str(wrap.value)
    assert "font_size=10" in str(wrap.value)

def test_text_placement_orientation_error_names_owner_and_value():
    treatment = SimpleNamespace(family="sans", weight=400, horizontal_scale=1,
                                font_size=10, line_height=1.2, transform="none",
                                letter_spacing=0, numeric_spacing="proportional")
    theme = SimpleNamespace(text_treatment=lambda role: treatment)
    metrics = SimpleNamespace(width=lambda text, size: len(text) * size,
                              content_identity="font-regular")
    with pytest.raises(ValueError) as orientation:
        place_text(placement_id="text-alpha", source_ref="/view/title", content="Title",
                   inline=1, baseline_block=10, typography_role="title",
                   theme_tokens=theme, font_metrics=metrics, orientation="diagonal")
    assert str(orientation.value).startswith("E_PRESENTATION_TEXT_ORIENTATION:")
    assert "placement_id='text-alpha'" in str(orientation.value)
    assert "orientation='diagonal'" in str(orientation.value)


def test_geometry_sum_type_error_names_bad_index_and_type():
    with pytest.raises(TypeError) as caught:
        geometry_sum((1.0, True, 3.0))
    assert str(caught.value).startswith("E_LAYOUT_GEOMETRY_SUM_INPUT:")
    assert "item_index=1" in str(caught.value)
    assert "actual_type=bool" in str(caught.value)


def test_point_mark_overflow_error_names_anchor_and_bounds():
    with pytest.raises(ValueError) as caught:
        PointMarkFootprint(date(2026, 5, 4), 12, 9)
    assert str(caught.value).startswith("E_LAYOUT_MARK_OVERFLOW:")
    assert "anchor_date=datetime.date(2026, 5, 4)" in str(caught.value)
    assert "left=12" in str(caught.value)
    assert "right=9" in str(caught.value)
