"""Generic catalogue-glyph borders over completed Layout Profile frame bounds.

Layout owns the complete run, including corners, residual spacing and closed
paths. One ShapePlacement is the whole border's capability-admission boundary;
Scene need not count, fit or reposition its individual glyphs.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from chrona.presentation.layout.mark_geometry import symbol_parts
from chrona.presentation.layout.model import LayoutDecision, Rect
from chrona.presentation.layout.surface_quality import ShapePlacement, SlotPlacement
from chrona.presentation.model.theme_tokens import ThemeTokenError

FRAME_GLYPH_ROLE = "frame-glyph"
FRAME_GLYPH_SEMANTIC_ID = "frameGlyph"
_TWO = Decimal(2)


@dataclass(frozen=True)
class FrameGlyphs:
    """Closed borders in profile pre-order, independent of Rect panel paint."""

    shapes: tuple[ShapePlacement, ...] = ()
    slots: tuple[SlotPlacement, ...] = ()
    extents: tuple[Rect, ...] = ()
    diagnostics: tuple[str, ...] = ()


def frame_glyph_boxes(bounds: Rect, size: Decimal, pitch: Decimal,
                      envelope: Decimal = Decimal(0)) -> tuple[Rect, ...]:
    """Four unique corners, then top/right/bottom/left edge interiors clockwise.

    Pitch is the minimum centre spacing. Both ends are pinned, so an edge
    with centre span L has floor(L/pitch) intervals of exactly L/intervals.
    Residual space is distributed, never cropped or filled with an extra glyph.
    The envelope reserves each completed glyph part's stroke outside its
    contain-fit square, keeping all paint inside the declared inset bounds.
    """
    width = bounds.inline_size - _TWO * envelope - size
    height = bounds.block_size - _TWO * envelope - size
    if width < pitch or height < pitch:
        return ()
    x, y = bounds.inline + envelope, bounds.block + envelope
    horizontal, vertical = int(width // pitch), int(height // pitch)
    origins = [(x, y), (x + width, y), (x + width, y + height), (x, y + height)]
    origins.extend((x + width * index / horizontal, y) for index in range(1, horizontal))
    origins.extend((x + width, y + height * index / vertical) for index in range(1, vertical))
    origins.extend((x + width - width * index / horizontal, y + height) for index in range(1, horizontal))
    origins.extend((x, y + height - height * index / vertical) for index in range(1, vertical))
    return tuple(Rect(inline, block, size, size) for inline, block in origins)


def complete_frame_glyphs(tokens: Any, decisions: tuple[LayoutDecision, ...]) -> FrameGlyphs:
    """Complete the independent glyph role selected by each existing frame.paint.

    Absent roles draw nothing. Populated and too-small dispositions apply to
    the whole border; content allocation and existing region-frame geometry
    are not inputs to, or modified by, this paint-only completion.
    """
    shapes, slots, extents, diagnostics = [], [], [], []
    for decision in decisions:
        frame = decision.frame
        if frame is None:
            continue
        role = f"{FRAME_GLYPH_ROLE}-{frame.paint}" if frame.paint is not None else FRAME_GLYPH_ROLE
        if not tokens.has_role(role):
            continue
        size, pitch = tokens.number(role, "glyphSize"), tokens.number(role, "glyphPitch")
        for property_name, value in (("glyphSize", size), ("glyphPitch", pitch)):
            if not value.is_finite() or value <= 0 or (property_name == "glyphPitch" and value < size):
                raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/{property_name}")
        if not frame.populated:
            diagnostics.append(f"I_LAYOUT_FRAME_GLYPH_OMITTED:{decision.node_id}:no-content")
            continue
        symbol = tokens.symbol(role)
        shape = symbol.get("shape")
        if not isinstance(shape, Mapping) or set(shape) != {"catalog"}:
            raise ThemeTokenError("E_THEME_TOKEN_TYPE", f"/body/roles/{role}/symbol")
        glyphs = {shape["catalog"]: tokens.catalog_glyph(shape["catalog"])}
        prototype = symbol_parts(symbol, (0.0, 0.0, float(size), float(size)), catalog_glyphs=glyphs)
        # Spec46 §7 uses ten stroke widths for a target-neutral path envelope;
        # do not assume SVG's default miter limit. A square cap at an arbitrary
        # tangent needs a diagonal allowance. Round/bevel needs half-width.
        envelope = max((Decimal(str(part.stroke_width)) / _TWO *
                        (20 if part.line_join == "miter" else 2 if part.line_cap == "square" else 1)
                        for part in prototype
                        if part.paint_mode == "stroke" and part.stroke_width is not None), default=Decimal(0))
        bounds = decision.bounds
        inset = frame.inset
        paint_bounds = Rect(bounds.inline + inset, bounds.block + inset,
                            bounds.inline_size - _TWO * inset, bounds.block_size - _TWO * inset)
        boxes = frame_glyph_boxes(paint_bounds, size, pitch, envelope)
        if not boxes:
            diagnostics.append(f"I_LAYOUT_FRAME_GLYPH_OMITTED:{decision.node_id}:too-small")
            continue
        parts = tuple(part for box in boxes for part in symbol_parts(
            symbol, (float(box.inline), float(box.block), float(box.inline_size), float(box.block_size)),
            catalog_glyphs=glyphs))
        identity = f"{FRAME_GLYPH_ROLE}:{decision.node_id}"
        slot_id = f"frame-glyph-slot:{decision.node_id}"
        shapes.append(ShapePlacement(identity, f"layout-node:{decision.node_id}", "Glyph", paint_bounds,
                                     slot_id=slot_id, semantic_id=FRAME_GLYPH_SEMANTIC_ID,
                                     symbol_parts=parts, visual_role=role))
        slots.append(SlotPlacement(slot_id, slot_id, paint_bounds))
        extents.append(paint_bounds)
    return FrameGlyphs(tuple(shapes), tuple(slots), tuple(extents), tuple(diagnostics))
