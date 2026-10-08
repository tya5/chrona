"""Deterministic Layout completion for bounded seeded canvas pattern tiles."""
from __future__ import annotations

from collections.abc import Mapping
from math import ceil, isfinite, pi, sqrt

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.pattern_placement import (
    PatternPathCommand,
    PatternPlacement,
    PatternTilePrimitive,
)

_MASK64 = (1 << 64) - 1
_GOLDEN = 0x9E3779B97F4A7C15
_MIX1 = 0xBF58476D1CE4E5B9
_MIX2 = 0x94D049BB133111EB


def complete_seeded_pattern(value: Mapping[str, object], bounds: Rect, *,
                            pointer: str = "/layout/pattern") -> PatternPlacement:
    """Complete a seeded grain/rain declaration as ordinary periodic geometry."""
    try:
        if not isinstance(value, Mapping):
            raise TypeError
        motif = value.get("motif")
        common = {"kind", "algorithm", "motif", "seed", "tile", "count"}
        expected = common | ({"radius"} if motif == "grain" else
                             {"length", "strokeWidth", "slant"} if motif == "rain" else set())
        if (motif not in {"grain", "rain"} or set(value) != expected
                or value.get("kind") != "seeded" or value.get("algorithm") != "splitmix64-v1"):
            raise ValueError
        seed = _integer(value["seed"], 0, 0xFFFFFFFF)
        count = _integer(value["count"], 1, 64)
        tile = value["tile"]
        if not isinstance(tile, Mapping) or set(tile) != {"inlineSize", "blockSize"}:
            raise ValueError
        tile_inline = _rounded_positive(tile["inlineSize"])
        tile_block = _rounded_positive(tile["blockSize"])

        if motif == "grain":
            radius = _rounded_positive(value["radius"])
            if not isfinite(radius * 2) or radius * 2 >= tile_inline or radius * 2 >= tile_block:
                raise ValueError
            primitives = tuple(_grain(radius, tile_inline, tile_block, _draws(seed, index))
                               for index in range(count))
            motif_area = pi * radius * radius
        else:
            length = _rounded_positive(value["length"])
            stroke_width = _rounded_positive(value["strokeWidth"])
            slant = _finite(value["slant"])
            dx = _finite(slant * length)
            if not isfinite(dx):
                raise ValueError
            inline_margin = (abs(dx) + stroke_width) / 2
            block_margin = (length + stroke_width) / 2
            inline_range = tile_inline - 2 * inline_margin
            block_range = tile_block - 2 * block_margin
            if inline_range <= 0 or block_range <= 0 or not all(map(isfinite, (inline_range, block_range))):
                raise ValueError
            primitives = tuple(_rain(length, stroke_width, dx, tile_inline, tile_block,
                                     inline_margin, block_margin, _draws(seed, index))
                               for index in range(count))
            motif_area = sqrt(dx * dx + length * length) * stroke_width

        region_inline = _finite(float(bounds.inline))
        region_block = _finite(float(bounds.block))
        region_width = _finite(float(bounds.inline_size))
        region_height = _finite(float(bounds.block_size))
        if not all(map(isfinite, (region_inline, region_block, region_width, region_height))) or min(region_width, region_height) <= 0:
            raise ValueError
        area = tile_inline * tile_block
        total_motif_area = count * motif_area
        density_ratio = (total_motif_area / area) * 10_000
        if (not isfinite(area) or area <= 0 or not isfinite(motif_area)
                or not isfinite(total_motif_area) or not isfinite(density_ratio)):
            raise ValueError
        density_raw = ceil(density_ratio)
        density = min(10_000, max(1, density_raw))
        return PatternPlacement(tile_inline, tile_block, 0.0, density, primitives,
                                (region_inline, region_block), bounds, bounds, 0.0)
    except (KeyError, TypeError, ValueError, OverflowError, ArithmeticError) as error:
        raise LayoutError("E_THEME_TOKEN_TYPE", pointer) from error


def _grain(radius: float, tile_inline: float, tile_block: float,
           draws: tuple[float, float]) -> PatternTilePrimitive:
    cx = _clamp(_round(radius + draws[0] * (tile_inline - 2 * radius)), radius, tile_inline - radius)
    cy = _clamp(_round(radius + draws[1] * (tile_block - 2 * radius)), radius, tile_block - radius)
    return PatternTilePrimitive("circle", cx=cx, cy=cy, radius=radius)


def _rain(length: float, stroke_width: float, dx: float, tile_inline: float, tile_block: float,
          inline_margin: float, block_margin: float,
          draws: tuple[float, float]) -> PatternTilePrimitive:
    cx = _clamp(_round(inline_margin + draws[0] * (tile_inline - 2 * inline_margin)),
                inline_margin, tile_inline - inline_margin)
    cy = _clamp(_round(block_margin + draws[1] * (tile_block - 2 * block_margin)),
                block_margin, tile_block - block_margin)
    x0 = _clamp(_round(cx - dx / 2), stroke_width / 2, tile_inline - stroke_width / 2)
    x1 = _clamp(_round(cx + dx / 2), stroke_width / 2, tile_inline - stroke_width / 2)
    y0 = _clamp(_round(cy - length / 2), stroke_width / 2, tile_block - stroke_width / 2)
    y1 = _clamp(_round(cy + length / 2), stroke_width / 2, tile_block - stroke_width / 2)
    if (x0, y0) == (x1, y1):
        raise ValueError
    commands = (PatternPathCommand("move", ((x0, y0),)), PatternPathCommand("line", ((x1, y1),)))
    return PatternTilePrimitive("path", paint="stroke", commands=commands,
                                stroke_width=stroke_width, line_cap="butt", line_join="round")


def _draws(seed: int, motif_index: int) -> tuple[float, float]:
    return (_draw(seed, motif_index * 2), _draw(seed, motif_index * 2 + 1))


def _draw(seed: int, index: int) -> float:
    z = (seed + (index + 1) * _GOLDEN) & _MASK64
    z = ((z ^ (z >> 30)) * _MIX1) & _MASK64
    z = ((z ^ (z >> 27)) * _MIX2) & _MASK64
    z = (z ^ (z >> 31)) & _MASK64
    return (z >> 11) / (1 << 53)


def _integer(value: object, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise ValueError
    return value


def _finite(value: object) -> float:
    if (not isinstance(value, (int, float)) or isinstance(value, bool)
            or not isfinite(float(value))):
        raise ValueError
    return float(value)


def _rounded_positive(value: object) -> float:
    rounded = _round(_finite(value))
    if rounded <= 0:
        raise ValueError
    return rounded


def _round(value: float) -> float:
    result = round(value, 3)
    if not isfinite(result):
        raise ValueError
    return result


def _clamp(value: float, low: float, high: float) -> float:
    if low > high or not all(map(isfinite, (value, low, high))):
        raise ValueError
    return min(high, max(low, value))
