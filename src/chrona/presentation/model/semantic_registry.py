"""Canonical presentation semantics and their stable Scene compatibility roles."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SemanticBinding:
    semantic_id: str
    primitive_kind: str
    purpose: str
    scene_role: str
    theme_role: str


_REGISTRY = {
    "planned": SemanticBinding("planned", "mark", "planned", "planned", "planned"),
    "actual": SemanticBinding("actual", "mark", "actual", "actual", "actual"),
    # Public Scene role remains hyphenated; theme authoring resolves the canonical asOf binding.
    "asOf": SemanticBinding("asOf", "line", "as-of", "as-of", "asOf"),
    "groupHeader": SemanticBinding("groupHeader", "decoration", "group-header", "group-header", "groupHeader"),
    "calendarClosed": SemanticBinding("calendarClosed", "decoration", "calendar-closed", "calendar-closed", "calendarClosed"),
    "axisBand": SemanticBinding("axisBand", "label", "axis-band", "axis-band", "axis"),
    "legendEntry": SemanticBinding("legendEntry", "decoration", "legend-swatch", "legend-swatch", "legend"),
    "annotation": SemanticBinding("annotation", "decoration", "annotation", "annotation", "annotation"),
}


def semantic_binding(semantic_id: str) -> SemanticBinding:
    """Return the only allowed mapping from normalized meaning to Scene role."""
    try:
        return _REGISTRY[semantic_id]
    except KeyError as error:
        raise ValueError(f"E_PRESENTATION_SEMANTIC_UNKNOWN:{semantic_id}") from error


def enabled_semantics(*, has_as_of: bool, has_group_headers: bool,
                      has_calendar_closure: bool, has_axis_bands: bool,
                      has_legend: bool, has_annotations: bool) -> tuple[SemanticBinding, ...]:
    """Enumerate enabled semantics for contract-level verification."""
    names = ["planned", "actual"]
    if has_as_of:
        names.append("asOf")
    if has_group_headers:
        names.append("groupHeader")
    if has_calendar_closure:
        names.append("calendarClosed")
    if has_axis_bands:
        names.append("axisBand")
    if has_legend:
        names.append("legendEntry")
    if has_annotations:
        names.append("annotation")
    return tuple(semantic_binding(name) for name in names)
