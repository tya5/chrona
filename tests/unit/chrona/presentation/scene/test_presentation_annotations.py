from datetime import date

import pytest

from chrona.presentation.layout.annotations import nearest_box_port, place_annotation_rail, project_annotation_box, resolve_annotation_anchor, route_annotation_leader
from chrona.presentation.layout.labels import LabelRect
from chrona.presentation.layout.routing import relation_route_quality
from chrona.presentation.layout.comparison_marks import ComparisonMark
from chrona.presentation.model.surface_content import AnnotationIntent


def annotation(**overrides):
    value = {
        "annotation_id": "note", "purpose": "callout",
        "anchor": {"kind": "object", "id": "ship", "facet": "planned", "endpoint": "finish"},
        "side": "above", "alignment": "center", "content": "Watch this",
    }
    value.update(overrides)
    return AnnotationIntent(**value)


def test_annotation_resolves_declared_actual_finish_without_plan_substitution():
    marks = [ComparisonMark("ship", "planned", "span", start=date(2027, 1, 1), end=date(2027, 1, 8)),
             ComparisonMark("ship", "actual", "span", start=date(2027, 1, 2), end=date(2027, 1, 10))]
    resolved = resolve_annotation_anchor(annotation(anchor={"kind": "object", "id": "ship", "facet": "actual", "endpoint": "finish"}), marks)
    assert resolved.mark.end == date(2027, 1, 10)


def test_annotation_rejects_missing_actual_and_non_object_anchors():
    marks = [ComparisonMark("ship", "planned", "span", start=date(2027, 1, 1), end=date(2027, 1, 8))]
    with pytest.raises(ValueError, match="E_PRESENTATION_ANCHOR_MISSING"):
        resolve_annotation_anchor(annotation(anchor={"kind": "object", "id": "ship", "facet": "actual", "endpoint": "finish"}), marks)
    with pytest.raises(ValueError, match="E_PRESENTATION_ANCHOR_UNSUPPORTED"):
        resolve_annotation_anchor(annotation(anchor={"kind": "group", "id": "team", "endpoint": "body"}), marks)


def test_annotation_box_uses_shared_finite_label_placement():
    intent = annotation()
    resolved = resolve_annotation_anchor(intent, [ComparisonMark("ship", "planned", "span", start=date(2027, 1, 1), end=date(2027, 1, 8))])
    box = project_annotation_box(intent, resolved, anchor_bounds=LabelRect(40, 40, 10, 10), text_size=(30, 10),
                                 candidate_sides=["above", "below"], viewport=LabelRect(0, 0, 100, 100), obstacles=[], overflow="visible-overflow")
    assert box.placement.side == "above" and box.leader_required


def test_leader_port_and_route_are_deterministic_and_bounded():
    box = LabelRect(10, 10, 20, 10)
    assert nearest_box_port(box, (20, 0)) == (20, 10)
    route = route_annotation_leader((0, 0), (40, 0), obstacles=[box], limit=32)
    assert route[0] == (0, 0) and route[-1] == (40, 0)
    with pytest.raises(ValueError, match="E_PRESENTATION_ROUTE_LIMIT"):
        route_annotation_leader((0, 0), (40, 0), obstacles=[box], limit=1)


def test_annotation_leader_compacts_visibility_grid_vertices_before_quality_evaluation():
    route = route_annotation_leader((0, 0), (40, 0), obstacles=[LabelRect(10, -5, 20, 10)], limit=32)

    assert relation_route_quality(route, max_bends=3, max_detour_ratio=2)
    assert all(
        (middle[0] - first[0]) * (last[1] - middle[1])
        != (middle[1] - first[1]) * (last[0] - middle[0])
        for first, middle, last in zip(route, route[1:], route[2:])
    )


def test_callout_uses_annotation_rail_without_timeline_obstacles():
    intent = annotation(annotation_id="risk")
    resolved = resolve_annotation_anchor(intent, [ComparisonMark("ship", "planned", "span", start=date(2027, 1, 1), end=date(2027, 1, 8))])

    box = place_annotation_rail(intent, resolved, anchor_y=50, text_size=(30, 10),
                                rail=LabelRect(110, 0, 40, 100), obstacles=(),
                                overflow="visible-overflow", required=True)

    assert box is not None
    assert box.placement.side == "rail"
    assert box.placement.bounds.x == 110
    assert box.leader_required
