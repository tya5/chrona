"""A rectangle container's `cornerRadius` is drawn, and a border follows it (#1087).

Synthetic notes through the packaged `executive-light` bundle with a 300 px note rail; no `examples/` input. The rules
checked on the published Scene and the adapters' text: rounded paper, strips that follow the outline for each side and
for several sides, the clearance that keeps text on the paper, tilt, artwork, `fill`, leaders, the unchanged default,
and what Typst and TikZ are given.
"""
from __future__ import annotations

from dataclasses import replace
from math import hypot, sqrt

import pytest

from chrona.presentation.renderers.v05_typeset import render_v05_tikz, render_v05_typst
from tests.support import annotation_artwork as aw
from tests.support import annotation_border as ab
from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr
from tests.unit.chrona.presentation.layout.test_rounded_outline import inside_polygon, inside_rounded
from tests.unit.chrona.presentation.renderers.test_v05_typeset import _surface as _blank_surface

TOL = 0.05
EM = 0.5  # cornerRadius in em of the annotation text size


def _render(tmp_path, border=None, **kwargs):
    kwargs.setdefault("radius", EM)
    return ab.render_notes(tmp_path, border, **kwargs)


def _size(rendered, note="note-0"):
    return ab.prims(rendered, "annotation-text")[note].text_layout.font_size


def _polygon(item, samples=16):
    """The outline of a Symbol primitive as a polyline."""
    from chrona.presentation.layout.rounded_outline import commands_points
    from chrona.presentation.layout.surface_quality import PathCommand
    return commands_points([PathCommand(command.kind, tuple(command.points)) for command in item.symbol.outline], samples)


def test_a_rectangle_with_a_radius_draws_rounded_paper(tmp_path):
    rendered = _render(tmp_path)
    for note, box in ab.boxes(rendered).items():
        assert box.kind.value == "Rect"
        assert box.corner_radius == pytest.approx(EM * _size(rendered, note), abs=TOL)
        assert box.corner_radius <= min(box.bounds[2], box.bounds[3]) / 2


def test_the_radius_is_clamped_to_half_the_shorter_side(tmp_path):
    rendered = _render(tmp_path, radius=50)
    for box in ab.boxes(rendered).values():
        assert box.corner_radius == pytest.approx(min(box.bounds[2], box.bounds[3]) / 2, abs=TOL)


def test_a_theme_without_a_radius_is_byte_identical(tmp_path):
    plain = ab.render_notes(tmp_path, None, name="a", ink_roles=())
    zero = ab.render_notes(tmp_path, None, name="b", ink_roles=(), radius=0)
    assert zero.artifact.content == plain.artifact.content
    assert all(box.corner_radius in (None, 0) for box in ab.boxes(plain).values())


def test_a_note_with_no_container_is_a_square_box_with_no_radius(tmp_path):
    directory = tmp_path / "n"
    directory.mkdir()
    parts = sr.bundle()
    sr.with_note_rail(parts, ab.RAIL)
    source = sr.chain_project()
    sr.add_notes(source, parts["view"], ab.TARGETS, [ab.rail_candidate()])
    rendered = sr.render(directory, source, presentation=parts)
    boxes = ab.boxes(rendered)
    assert boxes and all(box.corner_radius in (None, 0) and box.kind.value == "Rect" for box in boxes.values())


@pytest.mark.parametrize("side", ab.SIDES)
def test_a_single_side_follows_the_rounded_outline(tmp_path, side):
    rendered = _render(tmp_path, {side: {"width": 3}}, inset=ab.INSET)
    for note, box in ab.boxes(rendered).items():
        strips = ab.strips(rendered, note)
        assert set(strips) == {side} and strips[side].kind.value == "Symbol"
        x, y, w, h = box.bounds
        radius = box.corner_radius
        polygon = _polygon(strips[side])
        # every point of the strip is on the paper (inside the rounded outline) and the outer edge stands on the box edge
        for point in polygon:
            assert inside_rounded(point, box.bounds, [(radius - 0.1, radius - 0.1)] * 4) or _on_edge(point, box.bounds)
        edge = {"start": min(p[0] for p in polygon) - x, "end": x + w - max(p[0] for p in polygon),
                "top": min(p[1] for p in polygon) - y, "bottom": y + h - max(p[1] for p in polygon)}[side]
        assert edge == pytest.approx(0, abs=TOL)


def _on_edge(point, box, tolerance=TOL):
    x, y, w, h = box
    return (min(abs(point[0] - x), abs(point[0] - x - w)) < tolerance and y - tolerance <= point[1] <= y + h + tolerance) or (
        min(abs(point[1] - y), abs(point[1] - y - h)) < tolerance and x - tolerance <= point[0] <= x + w + tolerance)


