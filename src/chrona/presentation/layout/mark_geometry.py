"""Theme-selected point geometry completed in Layout coordinates."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from chrona.presentation.icons.normalizer import IconNormalizationError, parse_path_commands
from chrona.presentation.layout.surface_quality import PathCommand
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.presentation import MarkBandFrame
from chrona.presentation.layout.path_geometry import open_span_path, rounded_diamond_path
from chrona.presentation.layout.surface_quality import MarkPlacement


@dataclass(frozen=True)
class SymbolPartPlacement:
    commands: tuple[PathCommand, ...]
    paint_mode: str | None = None
    paint_color: str | None = None


def symbol_parts(value: Mapping[str, object], bounds: tuple[float, float, float, float],
                 layout_outline: tuple[PathCommand, ...] = ()) -> tuple[SymbolPartPlacement, ...]:
    """Return the exact completed built-in or glyph paths for one point mark."""
    if value.get("shape") != "glyph":
        if layout_outline:
            return (SymbolPartPlacement(layout_outline),)
        shape = _choice(value, "shape", {"diamond", "circle", "square", "chevron"})
        x, y, width, height = bounds
        if width < 0 or height < 0:
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
        if shape == "diamond":
            points = ((x + width / 2, y), (x + width, y + height / 2),
                      (x + width / 2, y + height), (x, y + height / 2))
            commands = _closed_lines(points)
        elif shape == "square":
            commands = _closed_lines(((x, y), (x + width, y), (x + width, y + height), (x, y + height)))
        elif shape == "chevron":
            commands = _closed_lines(((x, y), (x + width, y + height / 2),
                                      (x, y + height), (x + width / 3, y + height / 2)))
        else:
            cx, cy = x + width / 2, y + height / 2
            commands = (PathCommand("move", ((cx, y),)),
                        PathCommand("quadratic", ((x + width, y), (x + width, cy))),
                        PathCommand("quadratic", ((x + width, y + height), (cx, y + height))),
                        PathCommand("quadratic", ((x, y + height), (x, cy))),
                        PathCommand("quadratic", ((x, y), (cx, y))))
        return (SymbolPartPlacement(commands),)
    return tuple(SymbolPartPlacement(part.outline, part.paint, part.color)
                 for part in glyph_parts(value, bounds))


def compose_mark_placement(*, frame: MarkBandFrame, placement_id: str, source_ref: str,
                           bounds: Rect, start_port: tuple[float, float], end_port: tuple[float, float],
                           shape: str, semantic_id: str, theme_tokens: object, slot_id: str,
                           paint_order_base: int = 100, end_treatment: str = "closed") -> MarkPlacement:
    """Complete a mark's outline, role paint order, and symbol in one frame-aware path."""
    geometry = frame.role_geometries[semantic_id]
    radius = min(geometry.corner_radius * float(min(bounds.inline_size, bounds.block_size)),
                 float(min(bounds.inline_size, bounds.block_size)) / 2)
    commands = (open_span_path(inline=float(bounds.inline), block=float(bounds.block),
                               inline_size=float(bounds.inline_size), block_size=float(bounds.block_size), radius=radius)
                if shape == "open-span" else
                rounded_diamond_path(inline=float(bounds.inline), block=float(bounds.block),
                                     inline_size=float(bounds.inline_size), block_size=float(bounds.block_size), radius=radius)
                if shape == "point" and radius > 0 else ())
    completed_symbols = ()
    if shape in {"point", "open-span"}:
        variant = "baseline" if semantic_id in {"snapshot", "scenario"} else semantic_id
        token = theme_tokens.variant_symbol(variant)
        try:
            completed_symbols = symbol_parts(token, (float(bounds.inline), float(bounds.block),
                                                       float(bounds.inline_size), float(bounds.block_size)), commands)
        except ValueError as error:
            raise LayoutError("E_LAYOUT_LANE_FOOTPRINT_UNAVAILABLE", placement_id) from error
    return MarkPlacement(placement_id, source_ref, bounds, start_port, end_port,
                         mark_shape=shape, corner_radius=radius, path_commands=commands,
                         slot_id=slot_id, semantic_id=semantic_id,
                         paint_order=paint_order_base + geometry.paint_order,
                         end_treatment=end_treatment, symbol_parts=completed_symbols)


@dataclass(frozen=True)
class _GlyphPart:
    outline: tuple[PathCommand, ...]
    paint: str
    color: str | None


def glyph_parts(value: Mapping[str, object], bounds: tuple[float, float, float, float]) -> tuple[_GlyphPart, ...]:
    view_box = value.get("viewBox")
    if (not isinstance(view_box, (list, tuple)) or len(view_box) != 2
            or any(not isinstance(item, (int, float)) or isinstance(item, bool) or item <= 0 for item in view_box)):
        raise ValueError("E_THEME_TOKEN_TYPE")
    view_width, view_height = float(view_box[0]), float(view_box[1])
    parts = value.get("parts")
    if not isinstance(parts, (list, tuple)) or not parts:
        raise ValueError("E_THEME_TOKEN_TYPE")
    x, y, width, height = bounds
    if width < 0 or height < 0:
        raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
    scale = min(width / view_width, height / view_height)
    offset_x = x + (width - view_width * scale) / 2
    offset_y = y + (height - view_height * scale) / 2
    def transform(point: tuple[float, float]) -> tuple[float, float]:
        return (offset_x + point[0] * scale, offset_y + point[1] * scale)
    result = []
    for part in parts:
        if not isinstance(part, Mapping):
            raise ValueError("E_THEME_TOKEN_TYPE")
        paint = _choice(part, "paint", {"fill", "stroke", "none"})
        color = part.get("color")
        if color is not None and not isinstance(color, str):
            raise ValueError("E_THEME_TOKEN_TYPE")
        if paint == "none":
            continue
        raw = part.get("d")
        if not isinstance(raw, str) or not raw:
            raise ValueError("E_THEME_TOKEN_TYPE")
        try:
            parsed = parse_path_commands(raw)
        except IconNormalizationError as error:
            raise ValueError("E_THEME_TOKEN_TYPE") from error
        outline = []
        start = None
        for command in parsed:
            if command.kind == "move":
                point = transform(command.points[0])
                outline.append(PathCommand("move", (point,)))
                start = point
            elif command.kind == "line":
                outline.append(PathCommand("line", (transform(command.points[0]),)))
            elif command.kind == "close":
                if start is None:
                    raise ValueError("E_THEME_TOKEN_TYPE")
                outline.append(PathCommand("line", (start,)))
            else:
                raise ValueError("E_THEME_TOKEN_TYPE")
        if not outline:
            raise ValueError("E_THEME_TOKEN_TYPE")
        result.append(_GlyphPart(tuple(outline), paint, color))
    return tuple(result)


def _closed_lines(points: tuple[tuple[float, float], ...]) -> tuple[PathCommand, ...]:
    return (PathCommand("move", (points[0],)), *(PathCommand("line", (point,)) for point in points[1:]),
            PathCommand("line", (points[0],)))


def _choice(value: Mapping[str, object], name: str, choices: set[str]) -> str:
    result = value.get(name)
    if not isinstance(result, str) or result not in choices:
        raise ValueError("E_THEME_TOKEN_TYPE")
    return result
