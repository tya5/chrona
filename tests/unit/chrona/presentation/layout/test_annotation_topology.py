"""Atomic annotation connector topology and visible bridge geometry."""
from __future__ import annotations

from chrona.presentation.layout.annotation_topology import (
    local_route_bounds, route_annotation_candidate, visible_segments,
)
from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex,
)


def test_strict_connector_uses_one_shared_index() -> None:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("dep", "dependency-route", "timeline",
                              ObstacleSegment((20, 20), (80, 20))))
    trial = route_annotation_candidate((10, 10), (90, 10), index,
                                       bounds=(0, 0, 100, 40), max_bends=2,
                                       max_detour_ratio=2)
    assert trial is not None and trial.topology == "strict"
    assert trial.points == ((10, 10), (90, 10))
    assert trial.crossing_ids == ()


def test_bridge_gaps_only_later_connector_at_transverse_crossing() -> None:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("dep", "dependency-route", "timeline",
                              ObstacleSegment((50, 0), (50, 40))))
    trial = route_annotation_candidate((10, 20), (90, 20), index,
                                       bounds=(0, 0, 100, 40), max_bends=2,
                                       max_detour_ratio=2, allow_bridge=True)
    assert trial is not None and trial.topology == "bridge"
    assert trial.crossing_ids == ("dep",)
    assert [command.kind for command in trial.commands] == ["move", "line", "move", "line"]
    assert index.collisions(ObstacleSegment(*visible_segments(trial)[0]), classes=("dependency-route",)) == ()
    assert index.collisions(ObstacleSegment(*visible_segments(trial)[1]), classes=("dependency-route",)) == ()
    assert index.has("dep")


def test_bridge_never_exempts_text_or_rule() -> None:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("dep", "dependency-route", "timeline",
                              ObstacleSegment((50, 0), (50, 40))))
    index.add(SurfaceObstacle("text", "text", "timeline", ObstacleRect(45, 15, 55, 25)))
    index.add(SurfaceObstacle("rule", "rule", "timeline", ObstacleSegment((0, 30), (100, 30))))
    trial = route_annotation_candidate((10, 20), (90, 20), index,
                                       bounds=(0, 0, 100, 40), max_bends=2,
                                       max_detour_ratio=1.5, allow_bridge=True)
    assert trial is None or not any(index.collisions(ObstacleSegment(a, b), classes=("text", "rule"))
                                    for a, b in visible_segments(trial))


def test_local_corridor_excludes_slide_perimeter() -> None:
    assert local_route_bounds((1200, 300, 20, 20), (24, 1130, 312, 20),
                              (336, 1140), (0, 0, 1600, 1200)) == (180.0, 144.0, 1376.0, 1200)
