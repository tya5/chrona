"""Finite Theme terminal treatments resolved into Layout-owned geometry."""
from __future__ import annotations

from collections.abc import Mapping
from math import isfinite

from chrona.presentation.layout.surface_quality import MarkerGeometry, PathCommand


def marker_geometry(value: Mapping[str, object]) -> MarkerGeometry:
    """Resolve a closed terminal token before Scene receives the relation."""
    shape = _choice(value, "shape", {"triangle", "open-triangle", "chevron", "circle", "open-circle"})
    length, width, offset = (_number(value, name) for name in ("headLength", "headWidth", "attachmentOffset"))
    if length <= 0 or width <= 0 or not 0 <= offset <= length:
        raise ValueError("E_THEME_TOKEN_TYPE")
    if shape in {"circle", "open-circle"}:
        diameter = min(length, width)
        outline = (PathCommand("move", ((diameter / 2, 0.0),)),
                   PathCommand("quadratic", ((diameter, 0.0), (diameter, diameter / 2))),
                   PathCommand("quadratic", ((diameter, diameter), (diameter / 2, diameter))),
                   PathCommand("quadratic", ((0.0, diameter), (0.0, diameter / 2))),
                   PathCommand("quadratic", ((0.0, 0.0), (diameter / 2, 0.0))))
        return MarkerGeometry(outline, diameter, diameter, min(offset, diameter),
                              "fill" if shape == "circle" else "stroke")
    outline = (PathCommand("move", ((0.0, 0.0),)),
               PathCommand("line", ((length, width / 2),)),
               PathCommand("line", ((0.0, width),)))
    if shape == "triangle":
        outline += (PathCommand("line", ((0.0, 0.0),)),)
    return MarkerGeometry(outline, length, width, offset, "fill" if shape == "triangle" else "stroke")


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
