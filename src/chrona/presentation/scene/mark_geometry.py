"""Finite Theme treatment expansion into completed renderer-neutral geometry."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite

from chrona.presentation.icons.normalizer import IconNormalizationError, parse_path_commands
from chrona.presentation.layout.surface_quality import PathCommand
from chrona.presentation.layout.relation_terminals import marker_geometry
from chrona.presentation.scene.model import PatternGeometry, PatternStroke, SymbolGeometry


@dataclass(frozen=True)
class GlyphPart:
    """One planned, unpainted part of a Theme-bound multi-part glyph symbol."""

    outline: tuple[PathCommand, ...]
    paint: str
    color: str | None


def pattern_geometry(value: Mapping[str, object]) -> PatternGeometry | None:
    kind = _choice(value, "kind", {"outline", "diagonal-hatch"})
    if kind == "outline":
        if set(value) != {"kind"}:
            raise ValueError("E_THEME_TOKEN_TYPE")
        return None
    inline, block, angle, width = (_number(value, name) for name in
                                   ("tileInlineSize", "tileBlockSize", "angle", "strokeWidth"))
    if inline <= 0 or block <= 0 or width <= 0 or not 0 <= angle < 360:
        raise ValueError("E_THEME_TOKEN_TYPE")
    return PatternGeometry(inline, block, angle, (PatternStroke((0.0, 0.0), (0.0, block), width),))


def pattern_kind(value: Mapping[str, object]) -> str:
    return _choice(value, "kind", {"outline", "diagonal-hatch"})


def symbol_geometry(value: Mapping[str, object], bounds: tuple[float, float, float, float],
                    layout_outline: tuple[PathCommand, ...] = ()) -> SymbolGeometry:
    if layout_outline:
        return SymbolGeometry(layout_outline)
    shape = _choice(value, "shape", {"diamond", "circle", "square", "chevron"})
    x, y, width, height = bounds
    if width < 0 or height < 0:
        raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
    if shape == "diamond":
        points = ((x + width / 2, y), (x + width, y + height / 2), (x + width / 2, y + height), (x, y + height / 2))
        return SymbolGeometry(_closed_lines(points))
    if shape == "square":
        return SymbolGeometry(_closed_lines(((x, y), (x + width, y), (x + width, y + height), (x, y + height))))
    if shape == "chevron":
        return SymbolGeometry(_closed_lines(((x, y), (x + width, y + height / 2), (x, y + height), (x + width / 3, y + height / 2))))
    cx, cy = x + width / 2, y + height / 2
    return SymbolGeometry((PathCommand("move", ((cx, y),)),
                           PathCommand("quadratic", ((x + width, y), (x + width, cy))),
                           PathCommand("quadratic", ((x + width, y + height), (cx, y + height))),
                           PathCommand("quadratic", ((x, y + height), (x, cy))),
                           PathCommand("quadratic", ((x, y), (cx, y)))))


def glyph_parts(value: Mapping[str, object], bounds: tuple[float, float, float, float]) -> tuple[GlyphPart, ...]:
    """Plan a multi-part glyph's painted parts, fitted contain/centred into ``bounds``.

    Each part's ``d`` is ordinary SVG path data in the glyph's own ``viewBox``;
    this reuses the icon normalizer's path-data grammar (`parse_path_commands`)
    rather than a second parser. Only ``move``/``line``/``close`` commands are
    supported today (no curve has been needed by an approved target yet); a
    curved part raises the same diagnostic as any other malformed token value.
    """
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
    result: list[GlyphPart] = []
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
            commands = parse_path_commands(raw)
        except IconNormalizationError as error:
            raise ValueError("E_THEME_TOKEN_TYPE") from error
        outline: list[PathCommand] = []
        start: tuple[float, float] | None = None
        for command in commands:
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
        result.append(GlyphPart(tuple(outline), paint, color))
    return tuple(result)


def _closed_lines(points: tuple[tuple[float, float], ...]) -> tuple[PathCommand, ...]:
    return (PathCommand("move", (points[0],)), *(PathCommand("line", (point,)) for point in points[1:]),
            PathCommand("line", (points[0],)))


def _choice(value: Mapping[str, object], name: str, choices: set[str]) -> str:
    result = value.get(name)
    if not isinstance(result, str) or result not in choices:
        raise ValueError("E_THEME_TOKEN_TYPE")
    return result


def _number(value: Mapping[str, object], name: str) -> float:
    raw = value.get(name)
    if not isinstance(raw, (int, float)) or isinstance(raw, bool) or not isfinite(float(raw)):
        raise ValueError("E_THEME_TOKEN_TYPE")
    return float(raw)
