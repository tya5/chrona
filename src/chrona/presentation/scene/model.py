"""Renderer-neutral presentation Scene model."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from chrona.presentation.layout.axis import AxisInterval
from chrona.presentation.layout.lanes import LaneAssignment, LaneTrack
from chrona.presentation.scene.marks import ComparisonMark

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
    semantic_facet: str
    visual_role: str
    bounds: tuple[float, float, float, float]
    projection_instance_id: str = ""
    surface_id: str = ""
    purpose: str = ""
    text: str | None = None
    baseline: tuple[float, float] | None = None
    text_layout: TextLayout | None = None
    shape: str | None = None
    color: str | None = None
    opacity: float | None = None
    optional: bool = False
    corner_radius: float | None = None
    lane_group_id: str | None = None
    stack_index: int | None = None
    points: tuple[tuple[float, float], ...] = ()
    from_port_id: str | None = None
    to_port_id: str | None = None
    z_order: int = 0

    def __post_init__(self) -> None:
        """Preserve a non-empty completed purpose for existing positional builders."""
        if not self.purpose:
            object.__setattr__(self, "purpose", self.semantic_facet)


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
    scale_manifest: SurfaceScaleManifest
    primitives: tuple[ScenePrimitive, ...] = ()


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
