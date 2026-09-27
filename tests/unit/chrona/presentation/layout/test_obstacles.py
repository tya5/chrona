"""Shared surface obstacle geometry and identity invariants."""
from __future__ import annotations

import pytest
from datetime import date

from chrona.presentation.layout.annotations import annotation_rail_candidates, resolve_annotation_anchor
from chrona.presentation.layout.comparison_marks import ComparisonMark
from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex,
)
from chrona.presentation.layout.labels import LabelRect, place_label
from chrona.presentation.layout.routing import route_orthogonal
from chrona.presentation.layout.annotations import route_annotation_leader
from chrona.presentation.model.surface_content import AnnotationIntent


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


def test_rule_label_can_exempt_only_its_named_rule() -> None:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("as-of", "rule", "timeline", ObstacleSegment((20, 0), (20, 40))))
    index.add(SurfaceObstacle("another-rule", "rule", "timeline", ObstacleSegment((30, 0), (30, 40))))
    box = ObstacleRect(15, 10, 35, 20)
    assert [item.placement_id for item in index.collisions(box, rule_host_id="as-of")] == ["another-rule"]
    with pytest.raises(ValueError, match="E_LAYOUT_OBSTACLE_EXEMPTION_INVALID"):
        index.collisions(box, rule_host_id="missing")


def test_dependency_line_blocks_note_and_perpendicular_leader() -> None:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("dependency:x", "dependency-route", "timeline",
                              ObstacleSegment((12, 15), (80, 15), stroke_width=2)))
    assert index.collisions(ObstacleRect(40, 14, 60, 28))[0].placement_id == "dependency:x"
    assert index.collisions(ObstacleSegment((50, 3), (50, 30)))[0].placement_id == "dependency:x"
    assert index.collisions(ObstacleSegment((50, 30), (80, 30))) == ()


def test_note_beside_dependency_line_moves_in_same_rail_without_covering_it() -> None:
    intent = AnnotationIntent("risk", "note",
                              {"kind": "object", "id": "ship", "facet": "planned", "endpoint": "finish"},
                              "above", "center", "A risk")
    resolved = resolve_annotation_anchor(intent, (
        ComparisonMark("ship", "planned", "span", start=date(2027, 1, 1), end=date(2027, 1, 8)),))
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("dependency:ship", "dependency-route", "annotations",
                              ObstacleSegment((100, 50), (160, 50), stroke_width=2)))
    candidates = annotation_rail_candidates(intent, resolved, anchor_y=50, text_size=(30, 10),
                                            rail=LabelRect(110, 0, 40, 100), obstacles=index)
    assert candidates
    box = candidates[0].placement.bounds
    assert box.y != 45
    assert index.collisions(ObstacleRect(box.x, box.y, box.right, box.bottom)) == ()


def test_touching_rectangles_and_collinear_paths_have_declared_clearance() -> None:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("a", "mark", "timeline", ObstacleRect(0, 0, 10, 10)))
    assert index.collisions(ObstacleRect(10, 0, 20, 10)) == ()
    assert index.collisions(ObstacleRect(10, 0, 20, 10), clearance=0.1)
    line = SurfaceObstacleIndex()
    line.add(SurfaceObstacle("line", "dependency-route", "timeline", ObstacleSegment((0, 0), (10, 0))))
    assert line.collisions(ObstacleSegment((5, 0), (15, 0)))
    assert line.collisions(ObstacleSegment((10, 0), (15, 0))) == ()


def test_mark_boundary_port_ignores_float_noise_but_not_interior_crossing() -> None:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("mark", "mark", "timeline", ObstacleRect(0, 0, 10, 10)))
    assert index.collisions(ObstacleSegment((10, 5), (11, 5))) == ()
    assert index.collisions(ObstacleSegment((10 - 2e-13, 5), (11, 5))) == ()
    assert index.collisions(ObstacleSegment((5, 10 - 2e-13), (5, 11))) == ()
    assert index.collisions(ObstacleSegment((10 - 1e-5, 5), (11, 5)))
    assert index.collisions(ObstacleSegment((5, 10 - 1e-5), (5, 11)))


def test_duplicate_and_invalid_geometry_fail_before_composition() -> None:
    index = SurfaceObstacleIndex()
    obstacle = SurfaceObstacle("a", "mark", "timeline", ObstacleRect(0, 0, 1, 1))
    index.add(obstacle)
    with pytest.raises(ValueError, match="E_LAYOUT_OBSTACLE_ID_DUPLICATE"):
        index.add(obstacle)
    with pytest.raises(ValueError, match="E_LAYOUT_OBSTACLE_GEOMETRY"):
        ObstacleSegment((0, 0), (0, 0))
    with pytest.raises(ValueError, match="E_LAYOUT_OBSTACLE_GEOMETRY"):
        ObstacleRect(0, 0, float("nan"), 1)


def test_diagonal_fallback_route_is_exact_obstacle() -> None:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("fallback:diagonal", "dependency-route", "timeline",
                              ObstacleSegment((0, 0), (20, 20), stroke_width=2)))
    assert index.collisions(ObstacleRect(9, 9, 11, 11))
    assert index.collisions(ObstacleRect(1, 17, 3, 19)) == ()
    assert index.collisions(ObstacleSegment((0, 20), (20, 0)))


def test_egress_exempts_only_named_host_on_that_segment() -> None:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("host", "mark", "timeline", ObstacleRect(0, 0, 20, 10)))
    index.add(SurfaceObstacle("other", "mark", "timeline", ObstacleRect(12, 0, 30, 10)))
    corridor = ObstacleSegment((10, 5), (25, 5))
    assert [item.placement_id for item in index.egress_collisions(corridor, host_ids=("host",))] == ["other"]
    assert [item.placement_id for item in index.collisions(corridor)] == ["host", "other"]


def test_egress_may_branch_transversely_at_shared_stroked_route_endpoint() -> None:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("host", "mark", "timeline", ObstacleRect(-10, -10, 0, 10)))
    index.add(SurfaceObstacle("dependency", "dependency-route", "timeline",
                              ObstacleSegment((0, 0), (0, 30), stroke_width=1)))
    assert index.egress_collisions(ObstacleSegment((0, 0), (6, 0)), host_ids=("host",)) == ()
    assert index.egress_collisions(ObstacleSegment((0, 0), (0, -6)), host_ids=("host",)) == ()
    assert index.egress_collisions(ObstacleSegment((0, 0), (0, 6)), host_ids=("host",))


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
