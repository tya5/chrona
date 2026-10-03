"""Rounded corners on orthogonal relation routes: `timeline.relation.cornerRadius` (#1046).

Synthetic projections routed by the real surface composer; nothing reads `examples/`. The route (`points`) stays the
orthogonal polyline; `path_commands` is the drawn path with one quadratic arc per turn.
"""
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from PIL import Image

from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.path_geometry import flatten_path, rounded_orthogonal_path
from chrona.presentation.layout.sources import MeasuredSources, SourceInput
from chrona.presentation.layout.surface_routes import corner_arc_blocker
from chrona.presentation.model.projection import ReviewItem, ReviewProjection, ReviewRowProjection
from chrona.presentation.renderers.v05_svg import render_v05_svg
from chrona.presentation.scene.model import ScenePaint
from chrona.presentation.scene.v05_builder import build_scene_input, compose_review_surface

from tests.unit.chrona.presentation.scene.test_v05_builder import (
    _Font, _manifest, _theme, _title_measurement, surface_content,
)

D = date


def _item(oid, start, end, track="stacked"):
    return ReviewItem(oid, oid.upper(), "span", {"start": start, "end": end}, None, None, (), item_id=oid,
                      source_kind="primary", track=track)


def _surface(items, rows, relation, radius, entry="any"):
    from dataclasses import replace
    projection = ReviewProjection(tuple(items), (min(i.planned["start"] for i in items), max(i.planned["end"] for i in items)),
                                  (), (), tuple(rows))
    metrics = {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
               "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8),
               "timeline.mark.blockSize": Decimal(8)}
    if radius is not None:
        metrics["timeline.relation.cornerRadius"] = Decimal(radius)
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))}, metrics)
    manifest = replace(_manifest("title", "table", "timeline", "timeline-axis"), relation_entry=entry)
    value = build_scene_input(projection=projection, surface_content=surface_content(relations=(relation,)),
                              layout_manifest=manifest, resolved_theme=_theme(), font_metrics=_Font(),
                              measured_sources=measurement, capabilities={"svg": True})
    return compose_review_surface(value)


def _path(surface):
    paths = [p for p in surface.primitives if p.scene_id.startswith("relation:") and not p.scene_id.startswith("relation-label")]
    assert len(paths) == 1
    return paths[0]


def _rows(*groups):
    return [ReviewRowProjection(g[0].object_id, g[0].title, "", g[0].object_id, tuple(g)) for g in groups]


A = _item("a", D(2026, 2, 1), D(2026, 2, 8))
B = _item("b", D(2026, 2, 12), D(2026, 2, 20))
DEP = {"id": "dep", "from": {"object": "a", "endpoint": "end"}, "to": {"object": "b", "endpoint": "start"}}


def _drawn(radius, items=(A, B), relation=DEP, entry="any"):
    surface = _surface(items, _rows(*((i,) for i in items)), relation, radius, entry)
    return surface, _path(surface)


def test_absent_and_zero_radius_draw_the_same_square_route_with_no_curve_commands():
    absent, zero = _drawn(None)[1], _drawn(0)[1]
    assert absent.points == zero.points
    assert absent.path_commands == zero.path_commands == ()


def test_a_radius_adds_one_arc_per_turn_and_keeps_the_polyline_as_the_route():
    square, rounded = _drawn(0)[1], _drawn(4)[1]
    assert rounded.points == square.points
    turns = sum(1 for a, b, c in zip(rounded.points, rounded.points[1:], rounded.points[2:])
                if not (a[0] == b[0] == c[0] or a[1] == b[1] == c[1]))
    arcs = sum(c.kind == "quadratic" for c in rounded.path_commands)
    assert 0 < arcs <= turns  # a turn with no room beside the head stays square
    assert rounded.path_commands[0].points == (rounded.points[0],)
    assert rounded.path_commands[-1].points == (rounded.points[-1],)


def test_long_legs_take_the_full_radius_and_a_short_step_the_reduced_one():
    long_cmds = rounded_orthogonal_path(((0, 0), (0, 40), (40, 40)), 4)
    assert long_cmds[1].points == ((0.0, 36.0),) and long_cmds[2].points == ((0, 40), (4.0, 40.0))
    short_cmds = rounded_orthogonal_path(((0, 0), (0, 40), (5, 40)), 4)  # outgoing leg 5: half is 2.5
    assert short_cmds[2].points == ((0, 40), (2.5, 40.0))
    step = rounded_orthogonal_path(((0, 0), (0, 9), (30, 9), (30, 40)), 4)  # a 9 px step as in a narrow gap
    arcs = [c for c in step if c.kind == "quadratic"]
    assert [a.points[1] for a in arcs] == [(4.0, 9.0), (30.0, 13.0)]
    assert step[1].points == ((0.0, 5.0),)


