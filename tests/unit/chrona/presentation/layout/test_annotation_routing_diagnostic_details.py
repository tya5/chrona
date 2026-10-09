from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.annotation_search import (
    lattice_positions,
    nearest_free_routed_tail_box,
)
from chrona.presentation.layout.annotation_topology import route_strict_bounded
from chrona.presentation.layout.annotations import (
    AnnotationAnchor,
    project_annotation_box,
    resolve_annotation_anchor,
    route_annotation_leader,
)
from chrona.presentation.layout.comparison_marks import ComparisonMark
from chrona.presentation.layout.labels import LabelRect
from chrona.presentation.layout.obstacles import (
    ObstacleRect,
    ObstacleSegment,
    SurfaceObstacle,
    SurfaceObstacleIndex,
)
from chrona.presentation.layout.routing import (
    RelationRouteSelection,
    RouteAttemptEvidence,
    RouteSuppressionEvidence,
    route_quality_metrics,
)
from chrona.presentation.model.surface_content import AnnotationIntent


def _annotation(*, anchor=None, purpose="note", alignment="center"):
    return AnnotationIntent("annotation-alpha", purpose,
                            anchor or {"kind": "object", "id": "object-alpha",
                                       "facet": "planned", "endpoint": "finish"},
                            "above", alignment, "short note")


def test_annotation_route_budget_error_names_inputs():
    with pytest.raises(ValueError) as limit:
        route_annotation_leader((1, 2), (8, 9), obstacles=(), limit=0)
    assert str(limit.value).startswith("E_PRESENTATION_ROUTE_LIMIT:")
    assert "state_limit=0" in str(limit.value)
    assert "source=(1, 2)" in str(limit.value)
    assert "target=(8, 9)" in str(limit.value)


def test_unsupported_annotation_anchor_names_actual_kind():
    with pytest.raises(ValueError) as unsupported:
        resolve_annotation_anchor(_annotation(anchor={"kind": "group", "id": "group-alpha"}), ())
    assert str(unsupported.value).startswith("E_PRESENTATION_ANCHOR_UNSUPPORTED:")
    assert "annotation_id='annotation-alpha'" in str(unsupported.value)
    assert "anchor_kind='group'" in str(unsupported.value)


def test_missing_annotation_anchor_names_actual_target():
    with pytest.raises(ValueError) as missing:
        resolve_annotation_anchor(_annotation(), ())
    assert str(missing.value).startswith("E_PRESENTATION_ANCHOR_MISSING:")
    assert "object_id='object-alpha'" in str(missing.value)
    assert "facet='planned'" in str(missing.value)


def test_unsupported_annotation_purpose_names_actual_value():
    mark = ComparisonMark("object-alpha", "planned", "span",
                         start=date(2026, 1, 1), end=date(2026, 1, 4))
    resolved = AnnotationAnchor("annotation-alpha", "object-alpha", "planned", "finish", mark)
    with pytest.raises(ValueError) as purpose:
        project_annotation_box(_annotation(purpose="unknown-purpose"), resolved,
                               anchor_bounds=LabelRect(1, 1, 2, 2), text_size=(4, 3),
                               candidate_sides=("above",), viewport=LabelRect(0, 0, 50, 40),
                               obstacles=(), overflow="visible-overflow")
    assert str(purpose.value).startswith("E_PRESENTATION_ANCHOR_UNSUPPORTED:")
    assert "purpose='unknown-purpose'" in str(purpose.value)


def test_annotation_alignment_error_names_authored_field():
    mark = ComparisonMark("object-alpha", "planned", "span",
                         start=date(2026, 1, 1), end=date(2026, 1, 4))
    resolved = AnnotationAnchor("annotation-alpha", "object-alpha", "planned", "finish", mark)
    with pytest.raises(ValueError) as alignment:
        project_annotation_box(_annotation(alignment="diagonal"), resolved,
                               anchor_bounds=LabelRect(1, 1, 2, 2), text_size=(4, 3),
                               candidate_sides=("above",), viewport=LabelRect(0, 0, 50, 40),
                               obstacles=(), overflow="visible-overflow")
    assert str(alignment.value).startswith("E_PRESENTATION_LABEL_INPUT:")
    assert "annotation_id='annotation-alpha'" in str(alignment.value)
    assert "alignment='diagonal'" in str(alignment.value)


def test_obstacle_geometry_error_names_bad_bounds():
    with pytest.raises(ValueError) as rect:
        ObstacleRect(0, 0, 0, 4)
    assert str(rect.value).startswith("E_LAYOUT_OBSTACLE_GEOMETRY:")
    assert "right=0" in str(rect.value)

def test_obstacle_segment_geometry_error_names_bad_endpoints():
    with pytest.raises(ValueError) as segment:
        ObstacleSegment((1, 1), (1, 1))
    assert str(segment.value).startswith("E_LAYOUT_OBSTACLE_GEOMETRY:")
    assert "start=(1, 1)" in str(segment.value)


def test_surface_obstacle_input_error_names_clearance():
    with pytest.raises(ValueError) as obstacle:
        SurfaceObstacle("mark-alpha", "mark", "timeline", ObstacleRect(0, 0, 2, 2), -1)
    assert str(obstacle.value).startswith("E_LAYOUT_OBSTACLE_INPUT:")
    assert "placement_id='mark-alpha'" in str(obstacle.value)
    assert "clearance=-1" in str(obstacle.value)


