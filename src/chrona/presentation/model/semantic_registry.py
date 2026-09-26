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
    ICON = "Icon"


class ContrastClass(str, Enum):
    """Finite completed-paint policy classes with no renderer interpretation."""

    STATE_TEXT = "state-text"
    DECORATION = "decoration"
    MARK = "mark"


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
    contrast_class: ContrastClass | None = None


def _binding(semantic_id: str, primitive_kind: str, purpose: str,
             scene_role: str, theme_role: str, contrast_class: ContrastClass | None = None) -> SemanticBinding:
    return SemanticBinding(semantic_id, primitive_kind, purpose, scene_role, theme_role, contrast_class)


_REGISTRY: dict[str, SemanticBinding] = {binding.semantic_id: binding for binding in (
    # Comparison marks.
    _binding("planned", "mark", "planned", "planned", "planned", ContrastClass.MARK),
    _binding("actual", "mark", "actual", "actual", "actual", ContrastClass.MARK),
    _binding("snapshot", "mark", "snapshot", "snapshot", "snapshot", ContrastClass.MARK),
    _binding("missingActual", "mark", "missingActual", "missing-actual", "missing-actual", ContrastClass.MARK),
    _binding("summaryBar", "mark", "summary-bar", "summary-bar", "summaryBar", ContrastClass.MARK),
    _binding("progressFill", "mark", "progress-fill", "progress-fill", "progressFill", ContrastClass.MARK),
    _binding("iconMark", "icon", "icon-mark", "icon-mark", "icon-mark"),
    _binding("labelVisual", "icon", "label-visual", "text", "text"),
    # Time decorations.
    # Public Scene role remains hyphenated; theme authoring resolves the canonical asOf binding.
    _binding("asOf", "line", "as-of", "as-of", "asOf"),
    _binding("asOfLabel", "label", "as-of-label", "text", "text"),
    # Label chips (#428): a background drawn from a label's own measured box,
    # one binding per label semantic, Theme role ``<label purpose>-chip``.
    _binding("asOfLabelChip", "decoration", "label-chip", "as-of-label-chip", "as-of-label-chip"),
    _binding("memberLabelChip", "decoration", "label-chip", "member-label-chip", "member-label-chip"),
    _binding("finishDeltaChip", "decoration", "label-chip", "finish-delta-chip", "finish-delta-chip"),
    _binding("calendarClosed", "decoration", "calendar-closed", "calendar-closed", "calendarClosed", ContrastClass.DECORATION),
    # Axis.
    _binding("axisBand", "label", "axis-band", "axis-band", "axis"),
    _binding("axisBandDecoration", "decoration", "axis-band", "axis-band-decoration", "axis-band-decoration", ContrastClass.DECORATION),
    _binding("axisLabel", "label", "axis-label", "text", "axis"),
    # Second band tier (#426): a View may declare a second band tier, each
    # in its own Layout-assigned lane; the second ordinal resolves through
    # its own semantic id so a Theme can bind it a distinct fill. Two
    # ordinals meet the literal two-band-tier acceptance; a third is a
    # small, visible follow-up if a View ever needs it. (A third band id is
    # deliberately not pre-registered: the corpus-wide decoration contrast
    # witness in tools/presentation_contrast.py requires every registered
    # DECORATION-classified role to be painted somewhere in committed public
    # evidence, and no committed slide needs a third band.)
    _binding("axisBandDecoration2", "decoration", "axis-band", "axis-band-decoration2", "axis-band-decoration2", ContrastClass.DECORATION),
    # Second and third labels tier (#426, not contrast-classified, so the
    # decoration witness above does not constrain how many are registered):
    # distinct scene roles (not the shared "text" role axisLabel uses), so a
    # Theme can bind a labels tier its own colour, not only its own font
    # (font already varies per tier through the typographyRole passed
    # explicitly to place_text, independent of scene role). A tier that
    # leaves typographyRole at its default keeps the shared "axisLabel" id
    # every committed View already uses, so two fully-styled tiers (neither
    # left at the default) need both of these ordinals at once.
    _binding("axisLabel2", "label", "axis-label", "axis-label2", "axis2"),
    _binding("axisLabel3", "label", "axis-label", "axis-label3", "axis3"),
    _binding("axisGrid", "line", "axis-grid", "axis-major", "axis-major"),
    _binding("axisGridMinor", "line", "axis-grid", "axis-minor", "axis-minor"),
    # Grouping.
    _binding("groupBand", "decoration", "group-decoration", "group-band", "group-band", ContrastClass.DECORATION),
    _binding("rowBand", "decoration", "row-decoration", "row-band", "row-band", ContrastClass.DECORATION),
    _binding("groupHeaderBand", "decoration", "group-header-band", "group-header-band", "group-header-band", ContrastClass.DECORATION),
    _binding("groupHeader", "decoration", "group-header", "group-header", "groupHeader"),
    _binding("groupDetail", "label", "group-detail", "text", "text"),
    # Table.
    _binding("titleText", "label", "title-text", "text", "heading"),
    _binding("tableColumnLabel", "label", "table-column-label", "text", "text"),
    _binding("tableCell", "label", "table-cell", "text", "text"),
    _binding("tableVarianceAhead", "label", "table-cell", "variance-ahead", "variance-ahead", ContrastClass.STATE_TEXT),
    _binding("tableVarianceOnTrack", "label", "table-cell", "variance-on-track", "variance-on-track", ContrastClass.STATE_TEXT),
    _binding("tableVarianceBehind", "label", "table-cell", "variance-behind", "variance-behind", ContrastClass.STATE_TEXT),
    _binding("missingActualCell", "label", "table-cell", "missing-actual-cell", "missing-actual-cell", ContrastClass.STATE_TEXT),
    # Plot labels.
    _binding("memberLabel", "label", "member-label", "text", "text"),
    _binding("memberLabelInsidePlanned", "label", "member-label", "member-label-inside-planned", "member-label-inside-planned"),
    _binding("memberLabelInsideActual", "label", "member-label", "member-label-inside-actual", "member-label-inside-actual"),
    _binding("memberLabelInsideSnapshot", "label", "member-label", "member-label-inside-snapshot", "member-label-inside-snapshot"),
    _binding("memberLabelInsideScenario", "label", "member-label", "member-label-inside-scenario", "member-label-inside-scenario"),
    _binding("finishDelta", "label", "finish-delta", "variance-on-track", "variance-on-track"),
    _binding("varianceAhead", "label", "finish-delta", "variance-ahead", "variance-ahead"),
    _binding("varianceBehind", "label", "finish-delta", "variance-behind", "variance-behind"),
    _binding("milestoneDigestEntry", "label", "milestone-digest-entry", "text", "text"),
    # Relations.
    _binding("dependency", "line", "dependency", "dependency", "dependency"),
    _binding("dependency-critical", "line", "dependency", "dependency-critical", "dependency-critical"),
    _binding("relationLabel", "label", "relation-label", "annotation", "annotation"),
    _binding("networkNode", "mark", "network-node", "network-node", "network-node", ContrastClass.MARK),
    _binding("networkEdge", "line", "network-edge", "network-edge", "network-edge"),
    _binding("criticalEdge", "line", "critical-edge", "critical-edge", "critical-edge"),
    # Legend, notes and annotations.
    # The swatch's own theme role is "legend-swatch" (size/spacing), separate
    # from "legendLabel"'s "legend" (text) role; its drawn primitive is
    # dispatched per entry role by Layout, not fixed by this binding (#427).
    _binding("legendEntry", "decoration", "legend-swatch", "legend-swatch", "legend-swatch"),
    _binding("scaleLegendEntry", "decoration", "legend-swatch", "planned", "planned"),
    _binding("legendLabel", "label", "legend-label", "text", "legend"),
    _binding("projectNote", "label", "project-note", "text", "annotation"),
    _binding("noteIndex", "label", "note-index", "note-index", "note-index"),
    _binding("annotationCalloutBox", "decoration", "annotation-box", "annotation-callout-box", "annotation-callout-box"),
    _binding("annotationCalloutText", "label", "annotation-text", "annotation-callout-text", "annotation-callout-text"),
    _binding("annotationCalloutLeader", "line", "annotation-leader", "annotation-callout-leader", "annotation-callout-leader"),
    _binding("annotationHighlightBox", "decoration", "annotation-box", "annotation-highlight-box", "annotation-highlight-box"),
    _binding("annotationHighlightText", "label", "annotation-text", "annotation-highlight-text", "annotation-highlight-text"),
    _binding("annotationNoteBox", "decoration", "annotation-box", "annotation-note-box", "annotation-note-box"),
    _binding("annotationNoteText", "label", "annotation-text", "annotation-note-text", "annotation-note-text"),
    _binding("annotationNoteLeader", "line", "annotation-leader", "annotation-note-leader", "annotation-note-leader"),
    _binding("annotationArrowBox", "decoration", "annotation-box", "annotation-arrow-box", "annotation-arrow-box"),
    _binding("annotationArrowText", "label", "annotation-text", "annotation-arrow-text", "annotation-arrow-text"),
    _binding("annotationArrowLeader", "line", "annotation-leader", "annotation-arrow-leader", "annotation-arrow-leader"),
    # Summary panels.
    _binding("summaryHeader", "label", "summary-header", "text", "summary"),
    _binding("summaryMetric", "label", "summary-metric", "text", "summary"),
    _binding("summaryFigureValue", "label", "summary-figure-value", "metric", "metric"),
    _binding("summaryFigureCaption", "label", "summary-figure-caption", "subtitle", "subtitle"),
)}


