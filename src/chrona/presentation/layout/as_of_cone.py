"""Completed as-of light cone owned by Layout: a Theme-declared polygon falling from the as-of marker (#890).

The cone is ground, not content. Layout places the as-of line, so it also completes the cone from the same
x and the plot: apex at the top of the line, widening downward to a foot at a declared fraction of the plot
height, clipped to the plot. Scene gives the polygon its gradient; nothing here is random and nothing
depends on iteration order, and no trigonometry is used, so one Theme always gives the same bytes.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from chrona.presentation.layout.model import LayoutError, Rect, geometry_sum
from chrona.presentation.layout.surface_quality import PathCommand, ShapePlacement

AS_OF_CONE_ROLE = "as-of-cone"
AS_OF_CONE_SEMANTIC_ID = "asOfCone"
AS_OF_CONE_PLACEMENT_ID = "as-of-cone"
# Above the row, group, calendar and period bands (10 to 12) and the axis rules, below every mark (100 and up),
# the as-of line and all text: a rule of the shape, not a Theme choice (the role admits no paint order).
AS_OF_CONE_PAINT_ORDER = 50
MAX_SPREAD = Decimal(4)
_PRECISION = 3

Point = tuple[float, float]


def complete_as_of_cone(theme_tokens: Any, plot: Rect, x: float) -> ShapePlacement | None:
    """Return the cone of a Theme whose ``as-of-cone`` role declares a spread, else nothing.

    ``coneSpread`` is the half-width the beam gains per unit of depth (a ratio, ``0 < spread <= 4``) and
    ``coneExtent`` the depth of the foot as a fraction of the plot height (``0 < extent <= 1``; 1 reaches the
    last row). The triangle is clipped to the plot's inline extent. A clip that leaves no area gives no cone.
    """
    has_role = getattr(theme_tokens, "has_role", None)
    if not callable(has_role) or not has_role(AS_OF_CONE_ROLE):
        return None
    spread = theme_tokens.optional_number(AS_OF_CONE_ROLE, "coneSpread")
    extent = theme_tokens.optional_number(AS_OF_CONE_ROLE, "coneExtent")
    base = f"/body/roles/{AS_OF_CONE_ROLE}"
    if spread is None:
        return None  # a cone is declared by its spread; resource resolution rejects a half-declared role earlier
    if extent is None:
        raise LayoutError("E_THEME_ROLE_REQUIRED", f"{base}/coneExtent")
    if not 0 < spread <= MAX_SPREAD:
        raise LayoutError("E_VISUAL_CAPABILITY_LIMIT", f"{base}/coneSpread",
                          f"coneSpread {float(spread):g} must be in (0, {MAX_SPREAD}]")
    if not 0 < extent <= 1:
        raise LayoutError("E_VISUAL_CAPABILITY_LIMIT", f"{base}/coneExtent",
                          f"coneExtent {float(extent):g} must be in (0, 1]")
    top = float(plot.block)
    depth = float(extent) * float(plot.block_size)
    half = depth * float(spread)
    polygon = _clip_inline((x, top), (x + half, top + depth), (x - half, top + depth),
                           left=float(plot.inline), right=float(plot.inline + plot.inline_size))
    points = _distinct(tuple((round(px, _PRECISION), round(py, _PRECISION)) for px, py in polygon))
    apex = (round(x, _PRECISION), round(top, _PRECISION))
    if apex in points:  # the polygon always starts at the apex, whatever the clip did to the vertex order
        start = points.index(apex)
        points = points[start:] + points[:start]
    if len(points) < 3 or _area(points) <= 0:
        return None
    xs, ys = [px for px, _ in points], [py for _, py in points]
    bounds = Rect(Decimal(str(min(xs))), Decimal(str(min(ys))),
                  Decimal(str(round(max(xs) - min(xs), _PRECISION))), Decimal(str(round(max(ys) - min(ys), _PRECISION))))
    commands = (PathCommand("move", (points[0],)), *(PathCommand("line", (point,)) for point in points[1:]),
                PathCommand("line", (points[0],)))
    return ShapePlacement(AS_OF_CONE_PLACEMENT_ID, "actual-set", "Polygon", bounds, points,
                          paint_order=AS_OF_CONE_PAINT_ORDER, semantic_id=AS_OF_CONE_SEMANTIC_ID,
                          path_commands=commands)


def _clip_inline(*polygon: Point, left: float, right: float) -> tuple[Point, ...]:
    """Clip a convex polygon to the vertical strip ``left <= x <= right`` (Sutherland-Hodgman, order kept)."""
    result = tuple(polygon)
    for edge, keep_greater in ((left, True), (right, False)):
        clipped: list[Point] = []
        for index, current in enumerate(result):
            previous = result[index - 1]
            current_in = current[0] >= edge if keep_greater else current[0] <= edge
            previous_in = previous[0] >= edge if keep_greater else previous[0] <= edge
            if current_in != previous_in:
                weight = (edge - previous[0]) / (current[0] - previous[0])
                clipped.append((edge, previous[1] + weight * (current[1] - previous[1])))
            if current_in:
                clipped.append(current)
        result = tuple(clipped)
    return result


def _distinct(points: tuple[Point, ...]) -> tuple[Point, ...]:
    kept: list[Point] = []
    for point in points:
        if not kept or point != kept[-1]:
            kept.append(point)
    if len(kept) > 1 and kept[0] == kept[-1]:
        kept.pop()
    return tuple(kept)


def _area(points: tuple[Point, ...]) -> float:
    twice = geometry_sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, (*points[1:], points[0])))
    return abs(twice) / 2
