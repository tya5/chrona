from decimal import Decimal
from math import cos, hypot, pi, sin, sqrt, ulp

import pytest

import chrona.presentation.layout.chip_geometry as chip_geometry
from chrona.presentation.layout.chip_geometry import (
    ChipGeometryError,
    complete_chip_geometry,
)
from chrona.presentation.layout.model import Rect
from chrona.presentation.model.theme_tokens import BurstChipShape, CatalogChipShape, RectangleChipShape


def _rect_path(left, top, right, bottom):
    return f"M{left} {top}L{right} {top}L{right} {bottom}L{left} {bottom}Z"


def _catalog(fill_path, *, parts=None, viewport=(10, 10)):
    glyph_parts = parts if parts is not None else [{"paint": "fill", "data": fill_path}]
    return {"viewport": {"inlineSize": viewport[0], "blockSize": viewport[1]}, "parts": glyph_parts}


def _distance_to_segment(point, start, end):
    dx, dy = end[0] - start[0], end[1] - start[1]
    length_squared = dx * dx + dy * dy
    amount = 0 if length_squared == 0 else max(0, min(1, (
        (point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / length_squared))
    closest = (start[0] + amount * dx, start[1] + amount * dy)
    return hypot(point[0] - closest[0], point[1] - closest[1])


def _point_in_or_on_polygon(point, vertices):
    inside = False
    for start, end in zip(vertices, (*vertices[1:], vertices[0])):
        if _distance_to_segment(point, start, end) <= 1e-7:
            return True
        if (start[1] > point[1]) != (end[1] > point[1]):
            crossing_x = start[0] + ((point[1] - start[1]) * (end[0] - start[0]) /
                                     (end[1] - start[1]))
            if point[0] < crossing_x:
                inside = not inside
    return inside


def test_rectangle_geometry_preserves_symmetric_chip_padding_and_no_symbol_parts():
    geometry = complete_chip_geometry(text_inline=30, text_block=12, padding=(4, 2),
                                      shape=RectangleChipShape(), font_size=10)
    assert geometry.outer_bounds == Rect(Decimal(0), Decimal(0), Decimal(38), Decimal(16))
    assert geometry.padded_text_bounds == Rect(Decimal(0), Decimal(0), Decimal(38), Decimal(16))
    assert geometry.text_bounds == Rect(Decimal(4), Decimal(2), Decimal(30), Decimal(12))
    assert geometry.symbol_parts == ()


@pytest.mark.parametrize("points,ratio", [
    (2, .3), (3, .4), (5, .4), (8, .95), (5, 1.0), (6, 1.0 - 1e-15), (7, 1e-12),
])
def test_burst_radius_and_text_corner_clearance(points, ratio):
    text_width, text_height = 121.0, 17.0
    padding = (8.0, 3.0)
    padded_width = text_width + 2 * padding[0]
    padded_height = text_height + 2 * padding[1]
    theta = pi / points
    factor = (ratio if ratio <= cos(theta) else
              ratio * sin(theta) / sqrt(1 + ratio * ratio - 2 * ratio * cos(theta)))
    radius = hypot(padded_width / 2, padded_height / 2) / factor
    geometry = complete_chip_geometry(text_inline=text_width, text_block=text_height, padding=padding,
                                      shape=BurstChipShape(points, Decimal(str(ratio))), font_size=13)
    assert len(geometry.symbol_parts) == 1
    commands = geometry.symbol_parts[0].commands
    assert len(commands) == 2 * points + 1
    assert commands[0].kind == "move" and all(command.kind == "line" for command in commands[1:])
    assert commands[-1].points[0] == commands[0].points[0]
    center_x = float(geometry.padded_text_bounds.inline + geometry.padded_text_bounds.inline_size / 2)
    center_y = float(geometry.padded_text_bounds.block + geometry.padded_text_bounds.block_size / 2)
    vertices = tuple(command.points[0] for command in commands[:-1])
    center = (center_x, center_y)
    # Bound only binary-float roundoff at the emitted coordinate scale; a
    # fixed pixel allowance would weaken ordinary-sized containment tests.
    roundoff = 8 * max(ulp(value) for point in (*vertices, center) for value in point)
    actual_inradius = min(_distance_to_segment(center, start, end)
                          for start, end in zip(vertices, (*vertices[1:], vertices[0])))
    for index, command in enumerate(commands[:-1]):
        x, y = command.points[0]
        assert hypot(x - center_x, y - center_y) == pytest.approx(
            radius * (1 if index % 2 == 0 else ratio), rel=1e-12, abs=roundoff)
    assert geometry.outer_bounds.inline == 0 and geometry.outer_bounds.block == 0
    assert geometry.outer_bounds.inline_size > padded_width
    assert geometry.outer_bounds.block_size > padded_height
    for x in (geometry.padded_text_bounds.inline,
              geometry.padded_text_bounds.inline + geometry.padded_text_bounds.inline_size):
        for y in (geometry.padded_text_bounds.block,
                  geometry.padded_text_bounds.block + geometry.padded_text_bounds.block_size):
            corner = (float(x), float(y))
            assert _point_in_or_on_polygon(corner, vertices)
            assert hypot(corner[0] - center_x, corner[1] - center_y) <= actual_inradius + roundoff
    assert float(geometry.text_bounds.inline) == pytest.approx(
        float(geometry.padded_text_bounds.inline) + padding[0])
    assert float(geometry.text_bounds.block) == pytest.approx(
        float(geometry.padded_text_bounds.block) + padding[1])


def _burst_inradius_factor(points, ratio):
    theta = pi / points
    if ratio <= cos(theta):
        return ratio
    return ratio * sin(theta) / sqrt(1 + ratio * ratio - 2 * ratio * cos(theta))


@pytest.mark.parametrize("points,ratio", [(2, 1), (5, .4), (5, .95), (8, .95), (7, 1)])
def test_ellipse_fit_affinely_contains_padded_rectangle_and_bounds_height(points, ratio):
    text_width, text_height = 132.0, 19.0
    padding = (7.0, 4.0)
    padded_width = text_width + 2 * padding[0]
    padded_height = text_height + 2 * padding[1]
    factor = _burst_inradius_factor(points, ratio)
    geometry = complete_chip_geometry(
        text_inline=text_width, text_block=text_height, padding=padding,
        shape=BurstChipShape(points, Decimal(str(ratio)), "ellipse"), font_size=13,
    )
    commands = geometry.symbol_parts[0].commands
    vertices = tuple(command.points[0] for command in commands[:-1])
    assert len(vertices) == 2 * points
    center_x = float(geometry.padded_text_bounds.inline) + padded_width / 2
    center_y = float(geometry.padded_text_bounds.block) + padded_height / 2
    semiaxis_x = padded_width / (sqrt(2) * factor)
    semiaxis_y = padded_height / (sqrt(2) * factor)
    theta = pi / points
    for index, (x, y) in enumerate(vertices):
        radius = 1.0 if index % 2 == 0 else ratio
        angle = -pi / 2 + index * theta
        assert x - center_x == pytest.approx(semiaxis_x * radius * cos(angle), abs=1e-10)
        assert y - center_y == pytest.approx(semiaxis_y * radius * sin(angle), abs=1e-10)
    for x in (float(geometry.padded_text_bounds.inline),
              float(geometry.padded_text_bounds.inline + geometry.padded_text_bounds.inline_size)):
        for y in (float(geometry.padded_text_bounds.block),
                  float(geometry.padded_text_bounds.block + geometry.padded_text_bounds.block_size)):
            assert _point_in_or_on_polygon((x, y), vertices)
            normalized_radius = ((x - center_x) / semiaxis_x) ** 2 + ((y - center_y) / semiaxis_y) ** 2
            assert normalized_radius <= factor * factor + 1e-12
    assert geometry.outer_bounds.inline == 0 and geometry.outer_bounds.block == 0
    assert geometry.outer_bounds.block_size <= sqrt(2) / factor * padded_height + 1e-9


@pytest.mark.parametrize("points,ratio", [(2, 1), (5, .4), (7, .95)])
def test_ellipse_block_extent_does_not_depend_on_text_inline_width(points, ratio):
    shape = BurstChipShape(points, Decimal(str(ratio)), "ellipse")
    short = complete_chip_geometry(text_inline=20, text_block=15, padding=(3, 4),
                                   shape=shape, font_size=12)
    long = complete_chip_geometry(text_inline=200, text_block=15, padding=(3, 4),
                                  shape=shape, font_size=12)
    assert short.outer_bounds.block_size == long.outer_bounds.block_size
    assert short.outer_bounds.inline_size < long.outer_bounds.inline_size


@pytest.mark.parametrize("text_size,padding", [((0, 12), (0, 2)), ((12, 0), (2, 0))])
def test_ellipse_zero_padded_axis_is_rejected_as_invalid_geometry(text_size, padding):
    with pytest.raises(ChipGeometryError) as caught:
        complete_chip_geometry(text_inline=text_size[0], text_block=text_size[1], padding=padding,
                               shape=BurstChipShape(5, Decimal(".4"), "ellipse"), font_size=12)
    assert caught.value.reason == "invalid-measurement"


def test_catalog_nine_slice_preserves_parts_order_stroke_width_and_text_inset():
    glyph = _catalog("", parts=[
        {"paint": "fill", "data": _rect_path(0, 0, 10, 10)},
        {"paint": "stroke", "data": "M0 5L10 5", "strokeWidth": 0.5,
         "lineCap": "round", "lineJoin": "round"},
        {"paint": "fill", "data": _rect_path(2, 2, 8, 8)},
    ])
    shape = CatalogChipShape("test:frame", (Decimal(1), Decimal(2), Decimal(1), Decimal(2)), Decimal(".1"))
    geometry = complete_chip_geometry(text_inline=20, text_block=10, padding=(3, 2), shape=shape,
                                      font_size=10, glyph=glyph)
    assert geometry.outer_bounds == Rect(Decimal(0), Decimal(0), Decimal(30), Decimal(16))
    assert geometry.padded_text_bounds == Rect(Decimal(2), Decimal(1), Decimal(26), Decimal(14))
    assert geometry.text_bounds == Rect(Decimal(5), Decimal(3), Decimal(20), Decimal(10))
    assert tuple(part.paint_mode for part in geometry.symbol_parts) == ("fill", "stroke", "fill")
    assert geometry.symbol_parts[1].stroke_width == pytest.approx(0.5)
    assert geometry.symbol_parts[1].line_cap == "round"


def test_large_padding_does_not_cancel_original_measured_text_dimensions():
    geometry = complete_chip_geometry(text_inline=1, text_block=2, padding=(1e20, 1e20),
        shape=BurstChipShape(5, Decimal(".4")), font_size=12)
    assert geometry.text_bounds.inline_size == 1
    assert geometry.text_bounds.block_size == 2


@pytest.mark.parametrize("glyph", [
    _catalog("M0 0L10 0L10 10L0 10Z M3 3L3 7L7 7L7 3Z"),
    _catalog("", parts=[{"paint": "stroke", "data": "M0 0L10 10", "strokeWidth": 1,
                          "lineCap": "butt", "lineJoin": "miter"}]),
])
def test_catalog_rejects_hole_or_stroke_only_text_ground(glyph):
    shape = CatalogChipShape("test:frame", (Decimal(0),) * 4, Decimal(".1"))
    with pytest.raises(ChipGeometryError) as caught:
        complete_chip_geometry(text_inline=20, text_block=10, padding=(3, 2), shape=shape,
                               font_size=10, glyph=glyph)
    assert caught.value.reason == "catalog-fill-coverage"


def test_catalog_coverage_backend_failure_is_bounded(monkeypatch):
    shape = CatalogChipShape("test:frame", (Decimal(0),) * 4, Decimal(".1"))
    glyph = _catalog(_rect_path(0, 0, 10, 10))

    def fail(*_args, **_kwargs):
        raise RuntimeError("backend details are not surfaced")

    monkeypatch.setattr(chip_geometry, "filled_contours_cover_rectangle", fail)
    with pytest.raises(ChipGeometryError) as caught:
        complete_chip_geometry(text_inline=20, text_block=10, padding=(3, 2), shape=shape,
                               font_size=10, glyph=glyph)
    assert caught.value.reason == "catalog-coverage-geometry"
    assert "backend details" not in str(caught.value)


@pytest.mark.parametrize("values", [
    (float("nan"), 10, (1, 1), 12),
    (10, float("inf"), (1, 1), 12),
    (10, 10, (-1, 1), 12),
    (10, 10, (1, 1), 0),
])
def test_invalid_measured_geometry_is_rejected(values):
    text_inline, text_block, padding, font_size = values
    with pytest.raises(ChipGeometryError):
        complete_chip_geometry(text_inline=text_inline, text_block=text_block, padding=padding,
                               shape=RectangleChipShape(), font_size=font_size)


@pytest.mark.parametrize("fit", ["circle", "ellipse"])
def test_huge_numeric_conversion_and_unrepresentable_inradius_fail_closed(fit):
    with pytest.raises(ChipGeometryError) as huge:
        complete_chip_geometry(text_inline=10 ** 10000, text_block=10, padding=(1, 1),
                               shape=RectangleChipShape(), font_size=12)
    assert huge.value.reason == "nonfinite-geometry"

    with pytest.raises(ChipGeometryError) as tiny_ratio:
        complete_chip_geometry(text_inline=100, text_block=20, padding=(4, 2),
                               shape=BurstChipShape(5, Decimal("1e-320"), fit), font_size=12)
    assert tiny_ratio.value.reason == "nonfinite-geometry"

    with pytest.raises(ChipGeometryError) as huge_points:
        complete_chip_geometry(text_inline=100, text_block=20, padding=(4, 2),
                               shape=BurstChipShape(10 ** 400, Decimal(".5"), fit), font_size=12)
    assert huge_points.value.reason == "nonfinite-geometry"
