"""Owns Theme-treated background geometry; reads completed extents and ordered calendar intervals."""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Any

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.surface_base import SurfaceBaseGeometry
from chrona.presentation.layout.surface_groups import GroupHeaderExtentUpdate
from chrona.presentation.layout.surface_quality import GroupPlacement, ShapePlacement, intersects
from chrona.presentation.model.semantic_registry import axis_band_semantic_ids, semantic_binding

BACKGROUND_SEMANTIC_IDS = frozenset({
    "rowBand", "groupBand", "groupHeaderBand", "calendarClosed", "periodBand", *axis_band_semantic_ids(),
})


def _background_bounds(*, semantic_id: str, extent: str, source_bounds: Rect,
                       table_bounds: tuple[float, float, float, float],
                       timeline_bounds: tuple[float, float, float, float]) -> tuple[Rect, str]:
    """Resolve one finite source background extent without exposing coordinates to View."""
    if semantic_id == "calendarClosed":
        if extent != "timeline":
            raise LayoutError("E_LAYOUT_BACKGROUND_EXTENT", "/layoutManifest/reviewSurface/backgroundExtents")
        _, timeline_block, _, timeline_block_size = timeline_bounds
        return (Rect(source_bounds.inline, Decimal(str(timeline_block)), source_bounds.inline_size,
                     Decimal(str(timeline_block_size))), "timeline")
    table_inline, _, table_inline_size, _ = table_bounds
    timeline_inline, _, timeline_inline_size, _ = timeline_bounds
    if extent == "table":
        return Rect(Decimal(str(table_inline)), source_bounds.block,
                    Decimal(str(table_inline_size)), source_bounds.block_size), "table"
    if extent == "timeline":
        return Rect(Decimal(str(timeline_inline)), source_bounds.block,
                    Decimal(str(timeline_inline_size)), source_bounds.block_size), "timeline"
    if extent == "both":
        return (Rect(Decimal(str(table_inline)), source_bounds.block,
                     Decimal(str(timeline_inline + timeline_inline_size - table_inline)), source_bounds.block_size),
                "review-surface")
    raise LayoutError("E_LAYOUT_BACKGROUND_EXTENT", "/layoutManifest/reviewSurface/backgroundExtents")


def _background_shape(*, base: SurfaceBaseGeometry, theme_tokens: Any, placement_id: str,
                      source_ref: str, semantic_id: str, source_bounds: Rect) -> ShapePlacement | None:
    role = semantic_binding(semantic_id).scene_role
    treatment, paint_order = theme_tokens.background(role)
    if treatment == "none":
        return None
    bounds, slot_id = _background_bounds(
        semantic_id=semantic_id,
        extent=base.layout_manifest.background_extents.get(semantic_id, ""),
        source_bounds=source_bounds, table_bounds=base.table_bounds,
        timeline_bounds=base.timeline_bounds)
    return ShapePlacement(placement_id, source_ref, "Rect", bounds, slot_id=slot_id,
                          paint_order=paint_order, semantic_id=semantic_id)


def compose_row_group_backgrounds(*, base: SurfaceBaseGeometry, rows: tuple[Any, ...],
                                  groups: tuple[GroupPlacement, ...], theme_tokens: Any,
                                  row_decoration: str, group_decoration: str) -> tuple[ShapePlacement, ...]:
    """Complete group bands/header accents and alternating row stripes in legacy order."""
    shapes: list[ShapePlacement] = []
    for index, group in enumerate(groups):
        banded = group_decoration in {"all", "alternate"} and (
            group_decoration == "all" or index % 2 == 0)
        group_shape = None
        if banded:
            group_shape = _background_shape(
                base=base, theme_tokens=theme_tokens, placement_id=f"group:{group.group_id}",
                source_ref=group.group_id, semantic_id="groupBand", source_bounds=group.content_bounds)
            if group_shape is not None:
                shapes.append(group_shape)
        # The group's own band includes its own header row; do not double tint it.
        if group.header_bounds is not None and (
            group_decoration == "none" or (banded and group_shape is None)
        ):
            shape = _background_shape(
                base=base, theme_tokens=theme_tokens,
                placement_id=f"group-header-band:{group.group_id}", source_ref=group.group_id,
                semantic_id="groupHeaderBand", source_bounds=group.header_bounds)
            if shape is not None:
                shapes.append(shape)
    if row_decoration == "alternate":
        for index, row in enumerate(rows):
            if index % 2 == 0:
                shape = _background_shape(
                    base=base, theme_tokens=theme_tokens, placement_id=f"row-band:{row.row_id}",
                    source_ref=row.row_id, semantic_id="rowBand", source_bounds=row.bounds)
                if shape is not None:
                    shapes.append(shape)
    return tuple(shapes)


