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
from re import fullmatch


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
    # Free ink that lies on a ground the Theme chose: a group header on its band (#884), the as-of label, a member
    # label outside a bar, an axis label, table text (#980). Resolved by purpose for the shared role `text`, never by
    # that role alone (it stays unclassified). The treatment is fixed `required`; a chip is the label's own ground.
    GROUND_TEXT = "ground-text"


class Slot(str, Enum):
    """Every surface region a Layout Profile may bind content to."""

    TITLE = "title"
    HEADING = "heading"
    HEADING_TITLE = "heading.title"
    HEADING_KICKER = "heading.kicker"
    HEADING_SUBTITLE = "heading.subtitle"
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


REQUIRED_SLOTS = (Slot.TABLE, Slot.TIMELINE, Slot.TIMELINE_AXIS)


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
    # A gate (point mark) painted by its own Theme role when the Theme declares one (#991); its purpose stays `planned`.
    _binding("gate", "mark", "planned", "gate", "gate", ContrastClass.MARK),
    _binding("missingActual", "mark", "missingActual", "missing-actual", "missing-actual", ContrastClass.MARK),
    _binding("summaryBar", "mark", "summary-bar", "summary-bar", "summaryBar", ContrastClass.MARK),
    _binding("progressFill", "mark", "progress-fill", "progress-fill", "progressFill", ContrastClass.MARK),
    _binding("iconMark", "icon", "icon-mark", "icon-mark", "icon-mark"),
    _binding("labelVisual", "icon", "label-visual", "text", "text"),
    # Time decorations.
    # Public Scene role remains hyphenated; theme authoring resolves the canonical asOf binding.
    _binding("asOf", "line", "as-of", "as-of", "asOf"),
    _binding("asOfLabel", "label", "as-of-label", "text", "text", ContrastClass.GROUND_TEXT),
    # The as-of light cone (#890): a translucent gradient polygon from the marker, under every mark. Deliberately
    # not contrast-classified (a faint light is the point); the gates composite it as the ground of what lies on it.
    _binding("asOfCone", "decoration", "as-of-cone", "as-of-cone", "as-of-cone"),
    # A Project deadline (#822): a tick at the promised date and, when the planned finish is later, a run to it.
    # One role paints both, so a Theme gives them one ink; the run is what tells a missed promise from a kept one.
    _binding("deadlineMark", "line", "deadline-mark", "deadline-mark", "deadline-mark", ContrastClass.MARK),
    # Label chips (#428): a background drawn from a label's own measured box,
    # one binding per label semantic, Theme role ``<label purpose>-chip``.
    _binding("asOfLabelChip", "decoration", "label-chip", "as-of-label-chip", "as-of-label-chip"),
    _binding("memberLabelChip", "decoration", "label-chip", "member-label-chip", "member-label-chip"),
    _binding("finishDeltaChip", "decoration", "label-chip", "finish-delta-chip", "finish-delta-chip"),
    _binding("calendarClosed", "decoration", "calendar-closed", "calendar-closed", "calendarClosed", ContrastClass.DECORATION),
    # A calendar-exception day drawn in its own colour when the Theme declares a `calendar-exception` background (#991).
    _binding("calendarException", "decoration", "calendar-exception", "calendar-exception", "calendarException",
             ContrastClass.DECORATION),
    # A named Project period (#582): a band across the plot, selected by the View and painted by the Theme.
    _binding("periodBand", "decoration", "period-band", "period-band", "period-band", ContrastClass.DECORATION),
    _binding("periodLabel", "label", "period-label", "period-label", "period-label", ContrastClass.STATE_TEXT),
    _binding("periodLabelChip", "decoration", "label-chip", "period-label-chip", "period-label-chip"),
    # Canvas texture (#587): ground under every primitive. Deliberately not
    # contrast-classified: a faint texture is the point, and the gates treat its
    # substrate and ink as the ground of what lies on it instead.
    _binding("canvasTexture", "decoration", "canvas-texture", "canvas-texture", "canvas-texture"),
    # Fixed above-content overlays are distinct from the canvas ground and have
    # their contrast effect evaluated over covered content (Spec 46, #888).
    _binding("canvasOverlay", "decoration", "canvas-overlay", "canvas-overlay", "canvas-overlay"),
    _binding("canvasOverlayGradient", "decoration", "canvas-overlay-gradient", "canvas-overlay-gradient", "canvas-overlay-gradient"),
    # Region frame (#889): the panel Layout completes behind a framed Layout Profile node. Ground like the
    # texture and for the same reason not contrast-classified: what lies on it is gated against its fill.
    _binding("regionFrame", "decoration", "region-frame", "region-frame", "region-frame"),
    # A sparse catalogue border is ground only where its completed ink touches content.
    _binding("frameGlyph", "decoration", "frame-glyph", "frame-glyph", "frame-glyph"),
    # Axis.
    _binding("axisBand", "label", "axis-band", "axis-band", "axis", ContrastClass.GROUND_TEXT),
    _binding("axisBandDecoration", "decoration", "axis-band", "axis-band-decoration", "axis-band-decoration", ContrastClass.DECORATION),
    _binding("axisLabel", "label", "axis-label", "text", "axis", ContrastClass.GROUND_TEXT),
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
    # Second and third labels tier (#426; ground text since #980, and the
    # decoration witness above counts DECORATION roles only, so it does not
    # constrain how many are registered):
    # distinct scene roles (not the shared "text" role axisLabel uses), so a
    # Theme can bind a labels tier its own colour, not only its own font
    # (font already varies per tier through the typographyRole passed
    # explicitly to place_text, independent of scene role). A tier that
    # leaves typographyRole at its default keeps the shared "axisLabel" id
    # every committed View already uses, so two fully-styled tiers (neither
    # left at the default) need both of these ordinals at once.
    _binding("axisLabel2", "label", "axis-label", "axis-label2", "axis2", ContrastClass.GROUND_TEXT),
    _binding("axisLabel3", "label", "axis-label", "axis-label3", "axis3", ContrastClass.GROUND_TEXT),
    _binding("axisGrid", "line", "axis-grid", "axis-major", "axis-major"),
    _binding("axisGridMinor", "line", "axis-grid", "axis-minor", "axis-minor"),
    # Axis cells and the axis/plot boundary (#426 rows 6-7).
    _binding("axisRule", "line", "axis-rule", "axis-rule", "axis-rule"),
    _binding("axisCellSeparator", "line", "axis-cell-separator", "axis-cell-separator", "axis-cell-separator"),
    # Grouping.
    _binding("groupBand", "decoration", "group-decoration", "group-band", "group-band", ContrastClass.DECORATION),
    _binding("rowBand", "decoration", "row-decoration", "row-band", "row-band", ContrastClass.DECORATION),
    _binding("rowRule", "decoration", "row-rule", "row-rule", "row-rule", ContrastClass.DECORATION),
    _binding("groupHeaderBand", "decoration", "group-header-band", "group-header-band", "group-header-band", ContrastClass.DECORATION),
    _binding("groupHeaderStrip", "decoration", "group-header-strip", "group-header-strip", "group-header-strip", ContrastClass.DECORATION),
    # A patterned tab on each group header (#882), a Theme role Layout completes beside the header text.
    _binding("groupTab", "decoration", "group-tab", "group-tab", "group-tab", ContrastClass.DECORATION),
    _binding("groupHeader", "decoration", "group-header", "group-header", "groupHeader", ContrastClass.GROUND_TEXT),
    _binding("groupDetail", "label", "group-detail", "text", "text", ContrastClass.GROUND_TEXT),
    _binding("observationSource", "label", "observation-source", "text", "text", ContrastClass.GROUND_TEXT),
    _binding("observationColumnLabel", "label", "observation-column-label", "text", "text", ContrastClass.GROUND_TEXT),
    _binding("observationCell", "label", "observation-cell", "text", "text", ContrastClass.GROUND_TEXT),
    # Emphasis is classified by the existing state-text role, like finishDelta.
    _binding("observationAttentionCell", "label", "observation-cell", "variance-ahead", "variance-ahead"),
    _binding("observationCriticalCell", "label", "observation-cell", "variance-behind", "variance-behind"),
    # Table.
    _binding("titleText", "label", "title-text", "heading", "heading", ContrastClass.GROUND_TEXT),
    _binding("kickerText", "label", "kicker-text", "kicker", "kicker", ContrastClass.GROUND_TEXT),
    # The subtitle line a View's `heading.subtitle` declares (#991), in the Theme's `subtitle` typography role.
    _binding("subtitleText", "label", "subtitle-text", "subtitle", "subtitle", ContrastClass.GROUND_TEXT),
    # The caption a Layout Profile slot declares (#1064), in the Theme's `slot-heading` text role (`text` when absent).
    _binding("slotHeading", "label", "slot-heading", "slot-heading", "slot-heading", ContrastClass.GROUND_TEXT),
    _binding("tableColumnLabel", "label", "table-column-label", "text", "text", ContrastClass.GROUND_TEXT),
    _binding("tableCell", "label", "table-cell", "text", "text", ContrastClass.GROUND_TEXT),
    _binding("tableVarianceAhead", "label", "table-cell", "variance-ahead", "variance-ahead", ContrastClass.STATE_TEXT),
    _binding("tableVarianceOnTrack", "label", "table-cell", "variance-on-track", "variance-on-track", ContrastClass.STATE_TEXT),
    _binding("tableVarianceBehind", "label", "table-cell", "variance-behind", "variance-behind", ContrastClass.STATE_TEXT),
    _binding("missingActualCell", "label", "table-cell", "missing-actual-cell", "missing-actual-cell", ContrastClass.STATE_TEXT),
    # Plot labels.
    _binding("memberLabel", "label", "member-label", "text", "text", ContrastClass.GROUND_TEXT),
    _binding("memberLabelInsidePlanned", "label", "member-label", "member-label-inside-planned", "member-label-inside-planned", ContrastClass.GROUND_TEXT),
    _binding("memberLabelInsideActual", "label", "member-label", "member-label-inside-actual", "member-label-inside-actual", ContrastClass.GROUND_TEXT),
    _binding("memberLabelInsideSnapshot", "label", "member-label", "member-label-inside-snapshot", "member-label-inside-snapshot", ContrastClass.GROUND_TEXT),
    _binding("memberLabelInsideScenario", "label", "member-label", "member-label-inside-scenario", "member-label-inside-scenario", ContrastClass.GROUND_TEXT),
    _binding("finishDelta", "label", "finish-delta", "variance-on-track", "variance-on-track"),
    _binding("varianceAhead", "label", "finish-delta", "variance-ahead", "variance-ahead"),
    _binding("varianceBehind", "label", "finish-delta", "variance-behind", "variance-behind"),
    _binding("milestoneDigestEntry", "label", "milestone-digest-entry", "text", "text", ContrastClass.GROUND_TEXT),
    # Relations.
    _binding("dependency", "line", "dependency", "dependency", "dependency"),
    _binding("dependency-critical", "line", "dependency", "dependency-critical", "dependency-critical"),
    # A relation label is label text: its ink is the text role's, like every other label (#880). Its visual role
    # used to be "annotation", whose fill every Theme binds to a ground colour (it paints annotation boxes), so the
    # label read as ghost text. Its typography is still the Theme's "annotation" role (the theme-role field).
    _binding("relationLabel", "label", "relation-label", "text", "annotation", ContrastClass.GROUND_TEXT),
    _binding("networkNode", "mark", "network-node", "network-node", "network-node", ContrastClass.MARK),
    # Preserve the public network-label purpose while separating its shared ink from title ink.
    _binding("networkLabel", "label", "title-text", "text", "text", ContrastClass.GROUND_TEXT),
    _binding("networkEdge", "line", "network-edge", "network-edge", "network-edge"),
    _binding("criticalEdge", "line", "critical-edge", "critical-edge", "critical-edge"),
    # Legend, notes and annotations.
    # The swatch's own theme role is "legend-swatch" (size/spacing), separate
    # from "legendLabel"'s "legend" (text) role; its drawn primitive is
    # dispatched per entry role by Layout, not fixed by this binding (#427).
    _binding("legendEntry", "decoration", "legend-swatch", "legend-swatch", "legend-swatch"),
    _binding("scaleLegendEntry", "decoration", "legend-swatch", "planned", "planned"),
    _binding("legendLabel", "label", "legend-label", "text", "legend", ContrastClass.GROUND_TEXT),
    _binding("projectNote", "label", "project-note", "text", "annotation", ContrastClass.GROUND_TEXT),
    _binding("annotationListText", "label", "annotation-list-text", "text", "annotation", ContrastClass.GROUND_TEXT),
    _binding("noteIndex", "label", "note-index", "note-index", "note-index", ContrastClass.GROUND_TEXT),
    _binding("annotationCalloutBox", "decoration", "annotation-box", "annotation-callout-box", "annotation-callout-box"),
    _binding("annotationCalloutText", "label", "annotation-text", "annotation-callout-text", "annotation-callout-text", ContrastClass.GROUND_TEXT),
    _binding("annotationCalloutLeader", "line", "annotation-leader", "annotation-callout-leader", "annotation-callout-leader"),
    _binding("annotationHighlightBox", "decoration", "annotation-box", "annotation-highlight-box", "annotation-highlight-box"),
    _binding("annotationHighlightText", "label", "annotation-text", "annotation-highlight-text", "annotation-highlight-text", ContrastClass.GROUND_TEXT),
    _binding("annotationNoteBox", "decoration", "annotation-box", "annotation-note-box", "annotation-note-box", ContrastClass.DECORATION),
    _binding("annotationNoteText", "label", "annotation-text", "annotation-note-text", "annotation-note-text", ContrastClass.STATE_TEXT),
    _binding("annotationNoteLeader", "line", "annotation-leader", "annotation-note-leader", "annotation-note-leader"),
    _binding("annotationArrowBox", "decoration", "annotation-box", "annotation-arrow-box", "annotation-arrow-box"),
    _binding("annotationArrowText", "label", "annotation-text", "annotation-arrow-text", "annotation-arrow-text", ContrastClass.GROUND_TEXT),
    _binding("annotationArrowLeader", "line", "annotation-leader", "annotation-arrow-leader", "annotation-arrow-leader"),
    # Annotation kind header (#584): a title bar, the header text and an accent edge, painted from one
    # role set shared by every kind (the kind colour replaces the fill). The text is judged against the
    # bar (or the note box) it lies on; the bar and the accent are decorations.
    _binding("annotationKindBar", "decoration", "annotation-kind-bar", "annotation-kind-bar", "annotation-kind-bar", ContrastClass.DECORATION),
    _binding("annotationKindAccent", "decoration", "annotation-kind-accent", "annotation-kind-accent", "annotation-kind-accent", ContrastClass.DECORATION),
    _binding("annotationKindStamp", "decoration", "annotation-kind-stamp", "annotation-kind-stamp", "annotation-kind-stamp", ContrastClass.DECORATION),
    # Vector artwork behind an annotation container (#848): catalogue glyph parts painted over the note box.
    _binding("annotationArtwork", "decoration", "annotation-artwork", "annotation-artwork", "annotation-artwork", ContrastClass.DECORATION),
    # The ink of a per-side box border (#1049), one role per logical side; a kind-painted side uses annotationKindAccent.
    _binding("annotationBorderStart", "decoration", "annotation-border-start", "annotation-border-start", "annotation-border-start", ContrastClass.DECORATION),
    _binding("annotationBorderEnd", "decoration", "annotation-border-end", "annotation-border-end", "annotation-border-end", ContrastClass.DECORATION),
    _binding("annotationBorderTop", "decoration", "annotation-border-top", "annotation-border-top", "annotation-border-top", ContrastClass.DECORATION),
    _binding("annotationBorderBottom", "decoration", "annotation-border-bottom", "annotation-border-bottom", "annotation-border-bottom", ContrastClass.DECORATION),
    _binding("annotationKindLabel", "label", "annotation-kind-label", "annotation-kind-label", "annotation-kind-label", ContrastClass.STATE_TEXT),
    _binding("annotationKindSecondary", "label", "annotation-kind-secondary", "annotation-kind-secondary", "annotation-kind-secondary", ContrastClass.STATE_TEXT),
    _binding("annotationHeading", "label", "annotation-heading", "annotation-heading", "annotation-heading", ContrastClass.STATE_TEXT),
    # Summary panels.
    _binding("summaryHeader", "label", "summary-header", "text", "summary", ContrastClass.GROUND_TEXT),
    _binding("summaryMetric", "label", "summary-metric", "text", "summary", ContrastClass.GROUND_TEXT),
    _binding("summaryFigureValue", "label", "summary-figure-value", "metric", "metric", ContrastClass.GROUND_TEXT),
    _binding("summaryFigureCaption", "label", "summary-figure-caption", "subtitle", "subtitle", ContrastClass.GROUND_TEXT),
    _binding("summaryCaption", "label", "summary-caption", "summary-caption", "summary-caption", ContrastClass.GROUND_TEXT),
    _binding("summaryUnit", "label", "summary-unit", "summary-unit", "summary-unit", ContrastClass.GROUND_TEXT),
)}


