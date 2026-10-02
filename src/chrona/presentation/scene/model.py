"""Renderer-neutral presentation Scene model."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math
from typing import Any

from chrona.presentation.layout.surface_quality import FitWarning, MarkerGeometry, PathCommand
from chrona.presentation.layout.pattern_placement import PatternTilePrimitive
from chrona.presentation.model.font_metrics import FontTabularWarning
from chrona.presentation.model.info_diagnostics import PresentationInfo
from chrona.presentation.model.semantic_registry import ContrastClass, contrast_binding, semantic_binding


LANE_MEMBER_BINDING_IDS = (
    "planned", "actual", "snapshot", "missingActual", "summaryBar", "progressFill",
    "memberLabel", "memberLabelInsidePlanned", "memberLabelInsideActual",
    "memberLabelInsideSnapshot", "memberLabelInsideScenario", "finishDelta",
    "varianceAhead", "varianceBehind", "iconMark", "labelVisual",
)
LANE_MEMBER_PURPOSES = frozenset(semantic_binding(identifier).purpose
                                 for identifier in LANE_MEMBER_BINDING_IDS)
PRIMARY_LANE_MARK_PURPOSES = frozenset(
    semantic_binding(identifier).purpose for identifier in ("planned", "snapshot")
)
_LANE_PURPOSE_KINDS = frozenset(
    (scene_kind, semantic_binding(identifier).purpose)
    for identifier in LANE_MEMBER_BINDING_IDS
    for scene_kind in ({"Rect", "Symbol", "Path"} if semantic_binding(identifier).primitive_kind == "mark"
                       else {"Text"} if semantic_binding(identifier).primitive_kind == "label"
                       else {"Icon"})
)


def _finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def requires_lane_member_provenance(kind: str, purpose: str) -> bool:
    """Whether a non-icon primitive's semantics alone imply lane ownership.

    Icons can decorate global labels as well as lane members. Member icons are
    instead closed by the exact typed Layout emission inventory.
    """
    return kind != "Icon" and purpose in LANE_MEMBER_PURPOSES and (kind, purpose) in _LANE_PURPOSE_KINDS


@dataclass(frozen=True)
class ScenePaint:
    """Completed renderer-neutral appearance selected before adapter invocation."""

    fill: str | None
    stroke: str | None
    stroke_width: float | None
    dash: tuple[float, ...]
    opacity: float
    gradient: "LinearGradient | None" = None
    shadow: "DropShadow | None" = None
    stroke_finish: "StrokeFinish | None" = None
    image: "ImageFill | None" = None
    glow: "Glow | None" = None


@dataclass(frozen=True)
class ImageTile:
    """One completed nine-slice tile: a source rect stretched to a destination rect (#465)."""

    source: tuple[float, float, float, float]
    destination: tuple[float, float, float, float]


@dataclass(frozen=True)
class ImageFill:
    """A container's completed nine-slice raster fill; adapters only serialize it.

    ``payload`` is the verified PNG bytes -- carried in memory only, exactly
    as an Icon's raster payload is (never part of the serialized Scene
    document; see ``icon_asset_identity`` for the identity that is).
    """

    asset_identity: str
    viewport: tuple[int, int]
    payload: bytes
    tiles: tuple[ImageTile, ...]

    def __post_init__(self) -> None:
        if not self.tiles or self.viewport[0] <= 0 or self.viewport[1] <= 0:
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")


@dataclass(frozen=True)
class LinearGradient:
    start: tuple[float, float]
    end: tuple[float, float]
    stops: tuple[tuple[float, str], ...]
    fidelity: str


@dataclass(frozen=True)
class DropShadow:
    color: str
    offset_x: float
    offset_y: float
    blur: float
    opacity: float
    fidelity: str


@dataclass(frozen=True)
class Glow:
    """A completed halo of colour around a primitive (#587).

    ``region`` is the primitive's visible extent grown by three blur on every side and
    clipped to the canvas, completed by Scene: the halo never leaves the slide and is no
    part of the primitive's bounds. Adapters serialize it and decide nothing.
    """

    color: str
    blur: float
    opacity: float
    fidelity: str
    region: tuple[float, float, float, float]


@dataclass(frozen=True)
class StrokeFinish:
    line_cap: str
    line_join: str
    fidelity: str


@dataclass(frozen=True)
class TextLayout:
    """One measured text result shared by Scene geometry and renderer serialization."""

    bounds: tuple[float, float, float, float]
    baseline: tuple[float, float]
    lines: tuple[str, ...]
    family: str
    weight: int
    font_size: float
    line_height: float
    asset_identity: str
    letter_spacing: float = 0.0
    text_transform: str = "none"
    numeric_spacing: str = "proportional"
    orientation: str = "horizontal"
    rotation_degrees: int = 0

    def __post_init__(self) -> None:
        if (self.numeric_spacing not in {"proportional", "tabular"}
                or (self.orientation, self.rotation_degrees) not in {
                    ("horizontal", 0), ("rotate-cw", 90), ("rotate-ccw", -90)}):
            raise ValueError("E_PRESENTATION_TEXT_LAYOUT_INVALID")


@dataclass(frozen=True)
class SceneIconPath:
    """One adapter-ready icon path in final surface coordinates and paint."""

    commands: tuple[tuple[str, tuple[tuple[float, float], ...]], ...]
    fill: str | None
    stroke: str | None
    stroke_width: float | None
    line_cap: str | None = None
    line_join: str | None = None
    opacity: float = 1.0


@dataclass(frozen=True)
class PatternStroke:
    start: tuple[float, float]
    end: tuple[float, float]
    width: float

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")


@dataclass(frozen=True)
class PatternGeometry:
    """Completed repeat-tile geometry; target adapters choose syntax, not values."""

    tile_inline_size: float
    tile_block_size: float
    angle_degrees: float
    strokes: tuple[PatternStroke, ...] = ()
    density_basis_points: int | None = None
    primitives: tuple[PatternTilePrimitive, ...] = ()
    origin: tuple[float, float] | None = None
    region_bounds: tuple[float, float, float, float] | None = None
    clip_bounds: tuple[float, float, float, float] | None = None
    corner_radius: float | None = None

    def __post_init__(self) -> None:
        catalog = bool(self.primitives)
        if (self.tile_inline_size <= 0 or self.tile_block_size <= 0
                or not 0 <= self.angle_degrees < 360
                or (catalog and (self.strokes or self.density_basis_points is None
                                 or not 1 <= self.density_basis_points <= 10_000
                                 or self.origin is None or self.region_bounds is None
                                 or self.clip_bounds is None or self.corner_radius is None))
                or (not catalog and (not self.strokes or self.density_basis_points is not None
                                     or self.origin is not None or self.region_bounds is not None
                                     or self.clip_bounds is not None or self.corner_radius is not None))):
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")


@dataclass(frozen=True)
class SymbolGeometry:
    """Completed absolute point-symbol outline from Theme treatment and Layout bounds."""

    outline: tuple[PathCommand, ...]

    def __post_init__(self) -> None:
        if not self.outline:
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")


@dataclass(frozen=True)
class ScenePrimitive:
    """A measured renderer-neutral primitive; adapters serialize but never reinterpret it."""

    scene_id: str
    kind: str
    source_ref: str
    source_kind: str
    purpose: str
    visual_role: str
    bounds: tuple[float, float, float, float]
    slot_id: str = ""
    text: str | None = None
    baseline: tuple[float, float] | None = None
    text_layout: TextLayout | None = None
    marker_start: MarkerGeometry | None = None
    marker_end: MarkerGeometry | None = None
    pattern: PatternGeometry | None = None
    symbol: SymbolGeometry | None = None
    paint: ScenePaint | None = None
    corner_radius: float | None = None
    path_commands: tuple[PathCommand, ...] = ()
    points: tuple[tuple[float, float], ...] = ()
    href: str | None = None
    link_title: str | None = None
    icon_kind: str | None = None
    icon_asset_identity: str | None = None
    icon_viewport: tuple[int, int] | None = None
    icon_paths: tuple[SceneIconPath, ...] = ()
    icon_path_geometry: tuple[Any, ...] = ()
    icon_raster: bytes | None = None
    icon_alternative: str | None = None
    icon_decorative: bool = True
    visual_capability_source_ref: str = "/"
    table_row_id: str | None = None
    table_column_id: str | None = None
    paint_order: int = 0
    host_placement_id: str | None = None
    clip_source_id: str | None = None
    end_treatment: str = "closed"
    contrast_treatment: str | None = None
    glyph_paint_mode: str | None = None
    glyph_paint_color: str | None = None
    glyph_stroke_width: float | None = None
    glyph_line_cap: str | None = None
    glyph_line_join: str | None = None
    image_fill_pending: "ImageFill | None" = None
    lane_row_id: str | None = None
    lane_member_id: str | None = None

    def __post_init__(self) -> None:
        if (((self.marker_start is not None or self.marker_end is not None) and self.kind != "Path")
                or (self.pattern is not None and self.kind != "Rect")
                or (self.image_fill_pending is not None and self.kind not in {"Rect", "Symbol"})
                or (self.symbol is not None and self.kind != "Symbol")
                or (self.kind == "Symbol" and self.symbol is None)
                or (self.glyph_paint_mode is not None and self.kind != "Symbol")
                or (self.glyph_paint_mode not in (None, "fill", "stroke"))
                or (self.glyph_paint_color is not None and self.glyph_paint_mode is None)
                or (self.glyph_stroke_width is not None and (self.glyph_paint_mode != "stroke"
                    or self.glyph_stroke_width <= 0 or not math.isfinite(self.glyph_stroke_width)))
                or ((self.glyph_line_cap is None) != (self.glyph_stroke_width is None))
                or ((self.glyph_line_join is None) != (self.glyph_stroke_width is None))
                or (self.glyph_line_cap not in (None, "butt", "round", "square"))
                or (self.glyph_line_join not in (None, "miter", "round", "bevel"))
                or (self.purpose == "table-cell" and self.table_row_id is None)
                or (self.purpose == "table-cell" and self.table_column_id is None)
                or (self.purpose != "table-cell" and self.table_row_id is not None)
                or (self.purpose not in {"table-cell", "table-column-label"}
                    and self.table_column_id is not None)
                or ((self.lane_row_id is None) != (self.lane_member_id is None))
                or (self.lane_row_id is not None and not self.lane_row_id)
                or (self.lane_member_id is not None and not self.lane_member_id)
                or (self.kind == "Icon" and (self.icon_kind not in {"vector", "raster"}
                                               or self.icon_viewport is None
                                               or any(item <= 0 for item in self.icon_viewport)))
                or (self.kind != "Icon" and self.icon_viewport is not None)):
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
        if self.end_treatment not in {"closed", "open"}:
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
        classified = contrast_binding(self.visual_role)
        if ((classified is not None and classified.contrast_class == ContrastClass.STATE_TEXT
             and self.contrast_treatment not in {"required", "deemphasized"})
                or (self.visual_role == "annotation-note-text" and self.contrast_treatment != "required")
                or ((classified is None or classified.contrast_class != ContrastClass.STATE_TEXT)
                    and self.contrast_treatment is not None)):
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
        if self.paint_order < 0:
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
        if self.end_treatment == "open" and (self.kind != "Symbol" or self.symbol is None or self.purpose != "actual"):
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")

@dataclass(frozen=True)
class SceneSlot:
    """One resolved surface bound consumed verbatim by renderer adapters."""

    slot_id: str
    source: str
    scale_id: str | None
    bounds: tuple[float, float, float, float]
    priority: str = "required"
    overflow: str = "visible-overflow"


@dataclass(frozen=True)
class SceneRow:
    object_id: str
    group_id: str
    bounds: tuple[float, float, float, float]
    row_id: str = ""
    lane_mark_band_block: float | None = None

    def __post_init__(self) -> None:
        if self.lane_mark_band_block is not None:
            inline, block, _inline_size, block_size = self.bounds
            if (not math.isfinite(self.lane_mark_band_block)
                    or not math.isfinite(block) or not math.isfinite(block_size)
                    or self.lane_mark_band_block < block
                    or self.lane_mark_band_block > block + block_size):
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")


@dataclass(frozen=True)
class SceneColumn:
    """One typed table column completed by Layout; never inferred from a text ID."""

    column_id: str
    label: str
    bounds: tuple[float, float, float, float]


@dataclass(frozen=True)
class SceneGroup:
    group_id: str
    header_bounds: tuple[float, float, float, float] | None
    content_bounds: tuple[float, float, float, float]


@dataclass(frozen=True)
class SceneLaneMember:
    """Closed lane membership and primitive-emission inventory for one member."""

    row_id: str
    member_id: str
    emitted_primitive_ids: tuple[str, ...]
    primary_mark_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if (not isinstance(self.row_id, str) or not self.row_id
                or not isinstance(self.member_id, str) or not self.member_id
                or not isinstance(self.emitted_primitive_ids, tuple)
                or not isinstance(self.primary_mark_ids, tuple)
                or not self.emitted_primitive_ids or not self.primary_mark_ids
                or any(not isinstance(item, str) or not item
                       for item in (*self.emitted_primitive_ids, *self.primary_mark_ids))
                or len(set(self.emitted_primitive_ids)) != len(self.emitted_primitive_ids)
                or len(set(self.primary_mark_ids)) != len(self.primary_mark_ids)
                or not set(self.primary_mark_ids) <= set(self.emitted_primitive_ids)):
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")


@dataclass(frozen=True)
class SceneLaneRectObstacle:
    """One Layout-completed rectangular visible lane obstacle."""

    left: float
    top: float
    right: float
    bottom: float

    def __post_init__(self) -> None:
        if (not all(_finite_number(value) for value in (self.left, self.top, self.right, self.bottom))
                or self.right <= self.left or self.bottom <= self.top):
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")


@dataclass(frozen=True)
class SceneLaneSegmentObstacle:
    """One Layout-completed stroked path segment visible footprint."""

    start: tuple[float, float]
    end: tuple[float, float]
    stroke_width: float

    def __post_init__(self) -> None:
        if (not isinstance(self.start, tuple) or len(self.start) != 2
                or not isinstance(self.end, tuple) or len(self.end) != 2
                or not all(_finite_number(value) for value in (*self.start, *self.end, self.stroke_width))
                or self.start == self.end or self.stroke_width < 0):
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")


@dataclass(frozen=True)
class SceneLaneObstacle:
    """Layout-owned visible obstacle evidence for one emitted Scene primitive."""

    facet_id: str
    primitive_id: str
    row_id: str
    member_id: str
    obstacle_class: str
    geometry: SceneLaneRectObstacle | SceneLaneSegmentObstacle

    def __post_init__(self) -> None:
        if (not all(isinstance(value, str) and value for value in
                    (self.facet_id, self.primitive_id, self.row_id, self.member_id))
                or self.obstacle_class not in {"mark", "required-label"}
                or not isinstance(self.geometry, (SceneLaneRectObstacle, SceneLaneSegmentObstacle))):
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")


@dataclass(frozen=True)
class SurfaceScaleManifest:
    """Closed temporal scale evidence carried by one completed surface."""

    surface_id: str
    scale_id: str
    domain_start: date
    domain_end: date
    range_start: float
    range_end: float
    origin: float
    unit_ratio: float


@dataclass(frozen=True)
class ContentFamilyCounts:
    relations: int
    annotations: int
    notes: int
    legend_entries: int
    summary_panels: int
    group_details: int = 0
    milestones: int = 0
    observation_rows: int = 0


@dataclass(frozen=True)
class SceneManifest:
    """Non-authoritative inspection evidence for one completed Scene."""

    version: str
    settings_version: str
    viewport: tuple[float, float]
    selected_object_ids: tuple[str, ...]
    font_asset_identities: tuple[str, ...]
    content_family_counts: ContentFamilyCounts
    surface_scales: tuple[SurfaceScaleManifest, ...]
    visual_role_counts: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True)
