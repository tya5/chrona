from __future__ import annotations

from dataclasses import fields, replace
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
from chrona.presentation.layout.surface_annotations import _anchor_failure, annotation_anchor_bounds
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
        resolve_annotation_anchor(replace(_annotation(anchor={"kind": "group", "id": "group-alpha"}),
                                          anchor_source_ref="/body/annotations/3/anchor"), ())
    assert str(unsupported.value).startswith("E_PRESENTATION_ANCHOR_UNSUPPORTED:")
    assert unsupported.value.diagnostic_id == "E_PRESENTATION_ANCHOR_UNSUPPORTED"
    assert unsupported.value.path == "/body/annotations/3/anchor"
    assert "annotation_id='annotation-alpha'" in str(unsupported.value)
    assert "anchor_kind='group'" in str(unsupported.value)


def test_missing_annotation_anchor_names_actual_target():
    with pytest.raises(ValueError) as missing:
        resolve_annotation_anchor(replace(_annotation(
            anchor={"kind": "object", "id": "titlecard", "facet": "actual", "endpoint": "finish"}),
            anchor_source_ref="/body/annotations/0/anchor"), ())
    assert str(missing.value).startswith("E_PRESENTATION_ANCHOR_MISSING:")
    assert missing.value.diagnostic_id == "E_PRESENTATION_ANCHOR_MISSING"
    assert missing.value.path == "/body/annotations/0/anchor"
    assert "annotation_id='annotation-alpha'" in missing.value.detail
    assert "object_id='titlecard'" in missing.value.detail
    assert "facet='actual'" in missing.value.detail
    assert "endpoint='finish'" in missing.value.detail
    assert "no completed actual mark" in missing.value.detail


def test_missing_mark_endpoint_names_exact_endpoint_and_reason():
    mark = ComparisonMark("titlecard", "actual", "span", start=date(2026, 1, 1))
    annotation = replace(_annotation(anchor={"kind": "object", "id": "titlecard", "facet": "actual",
                                      "endpoint": "finish"}),
                         anchor_source_ref="/body/annotations/2/anchor")
    with pytest.raises(ValueError) as missing:
        resolve_annotation_anchor(annotation, (mark,))
    assert missing.value.diagnostic_id == "E_PRESENTATION_ANCHOR_MISSING"
    assert missing.value.path == "/body/annotations/2/anchor"
    assert "endpoint='finish'" in missing.value.detail
    assert "selected mark has no finish date" in missing.value.detail


def test_anchor_source_pointer_is_runtime_only_metadata():
    intent = _annotation()
    other = replace(intent, anchor_source_ref="/body/annotations/8/anchor")
    pointer = next(item for item in fields(AnnotationIntent) if item.name == "anchor_source_ref")
    assert intent.anchor_source_ref == "/"
    assert intent == other
    assert "anchor_source_ref" not in repr(intent)
    assert pointer.kw_only and pointer.compare is False and pointer.hash is False and pointer.repr is False


def test_post_resolution_anchor_geometry_failure_keeps_the_declared_view_pointer():
    mark = ComparisonMark("titlecard", "actual", "span")
    with pytest.raises(ValueError) as missing:
        annotation_anchor_bounds(mark, "body", None, None,
                                 source_ref="/body/annotations/4/anchor", annotation_id="view-note")
    assert missing.value.diagnostic_id == "E_PRESENTATION_ANCHOR_MISSING"
    assert missing.value.path == "/body/annotations/4/anchor"
    assert "annotation_id='view-note'" in missing.value.detail
    assert "object_id='titlecard'" in missing.value.detail
    assert "endpoint='body'" in missing.value.detail
    assert "no resolved endpoint date" in missing.value.detail


def test_post_resolution_anchor_detail_bounds_operands_but_preserves_full_pointer():
    long_id = "annotation-\n" + ("a" * 180)
    long_object_id = "object-\r" + ("b" * 180)
    pointer = "/body/annotations/123456789/anchor"
    mark = ComparisonMark(long_object_id, "actual", "span")
    with pytest.raises(ValueError) as missing:
        annotation_anchor_bounds(mark, "finish", None, None,
                                 source_ref=pointer, annotation_id=long_id)
    error = missing.value
    assert error.path == pointer
    assert "reason=selected mark has no resolved endpoint date" in error.detail
    assert "\n" not in error.detail and "\r" not in error.detail
    for operand in ("annotation_id=", "object_id="):
        rendered = error.detail.split(operand, 1)[1].split(", ", 1)[0]
        assert len(rendered) <= 96


def test_post_resolution_host_failure_keeps_the_same_anchor_provenance():
    annotation = replace(_annotation(anchor={"kind": "object", "id": "titlecard",
                                           "facet": "actual", "endpoint": "body"}),
                         anchor_source_ref="/body/annotations/5/anchor")
    failure = _anchor_failure(annotation, "selected mark has no matching rendered row or folded point")
    assert failure.diagnostic_id == "E_PRESENTATION_ANCHOR_MISSING"
    assert failure.path == "/body/annotations/5/anchor"
    assert "object_id='titlecard'" in failure.detail
    assert "facet='actual'" in failure.detail
    assert "endpoint='body'" in failure.detail


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
