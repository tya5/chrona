"""Compatibility exports for annotation geometry now owned by Layout."""
from chrona.presentation.layout.annotations import (
    AnnotationAnchor, AnnotationBox, nearest_box_port, place_annotation_rail,
    project_annotation_box, resolve_annotation_anchor, route_annotation_leader,
)

__all__ = (
    "AnnotationAnchor", "AnnotationBox", "nearest_box_port", "place_annotation_rail",
    "project_annotation_box", "resolve_annotation_anchor", "route_annotation_leader",
)
