"""Owns Theme-treated background geometry; reads completed extents and ordered calendar intervals."""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Any

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.surface_base import SurfaceBaseGeometry
from chrona.presentation.layout.surface_geometry import BACKGROUND_PAINT_ORDER, extend_to_plot_edges
from chrona.presentation.layout.surface_groups import (
    GroupHeaderExtentUpdate, SurfaceGroupPresentation, group_tab_bounds, group_tag_bounds, resolve_group_tab,
)
from chrona.presentation.layout.surface_quality import GroupPlacement, ShapePlacement, intersects
from chrona.presentation.model.semantic_registry import axis_band_semantic_ids, semantic_binding

BACKGROUND_SEMANTIC_IDS = frozenset({
    "rowBand", "groupBand", "groupHeaderBand", "groupTab", "calendarClosed", "calendarException", "periodBand", *axis_band_semantic_ids(),
})


def _background_bounds(*, semantic_id: str, extent: str, source_bounds: Rect,
                       table_bounds: tuple[float, float, float, float],
                       timeline_bounds: tuple[float, float, float, float],
                       text_bounds: Rect | None = None,
                       trailing_inset: Decimal = Decimal(0)) -> tuple[Rect, str]:
    """Resolve one finite source background extent without exposing coordinates to View."""
    if semantic_id in {"calendarClosed", "calendarException"}:
        if extent != "timeline":
            raise LayoutError("E_LAYOUT_BACKGROUND_EXTENT", "/layoutManifest/reviewSurface/backgroundExtents")
        return source_bounds, "timeline"
    table_inline, _, table_inline_size, _ = table_bounds
    timeline_inline, _, timeline_inline_size, _ = timeline_bounds
    if extent == "text" and semantic_id == "groupHeaderBand":
        if text_bounds is None:
            raise LayoutError("E_LAYOUT_BACKGROUND_EXTENT", "/layoutManifest/reviewSurface/backgroundExtents",
                              detail="groupHeaderBand:text requires completed header-content bounds")
        table_start = Decimal(str(table_inline))
        table_end = table_start + Decimal(str(table_inline_size))
        left = min(table_end, max(table_start, text_bounds.inline))
        right = min(table_end, max(left, text_bounds.inline + text_bounds.inline_size + trailing_inset))
        return Rect(left, source_bounds.block, right - left, source_bounds.block_size), "table"
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
                      source_ref: str, semantic_id: str, source_bounds: Rect,
                      extent_semantic: str | None = None,
                      text_bounds: Rect | None = None,
                      trailing_inset: Decimal = Decimal(0)) -> ShapePlacement | None:
    role = semantic_binding(semantic_id).scene_role
    treatment, paint_order = theme_tokens.background(role)
    if treatment == "none":
        return None
    bounds, slot_id = _background_bounds(
        semantic_id=semantic_id,
        extent=base.layout_manifest.background_extents.get(extent_semantic or semantic_id, ""),
        source_bounds=source_bounds, table_bounds=base.table_bounds,
        timeline_bounds=base.timeline_bounds, text_bounds=text_bounds, trailing_inset=trailing_inset)
    return ShapePlacement(placement_id, source_ref, "Rect", bounds, slot_id=slot_id,
                          paint_order=paint_order, semantic_id=semantic_id)


def compose_row_group_backgrounds(*, base: SurfaceBaseGeometry, rows: tuple[Any, ...],
                                  groups: tuple[GroupPlacement, ...], theme_tokens: Any,
                                  group_presentation: SurfaceGroupPresentation,
                                  row_decoration: str, group_decoration: str) -> tuple[ShapePlacement, ...]:
    """Complete group bands/header accents and the selected row decoration."""
    shapes: list[ShapePlacement] = []
    header_content_bounds = dict(group_presentation.header_content_bounds)
    header_trailing_insets = dict(group_presentation.header_band_trailing_insets)
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
                semantic_id="groupHeaderBand", source_bounds=group.header_bounds,
                text_bounds=header_content_bounds.get(group.group_id),
                trailing_inset=header_trailing_insets.get(group.group_id, Decimal(0)))
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
    elif row_decoration == "rules":
        if not theme_tokens.has_role("row-rule"):
            raise LayoutError("E_THEME_ROLE_REQUIRED", "/body/backgroundDecoration/rows",
                              detail="rules need Theme role /body/roles/row-rule")
        for shape in shapes:
            if shape.semantic_id not in {"rowBand", "groupBand", "groupHeaderBand"}:
                continue
            role = semantic_binding(shape.semantic_id).scene_role
            if shape.paint_order >= 10:
                raise LayoutError("E_LAYOUT_ROW_RULE_ORDER", "/body/backgroundDecoration/rows",
                                  detail=f"{shape.placement_id}: role={role}, order={shape.paint_order}; required <10")
        table_inline, _, _, _ = base.table_bounds
        timeline_inline, _, timeline_inline_size, _ = base.timeline_bounds
        right = timeline_inline + timeline_inline_size
        left_decimal, right_decimal = Decimal(str(table_inline)), Decimal(str(right))
        for row in rows:
            bottom = row.bounds.block + row.bounds.block_size
            shapes.append(ShapePlacement(
                f"row-rule:{row.row_id}", row.row_id, "Path",
                Rect(left_decimal, bottom, right_decimal - left_decimal, Decimal(0)),
                ((float(left_decimal), float(bottom)), (float(right_decimal), float(bottom))),
                slot_id="review-surface", paint_order=BACKGROUND_PAINT_ORDER, semantic_id="rowRule"))
    return tuple(shapes)


