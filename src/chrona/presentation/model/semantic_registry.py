"""The presentation vocabulary: the one place a semantic is introduced.

Every visual meaning the review surface can carry is declared here once, with
the Scene purpose, the Scene role and the Theme role it resolves to. Scene
builds primitives by looking a semantic up; nothing downstream spells a purpose
or a role as a literal, so adding a visual idea is one entry plus the code that
draws it, and a misspelling is a lookup failure rather than a silent blank.

The Slot and PrimitiveKind enumerations are the other two closed vocabularies:
what a Layout Profile may name, and what a renderer must be able to draw.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PrimitiveKind(str, Enum):
    """Every shape a renderer must handle; Scene emits nothing else."""

    RECT = "Rect"
    TEXT = "Text"
    SYMBOL = "Symbol"
    PATH = "Path"


class Slot(str, Enum):
    """Every surface region a Layout Profile may bind content to."""

    TITLE = "title"
    TABLE = "table"
    TIMELINE = "timeline"
    TIMELINE_AXIS = "timeline-axis"
    NETWORK = "network"
    SUMMARY = "summary"
    LEGEND = "legend"
    GROUP_DETAILS = "group-details"
    OBSERVATIONS = "observations"
    MILESTONES = "milestones"
    ANNOTATIONS = "annotations"
    NOTES = "notes"


REQUIRED_SLOTS = (Slot.TITLE, Slot.TABLE, Slot.TIMELINE, Slot.TIMELINE_AXIS)


@dataclass(frozen=True)
class SemanticBinding:
    """One visual meaning, and the vocabulary it resolves to downstream."""

    semantic_id: str
    primitive_kind: str
    purpose: str
    scene_role: str
    theme_role: str


def _binding(semantic_id: str, primitive_kind: str, purpose: str,
             scene_role: str, theme_role: str) -> SemanticBinding:
    return SemanticBinding(semantic_id, primitive_kind, purpose, scene_role, theme_role)


_REGISTRY: dict[str, SemanticBinding] = {binding.semantic_id: binding for binding in (
    # Comparison marks.
    _binding("planned", "mark", "planned", "planned", "planned"),
    _binding("actual", "mark", "actual", "actual", "actual"),
    _binding("snapshot", "mark", "snapshot", "snapshot", "snapshot"),
    _binding("missingActual", "mark", "missingActual", "missing-actual", "missing-actual"),
    _binding("summaryBar", "mark", "summary-bar", "summary-bar", "summaryBar"),
    # Time decorations.
    # Public Scene role remains hyphenated; theme authoring resolves the canonical asOf binding.
    _binding("asOf", "line", "as-of", "as-of", "asOf"),
    _binding("asOfLabel", "label", "as-of-label", "text", "text"),
    _binding("calendarClosed", "decoration", "calendar-closed", "calendar-closed", "calendarClosed"),
    # Axis.
    _binding("axisBand", "label", "axis-band", "axis-band", "axis"),
    _binding("axisLabel", "label", "axis-label", "text", "axis"),
    _binding("axisGrid", "line", "axis-grid", "axis-major", "axis-major"),
    # Grouping.
    _binding("groupBand", "decoration", "group-decoration", "group-band", "group-band"),
    _binding("groupHeaderBand", "decoration", "group-header-band", "group-band", "group-band"),
    _binding("groupHeader", "decoration", "group-header", "group-header", "groupHeader"),
    _binding("groupDetail", "label", "group-detail", "text", "text"),
    # Table.
    _binding("titleText", "label", "title-text", "text", "heading"),
    _binding("tableColumnLabel", "label", "table-column-label", "text", "text"),
    _binding("tableCell", "label", "table-cell", "text", "text"),
    # Plot labels.
    _binding("memberLabel", "label", "member-label", "text", "text"),
    _binding("finishDelta", "label", "finish-delta", "variance-on-track", "variance-on-track"),
    _binding("milestoneDigestEntry", "label", "milestone-digest-entry", "text", "text"),
    # Relations.
    _binding("dependency", "line", "dependency", "dependency", "dependency"),
    _binding("dependency-critical", "line", "dependency", "dependency-critical", "dependency-critical"),
    # Legend, notes and annotations.
    _binding("legendEntry", "decoration", "legend-swatch", "legend-swatch", "legend"),
    _binding("legendLabel", "label", "legend-label", "text", "legend"),
    _binding("projectNote", "label", "project-note", "text", "annotation"),
    _binding("noteIndex", "label", "note-index", "note-index", "note-index"),
    _binding("annotation", "decoration", "annotation", "annotation", "annotation"),
    _binding("annotationBox", "decoration", "annotation-box", "annotation", "annotation"),
    _binding("annotationText", "label", "annotation-text", "annotation-text", "annotation"),
    _binding("annotationLeader", "line", "annotation-leader", "annotation", "annotation"),
    # Summary panels.
    _binding("summaryHeader", "label", "summary-header", "text", "summary"),
    _binding("summaryMetric", "label", "summary-metric", "text", "summary"),
    _binding("summaryFigureValue", "label", "summary-figure-value", "metric", "metric"),
    _binding("summaryFigureCaption", "label", "summary-figure-caption", "subtitle", "subtitle"),
)}


def semantic_binding(semantic_id: str) -> SemanticBinding:
    """Return the only allowed mapping from normalized meaning to Scene role."""
    try:
        return _REGISTRY[semantic_id]
    except KeyError as error:
        raise ValueError(f"E_PRESENTATION_SEMANTIC_UNKNOWN:{semantic_id}") from error


def semantic_ids() -> tuple[str, ...]:
    """Every declared semantic, in declaration order."""
    return tuple(_REGISTRY)


def purposes() -> frozenset[str]:
    """Every Scene purpose the surface may carry, for contract verification."""
    return frozenset(binding.purpose for binding in _REGISTRY.values())


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
