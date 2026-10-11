from decimal import Decimal

import pytest

from chrona.presentation.layout.label_chip_measurement import measure_label_chip
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.model.theme_tokens import ThemeTokenView


CASES = (
    ("asOfLabel", "as-of-label-chip"),
    ("memberLabel", "member-label-chip"),
    ("finishDelta", "finish-delta-chip"),
    ("periodLabel", "period-label-chip"),
)


def _theme(semantic_role, *, shape=None, active=True, stroke_width=None, glyphs=None):
    values = {}
    role = {}
    if shape is not None:
        values["chip-shape"] = {"type": "chipShape", "value": shape}
        role["chipShape"] = "chip-shape"
    if active:
        role["backgroundTreatment"] = "fill"
    if stroke_width is not None:
        values["chip-stroke-width"] = {"type": "number", "value": stroke_width}
        role["strokeWidth"] = "chip-stroke-width"
    return ThemeTokenView({
        "version": "chrona/resolved-theme/v0.2",
        "kind": "resolved-theme",
        "body": {"values": values, "roles": {semantic_role: role}, "metrics": {}},
    }, catalog_glyphs=glyphs or {})


@pytest.mark.parametrize("semantic_id,role", CASES)
def test_absent_rectangle_and_shape_without_active_chip_keep_legacy_path(semantic_id, role):
    assert measure_label_chip(_theme(role), semantic_id, text_inline=30, text_block=12,
                              font_size=10, padding=(4, 2)) is None
    assert measure_label_chip(_theme(role, shape={"kind": "rectangle"}), semantic_id,
                              text_inline=30, text_block=12, font_size=10,
                              padding=(4, 2)) is None
    assert measure_label_chip(_theme(role, shape={"kind": "burst", "points": 7,
                                                  "innerRatio": .4}, active=False), semantic_id,
                              text_inline=30, text_block=12, font_size=10,
                              padding=(4, 2)) is None


@pytest.mark.parametrize("semantic_id,role", CASES)
def test_burst_uses_semantic_role_and_preserves_role_paint_with_asymmetric_inset(semantic_id, role):
    measured = measure_label_chip(
        _theme(role, shape={"kind": "burst", "points": 7, "innerRatio": .45},
               stroke_width=1.25),
        semantic_id, text_inline=31, text_block=11, font_size=10, padding=(4, 2),
    )
    assert measured is not None
    assert len(measured.geometry.symbol_parts) == 1
    assert measured.geometry.symbol_parts[0].paint_mode is None
    assert measured.geometry.text_bounds.inline_size == Decimal(31)
    assert measured.geometry.text_bounds.block_size == Decimal(11)
    assert measured.text_inline_inset == pytest.approx(float(measured.geometry.text_bounds.inline) + 12.5)
    assert measured.text_block_inset == pytest.approx(float(measured.geometry.text_bounds.block) + 12.5)
    # The declared role stroke is expanded once per side, per Spec 46 §7.
    assert float(measured.footprint.inline) == pytest.approx(-12.5)
    assert float(measured.footprint.block) == pytest.approx(-12.5)
    assert float(measured.footprint.inline_size) == pytest.approx(
        float(measured.geometry.outer_bounds.inline_size) + 25)
    assert float(measured.footprint.block_size) == pytest.approx(
        float(measured.geometry.outer_bounds.block_size) + 25)


@pytest.mark.parametrize("semantic_id,role", CASES)
def test_ellipse_completion_uses_each_roles_measurement_and_expands_stroke_once(semantic_id, role):
    measured = measure_label_chip(
        _theme(role, shape={"kind": "burst", "points": 7, "innerRatio": .8, "fit": "ellipse"},
               stroke_width=1.5),
        semantic_id, text_inline=140, text_block=18, font_size=12, padding=(6, 3),
    )
    assert measured is not None
    assert len(measured.geometry.symbol_parts) == 1
    assert measured.geometry.symbol_parts[0].paint_mode is None
    assert measured.geometry.outer_bounds.block_size <= (
        2 ** .5 / float(_inradius_factor(7, .8)) * (18 + 2 * 3) + 1e-8
    )
    assert float(measured.footprint.block) == pytest.approx(-15)
    assert float(measured.footprint.block_size) == pytest.approx(
        float(measured.geometry.outer_bounds.block_size) + 30)


def _inradius_factor(points, ratio):
    from math import cos, pi, sin, sqrt

    theta = pi / points
    if ratio <= cos(theta):
        return ratio
    return ratio * sin(theta) / sqrt(1 + ratio * ratio - 2 * ratio * cos(theta))


