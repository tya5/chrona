from datetime import date

import pytest

from chrona.presentation_annotations import project_annotation_box, resolve_annotation_anchor
from chrona.presentation_labels import LabelRect
from chrona.presentation_marks import ComparisonMark


def test_annotation_resolves_declared_actual_finish_without_plan_substitution():
    marks = [ComparisonMark("ship", "planned", "span", start=date(2027, 1, 1), end=date(2027, 1, 8)),
             ComparisonMark("ship", "actual", "span", start=date(2027, 1, 2), end=date(2027, 1, 10))]
    resolved = resolve_annotation_anchor({"id": "note", "anchor": {"kind": "object", "id": "ship", "facet": "actual", "endpoint": "finish"}}, marks)
    assert resolved.mark.end == date(2027, 1, 10)


def test_annotation_rejects_missing_actual_and_non_object_anchors():
    marks = [ComparisonMark("ship", "planned", "span", start=date(2027, 1, 1), end=date(2027, 1, 8))]
    with pytest.raises(ValueError, match="E_PRESENTATION_ANCHOR_MISSING"):
        resolve_annotation_anchor({"anchor": {"kind": "object", "id": "ship", "facet": "actual", "endpoint": "finish"}}, marks)
    with pytest.raises(ValueError, match="E_PRESENTATION_ANCHOR_UNSUPPORTED"):
        resolve_annotation_anchor({"anchor": {"kind": "group", "id": "team", "endpoint": "body"}}, marks)


def test_annotation_box_uses_shared_finite_label_placement():
    annotation = {"id": "note", "purpose": "callout", "anchor": {"kind": "object", "id": "ship", "facet": "planned", "endpoint": "finish"}}
    resolved = resolve_annotation_anchor(annotation, [ComparisonMark("ship", "planned", "span", start=date(2027, 1, 1), end=date(2027, 1, 8))])
    box = project_annotation_box(annotation, resolved, anchor_bounds=LabelRect(40, 40, 10, 10), text_size=(30, 10),
                                 candidate_sides=["above", "below"], viewport=LabelRect(0, 0, 100, 100), obstacles=[], overflow="diagnose")
    assert box.placement.side == "above" and box.leader_required
