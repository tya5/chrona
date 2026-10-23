from __future__ import annotations

from chrona.presentation.layout.member_name_yield import (
    endpoint_candidate_blocker_ids,
    route_candidate_ink,
)
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.relation_terminals import marker_ink_bounds, marker_geometry
from chrona.presentation.layout.surface_quality import MarkerGeometry, PathCommand
from chrona.presentation.layout.surface_routes import route_clears_retained_label_ink


def _triangle() -> MarkerGeometry:
    marker = marker_geometry({
        "shape": "triangle",
        "headLength": 10,
        "headWidth": 10,
        "attachmentOffset": 1,
    })
    assert marker is not None
    return marker


def _rect(obstacle: SurfaceObstacle) -> tuple[float, float, float, float]:
    geometry = obstacle.geometry
    assert isinstance(geometry, ObstacleRect)
    return geometry.left, geometry.top, geometry.right, geometry.bottom


def test_route_candidate_ink_includes_segment_and_both_terminal_bounds():
    points = ((0.0, 10.0), (40.0, 10.0))
    source, target = _triangle(), _triangle()

    ink = route_candidate_ink("r", points, source, target, 1.0)

    by_id = {item.placement_id: item for item in ink}
    assert set(by_id) == {
        "route-candidate:r:segment:0",
        "route-candidate:r:source:terminal",
        "route-candidate:r:target:terminal",
    }
    segment = by_id["route-candidate:r:segment:0"].geometry
    assert isinstance(segment, ObstacleSegment)
    assert segment == ObstacleSegment(points[0], points[1], 1.0)
    assert _rect(by_id["route-candidate:r:source:terminal"]) == marker_ink_bounds(
        source, side="start", points=points, path_commands=(), stroke_width=1.0)
    assert _rect(by_id["route-candidate:r:target:terminal"]) == marker_ink_bounds(
        target, side="end", points=points, path_commands=(), stroke_width=1.0)


def test_completed_terminal_ink_blocks_label_when_centerline_stroke_is_clear():
    points = ((0.0, 10.0), (40.0, 10.0))
    text = SurfaceObstacle("title", "text", "timeline", ObstacleRect(36.0, 12.0, 74.0, 25.0))
    obstacles = SurfaceObstacleIndex()
    obstacles.add(text)
    assert route_clears_retained_label_ink(points, obstacles, 1.0)

    ink = route_candidate_ink("r", points, None, _triangle(), 1.0)

    assert endpoint_candidate_blocker_ids(ink, obstacles) == ("title",)


def test_terminal_ink_blocks_icon_and_chip_member_label_visuals():
    points = ((0.0, 10.0), (40.0, 10.0))
    obstacles = SurfaceObstacleIndex()
    obstacles.add(SurfaceObstacle(
        "member-label-icon:station", "label-visual", "timeline",
        ObstacleRect(36.0, 12.0, 40.0, 16.0)))
    obstacles.add(SurfaceObstacle(
        "member-label-chip:station", "label-visual", "timeline",
        ObstacleRect(39.0, 13.0, 47.0, 20.0)))

    ink = route_candidate_ink("r", points, None, _triangle(), 1.0)

    assert endpoint_candidate_blocker_ids(ink, obstacles) == (
        "member-label-chip:station", "member-label-icon:station")


def test_curved_path_terminal_uses_completed_path_command_tangent():
    # The endpoint chord is diagonal, but the completed quadratic has a vertical end tangent.
    points = ((0.0, 0.0), (40.0, 40.0))
    commands = (
        PathCommand("move", ((0.0, 0.0),)),
        PathCommand("quadratic", ((40.0, 0.0), (40.0, 40.0))),
    )
    target = _triangle()
    expected = marker_ink_bounds(
        target, side="end", points=points, path_commands=commands, stroke_width=1.0)
    chord_only = marker_ink_bounds(
        target, side="end", points=points, path_commands=(), stroke_width=1.0)
    assert expected != chord_only

    ink = route_candidate_ink("curve", points, None, target, 1.0, path_commands=commands)

    terminal = next(item for item in ink if item.placement_id == "route-candidate:curve:target:terminal")
    assert _rect(terminal) == expected