def axis_band_semantic_ids() -> tuple[str, ...]:
    """Closed, ordinal-ordered axis band semantic ids (#426).

    A View's Nth declared band-role tier resolves through the Nth entry
    here; Layout, surface-quality validation and Scene construction all
    call this rather than repeating the literal strings.
    """
    return ("axisBandDecoration", "axisBandDecoration2")


def axis_label_semantic_ids() -> tuple[str, ...]:
    """Closed, ordinal-ordered axis label semantic ids (#426).

    A labels tier that leaves ``typographyRole`` at its default resolves to
    the first (shared) entry; a tier that names a role claims the next one,
    in declaration order among such tiers.
    """
    return ("axisLabel", "axisLabel2", "axisLabel3")


def label_chip_semantic(label_semantic_id: str) -> str | None:
    """Return the chip semantic a label may carry, keyed by the label's own semantic (#428)."""
    return {"asOfLabel": "asOfLabelChip", "memberLabel": "memberLabelChip",
            "finishDelta": "finishDeltaChip"}.get(label_semantic_id)


def semantic_binding(semantic_id: str) -> SemanticBinding:
    """Return the only allowed mapping from normalized meaning to Scene role."""
    try:
        return _REGISTRY[semantic_id]
    except KeyError as error:
        raise ValueError(f"E_PRESENTATION_SEMANTIC_UNKNOWN:{semantic_id}") from error


