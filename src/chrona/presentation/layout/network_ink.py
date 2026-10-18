"""Occupied bounds of completed dependency-network paint, before Scene projection."""
from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal
from math import isfinite
from typing import Any

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.path_geometry import flatten_path
from chrona.presentation.layout.relation_terminals import project_marker_outline
from chrona.presentation.model.semantic_registry import semantic_binding

Point = tuple[float, float]


def relation_paint_bounds(relation: Any, tokens: Any | None) -> tuple[float, float, float, float]:
    """Close the union of route stroke and terminal ink for passive Scene projection."""
    ink = network_ink_bounds((), (), (), (relation,), tokens)
    if not ink:
        return (0.0, 0.0, 0.0, 0.0)
    left, top = min(item.inline for item in ink), min(item.block for item in ink)
    right = max(item.inline + item.inline_size for item in ink)
    bottom = max(item.block + item.block_size for item in ink)
    return float(left), float(top), float(right - left), float(bottom - top)


def network_ink_bounds(nodes: Iterable[Any], text: Iterable[Any], shapes: Iterable[Any],
                       relations: Iterable[Any], theme_tokens: Any | None) -> tuple[Rect, ...]:
    """Return one conservative occupied rectangle per completed network primitive.

    This is a Layout geometry projection: it reads only completed placements and
    resolved Theme paint metrics. It neither creates Scene primitives nor infers
    placement. Theme-free synthetic use has no stroke expansion.
    """
    result: list[Rect] = []
    for node in nodes:
        if getattr(node, "is_container", False):
            continue  # Its actual band/header are represented by completed shapes/text.
        bounds = _rect_values(node.bounds)
        role = semantic_binding("networkNode").theme_role
        result.append(_expand_rect(bounds, _shape_stroke_margin(theme_tokens, role, rectangle=True)))

    for item in text:
        result.append(_rect_from_values(_rect_values(item.bounds)))

    for shape in shapes:
        role = getattr(shape, "visual_role", None)
        if role is None and shape.semantic_id:
            role = semantic_binding(shape.semantic_id).theme_role
        bounds = _rect_values(shape.bounds)
        commands = tuple(getattr(shape, "path_commands", ()) or ())
        points = tuple(getattr(shape, "points", ()) or ())
        if commands:
            points = (*points, *flatten_path(commands))
        for part in getattr(shape, "symbol_parts", ()) or ():
            points = (*points, *flatten_path(tuple(part.commands)))
        bounds = _include_points(bounds, points)
        has_stroke = (getattr(shape, "paint_channels", None) == "stroke"
                      or _has_optional_stroke(theme_tokens, role))
        margin = (_shape_stroke_margin(theme_tokens, role, rectangle=not commands and not points)
                  if has_stroke else 0.0)
        result.append(_expand_rect(bounds, margin))

    for relation in relations:
        if getattr(relation, "suppressed", False):
            continue
        role = semantic_binding(relation.semantic_id).theme_role
        stroke = _relation_stroke_width(theme_tokens, role)
        points: tuple[Point, ...] = tuple(getattr(relation, "points", ()) or ())
        commands = tuple(getattr(relation, "path_commands", ()) or ())
        route_points = flatten_path(commands) if commands else points
        if route_points:
            result.append(_points_rect(route_points, stroke / 2))
        for marker, side in ((getattr(relation, "marker_start", None), "start"),
                             (getattr(relation, "marker_end", None), "end")):
            if marker is None or not points:
                continue
            outline = project_marker_outline(marker, side=side, points=points,
                                             path_commands=commands or (),
                                             stroke_width=stroke or None)
            marker_points = flatten_path(outline)
            marker_width = (marker.stroke_width if marker.stroke_width is not None else stroke)
            result.append(_points_rect(marker_points,
                                       marker_width / 2 if marker.paint_mode == "stroke" else 0.0))
    return tuple(result)


def _rect_values(rect: Rect) -> tuple[float, float, float, float]:
    values = tuple(float(value) for value in
                   (rect.inline, rect.block, rect.inline_size, rect.block_size))
    if not all(isfinite(value) for value in values) or values[2] < 0 or values[3] < 0:
        raise ValueError("E_LAYOUT_NETWORK_INK: invalid completed bounds")
    return values


def _include_points(bounds: tuple[float, float, float, float],
                    points: Iterable[Point]) -> tuple[float, float, float, float]:
    points = tuple((float(x), float(y)) for x, y in points)
    if not points:
        return bounds
    if any(not isfinite(value) for point in points for value in point):
        raise ValueError("E_LAYOUT_NETWORK_INK: invalid completed path point")
    x, y, width, height = bounds
    return (min(x, *(point[0] for point in points)),
            min(y, *(point[1] for point in points)),
            max(x + width, *(point[0] for point in points)) - min(x, *(point[0] for point in points)),
            max(y + height, *(point[1] for point in points)) - min(y, *(point[1] for point in points)))


def _points_rect(points: Iterable[Point], margin: float = 0.0) -> Rect:
    points = tuple(points)
    if not points:
        raise ValueError("E_LAYOUT_NETWORK_INK: cannot bound an empty path")
    return _rect_from_values((min(point[0] for point in points) - margin,
                              min(point[1] for point in points) - margin,
                              max(point[0] for point in points) - min(point[0] for point in points) + 2 * margin,
                              max(point[1] for point in points) - min(point[1] for point in points) + 2 * margin))


def _expand_rect(bounds: tuple[float, float, float, float], margin: float) -> Rect:
    x, y, width, height = bounds
    return _rect_from_values((x - margin, y - margin, width + 2 * margin, height + 2 * margin))


def _rect_from_values(values: tuple[float, float, float, float]) -> Rect:
    return Rect(*(Decimal(str(value)) for value in values))


def _relation_stroke_width(tokens: Any | None, role: str) -> float:
    if tokens is None:
        return 0.0
    number = getattr(tokens, "number", None)
    if not callable(number):
        return 0.0
    value = float(number(role, "strokeWidth"))
    if not isfinite(value) or value < 0:
        raise ValueError(f"E_THEME_TOKEN_TYPE: /body/roles/{role}/strokeWidth")
    return value


def _has_optional_stroke(tokens: Any | None, role: str | None) -> bool:
    if tokens is None or role is None:
        return False
    optional_color = getattr(tokens, "optional_color", None)
    if not callable(optional_color):
        return False
    return optional_color(role, "stroke") is not None


def _shape_stroke_margin(tokens: Any | None, role: str | None, *, rectangle: bool) -> float:
    if tokens is None or role is None:
        return 0.0
    optional_color = getattr(tokens, "optional_color", None)
    if not callable(optional_color) or optional_color(role, "stroke") is None:
        return 0.0
    number = getattr(tokens, "optional_number", None)
    width = float(number(role, "strokeWidth") or 0) if callable(number) else 0.0
    if width <= 0:
        return 0.0
    choice = getattr(tokens, "optional_choice", None)
    alignment = choice(role, "strokeAlign", ("inside", "center", "outside")) if callable(choice) else None
    if alignment == "inside":
        return 0.0
    if alignment == "outside":
        # A rectangle's miter extent is one width; arbitrary outlines use the
        # existing four-width miter bound used by complete_stroke_clip.
        return width if rectangle else 4 * width
    return width / 2
