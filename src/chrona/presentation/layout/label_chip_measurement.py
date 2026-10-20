"""One Theme-selected nonrect chip completion and its visible candidate frame."""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
from math import isfinite
from typing import Any

from chrona.presentation.layout.chip_geometry import ChipGeometry, ChipGeometryError, complete_chip_geometry
from chrona.presentation.layout.filled_contour import ContourUnionError, filled_contours_cover_rectangle
from chrona.presentation.layout.mark_geometry import SymbolPartPlacement
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
    outline_precision: int | None = None

    @property
    def text_inline_inset(self) -> float:
        return float(self.geometry.text_bounds.inline - self.footprint.inline)

    @property
    def text_block_inset(self) -> float:
        return float(self.geometry.text_bounds.block - self.footprint.block)


def measure_label_chip(theme_tokens: Any, semantic_id: str, *, text_inline: float,
                       text_block: float, font_size: float,
                       padding: tuple[float, float], scene_precision: int = 3) -> MeasuredLabelChip | None:
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
    if (isinstance(scene_precision, bool) or not isinstance(scene_precision, int)
            or scene_precision < 0):
        raise LayoutError("E_LAYOUT_CHIP_TEXT_GROUND_INVALID", pointer,
                          detail="reason=precision-geometry")
    try:
        geometry = complete_chip_geometry(text_inline=text_inline, text_block=text_block,
                                         padding=padding, shape=shape, font_size=font_size, glyph=glyph)
        if isinstance(shape, BurstChipShape):
            # Unlike intrinsic catalog parts, a regular polygon uses both
            # channels of its existing chip role, just as a rectangle does.
            geometry = replace(geometry, symbol_parts=tuple(
                replace(part, paint_mode=None) for part in geometry.symbol_parts))
        footprint = _visible_frame(geometry, theme_tokens, role)
        if isinstance(shape, BurstChipShape):
            half_quantum = _half_quantum(scene_precision)
            footprint = Rect(footprint.inline - half_quantum, footprint.block - half_quantum,
                footprint.inline_size + 2 * half_quantum,
                footprint.block_size + 2 * half_quantum)
    except ChipGeometryError as error:
        raise LayoutError("E_LAYOUT_CHIP_TEXT_GROUND_INVALID", pointer,
                          detail=f"reason={error.reason}") from error
    return MeasuredLabelChip(geometry, footprint,
                             scene_precision if isinstance(shape, BurstChipShape) else None)


def complete_label_chip_placement(measured: MeasuredLabelChip, *, origin_x: float,
                                  origin_y: float) -> tuple[Rect, tuple[SymbolPartPlacement, ...]]:
    """Translate completed chip geometry and quantize only completed burst ink.

    The footprint and fit remain based on the unrounded measured geometry. The
    returned bounds never shrink that nominal frame and expand when rounding
    moves a burst vertex just beyond it.
    """
    if not isfinite(origin_x) or not isfinite(origin_y):
        raise ChipGeometryError("nonfinite-geometry")
    geometry = measured.geometry
    translate_x, translate_y = float(origin_x), float(origin_y)
    parts = tuple(replace(part, commands=tuple(replace(command, points=tuple(
        (x + translate_x, y + translate_y) for x, y in command.points))
        for command in part.commands)) for part in geometry.symbol_parts)
    bounds = Rect(Decimal(str(translate_x)) + geometry.outer_bounds.inline,
                  Decimal(str(translate_y)) + geometry.outer_bounds.block,
                  geometry.outer_bounds.inline_size, geometry.outer_bounds.block_size)
    if measured.outline_precision is None:
        return bounds, parts

    precision = measured.outline_precision
    try:
        parts = tuple(replace(part, commands=tuple(replace(command, points=tuple(
            (_quantize_coordinate(x, precision), _quantize_coordinate(y, precision))
            for x, y in command.points)) for command in part.commands)) for part in parts)
    except (InvalidOperation, OverflowError, ValueError) as error:
        raise ChipGeometryError("precision-geometry") from error
    if not all(isfinite(coordinate) for part in parts for command in part.commands
               for point in command.points for coordinate in point):
        raise ChipGeometryError("precision-geometry")

    points = tuple(point for part in parts if part.paint_mode in (None, "fill")
                   for command in part.commands for point in command.points)
    if points:
        x_values = tuple(Decimal(str(point[0])) for point in points)
        y_values = tuple(Decimal(str(point[1])) for point in points)
        left = min(bounds.inline, *x_values)
        top = min(bounds.block, *y_values)
        right = max(bounds.inline + bounds.inline_size, *x_values)
        bottom = max(bounds.block + bounds.block_size, *y_values)
        bounds = Rect(left, top, right - left, bottom - top)

    padded = geometry.padded_text_bounds
    padded_absolute = Rect(Decimal(str(translate_x)) + padded.inline,
                           Decimal(str(translate_y)) + padded.block,
                           padded.inline_size, padded.block_size)
    fills = tuple(part.commands for part in parts if part.paint_mode in (None, "fill"))
    try:
        covered = filled_contours_cover_rectangle(fills, padded_absolute)
    except ContourUnionError as error:
        raise ChipGeometryError("precision-geometry") from error
    except Exception as error:
        raise ChipGeometryError("precision-geometry") from error
    if not covered:
        raise ChipGeometryError("precision-geometry")
    return bounds, parts


def _half_quantum(precision: int) -> Decimal:
    # A float-based placement cannot move by less than its smallest positive
    # subnormal; avoid materializing enormous exponents for arbitrary precision.
    if precision > 323:
        return Decimal(0)
    return Decimal("0.5").scaleb(-precision)


def _quantize_coordinate(value: float, precision: int) -> float:
    number = Decimal(str(value))
    if number.is_zero():
        return 0.0
    decimal_places = max(0, -number.as_tuple().exponent)
    if precision >= decimal_places:
        return value
    quantum = Decimal(1).scaleb(-precision)
    needed = max(28, len(number.as_tuple().digits) + max(0, number.adjusted()) + precision + 2)
    with localcontext() as context:
        context.prec = needed
        rounded = number.quantize(quantum, rounding=ROUND_HALF_EVEN)
        return 0.0 if rounded.is_zero() else float(rounded)


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