_SCENE_ROLES = frozenset(binding.scene_role for binding in _REGISTRY.values())


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
            "finishDelta": "finishDeltaChip", "periodLabel": "periodLabelChip"}.get(label_semantic_id)


def semantic_binding(semantic_id: str) -> SemanticBinding:
    """Return the only allowed mapping from normalized meaning to Scene role."""
    try:
        return _REGISTRY[semantic_id]
    except KeyError as error:
        raise ValueError(f"E_PRESENTATION_SEMANTIC_UNKNOWN:{semantic_id}") from error


def is_annotation_artwork_role(role: object) -> bool:
    """The closed artwork paint family; its suffix is the common slug lexeme."""
    return isinstance(role, str) and (role == "annotation-artwork" or
                                     fullmatch(r"annotation-artwork-[a-z][a-z0-9-]*", role) is not None)


def is_frame_glyph_role(role: object) -> bool:
    """The independent catalogue border family, using the common slug lexeme."""
    return isinstance(role, str) and (role == "frame-glyph" or
                                     fullmatch(r"frame-glyph-[a-z][a-z0-9-]*", role) is not None)


def contrast_binding(scene_role: str) -> SemanticBinding | None:
    """Return the unique classified binding for one completed Scene role (a ground-text binding is not by role)."""
    if is_annotation_artwork_role(scene_role):
        return _REGISTRY["annotationArtwork"]
    matches = tuple(binding for binding in _REGISTRY.values()
                    if binding.scene_role == scene_role and binding.contrast_class not in (None, ContrastClass.GROUND_TEXT))
    if len(matches) > 1:
        raise ValueError(f"E_PRESENTATION_SEMANTIC_CONTRAST_AMBIGUOUS:{scene_role}")
    return matches[0] if matches else None