@pytest.mark.parametrize("text_inline,text_block,padding", [(0, 12, (0, 2)), (12, 0, (2, 0))])
def test_ellipse_zero_padded_axis_maps_to_selected_role_diagnostic(text_inline, text_block, padding):
    role = "period-label-chip"
    with pytest.raises(LayoutError) as caught:
        measure_label_chip(
            _theme(role, shape={"kind": "burst", "points": 5, "innerRatio": .6, "fit": "ellipse"}),
            "periodLabel", text_inline=text_inline, text_block=text_block,
            font_size=12, padding=padding,
        )
    assert caught.value.diagnostic_id == "E_LAYOUT_CHIP_TEXT_GROUND_INVALID"
    assert caught.value.path == f"/body/roles/{role}/chipShape"
    assert caught.value.detail == "reason=invalid-measurement"


def _rect_path(left, top, right, bottom):
    return f"M{left} {top}L{right} {top}L{right} {bottom}L{left} {bottom}Z"


def _catalog_theme(role, glyph, *, stroke_width=20, insets=None):
    return _theme(role, shape={
        "kind": "catalog", "glyph": "test:chip", "sliceInsets": insets or {
            "top": 1, "right": 1, "bottom": 1, "left": 1,
        }, "unitEm": .1,
    }, stroke_width=stroke_width, glyphs={"test:chip": glyph})


def test_catalog_keeps_parts_and_intrinsic_stroke_width_then_expands_visible_frame_once():
    glyph = {"viewport": {"inlineSize": 10, "blockSize": 10}, "parts": [
        {"paint": "fill", "data": _rect_path(0, 0, 10, 10)},
        {"paint": "stroke", "data": "M0 5L10 5", "strokeWidth": .5,
         "lineCap": "round", "lineJoin": "round"},
    ]}
    measured = measure_label_chip(_catalog_theme("member-label-chip", glyph), "memberLabel",
                                  text_inline=20, text_block=10, font_size=10,
                                  padding=(3, 2))
    assert measured is not None
    parts = measured.geometry.symbol_parts
    assert tuple(part.paint_mode for part in parts) == ("fill", "stroke")
    assert parts[1].stroke_width == pytest.approx(.5)
    assert parts[1].line_cap == "round" and parts[1].line_join == "round"
    assert tuple(command for command in parts[1].commands)  # emitted native outline retained

    # The source intrinsic width (.5), not the much larger role fallback (20),
    # controls the outline envelope. Include both the nominal frame and the
    # emitted centerline's ten-width expansion, independently of the helper.
    stroke_points = tuple(point for command in parts[1].commands for point in command.points)
    expansion = 10 * .5
    expected_left = min(0.0, *(point[0] - expansion for point in stroke_points))
    expected_top = min(0.0, *(point[1] - expansion for point in stroke_points))
    expected_right = max(float(measured.geometry.outer_bounds.inline_size),
                         *(point[0] + expansion for point in stroke_points))
    expected_bottom = max(float(measured.geometry.outer_bounds.block_size),
                          *(point[1] + expansion for point in stroke_points))
    assert measured.footprint == Rect(
        Decimal(str(expected_left)), Decimal(str(expected_top)),
        Decimal(str(expected_right - expected_left)), Decimal(str(expected_bottom - expected_top)),
    )
    assert measured.text_inline_inset == pytest.approx(
        float(measured.geometry.text_bounds.inline) - expected_left)


def test_uncovered_catalog_text_returns_bounded_layout_diagnostic():
    glyph = {"viewport": {"inlineSize": 10, "blockSize": 10}, "parts": [
        {"paint": "fill", "data": "M0 0L10 0L10 10L0 10Z M2 2L2 8L8 8L8 2Z"},
    ]}
    with pytest.raises(LayoutError) as caught:
        measure_label_chip(_catalog_theme("period-label-chip", glyph, stroke_width=None,
                                          insets={"top": 0, "right": 0, "bottom": 0, "left": 0}),
                           "periodLabel", text_inline=20, text_block=10, font_size=10,
                           padding=(3, 2))
    assert caught.value.diagnostic_id == "E_LAYOUT_CHIP_TEXT_GROUND_INVALID"
    assert caught.value.path == "/body/roles/period-label-chip/chipShape"
    assert caught.value.detail == "reason=catalog-fill-coverage"