def compose_calendar_backgrounds(*, base: SurfaceBaseGeometry, theme_tokens: Any,
                                 intervals: tuple[Any, ...]) -> tuple[ShapePlacement, ...]:
    """Complete ordered axis-derived calendar intervals as Theme-treated background shapes."""
    shapes = []
    for interval in intervals:
        timeline = base.timeline.bounds
        shape = _background_shape(
            base=base, theme_tokens=theme_tokens,
            placement_id=f"calendar-closed:{interval.day.isoformat()}",
            source_ref="project-calendar", semantic_id="calendarClosed",
            source_bounds=Rect(Decimal(str(interval.inline_start)), timeline.block,
                               Decimal(str(max(0.0, interval.inline_end - interval.inline_start))),
                               timeline.block_size))
        if shape is not None:
            shapes.append(shape)
    return tuple(shapes)


def replace_group_header_band(shapes: tuple[ShapePlacement, ...],
                              update: GroupHeaderExtentUpdate) -> tuple[ShapePlacement, ...]:
    """Purely replace an existing header-band extent when folded marks enlarge its host."""
    placement_id = f"group-header-band:{update.source.group_id}"
    return tuple(replace(shape, bounds=update.header_bounds) if shape.placement_id == placement_id else shape
                 for shape in shapes)


def validate_background_shapes(shapes: tuple[ShapePlacement, ...] | list[ShapePlacement],
                               theme_tokens: Any) -> None:
    """Reject compounded translucent fills, allowing only declared semantic overlays."""
    translucent = []
    for shape in shapes:
        if shape.semantic_id not in BACKGROUND_SEMANTIC_IDS:
            continue
        role = semantic_binding(shape.semantic_id).scene_role
        treatment, _ = theme_tokens.background(role)
        if treatment == "fill" and theme_tokens.opacity(role) < 1:
            translucent.append(shape)
    for index, shape in enumerate(translucent):
        for other in translucent[index + 1:]:
            if (shape.source_ref == other.source_ref
                    and {shape.semantic_id, other.semantic_id} == {"groupBand", "groupHeaderBand"}):
                continue
            if _is_later_overlay(shape, other, theme_tokens):
                continue
            if _is_later_overlay(other, shape, theme_tokens):
                continue
            if intersects(shape.bounds, other.bounds):
                raise LayoutError("E_LAYOUT_BACKGROUND_OVERLAP",
                                  "/layoutManifest/reviewSurface/backgroundExtents",
                                  detail=f"{shape.placement_id}:{other.placement_id}")


# The one explicit relation under which translucent backgrounds may intersect: a later-painted overlay over an
# earlier background of strictly lower rank. Row, group and header bands come first, a named period (#582)
# next, the calendar closure last; nothing else is allowed by default.
_OVERLAY_RANK = {"rowBand": 0, "groupBand": 0, "groupHeaderBand": 0, "periodBand": 1, "calendarClosed": 2}


def _is_later_overlay(upper: ShapePlacement, lower: ShapePlacement, theme_tokens: Any) -> bool:
    """Permit a later-painted translucent overlay over a background of lower rank."""
    if (upper.semantic_id not in _OVERLAY_RANK or lower.semantic_id not in _OVERLAY_RANK
            or _OVERLAY_RANK[upper.semantic_id] <= _OVERLAY_RANK[lower.semantic_id]):
        return False
    upper_role = semantic_binding(upper.semantic_id).scene_role
    lower_role = semantic_binding(lower.semantic_id).scene_role
    upper_treatment, upper_order = theme_tokens.background(upper_role)
    lower_treatment, lower_order = theme_tokens.background(lower_role)
    return (upper_treatment == "fill" and lower_treatment == "fill"
            and upper_order == upper.paint_order
            and lower_order == lower.paint_order
            and upper_order > lower_order)
