"""Renderer-neutral presentation Scene model."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from chrona.presentation.layout.surface_quality import PathCommand
from chrona.presentation.icons import NormalizedVectorIcon


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
class MarkerGeometry:
    """Completed local arrowhead geometry; never a renderer-selected name."""

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
    strokes: tuple[PatternStroke, ...]

    def __post_init__(self) -> None:
        if (self.tile_inline_size <= 0 or self.tile_block_size <= 0
                or not 0 <= self.angle_degrees < 360 or not self.strokes):
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
    marker: MarkerGeometry | None = None
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
    icon_vector: NormalizedVectorIcon | None = None
    icon_paths: tuple[SceneIconPath, ...] = ()
    icon_raster: bytes | None = None
    icon_alternative: str | None = None
    icon_decorative: bool = True
    icon_stroke_scale: float | None = None
    visual_capability_source_ref: str = "/"
    table_row_id: str | None = None
    table_column_id: str | None = None
    paint_order: int = 0
    clip_source_id: str | None = None
    end_treatment: str = "closed"

    def __post_init__(self) -> None:
        if ((self.marker is not None and self.kind != "Path")
                or (self.pattern is not None and self.kind != "Rect")
                or (self.symbol is not None and self.kind != "Symbol")
                or (self.kind == "Symbol" and self.symbol is None)
                or (self.purpose == "table-cell" and self.table_row_id is None)
                or (self.purpose == "table-cell" and self.table_column_id is None)
                or (self.purpose != "table-cell" and self.table_row_id is not None)
                or (self.purpose not in {"table-cell", "table-column-label"}
                    and self.table_column_id is not None)
                or (self.kind == "Icon" and (self.icon_kind not in {"vector", "raster"}
                                               or self.icon_viewport is None
                                               or any(item <= 0 for item in self.icon_viewport)))
                or (self.kind != "Icon" and self.icon_viewport is not None)):
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
        if self.end_treatment not in {"closed", "open"}:
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")

@dataclass(frozen=True)
class SceneSlot:
    """One resolved surface bound consumed verbatim by renderer adapters."""

    slot_id: str
    source: str
    scale_id: str | None
    bounds: tuple[float, float, float, float]
    priority: str = "required"
    overflow: str = "diagnose"


@dataclass(frozen=True)
class SceneRow:
    object_id: str
    group_id: str
    bounds: tuple[float, float, float, float]
    row_id: str = ""


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

    def __post_init__(self) -> None:
        """Reject incomplete clip references before any adapter can serialize them."""
        by_id = {item.scene_id: (index, item) for index, item in enumerate(self.primitives)}
        if len(by_id) != len(self.primitives):
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
        for index, item in enumerate(self.primitives):
            if item.clip_source_id is None:
                continue
            source = by_id.get(item.clip_source_id)
            if (source is None or source[0] >= index or source[1].kind != "Rect"
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
