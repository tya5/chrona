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

from dataclasses import dataclass, replace
from enum import Enum
from re import fullmatch
from types import MappingProxyType
from typing import Mapping

from chrona.resources.semantic_vocabulary import builtin_semantic_vocabulary


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


_REGISTRY: Mapping[str, SemanticBinding] = MappingProxyType({
    binding.semantic_id: binding
    for row in builtin_semantic_vocabulary().bindings
    for binding in (_binding(
        row.semantic_id, row.primitive_family, row.purpose, row.scene_role, row.theme_role,
        ContrastClass(row.contrast_class) if row.contrast_class is not None else None,
    ),)
})


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


def forecast_delta_semantic_ids() -> tuple[str, ...]:
    """The closed semantic family for forecast-derived finish-delta labels."""
    return ("forecastFinishDelta", "forecastVarianceAhead", "forecastVarianceBehind")


def label_chip_semantic(label_semantic_id: str) -> str | None:
    """Return the chip semantic a label may carry, keyed by the label's own semantic (#428)."""
    if label_semantic_id in forecast_delta_semantic_ids():
        return "finishDeltaChip"
    return {"asOfLabel": "asOfLabelChip", "memberLabel": "memberLabelChip",
            "finishDelta": "finishDeltaChip",
            "periodLabel": "periodLabelChip"}.get(label_semantic_id)


def semantic_binding(semantic_id: str) -> SemanticBinding:
    """Return the only allowed mapping from normalized meaning to Scene role."""
    try:
        return _REGISTRY[semantic_id]
    except KeyError as error:
        raise ValueError(f"E_PRESENTATION_SEMANTIC_UNKNOWN:{semantic_id}") from error


def mark_style_role(semantic_id: str) -> str:
    """Resolve opt-in mark paint reuse without changing established role keys."""
    return semantic_binding(semantic_id).theme_role if semantic_id == "forecast" else semantic_id


def is_annotation_artwork_role(role: object) -> bool:
    """The closed artwork paint family; its suffix is the common slug lexeme."""
    return isinstance(role, str) and (role == "annotation-artwork" or
                                     fullmatch(r"annotation-artwork-[a-z][a-z0-9-]*", role) is not None)


def is_frame_glyph_role(role: object) -> bool:
    """The independent catalogue border family, using the common slug lexeme."""
    return isinstance(role, str) and (role == "frame-glyph" or
                                     fullmatch(r"frame-glyph-[a-z][a-z0-9-]*", role) is not None)


def period_variant_role_base(role: object) -> str | None:
    """Return the one registered period-role family selected by a common slug suffix."""
    if not isinstance(role, str):
        return None
    match = fullmatch(r"period-(band|label):([a-z][a-z0-9-]*)", role)
    return f"period-{match.group(1)}" if match is not None else None


def contrast_binding(scene_role: str) -> SemanticBinding | None:
    """Return the unique classified binding for one completed Scene role (a ground-text binding is not by role)."""
    if is_annotation_artwork_role(scene_role):
        return _REGISTRY["annotationArtwork"]
    period_role = period_variant_role_base(scene_role)
    if period_role == "period-band":
        return _REGISTRY["periodBand"]
    if period_role == "period-label":
        return _REGISTRY["periodLabel"]
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


def contrast_binding_for_primitive(scene_role: str, kind: str, purpose: str | None) -> SemanticBinding | None:
    """Classify completed ink without mistaking a graphical legend key for text.

    Role identity and Theme paint remain unchanged. Only a closed graphical
    legend swatch borrows MARK contrast; purpose-based ground text remains Text-only.
    """
    binding = contrast_binding_for(scene_role, purpose if kind == "Text" else None)
    if (binding is not None and binding.contrast_class == ContrastClass.STATE_TEXT
            and kind in {"Rect", "Symbol", "Path"} and purpose == "legend-swatch"):
        return replace(binding, contrast_class=ContrastClass.MARK)
    return binding


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
