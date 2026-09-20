from datetime import date

import pytest

from chrona.presentation_annotations import resolve_annotation_anchor
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
