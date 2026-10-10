"""One Theme-selected nonrect chip completion and its visible candidate frame."""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from math import isfinite
from typing import Any

from chrona.presentation.layout.chip_geometry import ChipGeometry, ChipGeometryError, complete_chip_geometry
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.model.semantic_registry import label_chip_semantic, semantic_binding
from chrona.presentation.model.theme_tokens import BurstChipShape, CatalogChipShape, RectangleChipShape


@dataclass(frozen=True)
class MeasuredLabelChip:
    """Nominal local paint geometry and its once-expanded visible search frame.

    Candidate origins refer to ``footprint``'s top-left. Subtract its local
    origin to translate nominal paths and the text-safe rectangle unchanged.
    """

    geometry: ChipGeometry
    footprint: Rect

    @property
    def text_inline_inset(self) -> float:
        return float(self.geometry.text_bounds.inline - self.footprint.inline)

    @property
    def text_block_inset(self) -> float:
        return float(self.geometry.text_bounds.block - self.footprint.block)


def measure_label_chip(theme_tokens: Any, semantic_id: str, *, text_inline: float,
                       text_block: float, font_size: float,
                       padding: tuple[float, float]) -> MeasuredLabelChip | None:
    """Complete a selected nonrect chip; legacy rectangles keep their exact path.

    Only geometry metrics are read here. Scene alone resolves colors, opacity
    and paint policy. Catalog fills keep their original parts; no underlay or
    replacement outline is introduced.
    """
    semantic = label_chip_semantic(semantic_id)
    if semantic is None:
        return None
    role = semantic_binding(semantic).theme_role
    shape = theme_tokens.label_chip_shape(role)
    if theme_tokens.label_chip(role) is None or isinstance(shape, RectangleChipShape):
        return None
    pointer = f"/body/roles/{role}/chipShape"
    glyph = theme_tokens.catalog_glyph(shape.glyph) if isinstance(shape, CatalogChipShape) else None
    try:
        geometry = complete_chip_geometry(text_inline=text_inline, text_block=text_block,
                                         padding=padding, shape=shape, font_size=font_size, glyph=glyph)
        if isinstance(shape, BurstChipShape):
            # Unlike intrinsic catalog parts, a regular polygon uses both
            # channels of its existing chip role, just as a rectangle does.
            geometry = replace(geometry, symbol_parts=tuple(
                replace(part, paint_mode=None) for part in geometry.symbol_parts))
        footprint = _visible_frame(geometry, theme_tokens, role)
    except ChipGeometryError as error:
        raise LayoutError("E_LAYOUT_CHIP_TEXT_GROUND_INVALID", pointer,
                          detail=f"reason={error.reason}") from error
    return MeasuredLabelChip(geometry, footprint)


def _visible_frame(geometry: ChipGeometry, tokens: Any, role: str) -> Rect:
    """Conservative completed-path stroke envelope under Spec46 §7, once."""
    left, top = 0.0, 0.0
    right, bottom = float(geometry.outer_bounds.inline_size), float(geometry.outer_bounds.block_size)
    role_width = tokens.optional_number(role, "strokeWidth")
    for part in geometry.symbol_parts:
        if part.paint_mode == "fill":
            continue
        width = part.stroke_width if part.stroke_width is not None else role_width
        if width is None:
            continue
        width = float(width)
        if not isfinite(width) or width < 0:
            raise ChipGeometryError("nonfinite-geometry")
        expansion = 10 * width
        points = tuple(point for command in part.commands for point in command.points)
        if points:
            left = min(left, min(point[0] for point in points) - expansion)
            top = min(top, min(point[1] for point in points) - expansion)
            right = max(right, max(point[0] for point in points) + expansion)
            bottom = max(bottom, max(point[1] for point in points) + expansion)
    if not all(isfinite(value) for value in (left, top, right, bottom, right - left, bottom - top)):
        raise ChipGeometryError("nonfinite-geometry")
    return Rect(Decimal(str(left)), Decimal(str(top)), Decimal(str(right - left)), Decimal(str(bottom - top)))
