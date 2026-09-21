"""Immutable placement values and geometry invariants for review surfaces."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from chrona.presentation.layout.model import Rect


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


@dataclass(frozen=True)
class MarkPlacement:
    """Completed mark geometry and ports, independent of Scene primitives."""

    placement_id: str
    source_ref: str
    bounds: Rect
    start_port: tuple[float, float]
    end_port: tuple[float, float]
    required: bool = True


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
class RelationPlacement:
    """A completed relation path or an explicit, provenance-preserving suppression."""

    relation_id: str
    source_port_id: str
    target_port_id: str
    points: tuple[tuple[float, float], ...] = ()
    suppressed: bool = False
    diagnostic: str | None = None


@dataclass(frozen=True)
class SurfaceLayoutRequest:
    """Closed Layout input; semantic values are supplied by PresentationContract."""

    table_columns: tuple[tuple[str, str], ...] = ()
    table_cells: tuple[tuple[str, str, str], ...] = ()
    label_requests: tuple[Any, ...] = ()
    relation_requests: tuple[Any, ...] = ()


@dataclass(frozen=True)
class SurfacePlacement:
    """The complete geometry handoff from Layout to Scene."""

    text: tuple[TextPlacement, ...] = ()
    marks: tuple[MarkPlacement, ...] = ()
    shapes: tuple[ShapePlacement, ...] = ()
    relations: tuple[RelationPlacement, ...] = ()

    def assert_valid(self) -> None:
        """Reject invalid required geometry before a renderer receives it."""
        required = tuple(item for item in self.text if item.required and item.overflow != 'suppressed')
        for index, item in enumerate(required):
            for other in required[index + 1:]:
                if intersects(item.bounds, other.bounds):
                    raise ValueError(f"E_LAYOUT_TEXT_OVERLAP:{item.placement_id}:{other.placement_id}")
        for relation in self.relations:
            if relation.suppressed:
                if relation.points or not relation.diagnostic:
                    raise ValueError(f"E_LAYOUT_RELATION_SUPPRESSION_INVALID:{relation.relation_id}")
            elif len(relation.points) < 2:
                raise ValueError(f"E_LAYOUT_RELATION_PLACEMENT_INVALID:{relation.relation_id}")
        for mark in self.marks:
            if mark.bounds.inline_size <= 0 or mark.bounds.block_size <= 0:
                raise ValueError(f"E_LAYOUT_MARK_PLACEMENT_INVALID:{mark.placement_id}")
        for shape in self.shapes:
            if shape.kind == "Path":
                if len(shape.points) < 2:
                    raise ValueError(f"E_LAYOUT_SHAPE_PLACEMENT_INVALID:{shape.placement_id}")
            elif shape.bounds.inline_size < 0 or shape.bounds.block_size < 0:
                raise ValueError(f"E_LAYOUT_SHAPE_PLACEMENT_INVALID:{shape.placement_id}")