class DecorationDisposition:
    """One classified decoration deliberately omitted from a completed surface."""

    visual_role: str
    disposition: str

    def __post_init__(self) -> None:
        if self.disposition != "absent":
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")


@dataclass(frozen=True)
class SceneSurface:
    """Resolved geometry for one public adapter route."""

    surface_id: str
    slots: tuple[SceneSlot, ...]
    rows: tuple[SceneRow, ...]
    groups: tuple[SceneGroup, ...]
    scale_manifest: SurfaceScaleManifest | None
    primitives: tuple[ScenePrimitive, ...] = ()
    canvas_paint: ScenePaint | None = None
    columns: tuple[SceneColumn, ...] = ()
    diagnostics: tuple[str, ...] = ()
    canvas_bounds: tuple[float, float, float, float] | None = None
    fit_warnings: tuple[FitWarning, ...] = ()
    decoration_dispositions: tuple[DecorationDisposition, ...] = ()
    info_diagnostics: tuple[PresentationInfo, ...] = ()
    lane_mode: str | None = None
    lane_members: tuple[SceneLaneMember, ...] = ()
    lane_obstacles: tuple[SceneLaneObstacle, ...] = ()
    lane_clearance: float | None = None

    def __post_init__(self) -> None:
        """Reject incomplete clip references before any adapter can serialize them."""
        if self.canvas_bounds is not None and (len(self.canvas_bounds) != 4 or self.canvas_bounds[2] <= 0 or self.canvas_bounds[3] <= 0):
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
        by_id = {item.scene_id: (index, item) for index, item in enumerate(self.primitives)}
        if len(by_id) != len(self.primitives):
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
        if len({item.visual_role for item in self.decoration_dispositions}) != len(self.decoration_dispositions):
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
        lane_rows = {item.row_id: item for item in self.rows if item.row_id}
        if self.lane_mode not in (None, "lanes"):
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
        if self.lane_mode is None:
            if self.lane_members or self.lane_obstacles or self.lane_clearance is not None:
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
        else:
            if (not self.lane_members or not self.lane_obstacles
                    or not _finite_number(self.lane_clearance)
                    or self.lane_clearance < 0
                    or any(not isinstance(item, SceneLaneObstacle) for item in self.lane_obstacles) or any(
                    not member.row_id or member.row_id not in lane_rows
                    or lane_rows[member.row_id].lane_mark_band_block is None
                    for member in self.lane_members)):
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            if (len(lane_rows) != len(self.rows)
                    or any(row.lane_mark_band_block is None for row in self.rows)):
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            member_keys = [(member.row_id, member.member_id) for member in self.lane_members]
            emitted_ids = [primitive_id for member in self.lane_members
                           for primitive_id in member.emitted_primitive_ids]
            if len(set(member_keys)) != len(member_keys) or len(set(emitted_ids)) != len(emitted_ids):
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            if {row_id for row_id, _member_id in member_keys} != set(lane_rows):
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            expected = {primitive_id: (member.row_id, member.member_id)
                        for member in self.lane_members
                        for primitive_id in member.emitted_primitive_ids}
            tagged = {item.scene_id: (item.lane_row_id, item.lane_member_id)
                      for item in self.primitives if item.lane_row_id is not None}
            if expected != tagged or any(
                    primitive_id not in by_id for primitive_id in expected):
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            primary_ids = {primitive_id for member in self.lane_members
                           for primitive_id in member.primary_mark_ids}
            if any(by_id[primitive_id][1].purpose not in PRIMARY_LANE_MARK_PURPOSES
                   for primitive_id in primary_ids):
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            if any(requires_lane_member_provenance(item.kind, item.purpose)
                   and item.lane_row_id is None for item in self.primitives):
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            obstacle_facets = [item.facet_id for item in self.lane_obstacles]
            obstacle_owners: dict[str, tuple[str, str]] = {}
            for obstacle in self.lane_obstacles:
                if obstacle.primitive_id in obstacle_owners and obstacle_owners[obstacle.primitive_id] != (
                        obstacle.row_id, obstacle.member_id):
                    raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
                obstacle_owners[obstacle.primitive_id] = (obstacle.row_id, obstacle.member_id)
                if expected.get(obstacle.primitive_id) != (obstacle.row_id, obstacle.member_id):
                    raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            if (len(set(obstacle_facets)) != len(obstacle_facets)
                    or set(obstacle_owners) != set(expected)):
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
        for index, item in enumerate(self.primitives):
            if item.lane_row_id is not None:
                row = lane_rows.get(item.lane_row_id)
                if row is None or row.lane_mark_band_block is None:
                    raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            if item.host_placement_id is not None:
                host = by_id.get(item.host_placement_id)
                if (item.kind != "Text" or host is None or host[1].slot_id != item.slot_id
                        or host[1].paint_order >= item.paint_order):
                    raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
            if item.clip_source_id is None:
                continue
            source = by_id.get(item.clip_source_id)
            if (source is None or source[1].paint_order > item.paint_order
                    or (source[1].paint_order == item.paint_order and source[0] >= index)
                    or source[1].kind not in {"Rect", "Symbol"}
                    or (source[1].kind == "Symbol" and source[1].symbol is None)
                    or source[1].slot_id != item.slot_id):
                raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")


@dataclass(frozen=True)
class SceneProvenance:
    """Immutable render closure evidence for an inspection-only Scene."""

    mode: str
    chrona_version: str
    resources: tuple[tuple[str, str, str, str], ...]


@dataclass(frozen=True)
class InspectionScene:
    """The one completed runtime Scene exposed to adapters and inspection tooling."""

    provenance: SceneProvenance
    viewport: tuple[float, float]
    required_capabilities: tuple[str, ...]
    surfaces: tuple[SceneSurface, ...]
    manifest: SceneManifest
    diagnostics: tuple[str, ...]
    font_warnings: tuple[FontTabularWarning, ...] = ()
