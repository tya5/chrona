"""Validate completed pattern hosts without selecting geometry or tile phase."""
from __future__ import annotations

from math import isfinite

from chrona.presentation.layout.surface_quality import PathCommand
from chrona.presentation.model.semantic_registry import semantic_binding


_CUT_HOSTS = frozenset((semantic_binding(key).purpose, semantic_binding(key).scene_role)
                       for key in ("missingActual", "progressFill", "summaryBar"))


def completed_pattern_host_valid(*, kind: str, purpose: str, visual_role: str,
                                 bounds: tuple[float, ...], catalog: bool,
                                 origin: tuple[float, ...] | None,
                                 region: tuple[float, ...] | None,
                                 clip: tuple[float, ...] | None,
                                 radius: float | None,
                                 outline: tuple[PathCommand, ...] = (),
                                 paint_clipped: bool = False,
                                 end_treatment: str = "closed",
                                 glyph: bool = False) -> bool:
    """Check supplied facts; only a closed window-cut host may retain old phase."""
    if not catalog:
        return kind == "Rect"
    if (not isinstance(bounds, tuple) or not isinstance(origin, tuple)
            or region != bounds or clip != bounds or len(bounds) != 4
            or len(origin) != 2 or radius is None
            or not all(isinstance(value, (int, float)) and not isinstance(value, bool)
                       and isfinite(value) for value in (*bounds, *origin, radius))):
        return False
    x, y, width, height = bounds
    if width <= 0 or height <= 0 or not isfinite(x + width) or not isfinite(y + height):
        return False
    if kind == "Rect":
        return origin == (x, y) and 0 <= radius <= min(width, height) / 2
    if (kind != "Symbol" or (purpose, visual_role) not in _CUT_HOSTS
            or not paint_clipped or end_treatment != "closed" or glyph
            or radius != 0 or not outline):
        return False
    start = end = None
    count = 0
    for command in outline:
        if not isinstance(command, PathCommand):
            return False
        if any(not isinstance(point, tuple) or len(point) != 2
               or any(not isinstance(value, (int, float)) or isinstance(value, bool)
                      or not isfinite(value) for value in point) for point in command.points):
            return False
        if command.kind == "move":
            if start is not None and (end != start or count < 4):
                return False
            start = end = command.points[0]
            count = 1
        elif start is None:
            return False
        elif command.kind == "close":
            end = start
        else:
            end = command.points[-1]
        if command.kind != "move":
            count += 1
        if any(not (isfinite(px) and isfinite(py) and x <= px <= x + width
                    and y <= py <= y + height) for px, py in command.points):
            return False
    return start is not None and end == start and count >= 4
