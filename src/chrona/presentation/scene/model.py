"""Renderer-neutral presentation Scene model."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from chrona.presentation.layout.axis import AxisInterval
from chrona.presentation.layout.lanes import LaneAssignment, LaneTrack
from chrona.presentation.layout.comparison_marks import ComparisonMark
from chrona.presentation.layout.surface_quality import PathCommand


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
    angle: float
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
class ScenePrimitive:
    """A measured renderer-neutral primitive; adapters serialize but never reinterpret it."""

    scene_id: str
    kind: str
    source_ref: str
    source_kind: str
    purpose: str
    visual_role: str
    bounds: tuple[float, float, float, float]
    text: str | None = None
    baseline: tuple[float, float] | None = None
    text_layout: TextLayout | None = None
    shape: str | None = None
    pattern: str | None = None
    paint: ScenePaint | None = None
    corner_radius: float | None = None
    path_commands: tuple[PathCommand, ...] = ()
    points: tuple[tuple[float, float], ...] = ()
    href: str | None = None
    link_title: str | None = None

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


@dataclass(frozen=True)
class PresentationScene:
    title: str
    window: tuple[date, date]
    axes: tuple[AxisInterval, ...]
    ticks: tuple[AxisInterval, ...]
    marks: tuple[ComparisonMark, ...]
    lanes: tuple[LaneAssignment, ...]
    lane_tracks: tuple[LaneTrack, ...]
    primitives: tuple[ScenePrimitive, ...]
    slots: tuple[SceneSlot, ...]
    rows: tuple[SceneRow, ...]
    groups: tuple[SceneGroup, ...]
    surfaces: tuple[SceneSurface, ...]
    manifest: SceneManifest
    diagnostics: tuple[str, ...]
