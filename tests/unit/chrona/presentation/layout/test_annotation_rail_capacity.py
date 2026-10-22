from datetime import date

from chrona.presentation.layout.annotations import (
    annotation_rail_candidates,
    resolve_annotation_anchor,
)
from chrona.presentation.layout.comparison_marks import ComparisonMark
from chrona.presentation.layout.labels import LabelRect
from chrona.presentation.model.surface_content import AnnotationIntent


def test_annotation_rail_keeps_decimal_exact_shared_bottom_edge():
    annotation = AnnotationIntent(
        "edge-note", "note",
        {"kind": "object", "id": "task", "facet": "planned", "endpoint": "body"},
        "rail", "center", "A complete note.")
    resolved = resolve_annotation_anchor(annotation, (
        ComparisonMark("task", "planned", "span", start=date(2026, 1, 1), end=date(2026, 1, 2)),
    ))

    # This is the bottom-anchored signoff card geometry from the integration
    # case. In binary floats, rail.y + rail.height - card.height is
    # 714.2499999999999, one ulp before the preceding frame's exact 714.25.
    candidates = annotation_rail_candidates(
        annotation, resolved, anchor_y=1000.0, text_size=(180.0, 126.35),
        rail=LabelRect(1302.0, 217.55, 270.0, 623.05), obstacles=())

    assert candidates
    assert candidates[0].placement.bounds.y == 714.25
    assert candidates[0].placement.bounds.bottom == 840.6