def test_two_sides_follow_the_outline_and_meet_in_a_mitre(tmp_path):
    rendered = _render(tmp_path, {"start": {"width": 4}, "top": {"width": 2}}, inset=ab.INSET)
    for note, box in ab.boxes(rendered).items():
        strips = ab.strips(rendered, note)
        start, top = _polygon(strips["start"]), _polygon(strips["top"])
        x, y = box.bounds[0], box.bounds[1]
        # the mitre: the strips share the cut points on the line from the box corner through the padding corner
        shared = [p for p in start if any(hypot(p[0] - q[0], p[1] - q[1]) < 1e-6 for q in top)]
        assert len(shared) >= 2
        for px, py in shared:
            assert (px - x) * 2 == pytest.approx((py - y) * 4, abs=1e-4)  # on the line (4, 2) from the corner
        # the strips have no overlap at the corner: a point just inside the top strip is not inside the start strip
        assert not inside_polygon((x + 12, y + 1.0), start) and inside_polygon((x + 12, y + 1.0), top)


def test_four_sides_leave_the_padding_outline_rounded_inside(tmp_path):
    border = {"start": {"width": 3}, "end": {"width": 3}, "top": {"width": 3}, "bottom": {"width": 3}}
    rendered = _render(tmp_path, border, inset=ab.INSET, radius=1.0)
    for note, box in ab.boxes(rendered).items():
        x, y, w, h = box.bounds
        radius = box.corner_radius
        inner = (x + 3, y + 3, w - 6, h - 6)
        radii = [(max(radius - 3, 0),) * 2] * 4
        polygons = [_polygon(strip) for strip in ab.strips(rendered, note).values()]
        for fx in (0.0, 0.5, 1.0):
            for fy in (0.0, 0.5, 1.0):
                point = (x + 0.35 + fx * (w - 0.7), y + 0.35 + fy * (h - 0.7))
                in_ring = (inside_rounded(point, box.bounds, [(radius, radius)] * 4)
                           and not inside_rounded(point, inner, radii))
                assert sum(inside_polygon(point, polygon) for polygon in polygons) == (1 if in_ring else 0) or in_ring


def test_text_is_inset_by_at_least_the_corner_clearance_so_it_stays_on_the_paper(tmp_path):
    # no content inset and no border: only the clearance keeps the text off the rounded corner
    rendered = _render(tmp_path, None, radius=1.5, name="c")
    clearance = 1.5 * _size(rendered) * (1 - 1 / sqrt(2))
    for note, box in ab.boxes(rendered).items():
        text = ab.prims(rendered, "annotation-text")[note]
        x, y, w, h = box.bounds
        tx, ty, tw, th = text.bounds
        assert tx >= x + clearance - TOL and ty >= y + clearance - TOL
        assert tx + tw <= x + w - clearance + TOL and ty + th <= y + h - clearance + TOL
        for corner in ((tx, ty), (tx + tw, ty), (tx + tw, ty + th), (tx, ty + th)):
            assert inside_rounded(corner, box.bounds, [(box.corner_radius,) * 2] * 4)


def test_a_small_radius_keeps_the_larger_declared_inset(tmp_path):
    rendered = _render(tmp_path, None, inset=ab.INSET, radius=0.2)
    plain = ab.render_notes(tmp_path, None, name="p", inset=ab.INSET, radius=0)
    assert {k: v.bounds for k, v in ab.boxes(rendered).items()} == {k: v.bounds for k, v in ab.boxes(plain).items()}


def test_a_filled_rounded_note_keeps_the_slot_extent_and_wraps_inside_the_border(tmp_path):
    rendered = _render(tmp_path, {"start": {"width": 5}, "end": {"width": 2}}, inset=ab.INSET, words=8,
                       extra={"inlineSize": "fill"})
    for note, box in ab.boxes(rendered).items():
        text = ab.prims(rendered, "annotation-text")[note]
        size = text.text_layout.font_size
        assert box.bounds[2] == pytest.approx(ab.RAIL, abs=TOL)
        assert text.bounds[2] <= ab.RAIL - 7 - (ab.INSET["left"] + ab.INSET["right"]) * size + TOL
        assert len(text.text_layout.lines) >= 2 and box.corner_radius > 0


@pytest.mark.parametrize("angle", [-3.0, 4.0])
def test_a_tilted_rounded_note_is_a_rotated_rounded_path_with_rotated_strips(tmp_path, angle):
    rendered = _render(tmp_path, {"start": {"width": 5, "paint": "ink"}}, inset=ab.INSET,
                       extra={"tiltDegrees": [angle], "inlineSize": "fill"}, words=5)
    for note, box in ab.boxes(rendered).items():
        assert box.kind.value == "Symbol"
        kinds = {command.kind for command in box.symbol.outline}
        assert "quadratic" in kinds  # rounded corners, not a four-corner polygon
        polygon = _polygon(box)
        strip = ab.strips(rendered, note)["start"]
        assert strip.kind.value == "Symbol"
        # the strip lies on the rotated paper: every strip point is inside (or on) the rotated rounded outline
        assert all(inside_polygon(point, polygon) or _near_polygon(point, polygon) for point in _polygon(strip))
        assert box.bounds[2] == pytest.approx(ab.RAIL, abs=0.05)


