"""#1087: the rounded outline and the border strips that follow it, as pure geometry."""
from __future__ import annotations

from math import hypot, sqrt

import pytest

from chrona.presentation.layout.rounded_outline import (
    CORNER_CLEARANCE, border_strip, clamp_radius, commands_points, rounded_rect_commands,
)

BOX = (10.0, 20.0, 120.0, 60.0)


def inside_rounded(point, box, radii):
    """Whether ``point`` is inside the rectangle ``box`` whose corners (tl, tr, br, bl) have elliptical ``radii``."""
    px, py = point
    x, y, w, h = box
    if not (x <= px <= x + w and y <= py <= y + h):
        return False
    corners = ((x, y, 1, 1), (x + w, y, -1, 1), (x + w, y + h, -1, -1), (x, y + h, 1, -1))
    for (cx, cy, sx, sy), (rx, ry) in zip(corners, radii):
        if rx <= 0 or ry <= 0:
            continue
        u, v = (px - cx) * sx, (py - cy) * sy
        if u < rx and v < ry and ((rx - u) / rx) ** 2 + ((ry - v) / ry) ** 2 > 1:
            return False
    return True


def inside_polygon(point, polygon):
    px, py = point
    hit = False
    for (ax, ay), (bx, by) in zip(polygon, polygon[1:] + polygon[:1]):
        if (ay > py) != (by > py) and px < ax + (py - ay) * (bx - ax) / (by - ay):
            hit = not hit
    return hit


def near_a_mitre(point, box, widths, tolerance=0.2):
    """Whether ``point`` is within ``tolerance`` of a mitre line (the line from a box corner through its padding corner)."""
    x, y, w, h = box
    corners = ((x, y, 1, 1, widths["start"], widths["top"]), (x + w, y, -1, 1, widths["end"], widths["top"]),
               (x + w, y + h, -1, -1, widths["end"], widths["bottom"]), (x, y + h, 1, -1, widths["start"], widths["bottom"]))
    for cx, cy, sx, sy, wv, wh in corners:
        length = hypot(wv, wh)
        if length == 0:
            continue
        ux, uy = sx * wv / length, sy * wh / length
        along = (point[0] - cx) * ux + (point[1] - cy) * uy
        across = abs((point[0] - cx) * uy - (point[1] - cy) * ux)
        if along > 0 and across < tolerance:
            return True
    return False


def ring_of(box, radius, widths):
    x, y, w, h = box
    bl, br, bt, bb = widths["start"], widths["end"], widths["top"], widths["bottom"]
    inner = (x + bl, y + bt, w - bl - br, h - bt - bb)
    radii = [(max(radius - bl, 0), max(radius - bt, 0)), (max(radius - br, 0), max(radius - bt, 0)),
             (max(radius - br, 0), max(radius - bb, 0)), (max(radius - bl, 0), max(radius - bb, 0))]
    return inner, radii


def test_the_radius_is_clamped_to_half_the_shorter_side():
    assert clamp_radius(5, 100, 40) == 5 and clamp_radius(50, 100, 40) == 20 and clamp_radius(-1, 10, 10) == 0


def test_the_corner_clearance_is_where_a_point_is_on_the_arc():
    assert CORNER_CLEARANCE == pytest.approx(1 - 1 / sqrt(2))
    r = 10.0
    assert hypot(r - r * CORNER_CLEARANCE, r - r * CORNER_CLEARANCE) == pytest.approx(r)


