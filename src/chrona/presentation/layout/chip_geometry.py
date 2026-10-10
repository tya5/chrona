"""Completed, reusable geometry for label chips (#428, #1150, #1286)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import cos, hypot, isfinite, pi, sin, sqrt
from typing import Any, Mapping

from chrona.presentation.layout.filled_contour import ContourUnionError, filled_contours_cover_rectangle
from chrona.presentation.layout.glyph_slice_geometry import GlyphSliceError, slice_glyph_parts
from chrona.presentation.layout.mark_geometry import SymbolPartPlacement
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_quality import PathCommand
from chrona.presentation.model.semantic_registry import semantic_binding
from chrona.presentation.model.theme_tokens import (
    BurstChipShape, CatalogChipShape, ChipShapeToken, RectangleChipShape,
)


@dataclass(frozen=True)
class ChipGeometry:
    """One local chip frame, text-safe rectangles, and its completed symbol parts.

    All rectangles and path commands are relative to the nominal outer frame's
    top-left, which is always (0, 0). A placer translates the same completed
    geometry to each candidate origin; it does not measure or shape it again.
    """

    outer_bounds: Rect
    text_bounds: Rect
    padded_text_bounds: Rect
    symbol_parts: tuple[SymbolPartPlacement, ...] = ()


class ChipGeometryError(ValueError):
    """A bounded reason a selected chip geometry cannot be completed."""

    def __init__(self, reason: str):
        self.reason = reason if reason in {
            "invalid-measurement", "nonfinite-geometry", "unsupported-shape",
            "catalog-geometry", "catalog-fill-coverage", "catalog-coverage-geometry",
        } else "unsupported-shape"
        super().__init__(self.reason)


def chip_padding(theme_tokens: Any, chip_semantic: str | None, font_size: float, text_block: float) -> tuple[float, float]:
    """The inline and block padding of a label's chip; (0, 0) when the Theme declares no chip.

    Inline is `chipPadding` times the label font size and the block side is half of it, so the chip's block
    size is the text block plus a padding on each side. A role that declares `chipMinBlockSize` keeps the chip
    at least that tall: the shortfall is split above and below the text.
    """
    role = semantic_binding(chip_semantic).theme_role if chip_semantic else None
    chip = theme_tokens.label_chip(role) if role is not None else None
    if chip is None:
        return 0.0, 0.0
    inline = float(chip[0]) * font_size
    block = inline / 2
    minimum = theme_tokens.label_chip_min_block(role)
    if minimum is not None:
        block = max(block, (float(minimum) - text_block) / 2)
    return inline, block


def complete_chip_geometry(*, text_inline: float, text_block: float,
                           padding: tuple[float, float], shape: ChipShapeToken,
                           font_size: float, glyph: Mapping[str, object] | None = None) -> ChipGeometry:
    """Complete one chip in a local origin from already-measured text dimensions.

    ``padding`` is (inline, block) per side. Rectangle completion reproduces
    the existing symmetric chip footprint; burst completion contains the
    padded text rectangle in the selected regular star polygon's true
    inscribed circle; catalog completion uses the shared nine-slice warp and
    requires the padded text rectangle to be covered by its filled paths.
    """
    if (not isinstance(padding, tuple) or len(padding) != 2
            or any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in padding)
            or isinstance(text_inline, bool) or not isinstance(text_inline, (int, float))
            or isinstance(text_block, bool) or not isinstance(text_block, (int, float))
            or isinstance(font_size, bool) or not isinstance(font_size, (int, float))):
        raise ChipGeometryError("invalid-measurement")
    try:
        values = (float(text_inline), float(text_block), float(padding[0]), float(padding[1]), float(font_size))
    except (OverflowError, TypeError, ValueError) as error:
        raise ChipGeometryError("nonfinite-geometry") from error
    if not all(isfinite(value) for value in values):
        raise ChipGeometryError("nonfinite-geometry")
    text_width, text_height, pad_inline, pad_block, size = values
    if text_width < 0 or text_height < 0 or pad_inline < 0 or pad_block < 0 or size <= 0:
        raise ChipGeometryError("invalid-measurement")

    padded_width = text_width + 2 * pad_inline
    padded_height = text_height + 2 * pad_block
    if not isfinite(padded_width) or not isfinite(padded_height):
        raise ChipGeometryError("nonfinite-geometry")

    if isinstance(shape, RectangleChipShape):
        return _geometry(padded_width, padded_height, pad_inline, pad_block,
                         text_width, text_height, 0.0, 0.0,
                         padded_width=padded_width, padded_height=padded_height)
    if isinstance(shape, BurstChipShape):
        try:
            inner_ratio = float(shape.inner_ratio)
        except (OverflowError, TypeError, ValueError) as error:
            raise ChipGeometryError("nonfinite-geometry") from error
        return _burst_geometry(padded_width, padded_height, pad_inline, pad_block,
                               text_width, text_height, shape.points, inner_ratio)
    if isinstance(shape, CatalogChipShape):
        if not isinstance(glyph, Mapping):
            raise ChipGeometryError("catalog-geometry")
        return _catalog_geometry(padded_width, padded_height, pad_inline, pad_block,
                                 text_width, text_height, shape, glyph, size)
    raise ChipGeometryError("unsupported-shape")


def _geometry(outer_width: float, outer_height: float, text_x: float, text_y: float,
              text_width: float, text_height: float, padded_x: float, padded_y: float,
              *, padded_width: float | None = None, padded_height: float | None = None,
              symbol_parts: tuple[SymbolPartPlacement, ...] = ()) -> ChipGeometry:
    width, height = outer_width, outer_height
    padded_width = width - padded_x if padded_width is None else padded_width
    padded_height = height - padded_y if padded_height is None else padded_height
    if not all(isfinite(value) for value in (width, height, text_x, text_y, text_width, text_height,
                                             padded_x, padded_y, padded_width, padded_height)):
        raise ChipGeometryError("nonfinite-geometry")
    if min(width, height, text_width, text_height, padded_width, padded_height) < 0:
        raise ChipGeometryError("invalid-measurement")
    return ChipGeometry(
        Rect(Decimal(0), Decimal(0), Decimal(str(width)), Decimal(str(height))),
        Rect(Decimal(str(text_x)), Decimal(str(text_y)),
             Decimal(str(text_width)), Decimal(str(text_height))),
        Rect(Decimal(str(padded_x)), Decimal(str(padded_y)),
             Decimal(str(padded_width)), Decimal(str(padded_height))),
        symbol_parts,
    )


def _burst_geometry(padded_width: float, padded_height: float, pad_inline: float, pad_block: float,
                    text_width: float, text_height: float,
                    points: int, inner_ratio: float) -> ChipGeometry:
    if (isinstance(points, bool) or not isinstance(points, int) or points < 2
            or not isfinite(inner_ratio) or not 0 < inner_ratio <= 1):
        raise ChipGeometryError("invalid-measurement")
    try:
        theta = pi / points
    except (OverflowError, ValueError, ZeroDivisionError) as error:
        raise ChipGeometryError("nonfinite-geometry") from error
    if theta <= 0:
        raise ChipGeometryError("nonfinite-geometry")
    if inner_ratio <= cos(theta):
        inradius_factor = inner_ratio
    else:
        denominator = hypot(1 - inner_ratio, 2 * sqrt(inner_ratio) * sin(theta / 2))
        inradius_factor = inner_ratio * sin(theta) / denominator if denominator > 0 else 0.0
    if not isfinite(inradius_factor) or inradius_factor <= 0:
        raise ChipGeometryError("nonfinite-geometry")
    try:
        farthest_corner = hypot(padded_width / 2, padded_height / 2)
        radius = farthest_corner / inradius_factor
    except (OverflowError, ValueError, ZeroDivisionError) as error:
        raise ChipGeometryError("nonfinite-geometry") from error
    if not isfinite(radius) or radius <= 0:
        raise ChipGeometryError("nonfinite-geometry")
    try:
        vertices = tuple((radius * (inner_ratio if index % 2 else 1.0) *
                          cos(-pi / 2 + index * theta),
                          radius * (inner_ratio if index % 2 else 1.0) *
                          sin(-pi / 2 + index * theta))
                         for index in range(2 * points))
    except (OverflowError, ValueError, MemoryError) as error:
        raise ChipGeometryError("nonfinite-geometry") from error
    left = min(x for x, _y in vertices)
    right = max(x for x, _y in vertices)
    top = min(y for _x, y in vertices)
    bottom = max(y for _x, y in vertices)
    width, height = right - left, bottom - top
    padded_x = -padded_width / 2 - left
    padded_y = -padded_height / 2 - top
    commands = (PathCommand("move", ((vertices[0][0] - left, vertices[0][1] - top),)),
                *(PathCommand("line", ((x - left, y - top),)) for x, y in vertices[1:]),
                PathCommand("line", ((vertices[0][0] - left, vertices[0][1] - top),)))
    part = SymbolPartPlacement(commands, "fill")
    return _geometry(width, height, padded_x + pad_inline, padded_y + pad_block,
                     text_width, text_height,
                     padded_x, padded_y, padded_width=padded_width, padded_height=padded_height,
                     symbol_parts=(part,))


def _catalog_geometry(padded_width: float, padded_height: float, pad_inline: float, pad_block: float,
                      text_width: float, text_height: float,
                      shape: CatalogChipShape, glyph: Mapping[str, object], font_size: float) -> ChipGeometry:
    try:
        unit_px = float(shape.unit_em) * font_size
        insets = tuple(float(value) for value in shape.slice_insets)
    except (OverflowError, TypeError, ValueError) as error:
        raise ChipGeometryError("nonfinite-geometry") from error
    top, right, bottom, left = insets
    if not all(isfinite(value) for value in (unit_px, *insets)) or unit_px <= 0:
        raise ChipGeometryError("nonfinite-geometry")
    outer_width = padded_width + (left + right) * unit_px
    outer_height = padded_height + (top + bottom) * unit_px
    if not isfinite(outer_width) or not isfinite(outer_height):
        raise ChipGeometryError("nonfinite-geometry")
    try:
        parts = slice_glyph_parts(glyph, (0.0, 0.0, outer_width, outer_height),
                                  slice_insets=insets, unit_px=unit_px)
    except (GlyphSliceError, TypeError, ValueError, OverflowError) as error:
        raise ChipGeometryError("catalog-geometry") from error
    text_bounds = Rect(Decimal(str(left * unit_px + pad_inline)), Decimal(str(top * unit_px + pad_block)),
                       Decimal(str(text_width)), Decimal(str(text_height)))
    padded_bounds = Rect(Decimal(str(left * unit_px)), Decimal(str(top * unit_px)),
                         Decimal(str(padded_width)), Decimal(str(padded_height)))
    operands = tuple(part.commands for part in parts if part.paint_mode == "fill")
    try:
        covered = filled_contours_cover_rectangle(operands, padded_bounds)
    except ContourUnionError as error:
        raise ChipGeometryError("catalog-coverage-geometry") from error
    except Exception as error:
        raise ChipGeometryError("catalog-coverage-geometry") from error
    if not covered:
        raise ChipGeometryError("catalog-fill-coverage")
    return ChipGeometry(Rect(Decimal(0), Decimal(0), Decimal(str(outer_width)), Decimal(str(outer_height))),
                        text_bounds, padded_bounds, parts)