def test_the_terminal_leg_keeps_a_straight_run_for_the_head_and_its_tangent():
    cmds = rounded_orthogonal_path(((0, 0), (0, 20), (14, 20)), 6, end_run=10)
    assert cmds[2].points == ((0, 20), (4.0, 20.0))  # 14 - 10 leaves 4, below the half-leg 7
    assert cmds[-1].points == ((14, 20),)
    tight = rounded_orthogonal_path(((0, 0), (0, 20), (8, 20)), 6, end_run=10)
    assert [c.kind for c in tight] == ["move", "line", "line"] and tight[1].points == ((0, 20),)  # no room: square
    start = rounded_orthogonal_path(((0, 0), (6, 0), (6, 30)), 4, start_run=5)
    assert start[1].points == ((5.0, 0.0),) and start[2].points == ((6, 0), (6.0, 1.0))  # 6 - 5 leaves 1


def test_a_synthetic_route_ends_straight_for_the_target_head():
    # The last leg here is a 4 px drop and the head is 10 px: the turn before it stays square (no room for head and arc).
    surface, path = _drawn(4)
    head, end = path.marker_end.head_length, path.points[-1]
    assert path.points[-1][0] == path.points[-2][0] and abs(path.points[-1][1] - path.points[-2][1]) < head
    arcs = [c for c in path.path_commands if c.kind == "quadratic"]
    assert arcs
    for arc in arcs:
        assert abs(end[0] - arc.points[1][0]) + abs(end[1] - arc.points[1][1]) >= head - 1e-6


def test_collinear_points_are_not_turns_and_draw_straight():
    cmds = rounded_orthogonal_path(((0, 0), (0, 10), (0, 30), (20, 30)), 4)
    assert [c.kind for c in cmds].count("quadratic") == 1
    back = rounded_orthogonal_path(((0, 0), (0, 10), (0, 5)), 4)  # a doubled-back triple is not rounded either
    assert [c.kind for c in back] == ["move", "line", "line"]


ELBOW = ((0, 40), (40, 40), (40, 0))  # the arc at radius 4 passes (39, 39), one px inside the corner


def _blocker(rect):
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("mark:x", "mark", "timeline", ObstacleRect(*rect)))
    return corner_arc_blocker(index, frozenset(), 1.0, ("mark",))


def _arc_cut(commands):
    return next(c for c in commands if c.kind == "quadratic").points[1]


def test_an_arc_that_would_enter_an_obstacle_halves_its_radius_until_clear():
    assert _arc_cut(rounded_orthogonal_path(ELBOW, 4)) == (40.0, 36.0)
    cmds = rounded_orthogonal_path(ELBOW, 4, blocked=_blocker((38.0, 38.0, 38.9, 38.9)))
    assert _arc_cut(cmds) == (40.0, 38.0)  # radius 2 clears it


def test_an_arc_with_no_clear_radius_becomes_the_square_corner_of_the_polyline():
    cmds = rounded_orthogonal_path(ELBOW, 4, blocked=_blocker((39.0, 39.0, 39.9, 39.9)))
    assert [c.kind for c in cmds] == ["move", "line", "line"] and cmds[1].points == ((40, 40),)


def test_the_route_hosts_own_marks_are_exempt_from_the_arc_check():
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("host", "mark", "timeline", ObstacleRect(39.0, 39.0, 39.9, 39.9)))
    blocker = corner_arc_blocker(index, frozenset({"host"}), 1.0, ("mark",))
    assert _arc_cut(rounded_orthogonal_path(ELBOW, 4, blocked=blocker)) == (40.0, 36.0)


def test_svg_and_png_draw_the_same_arc_geometry():
    from dataclasses import replace
    surface, path = _drawn(4)
    surface = replace(surface, primitives=(replace(path, paint=replace(path.paint, stroke="#000000")),),
                      canvas_paint=ScenePaint("#ffffff", None, None, (), 1))  # only the route, black on white
    svg = render_v05_svg(surface)
    drawn = flatten_path(path.path_commands)
    corners = [c.points[0] for c in path.path_commands if c.kind == "quadratic"]
    assert corners
    for corner in corners:
        assert f"Q{corner[0]:g} {corner[1]:g} " in svg
    resvg = pytest.importorskip("resvg_py")
    zoom = 8
    image = Image.open(BytesIO(bytes(resvg.svg_to_bytes(svg_string=svg, zoom=zoom)))).convert("L")
    ox, oy = surface.canvas_bounds[0], surface.canvas_bounds[1]

    def ink(point):
        x, y = round((point[0] - ox) * zoom), round((point[1] - oy) * zoom)
        return min(image.getpixel((x + dx, y + dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1)) < 200

    def cut(i):  # how far the arc starts before its corner: the effective radius
        a, b = path.path_commands[i - 1].points[-1], path.path_commands[i].points[0]
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    index = max((i for i, c in enumerate(path.path_commands) if c.kind == "quadratic"), key=cut)
    assert cut(index) >= 3
    corner = path.path_commands[index].points[0]
    start = path.path_commands[index - 1].points[-1]
    arc_mid = ((start[0] + 2 * corner[0] + path.path_commands[index].points[1][0]) / 4,
               (start[1] + 2 * corner[1] + path.path_commands[index].points[1][1]) / 4)
    assert ink(arc_mid) and not ink(corner) and drawn
