"""Shared surface obstacle geometry and identity invariants."""
from __future__ import annotations

import pytest

from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex,
)
from chrona.presentation.layout.labels import LabelRect, place_label
from chrona.presentation.layout.routing import route_orthogonal
from chrona.presentation.layout.annotations import route_annotation_leader


def test_single_index_queries_rectangles_and_exact_route_segments() -> None:
    index = SurfaceObstacleIndex()
    index.extend((
        SurfaceObstacle("route:b", "dependency-route", "timeline",
                        ObstacleSegment((10, 20), (90, 20), stroke_width=2)),
        SurfaceObstacle("mark:a", "mark", "timeline", ObstacleRect(30, 30, 50, 40)),
    ))
    assert [item.placement_id for item in index.all()] == ["mark:a", "route:b"]
    assert [item.placement_id for item in index.collisions(ObstacleRect(40, 18, 60, 22))] == ["route:b"]
    # The route's bounding box would cover this note; its stroked segments do not.
    assert index.collisions(ObstacleRect(40, 22, 60, 29)) == ()
    assert [item.placement_id for item in index.collisions(ObstacleRect(40, 35, 60, 45))] == ["mark:a"]


def test_query_filters_and_named_exemptions_are_explicit() -> None:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("mark:a", "mark", "timeline", ObstacleRect(0, 0, 10, 10)))
    index.add(SurfaceObstacle("label:b", "text", "timeline", ObstacleRect(2, 2, 8, 8)))
    box = ObstacleRect(3, 3, 7, 7)
    assert [item.placement_id for item in index.collisions(box, classes=("text",))] == ["label:b"]
    assert [item.placement_id for item in index.collisions(box, host_id="mark:a")] == ["label:b"]
    assert index.collisions(box, regions=("table",)) == ()
    with pytest.raises(ValueError, match="E_LAYOUT_OBSTACLE_EXEMPTION_INVALID"):
        index.collisions(box, host_id="all-marks")
    with pytest.raises(ValueError, match="E_LAYOUT_OBSTACLE_EXEMPTION_INVALID"):
        index.collisions(box, port_ids=("mark:a",))


def test_dependency_line_blocks_note_and_perpendicular_leader() -> None:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("dependency:x", "dependency-route", "timeline",
                              ObstacleSegment((12, 15), (80, 15), stroke_width=2)))
    assert index.collisions(ObstacleRect(40, 14, 60, 28))[0].placement_id == "dependency:x"
    assert index.collisions(ObstacleSegment((50, 3), (50, 30)))[0].placement_id == "dependency:x"
    assert index.collisions(ObstacleSegment((50, 30), (80, 30))) == ()


def test_touching_rectangles_and_collinear_paths_have_declared_clearance() -> None:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("a", "mark", "timeline", ObstacleRect(0, 0, 10, 10)))
    assert index.collisions(ObstacleRect(10, 0, 20, 10)) == ()
    assert index.collisions(ObstacleRect(10, 0, 20, 10), clearance=0.1)
    line = SurfaceObstacleIndex()
    line.add(SurfaceObstacle("line", "dependency-route", "timeline", ObstacleSegment((0, 0), (10, 0))))
    assert line.collisions(ObstacleSegment((5, 0), (15, 0)))
    assert line.collisions(ObstacleSegment((10, 0), (15, 0))) == ()


def test_duplicate_and_invalid_geometry_fail_before_composition() -> None:
    index = SurfaceObstacleIndex()
    obstacle = SurfaceObstacle("a", "mark", "timeline", ObstacleRect(0, 0, 1, 1))
    index.add(obstacle)
    with pytest.raises(ValueError, match="E_LAYOUT_OBSTACLE_ID_DUPLICATE"):
        index.add(obstacle)
    with pytest.raises(ValueError, match="E_LAYOUT_OBSTACLE_GEOMETRY"):
        ObstacleSegment((0, 0), (1, 1))
    with pytest.raises(ValueError, match="E_LAYOUT_OBSTACLE_GEOMETRY"):
        ObstacleRect(0, 0, float("nan"), 1)


def test_existing_label_ladder_can_query_shared_inventory() -> None:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("mark:host", "mark", "timeline", ObstacleRect(10, 10, 30, 20)))
    index.add(SurfaceObstacle("route:other", "dependency-route", "timeline",
                              ObstacleSegment((32, 0), (32, 40), stroke_width=2)))
    placed = place_label(LabelRect(10, 10, 20, 10), (8, 8), ("end", "inside"),
                         bounds=LabelRect(0, 0, 100, 100), obstacles=index,
                         inside_host_obstacle_id="mark:host")
    assert placed is not None and placed.side == "inside"


def test_relation_router_queries_exact_shared_segment() -> None:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("route:prior", "dependency-route", "timeline",
                              ObstacleSegment((10, 20), (90, 20), stroke_width=2)))
    points = route_orthogonal((5, 10), (95, 10), index, bounds=(0, 0, 100, 40))
    assert points == ((5, 10), (95, 10))


def test_annotation_leader_uses_same_dependency_route_obstacle() -> None:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("dependency:one", "dependency-route", "timeline",
                              ObstacleSegment((10, 20), (90, 20), stroke_width=2)))
    points = route_annotation_leader((5, 10), (95, 10), obstacles=index, limit=1024)
    assert points == ((5, 10), (95, 10))
