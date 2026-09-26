"""Immutable placement values and geometry invariants for review surfaces."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from chrona.presentation.layout.model import Rect
from chrona.presentation.model.info_diagnostics import PresentationInfo, SuppressedPlotLabels


@dataclass(frozen=True)
class PathCommand:
    """One renderer-neutral, completed path instruction owned by Layout."""

    kind: str
    points: tuple[tuple[float, float], ...]

    def __post_init__(self) -> None:
        expected = {"move": 1, "line": 1, "quadratic": 2}.get(self.kind)
        if expected is None or len(self.points) != expected:
            raise ValueError("E_LAYOUT_PATH_COMMAND_INVALID")
        if not all(all(isinstance(value, (int, float)) for value in point) for point in self.points):
            raise ValueError("E_LAYOUT_PATH_COMMAND_INVALID")


@dataclass(frozen=True)
class MarkerGeometry:
    """Completed terminal geometry selected by Theme and owned by Layout."""

    outline: tuple[PathCommand, ...]
    head_length: float
    head_width: float
    attachment_offset: float
    paint_mode: str

    def __post_init__(self) -> None:
        if (not self.outline or self.head_length <= 0 or self.head_width <= 0
                or not 0 <= self.attachment_offset <= self.head_length
                or self.paint_mode not in {"fill", "stroke"}):
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")


GEOMETRY_TOLERANCE = Decimal("0.000001")


def _edges(rect: Rect) -> tuple[Any, Any, Any, Any]:
    """Return exact Layout coordinates for contact-versus-overlap checks."""
    return (rect.inline, rect.block,
            rect.inline + rect.inline_size,
            rect.block + rect.block_size)


def intersects(left: Rect, right: Rect) -> bool:
    """Return whether two positive-area rectangles overlap, not merely touch."""
    lx1, ly1, lx2, ly2 = _edges(left)
    rx1, ry1, rx2, ry2 = _edges(right)
    return (lx1 < rx2 - GEOMETRY_TOLERANCE and rx1 < lx2 - GEOMETRY_TOLERANCE
            and ly1 < ry2 - GEOMETRY_TOLERANCE and ry1 < ly2 - GEOMETRY_TOLERANCE)


@dataclass(frozen=True)
class CollisionDomain:
    """One physical text plane owned by Layout composition.

    ``collision_region`` remains diagnostic provenance. A domain instead names the
    slot and lane whose text shares physical space, so independent axis lanes do not
    exempt an overlay simply because it has a different provenance label.
    """

    slot: str
    lane: str


@dataclass(frozen=True)
class AnnotationPresentation:
    """Finite purpose-to-placement semantics selected by Layout."""

    purpose: str
    box_semantic_id: str
    text_semantic_id: str
    leader_semantic_id: str | None


def annotation_presentation(purpose: str) -> AnnotationPresentation:
    try:
        return {
            "callout": AnnotationPresentation("callout", "annotationCalloutBox", "annotationCalloutText", "annotationCalloutLeader"),
            "highlight": AnnotationPresentation("highlight", "annotationHighlightBox", "annotationHighlightText", None),
            "note": AnnotationPresentation("note", "annotationNoteBox", "annotationNoteText", "annotationNoteLeader"),
            "explanatory-arrow": AnnotationPresentation("explanatory-arrow", "annotationArrowBox", "annotationArrowText", "annotationArrowLeader"),
        }[purpose]
    except KeyError as error:
        raise ValueError("E_PRESENTATION_ANNOTATION_PURPOSE") from error


@dataclass(frozen=True)
class TextPlacement:
    """One measured text decision made by Layout before Scene emission."""

    placement_id: str
    source_ref: str
    content: str
    bounds: Rect
    typography_role: str
    overflow: str = "fit"
    required: bool = True
    baseline: tuple[float, float] | None = None
    lines: tuple[str, ...] = ()
    font_family: str = ""
    font_weight: int = 0
    font_size: float = 0.0
    line_height: float = 0.0
    letter_spacing: float = 0.0
    text_transform: str = "none"
    numeric_spacing: str = "proportional"
    orientation: str = "horizontal"
    rotation_degrees: int = 0
    font_asset_identity: str = ""
    collision_region: str = "surface"
    collision_domain: CollisionDomain = CollisionDomain("surface", "content")
    source_content: str | None = None
    available_inline_start: float | None = None
    available_inline_size: float | None = None
    fallback_ladder: tuple[str, ...] = ()
    selected_rung: str | None = None
    slot_id: str = ""
    semantic_id: str = ""
    annotation: AnnotationPresentation | None = None
    paint_order: int = 300
    host_placement_id: str | None = None


@dataclass(frozen=True)
class VisualRequest:
    """A closed View visual intent; only Layout resolves it to an icon placement."""

    target_kind: str
    selector: tuple[tuple[str, str], ...]
    ref: str | None = None
    encoding_field: str | None = None
    encoding_domain: tuple[tuple[str, str], ...] = ()
    side: str = "leading"
    decorative: bool = True
    source_ref: str = "/body/visuals"

    def __post_init__(self) -> None:
        if self.side not in {"leading", "trailing"} or not self.ref:
            raise ValueError("E_VIEW_VISUAL_REQUEST")


@dataclass(frozen=True)
class MarkPlacement:
    """Completed mark geometry and ports, independent of Scene primitives."""

    placement_id: str
    source_ref: str
    bounds: Rect
    start_port: tuple[float, float]
    end_port: tuple[float, float]
    required: bool = True
    mark_shape: str = "span"
    corner_radius: float = 0.0
    path_commands: tuple[PathCommand, ...] = ()
    slot_id: str = ""
    semantic_id: str = "planned"
    paint_order: int = 0
    end_treatment: str = "closed"


@dataclass(frozen=True)
class ShapePlacement:
    """Renderer-neutral completed non-text geometry for Scene projection."""

    placement_id: str
    source_ref: str
    kind: str
    bounds: Rect
    points: tuple[tuple[float, float], ...] = ()
    required: bool = True
    slot_id: str = ""
    clip_host_id: str | None = None
    paint_order: int = 0
    semantic_id: str = ""
    annotation: AnnotationPresentation | None = None
    corner_radius: float = 0.0


@dataclass(frozen=True)
class SlotPlacement:
    """One resolved surface slot consumed verbatim by Scene projection."""

    slot_id: str
    source_ref: str
    bounds: Rect
    priority: str = "required"
    overflow: str = "visible-overflow"
    scale_id: str | None = None


@dataclass(frozen=True)
class RowPlacement:
    """One completed review-row extent independent of the Scene model."""

    row_id: str
    object_id: str
    group_id: str
    bounds: Rect
    depth: int = 0


@dataclass(frozen=True)
class ColumnPlacement:
    """One completed table-column extent from Layout to Scene."""

    column_id: str
    label: str
    bounds: Rect


@dataclass(frozen=True)
class GroupPlacement:
    """Completed group content and optional header extents."""

    group_id: str
    content_bounds: Rect
    header_bounds: Rect | None = None


@dataclass(frozen=True)
class ScalePlacement:
    """Completed temporal-to-inline scale shared by all surface geometry."""

    surface_id: str
    scale_id: str
    domain_start: date
    domain_end: date
    range_start: float
    range_end: float
    origin: float
    unit_ratio: float


@dataclass(frozen=True)
class PrimitivePlacement:
    """Completed renderer-neutral primitive geometry before Scene projection."""

    placement_id: str
    source_ref: str
    kind: str
    bounds: Rect
    points: tuple[tuple[float, float], ...] = ()
    text: TextPlacement | None = None
    optional: bool = False


@dataclass(frozen=True)
class RelationPlacement:
    """A completed relation path or an explicit, provenance-preserving suppression."""

    relation_id: str
    source_port_id: str
    target_port_id: str
    points: tuple[tuple[float, float], ...] = ()
    suppressed: bool = False
    diagnostic: str | None = None
    semantic_id: str = "dependency"
    corner_radius: float = 0.0
    path_commands: tuple[PathCommand, ...] = ()
    marker_start: MarkerGeometry | None = None
    marker_end: MarkerGeometry | None = None
    label_content: str | None = None
    slot_id: str = ""
    annotation: AnnotationPresentation | None = None
    source_ref: str = ""
    paint_order: int = 250


@dataclass(frozen=True)
class PlacementDecision:
    """Inspectable late Layout decision; never an input allocation record."""

    decision_id: str
    source_ref: str
    requested_ladder: tuple[str, ...]
    selected_rung: str | None
    outcome: str
    search_count: int = 0
    selected_topology: str | None = None
    crossing_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (self.search_count < 0 or self.selected_topology not in {None, "strict", "bridge"}
                or (self.crossing_ids and self.selected_topology != "bridge")):
            raise ValueError("E_LAYOUT_PLACEMENT_DECISION_INVALID")


@dataclass(frozen=True)
class FitWarning:
    """A completed, user-visible fit fallback selected by Layout."""

    code: str
    placement_id: str
    source_ref: str
    failure_kind: str
    behaviour: str
    required_inline: float
    required_block: float
    available_inline: float
    available_block: float

    def __post_init__(self) -> None:
        if (not self.code.startswith("W" + "_LAYOUT_") or not self.placement_id or not self.source_ref
                or not self.failure_kind or not self.behaviour
                or min(self.required_inline, self.required_block,
                       self.available_inline, self.available_block) < 0):
            raise ValueError("E_LAYOUT_FIT_WARNING_INVALID")


@dataclass(frozen=True)
class AxisIntervalOutcome:
    """One calendar interval and its completed label measurement, if any."""

    candidate_id: str
    start: date
    end: date
    natural_start: date
    natural_end: date
    label: str | None = None
    label_fits: bool | None = None
    disposition: str = "not-applicable"
    reason: str | None = None


@dataclass(frozen=True)
class AxisTierOutcome:
    """Layout-owned result for one declared axis tier.

    This keeps auto selection, fiscal intervals and label measurements available
    to the failure-policy slice without reopening View syntax or recomputing
    text geometry in Scene.
    """

    tier_index: int
    source_ref: str
    role: str
    requested_units: tuple[str, ...]
    selected_unit: str
    every: int
    label_form: str | None
    intervals: tuple[AxisIntervalOutcome, ...]
    name_table_id: str | None = None


@dataclass(frozen=True)
class SurfaceLayoutRequest:
    """Closed Layout input; semantic values are supplied by PresentationContract."""

    projection: Any = None
    presentation_contract: Any = None
    surface_content: Any = None
    layout_manifest: Any = None
    measured_sources: Any = None
    theme_tokens: Any = None
    font_metrics: Any = None
    capabilities: dict[str, bool] = field(default_factory=dict)
    icon_assets: dict[str, Any] = field(default_factory=dict)
    visual_requests: tuple[VisualRequest, ...] = ()


@dataclass(frozen=True)
class IconPlacement:
    placement_id: str
    source_ref: str
    visual_capability_source_ref: str
    icon_id: str
    kind: str
    asset_identity: str
    viewport: tuple[int, int]
    payload: Any
    alternative: str
    decorative: bool
    bounds: Rect
    semantic_id: str = "iconMark"
    stroke_scale: float = 1.0
    slot_id: str = ""
    paint_order: int = 300


@dataclass(frozen=True)
class SurfacePlacement:
    """The complete geometry handoff from Layout to Scene."""

    text: tuple[TextPlacement, ...] = ()
    slots: tuple[SlotPlacement, ...] = ()
    rows: tuple[RowPlacement, ...] = ()
    columns: tuple[ColumnPlacement, ...] = ()
    groups: tuple[GroupPlacement, ...] = ()
    scale: ScalePlacement | None = None
    marks: tuple[MarkPlacement, ...] = ()
    shapes: tuple[ShapePlacement, ...] = ()
    primitives: tuple[PrimitivePlacement, ...] = ()
    relations: tuple[RelationPlacement, ...] = ()
    decisions: tuple[PlacementDecision, ...] = ()
    axis_tier_outcomes: tuple[AxisTierOutcome, ...] = ()
    diagnostics: tuple[str, ...] = ()
    icons: tuple[IconPlacement, ...] = ()
    canvas_bounds: Rect | None = None
    fit_warnings: tuple[FitWarning, ...] = ()
    info_diagnostics: tuple[PresentationInfo, ...] = ()

    def assert_valid(self) -> None:
        """Reject invalid required geometry before a renderer receives it."""
        suppressed_members = {item.placement_id for item in self.text
                              if item.semantic_id == "memberLabel" and item.overflow == "suppressed"}
        reported_suppressions = {item.removeprefix("W_LAYOUT_LABEL_SUPPRESSED:") for item in self.diagnostics
                                 if item.startswith("W_LAYOUT_LABEL_SUPPRESSED:")}
        counts = tuple(item for item in self.info_diagnostics if isinstance(item, SuppressedPlotLabels))
        if (not suppressed_members.issubset(reported_suppressions)
                or len(counts) != (1 if suppressed_members else 0)
                or (counts and counts[0].count != len(suppressed_members))):
            raise ValueError("E_LAYOUT_SUPPRESSION_COUNT_INVALID")
        required = tuple(item for item in self.text if item.required and item.overflow != 'suppressed')
        if self.canvas_bounds is not None and (self.canvas_bounds.inline_size <= 0 or self.canvas_bounds.block_size <= 0):
            raise ValueError("E_LAYOUT_CANVAS_BOUNDS_INVALID")
        for index, item in enumerate(required):
            for other in required[index + 1:]:
                if (item.overflow != "visible-overflow" and other.overflow != "visible-overflow"
                        and _collision_domains_intersect(item.collision_domain, other.collision_domain)
                        and intersects(item.bounds, other.bounds)):
                    raise ValueError(f"E_LAYOUT_TEXT_OVERLAP:{item.placement_id}:{other.placement_id}")
        for relation in self.relations:
            if relation.corner_radius < 0:
                raise ValueError(f"E_LAYOUT_RELATION_CORNER_RADIUS_INVALID:{relation.relation_id}")
            if relation.suppressed:
                if relation.points or not relation.diagnostic:
                    raise ValueError(f"E_LAYOUT_RELATION_SUPPRESSION_INVALID:{relation.relation_id}")
            elif len(relation.points) < 2:
                raise ValueError(f"E_LAYOUT_RELATION_PLACEMENT_INVALID:{relation.relation_id}")
            elif relation.path_commands and (relation.path_commands[0].kind != "move"
                                              or relation.path_commands[-1].points[-1] != relation.points[-1]):
                raise ValueError(f"E_LAYOUT_RELATION_PATH_INVALID:{relation.relation_id}")
        for mark in self.marks:
            if mark.bounds.inline_size <= 0 or mark.bounds.block_size <= 0:
                raise ValueError(f"E_LAYOUT_MARK_PLACEMENT_INVALID:{mark.placement_id}")
            if mark.corner_radius < 0 or mark.corner_radius > float(min(mark.bounds.inline_size, mark.bounds.block_size)) / 2:
                raise ValueError(f"E_LAYOUT_MARK_CORNER_RADIUS_INVALID:{mark.placement_id}")
            if mark.end_treatment not in {"closed", "open"}:
                raise ValueError(f"E_LAYOUT_MARK_END_TREATMENT_INVALID:{mark.placement_id}")
            if mark.mark_shape not in {"span", "point", "open-span"}:
                raise ValueError(f"E_LAYOUT_MARK_SHAPE_INVALID:{mark.placement_id}")
            if ((mark.end_treatment == "open") != (mark.mark_shape == "open-span")
                    or (mark.mark_shape == "open-span"
                        and (not mark.path_commands or mark.path_commands[0].kind != "move"
                             or mark.path_commands[-1].points[-1] != mark.path_commands[0].points[0]))):
                raise ValueError(f"E_LAYOUT_MARK_OPEN_OUTLINE_INVALID:{mark.placement_id}")
        for shape in self.shapes:
            if shape.kind == "Path":
                if len(shape.points) < 2:
                    raise ValueError(f"E_LAYOUT_SHAPE_PLACEMENT_INVALID:{shape.placement_id}")
            elif shape.bounds.inline_size < 0 or shape.bounds.block_size < 0:
                raise ValueError(f"E_LAYOUT_SHAPE_PLACEMENT_INVALID:{shape.placement_id}")
            if shape.clip_host_id is not None:
                host = next((mark for mark in self.marks if mark.placement_id == shape.clip_host_id), None)
                if host is None or host.slot_id != shape.slot_id:
                    raise ValueError(f"E_LAYOUT_CLIP_HOST_INVALID:{shape.placement_id}")
        hosts = {item.placement_id: item for item in self.marks}
        hosts.update({item.placement_id: item for item in self.shapes})
        for item in self.text:
            if item.host_placement_id is None:
                continue
            host = hosts.get(item.host_placement_id)
            if (host is None or host.slot_id != item.slot_id
                    or host.paint_order >= item.paint_order):
                raise ValueError(f"E_LAYOUT_TEXT_HOST_INVALID:{item.placement_id}")
            if item.semantic_id == "axisLabel":
                allowed = isinstance(host, ShapePlacement) and host.semantic_id == "axisBandDecoration"
            elif item.semantic_id == "noteIndex" or item.selected_rung == "inside":
                allowed = isinstance(host, MarkPlacement) and host.semantic_id in {
                    "planned", "actual", "snapshot", "scenario", "missing-actual",
                }
            else:
                allowed = False
            if not allowed:
                raise ValueError(f"E_LAYOUT_TEXT_HOST_INVALID:{item.placement_id}")
        for primitive in self.primitives:
            if primitive.kind == "Path" and len(primitive.points) < 2:
                raise ValueError(f"E_LAYOUT_PRIMITIVE_PLACEMENT_INVALID:{primitive.placement_id}")
            if primitive.kind == "Text" and primitive.text is None:
                raise ValueError(f"E_LAYOUT_PRIMITIVE_PLACEMENT_INVALID:{primitive.placement_id}")
        if self.slots:
            slot_ids = {slot.slot_id for slot in self.slots}
            for kind, items in (("text", self.text), ("mark", self.marks), ("shape", self.shapes),
                                ("relation", self.relations), ("icon", self.icons)):
                for item in items:
                    if not item.slot_id or item.slot_id not in slot_ids:
                        identifier = getattr(item, "placement_id", getattr(item, "relation_id", ""))
                        raise ValueError(f"E_LAYOUT_SLOT_OWNERSHIP_INVALID:{kind}:{identifier}")
        for decision in self.decisions:
            if decision.outcome not in {"placed", "suppressed", "diagnosed"}:
                raise ValueError(f"E_LAYOUT_DECISION_INVALID:{decision.decision_id}")
            if not decision.requested_ladder or len(set(decision.requested_ladder)) != len(decision.requested_ladder):
                raise ValueError(f"E_LAYOUT_DECISION_INVALID:{decision.decision_id}")
            if decision.outcome == "placed" and decision.selected_rung not in decision.requested_ladder:
                raise ValueError(f"E_LAYOUT_DECISION_INVALID:{decision.decision_id}")
            if decision.outcome == "suppressed" and decision.selected_rung != "suppress":
                raise ValueError(f"E_LAYOUT_DECISION_INVALID:{decision.decision_id}")
        tier_indices: set[int] = set()
        for outcome in self.axis_tier_outcomes:
            if (outcome.tier_index < 0 or outcome.tier_index in tier_indices
                    or outcome.role not in {"band", "grid-major", "grid-minor", "labels"}
                    or not outcome.requested_units or outcome.selected_unit not in outcome.requested_units
                    or outcome.every < 1):
                raise ValueError(f"E_LAYOUT_AXIS_OUTCOME_INVALID:{outcome.tier_index}")
            tier_indices.add(outcome.tier_index)
            if outcome.role == "labels":
                if outcome.label_form is None or outcome.name_table_id is None or any(item.label is None or item.label_fits is None
                                                     for item in outcome.intervals):
                    raise ValueError(f"E_LAYOUT_AXIS_OUTCOME_INVALID:{outcome.tier_index}")
                for item in outcome.intervals:
                    if item.disposition not in {"placed", "thinned"}:
                        raise ValueError(f"E_LAYOUT_AXIS_OUTCOME_INVALID:{outcome.tier_index}")
                    if item.disposition == "placed" and (
                            (item.label_fits and item.reason is not None)
                            or (not item.label_fits and item.reason != "visible-overflow")):
                        raise ValueError(f"E_LAYOUT_AXIS_OUTCOME_INVALID:{outcome.tier_index}")
                    if item.disposition == "thinned" and item.reason not in {"label-does-not-fit", "thinning-stride"}:
                        raise ValueError(f"E_LAYOUT_AXIS_OUTCOME_INVALID:{outcome.tier_index}")
            elif outcome.label_form is not None or outcome.name_table_id is not None or any(item.label is not None or item.label_fits is not None
                                                       or item.disposition != "not-applicable" or item.reason is not None
                                                       for item in outcome.intervals):
                raise ValueError(f"E_LAYOUT_AXIS_OUTCOME_INVALID:{outcome.tier_index}")
            identifiers = tuple(item.candidate_id for item in outcome.intervals)
            if len(set(identifiers)) != len(identifiers):
                raise ValueError(f"E_LAYOUT_AXIS_OUTCOME_INVALID:{outcome.tier_index}")


def _collision_domains_intersect(left: CollisionDomain, right: CollisionDomain) -> bool:
    """Return whether two explicit physical text planes share collision space."""
    return left == right
