"""Completed region frames owned by Layout: one Rect behind each framed Layout Profile node (#889).

A frame is ground, not content. The engine arranges the whole profile first and records
each declared frame with its node's completed bounds; this module then completes one
Rect per drawable frame (its bounds, corner radius, identity and pseudo-slot) and
records every omission. Nothing here feeds back into the arranged bounds, so a frame
never moves or clips content. Scene emits the Rects right after the canvas texture, and
nothing here is random or depends on dictionary order: the profile's pre-order is the
only order.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.pattern_placement import PatternedPlacement, complete_pattern_placement
from chrona.presentation.layout.surface_quality import ShapePlacement, SlotPlacement

REGION_FRAME_ROLE = "region-frame"
REGION_FRAME_SEMANTIC_ID = "regionFrame"
REGION_FRAME_PAINT_ORDER = 0
_TWO = Decimal(2)


@dataclass(frozen=True)
class RegionFrames:
    """The completed frames of one surface, in the profile's pre-order."""

    shapes: tuple[ShapePlacement, ...] = ()
    patterns: tuple[PatternedPlacement, ...] = ()
    slots: tuple[SlotPlacement, ...] = ()
    diagnostics: tuple[str, ...] = ()
    # What each frame paints in, stroke included: the canvas must contain it, so a stroke is never cut.
    extents: tuple[Rect, ...] = ()


def region_frame_placement_id(node_id: str) -> str:
    return f"{REGION_FRAME_ROLE}:{node_id}"


def region_frame_slot_id(node_id: str) -> str:
    return f"frame:{node_id}"


def complete_region_frames(theme_tokens: Any, decisions: tuple[Any, ...]) -> RegionFrames:
    """Complete every declared frame of a Layout manifest, or nothing when the Theme names no ``region-frame`` role.

    Layout says where a frame is; the Theme says whether and how it is painted, so a Theme
    without the role draws no frame and fails nothing. A frame is the node's bounds deflated on
    each side by its inset and half the role's stroke width, so the outer edge of the stroke
    stands the inset inside the node. A frame is omitted, and the omission recorded, when its
    node holds no slot or when the deflated Rect has no area; a corner radius larger than half
    the shorter side is reduced and the reduction recorded.
    """
    framed = tuple(item for item in decisions if item.frame is not None)
    has_role = getattr(theme_tokens, "has_role", None)
    if not framed or not callable(has_role) or not has_role(REGION_FRAME_ROLE):
        return RegionFrames()
    stroke = theme_tokens.optional_color(REGION_FRAME_ROLE, "stroke")
    width = theme_tokens.optional_number(REGION_FRAME_ROLE, "strokeWidth") if stroke is not None else None
    half_stroke = (width or Decimal(0)) / _TWO
    radius = theme_tokens.optional_number(REGION_FRAME_ROLE, "frameCornerRadius")
    if radius is not None and radius < 0:
        raise LayoutError("E_THEME_TOKEN_TYPE", f"/body/roles/{REGION_FRAME_ROLE}/frameCornerRadius")
    pattern = theme_tokens.optional_pattern(REGION_FRAME_ROLE)
    catalog_pattern = pattern if isinstance(pattern, Mapping) and pattern.get("kind") == "catalog" else None
    shapes: list[ShapePlacement] = []
    patterns: list[PatternedPlacement] = []
    slots: list[SlotPlacement] = []
    extents: list[Rect] = []
    diagnostics: list[str] = []
    for decision in framed:
        node_id = decision.node_id
        if not decision.frame.populated:
            diagnostics.append(f"I_LAYOUT_REGION_FRAME_OMITTED:{node_id}:no-content")
            continue
        deflate = decision.frame.inset + half_stroke
        bounds = decision.bounds
        inline_size = bounds.inline_size - _TWO * deflate
        block_size = bounds.block_size - _TWO * deflate
        if inline_size <= 0 or block_size <= 0:
            diagnostics.append(f"I_LAYOUT_REGION_FRAME_OMITTED:{node_id}:too-small")
            continue
        rect = Rect(bounds.inline + deflate, bounds.block + deflate, inline_size, block_size)
        applied = float(radius or 0)
        limit = float(min(inline_size, block_size) / _TWO)
        if applied > limit:
            applied = limit
            diagnostics.append(f"W_LAYOUT_REGION_FRAME_CORNER_REDUCED:{node_id}")
        slot_id = region_frame_slot_id(node_id)
        shape = ShapePlacement(
            region_frame_placement_id(node_id), f"layout-node:{node_id}", "Rect", rect, slot_id=slot_id,
            paint_order=REGION_FRAME_PAINT_ORDER, semantic_id=REGION_FRAME_SEMANTIC_ID, corner_radius=applied)
        shapes.append(shape)
        slots.append(SlotPlacement(slot_id, slot_id, rect))
        extents.append(Rect(rect.inline - half_stroke, rect.block - half_stroke,
                            rect.inline_size + _TWO * half_stroke, rect.block_size + _TWO * half_stroke))
        if catalog_pattern is not None:
            patterns.append(PatternedPlacement(
                shape.placement_id, complete_pattern_placement(catalog_pattern, rect, applied)))
    return RegionFrames(tuple(shapes), tuple(patterns), tuple(slots), tuple(diagnostics), tuple(extents))