def contrast_binding_for(scene_role: str, purpose: str | None) -> SemanticBinding | None:
    """Return the classified binding of a completed primitive: by its role, else (Text only) by its purpose.

    `purpose` is passed for a Text primitive only. Ink that lies on a ground the Theme chose is ground text
    (#884, #980): the shared role `text` is resolved by purpose (the role itself stays unclassified), and a
    label with a role of its own (a second axis tier, an inside label, an annotation prose) by role and purpose.
    """
    binding = contrast_binding(scene_role)
    if binding is not None or purpose is None:
        return binding
    # A role no binding registers as its scene role is a Theme text paint role (`tableColumnLabel`, `legend`, a
    # View-named column role, #1062): it paints the same free ink and is judged by its purpose like `text`.
    # Title inks are general Theme typography roles too: a View may name them
    # for a table cell. Registering their title semantics must not disable the
    # purpose-based ground gate for those other text uses (#1164).
    theme_text_role = scene_role not in _SCENE_ROLES or scene_role in {"heading", "subtitle", "kicker", "summary-caption", "summary-unit"}
    return next((item for item in contrast_bindings(ContrastClass.GROUND_TEXT)
                 if item.purpose == purpose and (theme_text_role or scene_role in ("text", item.scene_role))), None)


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


def is_label_chip_role(role: str) -> bool:
    """Classify chip roles from the same registry that pairs labels with chips."""
    return any(binding.purpose == "label-chip" and binding.theme_role == role
               for binding in _REGISTRY.values())


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
