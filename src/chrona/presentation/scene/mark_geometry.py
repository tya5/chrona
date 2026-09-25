"""Finite Theme treatment expansion into completed renderer-neutral geometry."""
from __future__ import annotations

from collections.abc import Mapping
from math import isfinite

from chrona.presentation.layout.surface_quality import PathCommand
from chrona.presentation.layout.relation_terminals import marker_geometry
from chrona.presentation.scene.model import PatternGeometry, PatternStroke, SymbolGeometry


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


def symbol_geometry(shape: str, bounds: tuple[float, float, float, float],
                    layout_outline: tuple[PathCommand, ...] = ()) -> SymbolGeometry:
    if layout_outline:
        return SymbolGeometry(layout_outline)
    if shape not in {"diamond", "circle", "square", "chevron"}:
        raise ValueError("E_THEME_TOKEN_TYPE")
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