def test_a_rounded_rectangle_is_closed_and_its_arcs_are_circular():
    commands = rounded_rect_commands(BOX, 8)
    assert commands[0].kind == "move" and commands[0].points[0] == (10, 20 + 8)  # the start of the first corner arc
    assert {command.kind for command in commands} == {"move", "line", "quadratic"}
    points = commands_points(commands, samples=12)
    # every point is within the box and the four corners are rounded: the box corners themselves are outside
    assert all(10 - 1e-9 <= x <= 130 + 1e-9 and 20 - 1e-9 <= y <= 80 + 1e-9 for x, y in points)
    polygon = points
    for corner in ((10, 20), (130, 20), (130, 80), (10, 80)):
        assert not inside_polygon((corner[0] + (0.5 if corner[0] == 10 else -0.5), corner[1] + (0.5 if corner[1] == 20 else -0.5)), polygon)
    assert inside_polygon((70, 50), polygon)
    # the arc stays on the circle of radius 8 (three corner-arc points checked against the first corner's centre)
    arc_points = [p for p in points if p[0] < 18 and p[1] < 28]
    assert arc_points and all(abs(hypot(p[0] - 18, p[1] - 28) - 8) < 0.05 for p in arc_points)


def test_a_zero_radius_is_the_plain_rectangle():
    commands = rounded_rect_commands(BOX, 0)
    assert {command.kind for command in commands} == {"move", "line"}


@pytest.mark.parametrize("radius,widths", [
    (8, {"start": 3, "end": 3, "top": 3, "bottom": 3}),
    (8, {"start": 4, "end": 1, "top": 2, "bottom": 5}),
    (12, {"start": 10, "end": 0, "top": 0, "bottom": 0}),
    (12, {"start": 3, "end": 0, "top": 2, "bottom": 0}),
    (6, {"start": 9, "end": 9, "top": 1, "bottom": 1}),
    (0.5, {"start": 3, "end": 3, "top": 3, "bottom": 3}),
])
def test_the_strips_tile_the_ring_between_the_two_outlines(radius, widths):
    outer = [(radius, radius)] * 4
    inner_box, inner_radii = ring_of(BOX, radius, widths)
    polygons = {side: commands_points(border_strip(side, BOX, radius, widths), samples=24)
                for side in widths if widths[side] > 0}
    checked = 0
    for ix in range(0, 241):
        for iy in range(0, 121):
            point = (10 + ix * 0.5, 20 + iy * 0.5)
            in_outer, in_inner = inside_rounded(point, BOX, outer), inside_rounded(point, inner_box, inner_radii)
            # stay clear of the outline and of the mitre lines, where polyline sampling may differ by a hair
            margin_points = [(point[0] + dx, point[1] + dy) for dx in (-0.12, 0.12) for dy in (-0.12, 0.12)]
            if near_a_mitre(point, BOX, widths) or any(inside_rounded(m, BOX, outer) != in_outer or inside_rounded(m, inner_box, inner_radii) != in_inner
                   for m in margin_points):
                continue
            hits = [side for side, polygon in polygons.items() if inside_polygon(point, polygon)]
            if in_outer and not in_inner:
                assert len(hits) in (1, 2), (point, hits)  # two only on a mitre line (never exactly hit at this grid)
                checked += 1
            else:
                assert not hits, (point, hits)
    assert checked > 50


def test_a_strip_stands_on_the_box_edge_and_ends_on_the_mitre():
    widths = {"start": 4, "end": 0, "top": 2, "bottom": 0}
    start = commands_points(border_strip("start", BOX, 8, widths), samples=8)
    assert min(x for x, _ in start) == pytest.approx(10) and max(x for x, _ in start) == pytest.approx(10 + 4 + 0, abs=4.0)
    # the outer edge touches the box edge along the straight run
    assert any(x == pytest.approx(10) and y == pytest.approx(20 + 8) for x, y in start)
    assert any(x == pytest.approx(10) and y == pytest.approx(80 - 8) for x, y in start)


def test_a_wide_border_has_a_sharp_padding_corner():
    widths = {"start": 20, "end": 20, "top": 20, "bottom": 20}
    strip = border_strip("top", BOX, 8, widths)
    assert strip[0].kind == "move"
    inner_points = commands_points(strip, samples=4)
    assert (10 + 20, 20 + 20) in [(round(x, 6), round(y, 6)) for x, y in inner_points]