def test_obstacle_override_error_names_unknown_id():
    index = SurfaceObstacleIndex()
    registered = SurfaceObstacle("mark-alpha", "mark", "timeline", ObstacleRect(0, 0, 2, 2))
    index.add(registered)
    with pytest.raises(ValueError) as override:
        index.copy(geometry_overrides={"mark-missing": ObstacleRect(0, 0, 1, 1)})
    assert str(override.value).startswith("E_LAYOUT_OBSTACLE_INPUT:")
    assert "mark-missing" in str(override.value)


def test_obstacle_clearance_error_names_invalid_clearance():
    index = SurfaceObstacleIndex()
    with pytest.raises(ValueError) as clearance:
        index.collisions(ObstacleRect(4, 4, 6, 6), clearance=-0.5)
    assert str(clearance.value).startswith("E_LAYOUT_OBSTACLE_INPUT:")
    assert "clearance=-0.5" in str(clearance.value)


def test_duplicate_obstacle_error_names_registered_id():
    index = SurfaceObstacleIndex()
    registered = SurfaceObstacle("mark-alpha", "mark", "timeline", ObstacleRect(0, 0, 2, 2))
    index.add(registered)
    with pytest.raises(ValueError) as duplicate:
        index.add(registered)
    assert str(duplicate.value).startswith("E_LAYOUT_OBSTACLE_ID_DUPLICATE:")
    assert "placement_id='mark-alpha'" in str(duplicate.value)


def test_obstacle_host_exemption_error_names_actual_class():
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("text-alpha", "text", "timeline", ObstacleRect(0, 0, 2, 2)))
    candidate = ObstacleRect(4, 4, 6, 6)
    with pytest.raises(ValueError) as host:
        index.collisions(candidate, host_id="text-alpha")
    assert str(host.value).startswith("E_LAYOUT_OBSTACLE_EXEMPTION_INVALID:")
    assert "host_id='text-alpha'" in str(host.value)
    assert "actual_class='text'" in str(host.value)

def test_obstacle_rule_exemption_error_names_missing_id():
    index = SurfaceObstacleIndex()
    candidate = ObstacleRect(4, 4, 6, 6)
    with pytest.raises(ValueError) as rule:
        index.collisions(candidate, rule_host_id="rule-missing")
    assert str(rule.value).startswith("E_LAYOUT_OBSTACLE_EXEMPTION_INVALID:")
    assert "rule_host_id='rule-missing'" in str(rule.value)


def test_obstacle_port_exemption_error_names_missing_id():
    index = SurfaceObstacleIndex()
    candidate = ObstacleRect(4, 4, 6, 6)
    with pytest.raises(ValueError) as port:
        index.collisions(candidate, port_ids=("port-missing",))
    assert str(port.value).startswith("E_LAYOUT_OBSTACLE_EXEMPTION_INVALID:")
    assert "invalid_port_ids=('port-missing',)" in str(port.value)


def test_route_attempt_and_selection_errors_name_candidate_and_metrics():
    with pytest.raises(ValueError) as attempt:
        RouteAttemptEvidence("north", "south", "egress-collision")
    assert str(attempt.value).startswith("E_LAYOUT_ROUTE_ATTEMPT_INVALID:")
    assert "source_side='north'" in str(attempt.value)
    assert "outcome='egress-collision'" in str(attempt.value)

    with pytest.raises(ValueError) as disposition:
        RouteAttemptEvidence("north", "south", "quality-rejected", length=1,
                             direct_length=1, bends=0, max_bends=0,
                             max_detour_ratio=1, search_disposition="unknown")
    assert "search_disposition='unknown'" in str(disposition.value)

    with pytest.raises(ValueError) as metrics:
        route_quality_metrics(((1, 2),))
    assert "point_count=1" in str(metrics.value)

    with pytest.raises(ValueError) as suppression:
        RouteSuppressionEvidence("relation-alpha", ())
    assert "relation_id='relation-alpha'" in str(suppression.value)

    with pytest.raises(ValueError) as selection:
        RelationRouteSelection(None, ((1, 2),), ())
    assert "point_count=1" in str(selection.value)


def test_annotation_lattice_search_error_names_candidate_inputs():
    with pytest.raises(ValueError) as lattice:
        lattice_positions(LabelRect(0, 0, 10, 10), (0, 2), (4, 4), 5)
    assert str(lattice.value).startswith("E_LAYOUT_ANNOTATION_SEARCH_INPUT:")
    assert "box_size=(0, 2)" in str(lattice.value)
    assert "max_positions=5" in str(lattice.value)


def test_routed_tail_search_error_names_budget_and_anchor():
    with pytest.raises(ValueError) as tail:
        nearest_free_routed_tail_box(
            region=LabelRect(0, 0, 20, 20), anchor=SimpleNamespace(
                bounds=SimpleNamespace(inline=1, inline_size=2, block=1, block_size=2),
                placement_id="mark-alpha"),
            endpoint="finish", siblings=(), box_size=(4, 3), max_positions=5,
            obstacles=SurfaceObstacleIndex(), obstacle_classes=("mark",),
            corner_radius=0, tail_base=1, content_bounds=(0, 0, 20, 20),
            route_state_limit=0)
    assert "route_state_limit=0" in str(tail.value)
    assert "anchor_id='mark-alpha'" in str(tail.value)


def test_annotation_topology_error_names_search_budget_and_route():
    with pytest.raises(ValueError) as topology:
        route_strict_bounded((1, 2), (8, 9), SurfaceObstacleIndex(),
                             bounds=(0, 0, 10, 10), limit=0,
                             max_bends=3, max_detour_ratio=2)
    assert str(topology.value).startswith("E_LAYOUT_ANNOTATION_SEARCH_INPUT:")
    assert "state_limit=0" in str(topology.value)
    assert "start=(1, 2)" in str(topology.value)
