"""Pure repeat-cell coverage for completed Rect pattern geometry."""
from __future__ import annotations

from math import cos, floor, isfinite, radians, sin
from typing import Iterable

from chrona.presentation.scene.model import ScenePrimitive


def _error(code: str, detail: str) -> ValueError:
    return ValueError(f"{code}: {detail}")


def _finite(value: object) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and isfinite(value))


def _finite_tuple(value: object, size: int) -> bool:
    return (isinstance(value, tuple) and len(value) == size
            and all(_finite(item) for item in value))


def repeat_cells(node: ScenePrimitive) -> Iterable[tuple[float, float]]:
    """Return global top-lefts for the finite repeated tiles meeting ``node``.

    This only enumerates the affine lattice already recorded in Scene.  It does
    not choose a density, alter phase, or create/measure any geometry.
    """
    pattern = getattr(node, "pattern", None)
    scene_id = getattr(node, "scene_id", "<unknown>")
    bounds = getattr(node, "bounds", None)
    if getattr(node, "kind", None) != "Rect" or pattern is None:
        raise _error("E_PRESENTATION_PRIMITIVE_INVALID",
                     f"scene_id={scene_id!r}; expected a patterned Rect")
    if (not _finite_tuple(bounds, 4) or bounds[2] <= 0 or bounds[3] <= 0
            or not isfinite(bounds[0] + bounds[2])
            or not isfinite(bounds[1] + bounds[3])):
        raise _error("E_PRESENTATION_PRIMITIVE_INVALID",
                     f"scene_id={scene_id!r} bounds={bounds!r}; expected finite positive Rect bounds")

    width = getattr(pattern, "tile_inline_size", None)
    height = getattr(pattern, "tile_block_size", None)
    angle = getattr(pattern, "angle_degrees", None)
    catalog = bool(getattr(pattern, "primitives", ()))
    if (not _finite(width) or not _finite(height) or width <= 0 or height <= 0
            or not _finite(angle) or not 0 <= angle < 360):
        raise _error("E_PRESENTATION_PRIMITIVE_INVALID",
                     f"scene_id={scene_id!r}; expected positive finite tile dimensions and finite angle")

    paint = getattr(node, "paint", None)
    stroke = getattr(paint, "stroke", None)
    if not isinstance(stroke, str) or not stroke:
        raise _error("E_PRESENTATION_PAINT_INVALID",
                     f"scene_id={scene_id!r} pattern requires completed paint.stroke")
    if catalog:
        origin = getattr(pattern, "origin", None)
        if (not _finite_tuple(origin, 2)
                or getattr(pattern, "region_bounds", None) != bounds
                or getattr(pattern, "clip_bounds", None) != bounds
                or getattr(pattern, "corner_radius", None) != (getattr(node, "corner_radius", None) or 0)):
            raise _error("E_PRESENTATION_PRIMITIVE_INVALID",
                         f"scene_id={scene_id!r} catalogue pattern region/clip/radius/origin must match its Rect")
        fill = getattr(paint, "fill", None)
        if fill is not None and (not isinstance(fill, str) or not fill or getattr(paint, "opacity", None) != 1):
            raise _error("E_PRESENTATION_PAINT_INVALID",
                         f"scene_id={scene_id!r} catalogue pattern requires an opaque substrate when fill is present")
        ox, oy = origin
        cx, cy = width / 2, height / 2
    else:
        if getattr(paint, "stroke_width", None) is None:
            raise _error("E_PRESENTATION_PAINT_INVALID",
                         f"scene_id={scene_id!r} legacy pattern requires completed paint.stroke_width")
        ox = oy = cx = cy = 0.0

    angle_radians = radians(angle)
    c, s = cos(angle_radians), sin(angle_radians)

    def transform(px: float, py: float) -> tuple[float, float]:
        return (ox + cx + c * (px - cx) - s * (py - cy),
                oy + cy + s * (px - cx) + c * (py - cy))

    left, top, host_width, host_height = bounds
    host_corners = ((left, top), (left + host_width, top),
                    (left, top + host_height), (left + host_width, top + host_height))
    # Invert the same transform, then bound the two lattice coordinates.  A
    # one-cell margin covers floating-point boundary rounding; AABB filtering
    # below drops candidates that cannot meet the host.
    lattice_points = tuple(
        (cx + c * (x - ox - cx) + s * (y - oy - cy),
         cy - s * (x - ox - cx) + c * (y - oy - cy))
        for x, y in host_corners
    )
    min_i = floor(min(x for x, _ in lattice_points) / width) - 1
    max_i = floor(max(x for x, _ in lattice_points) / width) + 1
    min_j = floor(min(y for _, y in lattice_points) / height) - 1
    max_j = floor(max(y for _, y in lattice_points) / height) + 1

    cells: list[tuple[float, float]] = []
    for j in range(min_j, max_j + 1):
        for i in range(min_i, max_i + 1):
            tile_corners = (transform(i * width, j * height),
                            transform((i + 1) * width, j * height),
                            transform(i * width, (j + 1) * height),
                            transform((i + 1) * width, (j + 1) * height))
            xs = tuple(x for x, _ in tile_corners)
            ys = tuple(y for _, y in tile_corners)
            if (max(xs) < left or min(xs) > left + host_width
                    or max(ys) < top or min(ys) > top + host_height):
                continue
            cells.append(transform(i * width, j * height))
    return tuple(cells)
