"""Layout-owned nine-slice tile geometry for an image-backed annotation
container (#465).

Pure geometry, parallel in shape to ``balloon_geometry.py``: source rects are
in the artwork's own pixel space; destination rects are absolute Layout
coordinates. Up to nine tiles are returned; a zero inset on one axis
collapses that axis's three tiles into one full-bleed stretch (the
"three-slice" a scroll needs when only its top/bottom rods are fixed), and a
paint box smaller than the declared fixed border scales that border down
instead of inverting or overlapping a tile.
"""
from __future__ import annotations

Rect = tuple[float, float, float, float]
SliceInsets = tuple[float, float, float, float]  # top, right, bottom, left


def image_slice_tiles(box: Rect, *, viewport: tuple[int, int],
                      slice_insets: SliceInsets) -> tuple[tuple[Rect, Rect], ...]:
    """Return ``(source, destination)`` rect pairs stretching one raster asset
    of ``viewport`` pixels to fill ``box``, honouring the declared fixed
    border ``slice_insets`` (in the asset's own pixel units).
    """
    view_width, view_height = viewport
    top, right, bottom, left = slice_insets
    if (view_width <= 0 or view_height <= 0
            or min(top, right, bottom, left) < 0):
        raise ValueError(f"E_LAYOUT_IMAGE_SLICE_GEOMETRY: viewport={viewport!r} requires positive dimensions and sliceInsets={slice_insets!r} nonnegative")
    x, y, width, height = box
    if width <= 0 or height <= 0:
        raise ValueError(f"E_LAYOUT_IMAGE_SLICE_GEOMETRY: destination box width={width!r}, height={height!r} must be positive")
    # Clamp the fixed border so it never exceeds the destination box: a paint
    # box smaller than the declared border scales the border down uniformly
    # rather than inverting or overlapping a tile.
    scale_x = min(1.0, width / (left + right)) if (left + right) > width else 1.0
    scale_y = min(1.0, height / (top + bottom)) if (top + bottom) > height else 1.0
    dest_left, dest_right = left * scale_x, right * scale_x
    dest_top, dest_bottom = top * scale_y, bottom * scale_y

    source_columns = ((0.0, left), (left, view_width - right), (view_width - right, view_width))
    source_rows = ((0.0, top), (top, view_height - bottom), (view_height - bottom, view_height))
    dest_columns = ((x, x + dest_left), (x + dest_left, x + width - dest_right), (x + width - dest_right, x + width))
    dest_rows = ((y, y + dest_top), (y + dest_top, y + height - dest_bottom), (y + height - dest_bottom, y + height))

    tiles: list[tuple[Rect, Rect]] = []
    for (sy0, sy1), (dy0, dy1) in zip(source_rows, dest_rows):
        source_height, dest_height = sy1 - sy0, dy1 - dy0
        if source_height <= 0 or dest_height <= 0:
            continue
        for (sx0, sx1), (dx0, dx1) in zip(source_columns, dest_columns):
            source_width, dest_width = sx1 - sx0, dx1 - dx0
            if source_width <= 0 or dest_width <= 0:
                continue
            tiles.append(((sx0, sy0, source_width, source_height), (dx0, dy0, dest_width, dest_height)))
    if not tiles:
        raise ValueError(f"E_LAYOUT_IMAGE_SLICE_GEOMETRY: box={box!r}, viewport={viewport!r}, sliceInsets={slice_insets!r} produce no positive-area source/destination tile")
    return tuple(tiles)
