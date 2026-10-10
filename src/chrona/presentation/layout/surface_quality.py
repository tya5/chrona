"""Immutable placement values and geometry invariants for review surfaces."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from math import hypot, isfinite
from typing import TYPE_CHECKING, Any

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.pattern_placement import PatternedPlacement
from chrona.presentation.layout.obstacles import ObstacleGeometry
from chrona.presentation.layout.lane_subtracks import FixedLanePreflight
from chrona.presentation.model.info_diagnostics import PresentationInfo, SuppressedPlotLabels
from chrona.presentation.model.diagnostic_sources import DiagnosticProvenance, DiagnosticSubject
from chrona.presentation.model.semantic_registry import axis_band_semantic_ids, axis_label_semantic_ids

if TYPE_CHECKING:  # avoid the runtime cycle: canvas_overlays uses SlotPlacement.
    from chrona.presentation.layout.canvas_overlays import CanvasOverlays
    from chrona.presentation.layout.canvas_viewport import CanvasViewportWarning, DeclaredViewport
from chrona.presentation.model.theme_tokens import BOX_FOLLOWS_TEXT, FIT_ADJUSTS, TEXT_FOLLOWS_BOX


def _diagnostic_value(value: Any) -> str:
    """Bounded scalar context; never expand invalid payload objects."""
    return repr(value[:160]) if isinstance(value, str) else type(value).__name__


@dataclass(frozen=True)
class PathCommand:
    """One renderer-neutral, completed path instruction owned by Layout."""

    kind: str
    points: tuple[tuple[float, float], ...]

    def __post_init__(self) -> None:
        expected = {"move": 1, "line": 1, "quadratic": 2}.get(self.kind)
        if expected is None or len(self.points) != expected:
            raise ValueError(f"E_LAYOUT_PATH_COMMAND_INVALID: command kind={self.kind!r} has {len(self.points)} points; expected {expected if expected is not None else 'move, line or quadratic'}")
        if not all(all(isinstance(value, (int, float)) for value in point) for point in self.points):
            types = tuple(tuple(type(value).__name__ for value in point) for point in self.points)
            raise ValueError(f"E_LAYOUT_PATH_COMMAND_INVALID: {self.kind!r} point coordinate types={types!r}; expected numeric coordinates")


def is_closed_stroke_contour(commands: tuple[PathCommand, ...]) -> bool:
    """Validate each finite nondegenerate subpath without flattening curves or holes."""
    contours: list[list[tuple[float, float]]] = []
    for command in commands:
        if command.kind == "move":
            contours.append([command.points[0]])
        elif not contours:
            return False
        else:
            contours[-1].extend(command.points)
    if not contours:
        return False
    for points in contours:
        if (len(points) < 4 or not all(isfinite(value) for point in points for value in point)
                or hypot(points[-1][0] - points[0][0], points[-1][1] - points[0][1]) > 1e-6):
            return False
        x, y = points[0]
        nonzero = next(((px - x, py - y) for px, py in points[1:] if (px, py) != (x, y)), None)
        if nonzero is None or not any(abs(nonzero[0] * (py - y) - nonzero[1] * (px - x)) > 1e-12
                                     for px, py in points[1:]):
            return False
    return True


@dataclass(frozen=True)
class StrokeClip:
    """Completed contour and finite clip region, never inferred by an adapter."""

    outline: tuple[PathCommand, ...]
    outside: bool
    region: tuple[float, float, float, float]
    stroke_width: float

    def __post_init__(self) -> None:
        if (not isinstance(self.outside, bool)
                or (self.outline and not is_closed_stroke_contour(self.outline))
                or len(self.region) != 4 or not all(isfinite(value) for value in self.region)
                or self.region[2] <= 0 or self.region[3] <= 0
                or isinstance(self.stroke_width, bool) or not isfinite(self.stroke_width) or self.stroke_width <= 0):
            raise ValueError("E_LAYOUT_STROKE_CLIP_INVALID: expected a closed nondegenerate contour (or native rectangle), boolean outside, finite positive region and stroke width")


@dataclass(frozen=True)
class AlignedStrokePlacement:
    primitive_id: str
    clip: StrokeClip


@dataclass(frozen=True)
class MarkerGeometry:
    """Completed terminal geometry selected by Theme and owned by Layout."""

    outline: tuple[PathCommand, ...]
    head_length: float
    head_width: float
    attachment_offset: float
    paint_mode: str
    # not part of repr/equality: the SVG marker id hashes repr, and this is derived from the shape
    centred: bool = field(default=False, repr=False, compare=False)  # a round terminal centred on the endpoint, so its leg needs no straight run (#1044)
    angle_degrees: float | None = field(default=None, repr=False)
    physical_units: bool = field(default=False, repr=False)
    stroke_width: float | None = field(default=None, repr=False)
    # Layout routing extent, not an adapter input; legacy heads keep the nominal run.
    painted_run: float | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if (not self.outline or self.head_length <= 0 or self.head_width <= 0
                or not isfinite(self.attachment_offset)
                or (not self.physical_units and not 0 <= self.attachment_offset <= self.head_length)
                or (self.stroke_width is not None and (not self.physical_units
                    or isinstance(self.stroke_width, bool) or not isinstance(self.stroke_width, (int, float))
                    or not isfinite(self.stroke_width) or self.stroke_width < 0))
                or (self.physical_units and self.paint_mode == "stroke" and self.stroke_width is None)
                or (self.painted_run is not None and (not self.physical_units
                    or not isfinite(self.painted_run) or self.painted_run < 0))
                or (self.physical_units and self.paint_mode == "fill" and self.stroke_width is not None)
                or self.paint_mode not in {"fill", "stroke"}
                or (self.angle_degrees is not None and (not isinstance(self.angle_degrees, (int, float))
                    or isinstance(self.angle_degrees, bool) or not isfinite(self.angle_degrees)))):
            raise ValueError(f"E_PRESENTATION_PRIMITIVE_INVALID: MarkerGeometry paint_mode={self.paint_mode!r}, head_length={self.head_length}, head_width={self.head_width}, attachment_offset={self.attachment_offset}, outline_count={len(self.outline)}, physical_units={self.physical_units}, stroke_width={self.stroke_width}, painted_run={self.painted_run}, angle_degrees={self.angle_degrees}; expected a finite supported terminal with positive head dimensions")


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
        raise ValueError(f"E_PRESENTATION_ANNOTATION_PURPOSE: purpose {purpose!r}; expected callout, highlight, note or explanatory-arrow") from error


@dataclass(frozen=True)
class TextFit:
    """The completed viewer-fit facts of one text run (#1050), measured by Layout and only serialised by adapters.

    ``text-follows-box`` carries one positive measured inline size per line (``line_inline_sizes``) and the
    ``lengthAdjust`` choice. ``box-follows-text`` carries the id of its box shape and the count of trailing spaces
    that stand for the end inset (``end_pad_spaces``); it has no widths, the viewer decides the end edge.
    """

    mode: str
    adjust: str = "spacing"
    line_inline_sizes: tuple[float, ...] = ()
    box_id: str | None = None
    end_pad_spaces: int = 0

    def __post_init__(self) -> None:
        widths_ok = all(isinstance(item, (int, float)) and not isinstance(item, bool) and item > 0 and item == item
                        and item != float("inf") for item in self.line_inline_sizes)
        if self.adjust not in FIT_ADJUSTS or not widths_ok:
            raise ValueError("E_PRESENTATION_TEXT_LAYOUT_INVALID: viewer fit")
        if self.mode == TEXT_FOLLOWS_BOX:
            valid = bool(self.line_inline_sizes) and self.box_id is None and self.end_pad_spaces == 0
        elif self.mode == BOX_FOLLOWS_TEXT:
            valid = (not self.line_inline_sizes and self.adjust == "spacing" and bool(self.box_id)
                     and isinstance(self.end_pad_spaces, int) and not isinstance(self.end_pad_spaces, bool)
                     and self.end_pad_spaces >= 0)
        else:
            valid = False
        if not valid:
            raise ValueError("E_PRESENTATION_TEXT_LAYOUT_INVALID: viewer fit")


@dataclass(frozen=True)
class TextRunPlacement:
    """One measured run of a line set at its own size: a small-caps line is several (#1285)."""

    text: str
    font_size: float
    inline_size: float


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
    rotation_degrees: int | float = 0
    horizontal_scale: float = 1.0
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
    lane_row_id: str | None = None
    lane_member_id: str | None = None
    lane_source_kind: str | None = None
    # A viewer-fit mode's completed facts for this run (#1050); None is `raw`, today's output.
    fit: TextFit | None = None
    # One tuple of measured runs per line when the role is `small-caps` (#1285); empty otherwise.
    runs: tuple[tuple[TextRunPlacement, ...], ...] = ()


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
            raise ValueError(f"E_VIEW_VISUAL_REQUEST: source {self.source_ref!r}, side={self.side!r}, ref={self.ref!r}; expected leading/trailing and a non-empty reference")


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
    symbol_parts: tuple[Any, ...] = ()
    lane_row_id: str | None = None
    lane_member_id: str | None = None
    lane_source_kind: str | None = None
    subjects: tuple[DiagnosticSubject, ...] = ()


@dataclass(frozen=True)
class LayoutImageFill:
    """One completed nine-slice image fill for an annotation container (#465).

    ``tiles`` pairs each source rect (in the raster asset's own pixel space)
    with its destination rect (absolute Layout coordinates); Scene carries
    this unchanged, and adapters only serialize it.
    """

    asset_identity: str
    viewport: tuple[int, int]
    payload: bytes
    # Plain (x, y, width, height) float tuples, not the Decimal-based Rect:
    # `image_slice_geometry.image_slice_tiles` works in the same float space
    # as the rest of the annotation candidate search (LabelRect/floats).
    tiles: tuple[tuple[tuple[float, float, float, float], tuple[float, float, float, float]], ...]


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
    path_commands: tuple[PathCommand, ...] = ()
    image_fill: LayoutImageFill | None = None
    lane_row_id: str | None = None
    lane_member_id: str | None = None
    # Completed catalogue-glyph parts of an annotation kind stamp (#584); Scene emits one Symbol per part.
    symbol_parts: tuple[Any, ...] = ()
    # The viewer-fit mode of a text-bearing box (#1050); `raw` is today's output.
    viewer_fit: str = "raw"
    # Selected Theme role for completed named region frames; absent keeps the legacy Scene role.
    visual_role: str | None = None
    subjects: tuple[DiagnosticSubject, ...] = ()


@dataclass(frozen=True)
class SlotPlacement:
    """One resolved surface slot consumed verbatim by Scene projection."""

    slot_id: str
    source_ref: str
    bounds: Rect
    priority: str = "required"
    overflow: str = "visible-overflow"
    scale_id: str | None = None
    direction: str = "block"
    gap: Decimal | None = None
    item_min_inline_size: Decimal | None = None
    columns: int | None = None


@dataclass(frozen=True)
class RowPlacement:
    """One completed review-row extent independent of the Scene model."""

    row_id: str
    object_id: str
    group_id: str
    bounds: Rect
    depth: int = 0
    lane_mark_band_block: Decimal | None = None

    def __post_init__(self) -> None:
        anchor = self.lane_mark_band_block
        if anchor is not None and (not anchor.is_finite()
                                   or anchor < self.bounds.block
                                   or anchor > self.bounds.block + self.bounds.block_size):
            raise ValueError(f"E_LAYOUT_LANE_ROW_ANCHOR_INVALID: row {_diagnostic_value(self.row_id)} anchor={anchor}; block range={self.bounds.block}..{self.bounds.block + self.bounds.block_size}")


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
class RelationFanIn:
    """Layout-authorized same-port arrivals with one stable terminal paint owner."""

    target_port_id: str
    terminal_owner_id: str

    def __post_init__(self) -> None:
        for name, value in (("target_port_id", self.target_port_id),
                            ("terminal_owner_id", self.terminal_owner_id)):
            if not isinstance(value, str) or not value:
                raise ValueError(f"E_PRESENTATION_PRIMITIVE_INVALID: fan_in.{name} must be a non-empty string")


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
    from_instance_id: str | None = None
    to_instance_id: str | None = None
    fan_in: RelationFanIn | None = None


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
    box_position_limit: int = 0
    box_positions_examined: int = 0
    route_state_limit: int = 0
    route_states_examined: int = 0
    route_search_exhausted: bool = False

    def __post_init__(self) -> None:
        if (self.search_count < 0 or self.selected_topology not in {
                None, "strict", "bridge", "direct-tail", "routed-tail"}
                or (self.crossing_ids and self.selected_topology != "bridge")
                or self.box_position_limit < 0
                or not 0 <= self.box_positions_examined <= self.box_position_limit
                or self.route_state_limit < 0
                or not 0 <= self.route_states_examined <= self.route_state_limit):
            raise ValueError(f"E_LAYOUT_PLACEMENT_DECISION_INVALID: decision {_diagnostic_value(self.decision_id)} topology={self.selected_topology!r}, search_count={self.search_count}, box positions={self.box_positions_examined}/{self.box_position_limit}, route states={self.route_states_examined}/{self.route_state_limit}, crossings={len(self.crossing_ids)}")


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
    subjects: tuple[DiagnosticSubject, ...] = ()

    def __post_init__(self) -> None:
        if (not self.code.startswith("W" + "_LAYOUT_") or not self.placement_id or not self.source_ref
                or not self.failure_kind or not self.behaviour
                or min(self.required_inline, self.required_block,
                       self.available_inline, self.available_block) < 0):
            raise ValueError(f"E_LAYOUT_FIT_WARNING_INVALID: code={_diagnostic_value(self.code)}, placement={_diagnostic_value(self.placement_id)}, source={_diagnostic_value(self.source_ref)}, failure={self.failure_kind!r}, behaviour={self.behaviour!r}, required={self.required_inline}x{self.required_block}, available={self.available_inline}x{self.available_block}")


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
    # The secondary label of the cell (#493): None when the tier declares none.
    secondary_label: str | None = None
    secondary_disposition: str | None = None  # "placed" | "omitted"
    secondary_reason: str | None = None  # "does-not-fit" | "primary-does-not-fit" when omitted


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
    fixed_lane_preflight: FixedLanePreflight | None = None
    capacity_short_sources: tuple[CapacitySourceEvidence, ...] = ()
    declared_viewport: DeclaredViewport | None = None


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
    completed_paths: tuple[Any, ...] = ()
    lane_row_id: str | None = None
    lane_member_id: str | None = None
    host_placement_id: str | None = None
    subjects: tuple[DiagnosticSubject, ...] = ()


@dataclass(frozen=True)
class LaneEmissionFacet:
    """One completed Scene primitive's Layout-owned visible obstacle."""

    facet_id: str
    placement_type: str
    placement_id: str
    primitive_id: str
    obstacle: ObstacleGeometry
    obstacle_class: str
    part_index: int | None = None

    def __post_init__(self) -> None:
        from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment
        if (not self.facet_id or not self.placement_id or not self.primitive_id
                or self.placement_type not in {"mark", "shape", "icon", "text", "relation"}
                or self.obstacle_class not in {"mark", "required-label", "leader-route"}
                or not isinstance(self.obstacle, (ObstacleRect, ObstacleSegment))
                or (self.part_index is not None and self.part_index < 0)):
            raise ValueError(f"E_LAYOUT_LANE_EMISSION_INVALID: facet {_diagnostic_value(self.facet_id)}, placement={_diagnostic_value(self.placement_id)}, primitive={_diagnostic_value(self.primitive_id)}, type={self.placement_type!r}, obstacle_class={self.obstacle_class!r}, obstacle_type={type(self.obstacle).__name__}, part_index={self.part_index}")


@dataclass(frozen=True)
class LaneEmissionPlacement:
    """Typed owner and exact primitive/facet projection for one Layout placement."""

    placement_type: str
    placement_id: str
    row_id: str
    member_id: str
    purpose: str
    facets: tuple[LaneEmissionFacet, ...]

    def __post_init__(self) -> None:
        if (self.placement_type not in {"mark", "text", "icon", "shape", "relation"}
                or not all(isinstance(value, str) and value for value in
                           (self.placement_id, self.row_id, self.member_id, self.purpose))
                or not isinstance(self.facets, tuple) or not self.facets):
            raise ValueError(f"E_LAYOUT_LANE_EMISSION_INVALID: placement {_diagnostic_value(self.placement_id)}, type={self.placement_type!r}, row={_diagnostic_value(self.row_id)}, member={_diagnostic_value(self.member_id)}, purpose={self.purpose!r}, facets_type={type(self.facets).__name__}, facets_count={len(self.facets) if isinstance(self.facets, tuple) else 'unavailable'}")


@dataclass(frozen=True)
class CapacitySourceEvidence:
    """Exact required timeline source that the final profile still underserves."""

    source_id: str
    required_block: Decimal
    allocated_block: Decimal

    def __post_init__(self) -> None:
        if (self.source_id != "timeline" or not self.required_block.is_finite()
                or not self.allocated_block.is_finite()
                or self.allocated_block >= self.required_block):
            raise ValueError(f"E_LAYOUT_SUPPRESSION_EVIDENCE_INVALID: source={_diagnostic_value(self.source_id)}, required_block={self.required_block}, allocated_block={self.allocated_block}; expected timeline with finite required > allocated")


@dataclass(frozen=True)
class LaneLabelSuppression:
    """Typed attribution for one suppressed lane member name."""

    placement_id: str
    lane_id: str
    member_id: str
    row_bounds: Rect
    remaining_capacity: Decimal
    reason: str
    short_sources: tuple[CapacitySourceEvidence, ...] = ()

    def __post_init__(self) -> None:
        if (not self.placement_id or not self.lane_id or not self.member_id
                or not self.remaining_capacity.is_finite() or self.remaining_capacity < 0
                or self.reason not in {"capacity", "obstruction"}
                or (self.reason == "capacity" and not self.short_sources)
                or (self.reason == "capacity" and self.remaining_capacity != 0)
                or (self.reason == "obstruction" and self.short_sources)
                or len({item.source_id for item in self.short_sources}) != len(self.short_sources)):
            raise ValueError(f"E_LAYOUT_SUPPRESSION_EVIDENCE_INVALID: placement={_diagnostic_value(self.placement_id)}, lane={_diagnostic_value(self.lane_id)}, member={_diagnostic_value(self.member_id)}, reason={self.reason!r}, remaining_capacity={self.remaining_capacity}, short_sources_count={len(self.short_sources)}")


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
    lane_emissions: tuple[LaneEmissionPlacement, ...] = ()
    patterns: tuple[PatternedPlacement, ...] = ()
    lane_label_suppressions: tuple[LaneLabelSuppression, ...] = ()
    aligned_strokes: tuple[AlignedStrokePlacement, ...] = ()
    canvas_overlays: CanvasOverlays | None = None
    diagnostic_provenance: tuple[DiagnosticProvenance, ...] = ()
    canvas_warning: CanvasViewportWarning | None = None

    def assert_valid(self) -> None:
        """Reject invalid required geometry before a renderer receives it."""
        suppressed_members = {item.placement_id for item in self.text
                              if item.semantic_id == "memberLabel" and item.overflow == "suppressed"}
        suppressed_lane_members = {item.placement_id for item in self.text
                                   if item.semantic_id == "memberLabel" and item.overflow == "suppressed"
                                   and item.lane_row_id is not None}
        reported_suppressions = {item.removeprefix("W_LAYOUT_LABEL_SUPPRESSED:") for item in self.diagnostics
                                 if item.startswith("W_LAYOUT_LABEL_SUPPRESSED:")}
        counts = tuple(item for item in self.info_diagnostics if isinstance(item, SuppressedPlotLabels))
        suppression_facts = {item.placement_id: item for item in self.lane_label_suppressions}
        suppressed_text = {item.placement_id: item for item in self.text
                           if item.semantic_id == "memberLabel" and item.overflow == "suppressed"}
        if (not suppressed_members.issubset(reported_suppressions)
                or set(suppression_facts) != suppressed_lane_members
                or len(suppression_facts) != len(self.lane_label_suppressions)
                or len(counts) != (1 if suppressed_members else 0)
                or (counts and counts[0].count != len(suppressed_members))):
            raise ValueError(f"E_LAYOUT_SUPPRESSION_COUNT_INVALID: suppressed={len(suppressed_members)}, reported={len(reported_suppressions)}, lane_members={len(suppressed_lane_members)}, evidence={len(self.lane_label_suppressions)}, count_rows={len(counts)}, declared_count={counts[0].count if counts else None}")
        rows_by_id = {item.row_id: item for item in self.rows}
        for placement_id, fact in suppression_facts.items():
            text = suppressed_text[placement_id]
            row = rows_by_id.get(fact.lane_id)
            if (text.lane_row_id != fact.lane_id or text.lane_member_id != fact.member_id
                    or row is None or row.bounds != fact.row_bounds):
                raise ValueError(f"E_LAYOUT_SUPPRESSION_EVIDENCE_INVALID: placement={_diagnostic_value(placement_id)}, text lane/member={text.lane_row_id!r}/{text.lane_member_id!r}, evidence lane/member={fact.lane_id!r}/{fact.member_id!r}, row_found={row is not None}, bounds_match={row is not None and row.bounds == fact.row_bounds}")
        required = tuple(item for item in self.text if item.required and item.overflow != 'suppressed')
        if self.canvas_bounds is not None and (self.canvas_bounds.inline_size <= 0 or self.canvas_bounds.block_size <= 0):
            raise ValueError(f"E_LAYOUT_CANVAS_BOUNDS_INVALID: inline_size={self.canvas_bounds.inline_size}, block_size={self.canvas_bounds.block_size}; expected positive canvas dimensions")
        if self.canvas_overlays is not None:
            for role, overlay in (("canvas-overlay-gradient", self.canvas_overlays.radial),
                                  ("canvas-overlay", self.canvas_overlays.pattern)):
                if overlay is None:
                    continue
                slot = overlay.slot
                if (self.canvas_bounds is None or overlay.placement_id != role
                        or slot.slot_id != role or slot.source_ref != role
                        or slot.bounds != self.canvas_bounds):
                    raise ValueError(f"E_LAYOUT_CANVAS_OVERLAY_INVALID:{role}")
                if role == "canvas-overlay" and (
                        overlay.pattern.region != self.canvas_bounds
                        or overlay.pattern.clip != self.canvas_bounds):
                    raise ValueError(f"E_LAYOUT_CANVAS_OVERLAY_INVALID:{role}")
        for index, item in enumerate(required):
            for other in required[index + 1:]:
                if (item.overflow != "visible-overflow" and other.overflow != "visible-overflow"
                        and _collision_domains_intersect(item.collision_domain, other.collision_domain)
                        and not (item.orientation == other.orientation == "tilt" and item.source_ref == other.source_ref)
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
        pattern_ids = [item.placement_id for item in self.patterns]
        if len(pattern_ids) != len(set(pattern_ids)):
            raise ValueError(f"E_LAYOUT_PATTERN_PLACEMENT_DUPLICATE: pattern placement IDs={tuple(item.placement_id[:160] for item in self.patterns[:8])!r}, total={len(self.patterns)}")
        marks_by_id = {item.placement_id: item for item in self.marks}
        shapes_by_id = {item.placement_id: item for item in self.shapes}
        for item in self.patterns:
            mark = marks_by_id.get(item.placement_id)
            shape = shapes_by_id.get(item.placement_id)
            if not ((mark is not None and mark.mark_shape == "span")
                    or (shape is not None and shape.kind == "Rect")):
                raise ValueError(f"E_LAYOUT_PATTERN_REGION_INVALID:{item.placement_id}")
        hosts = {item.placement_id: item for item in self.marks}
        hosts.update({item.placement_id: item for item in self.shapes})
        emitted_mark_hosts = {
            facet.primitive_id: (hosts.get(emission.placement_id), facet.part_index or 0)
            for emission in self.lane_emissions if emission.placement_type == "mark"
            for facet in emission.facets
        }
        for item in self.text:
            if item.host_placement_id is None:
                continue
            host = hosts.get(item.host_placement_id)
            part_index = 0
            if host is None and item.host_placement_id in emitted_mark_hosts:
                host, part_index = emitted_mark_hosts[item.host_placement_id]
            if (host is None or host.slot_id != item.slot_id
                    or host.paint_order + part_index >= item.paint_order):
                raise ValueError(f"E_LAYOUT_TEXT_HOST_INVALID:{item.placement_id}")
            if item.semantic_id in axis_label_semantic_ids():
                allowed = isinstance(host, ShapePlacement) and host.semantic_id in axis_band_semantic_ids()
            elif item.semantic_id == "memberLabel" and item.collision_region == "plot-label":
                allowed = (isinstance(host, MarkPlacement)
                           and host.source_ref == item.source_ref
                           and (item.lane_member_id is None
                                or host.lane_member_id == item.lane_member_id))
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
                    if item.disposition == "thinned" and item.reason != "label-does-not-fit":
                        raise ValueError(f"E_LAYOUT_AXIS_OUTCOME_INVALID:{outcome.tier_index}")
                    if item.secondary_disposition is None:
                        secondary_valid = item.secondary_label is None and item.secondary_reason is None
                    elif item.secondary_disposition == "placed":
                        secondary_valid = (item.disposition == "placed" and item.label_fits
                                           and item.secondary_label is not None and item.secondary_reason is None)
                    else:
                        secondary_valid = (item.disposition == "placed" and item.secondary_disposition == "omitted"
                                           and item.secondary_label is not None
                                           and item.secondary_reason in {"does-not-fit", "primary-does-not-fit"})
                    if not secondary_valid:
                        raise ValueError(f"E_LAYOUT_AXIS_OUTCOME_INVALID:{outcome.tier_index}")
            elif outcome.label_form is not None or outcome.name_table_id is not None or any(item.label is not None or item.label_fits is not None
                                                       or item.disposition != "not-applicable" or item.reason is not None
                                                       or item.secondary_label is not None or item.secondary_disposition is not None
                                                       or item.secondary_reason is not None
                                                       for item in outcome.intervals):
                raise ValueError(f"E_LAYOUT_AXIS_OUTCOME_INVALID:{outcome.tier_index}")
            identifiers = tuple(item.candidate_id for item in outcome.intervals)
            if len(set(identifiers)) != len(identifiers):
                raise ValueError(f"E_LAYOUT_AXIS_OUTCOME_INVALID:{outcome.tier_index}")


def _collision_domains_intersect(left: CollisionDomain, right: CollisionDomain) -> bool:
    """Return whether two explicit physical text planes share collision space."""
    return left == right