def contrast_binding(scene_role: str) -> SemanticBinding | None:
    """Return the unique classified binding for one completed Scene role."""
    matches = tuple(binding for binding in _REGISTRY.values()
                    if binding.scene_role == scene_role and binding.contrast_class is not None)
    if len(matches) > 1:
        raise ValueError(f"E_PRESENTATION_SEMANTIC_CONTRAST_AMBIGUOUS:{scene_role}")
    return matches[0] if matches else None


def contrast_bindings(contrast_class: ContrastClass) -> tuple[SemanticBinding, ...]:
    """Return classified bindings in the registry's stable declaration order."""
    return tuple(binding for binding in _REGISTRY.values() if binding.contrast_class == contrast_class)


def label_host_semantic(source_kind: str) -> str:
    """Return the closed visual host semantic for a projection source."""
    return {
        "primary": "planned",
        "combined": "planned",
        "actual": "actual",
        "snapshot": "snapshot",
        "scenario": "scenario",
    }[source_kind]


def inside_member_label_semantic(source_kind: str) -> str:
    """Return the host-specific inside-label semantic for a projection source."""
    return {
        "planned": "memberLabelInsidePlanned",
        "actual": "memberLabelInsideActual",
        "snapshot": "memberLabelInsideSnapshot",
        "scenario": "memberLabelInsideScenario",
    }[label_host_semantic(source_kind)]


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
        names.extend((
            "annotationCalloutBox", "annotationCalloutText", "annotationCalloutLeader",
            "annotationHighlightBox", "annotationHighlightText",
            "annotationNoteBox", "annotationNoteText", "annotationNoteLeader",
            "annotationArrowBox", "annotationArrowText", "annotationArrowLeader",
        ))
    return tuple(semantic_binding(name) for name in names)
