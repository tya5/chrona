"""Immutable placement values and geometry invariants for review surfaces."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from chrona.presentation.layout.model import Rect


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


def _edges(rect: Rect) -> tuple[float, float, float, float]:
    return (float(rect.inline), float(rect.block),
            float(rect.inline + rect.inline_size),
            float(rect.block + rect.block_size))


def intersects(left: Rect, right: Rect) -> bool:
    """Return whether two positive-area rectangles overlap, not merely touch."""
    lx1, ly1, lx2, ly2 = _edges(left)
    rx1, ry1, rx2, ry2 = _edges(right)
    return lx1 < rx2 and rx1 < lx2 and ly1 < ry2 and ry1 < ly2


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
    font_asset_identity: str = ""
    collision_region: str = "surface"
    collision_domain: CollisionDomain = CollisionDomain("surface", "content")
    source_content: str | None = None
    fallback_ladder: tuple[str, ...] = ()
    selected_rung: str | None = None


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
        if self.side not in {"leading", "trailing"} or bool(self.ref) == bool(self.encoding_field):
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


@dataclass(frozen=True)
class ShapePlacement:
    """Renderer-neutral completed non-text geometry for Scene projection."""

    placement_id: str
    source_ref: str
    kind: str
    bounds: Rect
    points: tuple[tuple[float, float], ...] = ()
    required: bool = True


@dataclass(frozen=True)
class SlotPlacement:
    """One resolved surface slot consumed verbatim by Scene projection."""

    slot_id: str
    source_ref: str
    bounds: Rect
    priority: str = "required"
    overflow: str = "diagnose"
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


@dataclass(frozen=True)
class PlacementDecision:
    """Inspectable late Layout decision; never an input allocation record."""

    decision_id: str
    source_ref: str
    requested_ladder: tuple[str, ...]
    selected_rung: str | None
    outcome: str


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
    locale: str = "en-US"
    capabilities: dict[str, bool] = field(default_factory=dict)
    icon_bindings: tuple[Any, ...] = ()
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
    payload: Any
    alternative: str
    decorative: bool
    bounds: Rect


@dataclass(frozen=True)
class SurfacePlacement:
    """The complete geometry handoff from Layout to Scene."""

    text: tuple[TextPlacement, ...] = ()
    slots: tuple[SlotPlacement, ...] = ()
    rows: tuple[RowPlacement, ...] = ()
    groups: tuple[GroupPlacement, ...] = ()
    scale: ScalePlacement | None = None
    marks: tuple[MarkPlacement, ...] = ()
    shapes: tuple[ShapePlacement, ...] = ()
    primitives: tuple[PrimitivePlacement, ...] = ()
    relations: tuple[RelationPlacement, ...] = ()
    decisions: tuple[PlacementDecision, ...] = ()
    diagnostics: tuple[str, ...] = ()
    icons: tuple[IconPlacement, ...] = ()

    def assert_valid(self) -> None:
        """Reject invalid required geometry before a renderer receives it."""
        required = tuple(item for item in self.text if item.required and item.overflow != 'suppressed')
        for index, item in enumerate(required):
            for other in required[index + 1:]:
                if _collision_domains_intersect(item.collision_domain, other.collision_domain) and intersects(item.bounds, other.bounds):
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
        for shape in self.shapes:
            if shape.kind == "Path":
                if len(shape.points) < 2:
                    raise ValueError(f"E_LAYOUT_SHAPE_PLACEMENT_INVALID:{shape.placement_id}")
            elif shape.bounds.inline_size < 0 or shape.bounds.block_size < 0:
                raise ValueError(f"E_LAYOUT_SHAPE_PLACEMENT_INVALID:{shape.placement_id}")
        for primitive in self.primitives:
            if primitive.kind == "Path" and len(primitive.points) < 2:
                raise ValueError(f"E_LAYOUT_PRIMITIVE_PLACEMENT_INVALID:{primitive.placement_id}")
            if primitive.kind == "Text" and primitive.text is None:
                raise ValueError(f"E_LAYOUT_PRIMITIVE_PLACEMENT_INVALID:{primitive.placement_id}")
        for decision in self.decisions:
            if decision.outcome not in {"placed", "suppressed", "diagnosed"}:
                raise ValueError(f"E_LAYOUT_DECISION_INVALID:{decision.decision_id}")
            if not decision.requested_ladder or len(set(decision.requested_ladder)) != len(decision.requested_ladder):
                raise ValueError(f"E_LAYOUT_DECISION_INVALID:{decision.decision_id}")
            if decision.outcome == "placed" and decision.selected_rung not in decision.requested_ladder:
                raise ValueError(f"E_LAYOUT_DECISION_INVALID:{decision.decision_id}")
            if decision.outcome == "suppressed" and decision.selected_rung != "suppress":
                raise ValueError(f"E_LAYOUT_DECISION_INVALID:{decision.decision_id}")


def _collision_domains_intersect(left: CollisionDomain, right: CollisionDomain) -> bool:
    """Return whether two explicit physical text planes share collision space."""
    return left == right
