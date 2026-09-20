"""Resolve View presentation annotation anchors against projected marks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .presentation_marks import ComparisonMark


@dataclass(frozen=True)
class AnnotationAnchor:
    annotation_id: str
    object_id: str
    facet: str
    endpoint: str
    mark: ComparisonMark


def resolve_annotation_anchor(annotation: dict, marks: Iterable[ComparisonMark]) -> AnnotationAnchor:
    """Resolve only the initial object target; never substitute an absent Actual."""
    anchor = annotation.get("anchor")
    if not isinstance(anchor, dict) or anchor.get("kind") != "object":
        raise ValueError("E_PRESENTATION_ANCHOR_UNSUPPORTED")
    object_id, facet, endpoint = anchor.get("id"), anchor.get("facet"), anchor.get("endpoint")
    if not isinstance(object_id, str) or facet not in {"planned", "actual"} or endpoint not in {"start", "finish", "at", "body"}:
        raise ValueError("E_PRESENTATION_ANCHOR_MISSING")
    candidates = [mark for mark in marks if mark.source_id == object_id and mark.facet == facet]
    if not candidates:
        raise ValueError("E_PRESENTATION_ANCHOR_MISSING")
    mark = candidates[0]
    if endpoint == "start" and mark.start is None:
        raise ValueError("E_PRESENTATION_ANCHOR_MISSING")
    if endpoint == "finish" and mark.end is None:
        raise ValueError("E_PRESENTATION_ANCHOR_MISSING")
    if endpoint == "at" and mark.at is None:
        raise ValueError("E_PRESENTATION_ANCHOR_MISSING")
    return AnnotationAnchor(str(annotation.get("id", "")), object_id, facet, endpoint, mark)