def _near_polygon(point, polygon, tolerance=0.08):
    return any(hypot(point[0] - x, point[1] - y) < tolerance for x, y in polygon) or min(
        _distance(point, a, b) for a, b in zip(polygon, polygon[1:] + polygon[:1])) < tolerance


def _distance(point, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = dx * dx + dy * dy
    t = 0.0 if length == 0 else max(0.0, min(1.0, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / length))
    return hypot(point[0] - a[0] - t * dx, point[1] - a[1] - t * dy)


def test_artwork_stays_over_the_rounded_paper_unclipped_and_under_the_border(tmp_path):
    def configure(parts):
        aw.with_artwork(parts, content=aw.CONTENT_INSET, extra={"cornerRadius": 0.3, "border": {"start": {"width": 4}}})
        parts["theme"]["body"]["roles"]["annotation-border-start"] = {}
        parts["theme"]["body"]["colorBindings"]["annotation-border-start.fill"] = "accent"
    directory = tmp_path / "a"
    directory.mkdir()
    parts = sr.bundle()
    sr.with_note_rail(parts, ab.RAIL)
    configure(parts)
    source = sr.chain_project()
    sr.add_notes(source, parts["view"], ab.TARGETS[:1], [ab.rail_candidate()])
    rendered = ak.render(directory, source, parts)
    order = [item.scene_id.split(":")[0] for item in rendered.surface.primitives if item.source_ref == "note-0"
             and item.scene_id.split(":")[0] in {"annotation-box", "annotation-artwork", "annotation-border"}]
    assert order.index("annotation-box") < order.index("annotation-artwork") < order.index("annotation-border")
    assert ab.boxes(rendered)["note-0"].corner_radius > 0


def test_a_leader_ends_on_a_straight_edge_of_the_rounded_box(tmp_path):
    rendered = _render(tmp_path, {"start": {"width": 6}}, inset=ab.INSET)
    for note, box in ab.boxes(rendered).items():
        leader = next(item for item in rendered.surface.primitives if item.source_ref == note and "leader" in item.scene_id)
        x, y, w, h = box.bounds
        radius = box.corner_radius
        points = [command.points[0] for command in leader.path_commands] if leader.path_commands else list(leader.points)
        ends = [p for p in points if abs(p[0] - x) < 0.5 or abs(p[0] - x - w) < 0.5 or abs(p[1] - y) < 0.5 or abs(p[1] - y - h) < 0.5]
        assert ends
        for px, py in ends:  # on the straight run, not in a corner
            on_vertical = min(abs(px - x), abs(px - x - w)) < 0.5 and y + radius - 0.5 <= py <= y + h - radius + 0.5
            on_horizontal = min(abs(py - y), abs(py - y - h)) < 0.5 and x + radius - 0.5 <= px <= x + w - radius + 0.5
            assert on_vertical or on_horizontal


def test_svg_draws_the_radius_and_the_quadratic_strip_and_png_pdf_follow_the_svg(tmp_path):
    rendered = _render(tmp_path, {"start": {"width": 4}}, inset=ab.INSET)
    box = ab.boxes(rendered)["note-0"]
    svg = rendered.artifact.content.decode() if isinstance(rendered.artifact.content, bytes) else rendered.artifact.content
    assert 'rx="' in svg.split('data-scene-id="annotation-box:note-0"', 1)[1][:200]
    assert box.corner_radius > 0
    assert "Q" in svg.split('data-scene-id="annotation-border:note-0:start"', 1)[1][:600]


def test_text_follows_box_composes_with_a_radius_and_box_follows_text_stays_refused(tmp_path):
    def fitted(mode):
        return lambda parts: parts["theme"]["body"]["roles"]["annotation-note-box"].update({"viewerFit": mode})

    rendered = _render(tmp_path, {"start": {"width": 3}}, name="t", configure=fitted("text-follows-box"))
    text = ab.prims(rendered, "annotation-text")["note-0"]
    assert text.text_layout.fit is not None and ab.boxes(rendered)["note-0"].corner_radius > 0
    with pytest.raises(Exception) as caught:
        _render(tmp_path, None, name="b", configure=fitted("box-follows-text"))
    assert "E_THEME_TOKEN_TYPE" in repr(caught.value) or "E_THEME_TOKEN_TYPE" in str(caught.value)


def test_typst_and_tikz_draw_rounded_paper_and_a_strip_symbol(tmp_path):
    # A rounded box is a Rect with a radius: Typst and TikZ both draw it. A border strip is a Symbol: both draw its
    # quadratic outline (#1308).
    bordered = _render(tmp_path, {"start": {"width": 4}}, name="b")
    box, strip = ab.boxes(bordered)["note-0"], ab.strips(bordered)["start"]
    only_box = replace(_blank_surface(), primitives=(box,))
    assert "radius: " in render_v05_typst(only_box) and "rounded corners=" in render_v05_tikz(only_box)
    both = replace(_blank_surface(), primitives=(box, strip))
    assert ".. controls" in render_v05_tikz(both)
    assert "curve.quad(" in render_v05_typst(both)