def compose_group_tabs(*, groups: tuple[GroupPlacement, ...], theme_tokens: Any,
                       tag_column: tuple[float, float] | None = None) -> tuple[ShapePlacement, ...]:
    """Complete one tab Rect per group header from the Theme `group-tab` role (#882); none without the role."""
    tab = resolve_group_tab(theme_tokens)
    if tab is None:
        return ()
    _, paint_order = theme_tokens.background(semantic_binding("groupTab").scene_role)
    if tab.target == "tag":
        if tag_column is None:
            return ()
        return tuple(ShapePlacement(f"group-tab:{group.group_id}", group.group_id, "Rect",
                                    group_tag_bounds(tab, tag_column, group.content_bounds),
                                    slot_id="review-surface", paint_order=paint_order, semantic_id="groupTab")
                     for group in groups if group.group_id)
    # The header spans table and timeline, so the tab shares the review-surface slot of a `both` band.
    return tuple(ShapePlacement(f"group-tab:{group.group_id}", group.group_id, "Rect",
                                group_tab_bounds(tab, group.header_bounds), slot_id="review-surface",
                                paint_order=paint_order, semantic_id="groupTab")
                 for group in groups if group.header_bounds is not None)


def compose_calendar_backgrounds(*, base: SurfaceBaseGeometry, theme_tokens: Any,
                                 intervals: tuple[Any, ...]) -> tuple[ShapePlacement, ...]:
    """Complete ordered axis-derived calendar intervals as Theme-treated background shapes."""
    shapes = []
    for interval in intervals:
        plot = base.plot
        left, right = extend_to_plot_edges(interval.inline_start, interval.inline_end, scale=base.scale, plot=plot)
        # An exception day takes its own role only where the Theme declares one with a background (#991); the
        # closed-day role keeps every other day, and every day of a Theme without it.
        own = (getattr(interval, "exception", False)
               and theme_tokens.optional_background(semantic_binding("calendarException").scene_role) is not None)
        shape = _background_shape(
            base=base, theme_tokens=theme_tokens,
            placement_id=f"calendar-{'exception' if own else 'closed'}:{interval.day.isoformat()}",
            source_ref="project-calendar", semantic_id="calendarException" if own else "calendarClosed",
            extent_semantic="calendarClosed",
            source_bounds=Rect(Decimal(str(left)), plot.block, Decimal(str(max(0.0, right - left))),
                               plot.block_size))
        if shape is not None:
            shapes.append(shape)
    return tuple(shapes)


def replace_group_header_band(shapes: tuple[ShapePlacement, ...],
                              update: GroupHeaderExtentUpdate, *, extent: str = "both") -> tuple[ShapePlacement, ...]:
    """Purely replace an existing header-band extent when folded marks enlarge its host."""
    placement_id = f"group-header-band:{update.source.group_id}"
    def completed_bounds(shape: ShapePlacement) -> Rect:
        if extent == "text":
            return Rect(shape.bounds.inline, update.header_bounds.block,
                        shape.bounds.inline_size, update.header_bounds.block_size)
        return update.header_bounds
    return tuple(replace(shape, bounds=completed_bounds(shape)) if shape.placement_id == placement_id else shape
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
_OVERLAY_RANK = {"rowBand": 0, "groupBand": 0, "groupHeaderBand": 0, "periodBand": 1, "calendarClosed": 2, "calendarException": 2}


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
