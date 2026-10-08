"""Completed canvas texture owned by Layout: one declared tile repeated over the canvas.

A texture is ground, not content. Layout completes one Rect over the whole
completed canvas, the repeat phase (the canvas top-left) and the pseudo-slot
that owns the Rect. Scene emits it as the first primitive; nothing here is random
and nothing depends on iteration order, so one Theme always gives the same bytes.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.pattern_placement import (
    PatternedPlacement,
    complete_pattern_placement,
)
from chrona.presentation.layout.seeded_pattern import complete_seeded_pattern
from chrona.presentation.layout.surface_quality import ShapePlacement, SlotPlacement

CANVAS_TEXTURE_ROLE = "canvas-texture"
CANVAS_TEXTURE_SEMANTIC_ID = "canvasTexture"
CANVAS_TEXTURE_PLACEMENT_ID = "canvas-texture"
CANVAS_SLOT_ID = "canvas"
CANVAS_TEXTURE_PAINT_ORDER = 0


@dataclass(frozen=True)
class CanvasTexture:
    """The completed texture Rect, its tile placement and the slot that owns it."""

    shape: ShapePlacement
    pattern: PatternedPlacement
    slot: SlotPlacement


def complete_canvas_texture(theme_tokens: Any, canvas: Rect) -> CanvasTexture | None:
    """Return the texture of a Theme whose ``canvas-texture`` role names a pattern, else nothing.

    The role is declared by its pattern: there is no ``none`` spelling, and a Theme that
    does not name a pattern for the role has no texture. The pattern must be a
    catalogue or seeded pattern; resource closure rejects anything else earlier (a role without a
    pattern is rejected there too), so a failure here is a fail-closed guard, never a
    partial texture.
    """
    has_role = getattr(theme_tokens, "has_role", None)
    if not callable(has_role) or not has_role(CANVAS_TEXTURE_ROLE):
        return None
    pattern = theme_tokens.optional_pattern(CANVAS_TEXTURE_ROLE)
    if pattern is None:
        return None
    if not isinstance(pattern, Mapping) or pattern.get("kind") not in {"catalog", "seeded"}:
        raise LayoutError("E_THEME_ROLE_PROPERTY_UNSUPPORTED", f"/body/roles/{CANVAS_TEXTURE_ROLE}/pattern")
    completed_pattern = (
        complete_seeded_pattern(pattern, canvas, pointer=f"/body/roles/{CANVAS_TEXTURE_ROLE}/pattern")
        if pattern["kind"] == "seeded" else complete_pattern_placement(pattern, canvas)
    )
    shape = ShapePlacement(
        CANVAS_TEXTURE_PLACEMENT_ID, "canvas", "Rect", canvas, slot_id=CANVAS_SLOT_ID,
        paint_order=CANVAS_TEXTURE_PAINT_ORDER, semantic_id=CANVAS_TEXTURE_SEMANTIC_ID)
    return CanvasTexture(
        shape,
        PatternedPlacement(shape.placement_id, completed_pattern),
        SlotPlacement(CANVAS_SLOT_ID, CANVAS_SLOT_ID, canvas),
    )
