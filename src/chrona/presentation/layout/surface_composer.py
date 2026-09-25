"""Complete shared surface geometry before Scene primitive projection."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from collections.abc import Mapping
import re
from typing import Any

from chrona.presentation.layout.model import LayoutError, LayoutManifest, Rect, geometry_sum
from chrona.presentation.model.semantic_registry import REQUIRED_SLOTS, semantic_binding
from chrona.presentation.model.projection import shared_track_member_key
from chrona.presentation.layout.presentation import MarkGeometry, TrackPlacement, mark_bounds, place_mark_tracks, place_rows, place_table_columns, required_row_block_extents
from chrona.presentation.layout.axis import axis_intervals, axis_label_fits, format_axis_tier_label, thinning_schedule
from chrona.presentation.layout.text import ellipsize_text, measure_text_width, metric_for_family, metric_for_role, paint_text, place_text, wrap_text
from chrona.presentation.layout.annotations import (
    nearest_box_port, place_annotation_rail, project_annotation_box,
    resolve_annotation_anchor, route_annotation_leader,
)
from chrona.presentation.layout.comparison_marks import ComparisonMark
from chrona.presentation.layout.labels import LabelObstacle, LabelRect, LabelRequest, place_label
from chrona.presentation.layout.relation_terminals import marker_geometry
from chrona.presentation.layout.routing import place_relation_route, relation_route_quality
from chrona.presentation.layout.path_geometry import open_span_path, rounded_diamond_path, rounded_orthogonal_path
from chrona.presentation.layout.surface_quality import (
    AxisIntervalOutcome, AxisTierOutcome, CollisionDomain, ColumnPlacement, FitWarning, GroupPlacement, MarkPlacement, PlacementDecision, RelationPlacement, RowPlacement, ScalePlacement,
    IconPlacement, ShapePlacement, SlotPlacement, SurfacePlacement, SurfaceLayoutRequest, annotation_presentation, intersects,
)


@dataclass(frozen=True)
class SurfaceLayoutComposition:
    """Completed common surface geometry and the semantic rows it was derived from."""

    placement: SurfacePlacement
    review_rows: tuple[Any, ...]
    track_placements: tuple[TrackPlacement, ...]


MARK_GEOMETRY_ROLES = ("planned", "actual", "snapshot", "scenario", "missing-actual")
BACKGROUND_SEMANTIC_IDS = frozenset({"rowBand", "groupBand", "groupHeaderBand", "calendarClosed"})
# Layout emits coordinates at micro-point precision.  Intermediate measurement
# APIs are float-based, so containment must not turn a sub-micro-point binary
# conversion residue into a user-visible overflow diagnostic.
GEOMETRY_TOLERANCE = Decimal("0.000001")


def _background_bounds(*, semantic_id: str, extent: str, source_bounds: Rect, table_bounds: tuple[float, float, float, float],
                       timeline_bounds: tuple[float, float, float, float]) -> tuple[Rect, str]:
    """Resolve one finite background extent without exposing coordinates to View."""
    if semantic_id == "calendarClosed":
        if extent != "timeline":
            raise LayoutError("E_LAYOUT_BACKGROUND_EXTENT", "/layoutManifest/reviewSurface/backgroundExtents")
        _, timeline_block, _, timeline_block_size = timeline_bounds
        return (Rect(source_bounds.inline, Decimal(str(timeline_block)), source_bounds.inline_size,
                     Decimal(str(timeline_block_size)),), "timeline")
    table_inline, _, table_inline_size, _ = table_bounds
    timeline_inline, _, timeline_inline_size, _ = timeline_bounds
    if extent == "table":
        return Rect(Decimal(str(table_inline)), source_bounds.block, Decimal(str(table_inline_size)), source_bounds.block_size), "table"
    if extent == "timeline":
        return Rect(Decimal(str(timeline_inline)), source_bounds.block, Decimal(str(timeline_inline_size)), source_bounds.block_size), "timeline"
    if extent == "both":
        return (Rect(Decimal(str(table_inline)), source_bounds.block,
                     Decimal(str(timeline_inline + timeline_inline_size - table_inline)), source_bounds.block_size),
                "review-surface")
    raise LayoutError("E_LAYOUT_BACKGROUND_EXTENT", "/layoutManifest/reviewSurface/backgroundExtents")


def _validate_background_shapes(shapes: list[ShapePlacement], theme_tokens: Any) -> None:
    """Reject completed translucent background fills that would compound."""
    translucent: list[ShapePlacement] = []
    for shape in shapes:
        if shape.semantic_id not in BACKGROUND_SEMANTIC_IDS:
            continue
        role = semantic_binding(shape.semantic_id).scene_role
        treatment, _ = theme_tokens.background(role)
        if treatment == "fill" and theme_tokens.opacity(role) < 1:
            translucent.append(shape)
    for index, shape in enumerate(translucent):
        for other in translucent[index + 1:]:
            if intersects(shape.bounds, other.bounds):
                raise LayoutError("E_LAYOUT_BACKGROUND_OVERLAP", "/layoutManifest/reviewSurface/backgroundExtents",
                                  detail=f"{shape.placement_id}:{other.placement_id}")


def _contains_block_interval(*, container_start: Decimal, container_end: Decimal,
                             item_start: Decimal, item_end: Decimal) -> bool:
    """Apply the Layout coordinate tolerance to a physical containment test."""
    return item_start >= container_start - GEOMETRY_TOLERANCE and item_end <= container_end + GEOMETRY_TOLERANCE


def _completed_canvas(*, requested: Rect, rectangles: tuple[Rect, ...],
                      paths: tuple[tuple[tuple[float, float], ...], ...]) -> Rect:
    """Expand the requested canvas to contain Layout's completed geometry.

    A requested viewport is a minimum allocation.  This deliberately lives in
    the composition layer rather than in Scene or a renderer: every target
    receives the identical, already-completed extent.
    """
    inline_end = requested.inline + requested.inline_size
    block_end = requested.block + requested.block_size
    for bounds in rectangles:
        inline_end = max(inline_end, bounds.inline + bounds.inline_size)
        block_end = max(block_end, bounds.block + bounds.block_size)
    for points in paths:
        for inline, block in points:
            inline_end = max(inline_end, Decimal(str(inline)))
            block_end = max(block_end, Decimal(str(block)))
    return Rect(requested.inline, requested.block,
                inline_end - requested.inline, block_end - requested.block)


def resolve_mark_geometries(theme_tokens: Any) -> dict[str, MarkGeometry]:
    """Close every comparison-mark role to lane-relative Layout geometry."""
    result = {}
    for role in MARK_GEOMETRY_ROLES:
        height, offset, paint_order, corner_radius = theme_tokens.mark_geometry(role)
        result[role] = MarkGeometry(float(height), float(offset), paint_order, float(corner_radius))
    return result


def timeline_content_block_requirement(*, projection: Any, group_presentation: str,
                                       metric_values: dict[str, Decimal], role_geometries: dict[str, MarkGeometry] | None = None) -> Decimal:
    """Return the minimum timeline block extent for explicit review rows."""
    rows = projection.rows or tuple(
        type("_Row", (), {"group_id": item.group_id, "items": (item,)})()
        for item in projection.items
    )
    requirements = required_row_block_extents(
        review_rows=tuple(rows), row_minimum=float(metric_values["timeline.row.minBlockSize"]),
        row_padding=float(metric_values["timeline.row.paddingBlock"]),
        mark_block_size=float(metric_values["timeline.mark.blockSize"]), role_geometries=role_geometries,
    )
    headers = 0
    previous = object()
    for row in rows:
        if row.group_id != previous:
            headers += 1 if row.group_id and group_presentation == "header" else 0
            previous = row.group_id
    return Decimal(str(geometry_sum(requirements))) + Decimal(headers) * metric_values.get("timeline.groupHeader.blockSize", 0)


def progress_fill_bounds(host: Rect, fraction: float) -> Rect | None:
    """Return the optional completed progress submark bounds for one host mark."""
    if not 0 <= fraction <= 1:
        raise LayoutError("E_PRESENTATION_PROGRESS_INVALID", "/progressFill")
    if fraction == 0:
        return None
    return Rect(host.inline, host.block, host.inline_size * Decimal(str(fraction)), host.block_size)


def relation_label_content(relation: Any) -> str:
    """Format only selected, non-zero relation facts before measured placement."""
    parts: list[str] = []
    if "endpointPair" in relation.label_content:
        parts.append(f"{relation.source_endpoint}->{relation.target_endpoint}")
    if "lag" in relation.label_content:
        raw = relation.lag.get("value") if isinstance(relation.lag, Mapping) else relation.lag
        value = str(raw)
        if all(int(component) == 0 for component in re.findall(r"-?\d+", value)):
            value = ""
        elif value and value[0] not in "+-":
            value = "+" + value
        if value:
            parts.append(value + (f" [{relation.lag_calendar}]" if relation.lag_calendar else ""))
    return " ".join(parts)


def relation_label_anchor(points: tuple[tuple[float, float], ...]) -> LabelRect:
    """Choose the first longest route segment; ties retain canonical route order."""
    left, right = max(zip(points, points[1:]), key=lambda pair: abs(pair[1][0] - pair[0][0]) + abs(pair[1][1] - pair[0][1]))
    x1, y1 = left
    x2, y2 = right
    return LabelRect(min(x1, x2), min(y1, y2), max(1.0, abs(x2 - x1)), max(1.0, abs(y2 - y1)))


def resolve_text_visual_requests(text: list[Any], request: SurfaceLayoutRequest, *,
                                 handled_sources: set[str] | None = None,
                                 axis_label_targets: Mapping[tuple[str, str, str], str] | None = None) -> tuple[list[Any], list[IconPlacement]]:
    """Turn already-resolved View visual intents into completed Layout geometry.

    The caller supplies only placement identities; target vocabulary translation
    remains at the typed View boundary.  This helper deliberately has no Scene,
    Theme lookup, or catalog lookup dependency.
    """
    handled_sources = handled_sources or set()
    requested: dict[str, dict[str, Any]] = {}
    occupied: set[tuple[str, str]] = set()
    for visual in request.visual_requests:
        if visual.target_kind == "mark" or visual.source_ref in handled_sources:
            continue
        selector = dict(visual.selector)
        if visual.target_kind == "axis-band":
            continue
        axis_key = (visual.target_kind, selector.get("level", ""), selector.get("index", ""))
        placement_id = (selector.get("placementId") or (axis_label_targets or {}).get(axis_key)
                        or visual_target_placement_id(visual.target_kind, selector))
        key = (placement_id, visual.side)
        if key in occupied:
            raise LayoutError("E_LAYOUT_VISUAL_DUPLICATE", visual.source_ref)
        occupied.add(key)
        if visual.ref is None:
            raise LayoutError("E_LAYOUT_VISUAL_TARGET", visual.source_ref)
        requested.setdefault(placement_id, {})[visual.side] = visual
    icons: list[IconPlacement] = []
    for placement_id, by_side in requested.items():
        matches = [item for item in text if item.placement_id == placement_id
                   and item.overflow != "suppressed"]
        if len(matches) != 1:
            raise LayoutError("E_LAYOUT_VISUAL_TARGET", next(iter(by_side.values())).source_ref)
    for index, item in enumerate(text):
        by_side = requested.pop(item.placement_id, None)
        if not by_side or item.overflow == "suppressed":
            continue
        item_metrics = metric_for_family(item.font_family, item.font_weight, request.font_metrics)
        resolved: dict[str, tuple[Any, float, float]] = {}
        for side, visual in by_side.items():
            icon = request.icon_assets.get(visual.ref)
            if icon is None:
                raise LayoutError("E_ICON_NAME_UNKNOWN", visual.source_ref)
            try:
                scale, gap_ratio = request.theme_tokens.icon_ratios(item.typography_role)
            except Exception as error:
                raise LayoutError("E_THEME_ICON_RATIO", visual.source_ref) from error
            height = item.font_size * float(scale)
            if height <= 0 or icon.viewport[1] <= 0:
                raise LayoutError("E_LAYOUT_REQUIRED_OVERFLOW", visual.source_ref)
            resolved[side] = (icon, height * icon.viewport[0] / icon.viewport[1], item.font_size * float(gap_ratio))
        leading = geometry_sum(width + gap for side, (_, width, gap) in resolved.items() if side == "leading")
        trailing = geometry_sum(width + gap for side, (_, width, gap) in resolved.items() if side == "trailing")
        available = (item.available_inline_size if item.available_inline_size is not None
                     else float(item.bounds.inline_size)) - leading - trailing
        if available <= 0:
            raise LayoutError("E_LAYOUT_REQUIRED_OVERFLOW", next(iter(by_side.values())).source_ref)
        source = item.source_content if item.source_content is not None else item.content
        if len(item.lines) > 1:
            lines = wrap_text(source, available_inline=available, font_size=item.font_size, font_metrics=item_metrics,
                              letter_spacing=item.letter_spacing, text_transform=item.text_transform)
            content, overflow = "\n".join(lines), item.overflow
        elif item.source_content is not None:
            content = ellipsize_text(source, available_inline=available, font_size=item.font_size, font_metrics=item_metrics,
                                     letter_spacing=item.letter_spacing, text_transform=item.text_transform)
            lines, overflow = (content,), "ellipsized" if content != source else "fit"
        elif measure_text_width(source, font_size=item.font_size, font_metrics=item_metrics,
                                letter_spacing=item.letter_spacing, text_transform=item.text_transform) <= available:
            content, lines, overflow = source, (source,), item.overflow
        else:
            raise LayoutError("E_LAYOUT_REQUIRED_OVERFLOW", next(iter(by_side.values())).source_ref)
        width = max(measure_text_width(line, font_size=item.font_size, font_metrics=item_metrics,
                                       letter_spacing=item.letter_spacing, text_transform=item.text_transform) for line in lines)
        baseline = item.baseline
        if baseline is None or not hasattr(item_metrics, "cap_height_at"):
            raise LayoutError("E_FONT_METRICS_CAP_HEIGHT", next(iter(by_side.values())).source_ref)
        available_start = (item.available_inline_start if item.available_inline_start is not None
                           else float(item.bounds.inline))
        shifted_baseline = (available_start + leading, baseline[1])
        painted_lines = tuple(paint_text(line, text_transform=item.text_transform) for line in lines)
        text[index] = replace(item, content=paint_text(content, text_transform=item.text_transform),
                              lines=painted_lines, overflow=overflow,
                              bounds=Rect(Decimal(str(shifted_baseline[0])), item.bounds.block,
                                          Decimal(str(width)), Decimal(str(item.font_size * item.line_height * len(lines)))),
                              baseline=shifted_baseline)
        cap_height = float(item_metrics.cap_height_at(item.font_size))
        for side, visual in by_side.items():
            icon, icon_width, gap = resolved[side]
            inline = (available_start if side == "leading"
                      else available_start + leading + available + trailing - gap - icon_width)
            bounds = Rect(Decimal(str(inline)), Decimal(str(baseline[1] - cap_height + (cap_height - item.font_size * float(request.theme_tokens.icon_ratios(item.typography_role)[0])) / 2)),
                          Decimal(str(icon_width)), Decimal(str(item.font_size * float(request.theme_tokens.icon_ratios(item.typography_role)[0]))) )
            icons.append(IconPlacement(f"visual:{item.placement_id}:{side}", item.source_ref, visual.source_ref,
                                       icon.icon_id, icon.kind, icon.content_identity, icon.viewport, icon.payload, icon.alternative,
                                       visual.decorative, bounds, "labelVisual", icon_width / icon.viewport[0], item.slot_id))
    if requested:
        raise LayoutError("E_LAYOUT_VISUAL_TARGET", next(iter(next(iter(requested.values())).values())).source_ref)
    return text, icons


def resolve_mark_visual_requests(marks: list[MarkPlacement], request: SurfaceLayoutRequest) -> list[IconPlacement]:
    """Project the closed View mark target onto one completed planned/actual mark."""
    icons: list[IconPlacement] = []
    occupied: set[str] = set()
    for visual in request.visual_requests:
        if visual.target_kind != "mark":
            continue
        placement_id = visual_target_placement_id("mark", dict(visual.selector))
        if placement_id in occupied:
            raise LayoutError("E_LAYOUT_VISUAL_DUPLICATE", visual.source_ref)
        occupied.add(placement_id)
        # Row-instance identifiers extend the closed object/facet family after
        # the stable View selector; the selector itself never guesses an
        # instance suffix.
        mark = [item for item in marks if item.placement_id == placement_id
                or item.placement_id.startswith(placement_id + ":")]
        icon = request.icon_assets.get(visual.ref or "")
        if len(mark) != 1 or icon is None:
            raise LayoutError("E_LAYOUT_VISUAL_TARGET" if len(mark) != 1 else "E_ICON_NAME_UNKNOWN", visual.source_ref)
        host = mark[0]
        try:
            scale, _ = request.theme_tokens.icon_ratios("icon-mark")
        except Exception as error:
            raise LayoutError("E_THEME_ICON_RATIO", visual.source_ref) from error
        height = float(host.bounds.block_size) * float(scale)
        if height <= 0:
            raise LayoutError("E_LAYOUT_REQUIRED_OVERFLOW", visual.source_ref)
        width = min(float(host.bounds.inline_size), height * icon.viewport[0] / icon.viewport[1])
        bounds = Rect(host.bounds.inline + (host.bounds.inline_size - Decimal(str(width))) / 2,
                      host.bounds.block + (host.bounds.block_size - Decimal(str(height))) / 2,
                      Decimal(str(width)), Decimal(str(height)))
        icons.append(IconPlacement(f"visual:{host.placement_id}", host.source_ref, visual.source_ref,
                                   icon.icon_id, icon.kind, icon.content_identity, icon.viewport, icon.payload, icon.alternative,
                                   visual.decorative, bounds, "iconMark", width / icon.viewport[0], host.slot_id))
    return icons


def resolve_axis_band_visual_requests(shapes: list[ShapePlacement], request: SurfaceLayoutRequest,
                                      targets: Mapping[tuple[str, str, str], str]) -> list[IconPlacement]:
    """Place a band-targeted icon from typed axis metadata, never an ID parser."""
    icons: list[IconPlacement] = []
    for visual in request.visual_requests:
        if visual.target_kind != "axis-band":
            continue
        selector = dict(visual.selector)
        placement_id = targets.get(("axis-band", selector.get("level", ""), selector.get("index", "")))
        shape = next((item for item in shapes if item.placement_id == placement_id), None)
        icon = request.icon_assets.get(visual.ref or "")
        if shape is None or icon is None:
            raise LayoutError("E_LAYOUT_VISUAL_TARGET" if shape is None else "E_ICON_NAME_UNKNOWN", visual.source_ref)
        scale, _ = request.theme_tokens.icon_ratios("icon-mark")
        height = min(float(shape.bounds.inline_size), float(shape.bounds.block_size)) * float(scale)
        if height <= 0 or icon.viewport[1] <= 0:
            raise LayoutError("E_LAYOUT_REQUIRED_OVERFLOW", visual.source_ref)
        width = height * icon.viewport[0] / icon.viewport[1]
        bounds = Rect(shape.bounds.inline + (shape.bounds.inline_size - Decimal(str(width))) / 2,
                      shape.bounds.block + (shape.bounds.block_size - Decimal(str(height))) / 2,
                      Decimal(str(width)), Decimal(str(height)))
        icons.append(IconPlacement(f"visual:{shape.placement_id}", shape.source_ref, visual.source_ref,
                                   icon.icon_id, icon.kind, icon.content_identity, icon.viewport, icon.payload,
                                   icon.alternative, visual.decorative, bounds, "iconMark", width / icon.viewport[0], shape.slot_id))
    return icons


def candidate_label_visuals(placement_id: str, typography_role: str,
                            request: SurfaceLayoutRequest) -> tuple[tuple[Any, Any, float, float], ...]:
    """Resolve visual advances before a candidate-label solver chooses bounds."""
    return resolve_label_visual_advances(
        placement_id, typography_role, visual_requests=request.visual_requests,
        icon_assets=request.icon_assets, theme_tokens=request.theme_tokens,
    )


def resolve_label_visual_advances(placement_id: str, typography_role: str, *,
                                  visual_requests: tuple[Any, ...], icon_assets: dict[str, Any],
                                  theme_tokens: Any) -> tuple[tuple[Any, Any, float, float], ...]:
    """Resolve the closed inline advance of label visuals in Layout.

    Source measurement and final placement call this same resolver. That keeps
    an icon's aspect ratio, role scale, and role gap out of the render use case
    and prevents a solver from allocating text bounds that final composition
    cannot honor.
    """
    matching = []
    for visual in visual_requests:
        if visual.target_kind in {"mark", "axis-band", "axis-label"}:
            continue
        target = visual_target_placement_id(visual.target_kind, dict(visual.selector))
        if placement_id == target or placement_id.startswith(target + ":"):
            matching.append(visual)
    if not matching:
        return ()
    found: dict[str, tuple[Any, Any, float, float]] = {}
    size = theme_tokens.text_treatment(typography_role).font_size
    try:
        scale, gap_ratio = theme_tokens.icon_ratios(typography_role)
    except Exception as error:
        raise LayoutError("E_THEME_ICON_RATIO", "/body/visuals") from error
    for visual in matching:
        if visual.side in found:
            raise LayoutError("E_LAYOUT_VISUAL_DUPLICATE", visual.source_ref)
        icon = icon_assets.get(visual.ref or "")
        if icon is None or icon.viewport[1] <= 0:
            raise LayoutError("E_ICON_NAME_UNKNOWN", visual.source_ref)
        height = float(size * scale)
        if height <= 0:
            raise LayoutError("E_LAYOUT_REQUIRED_OVERFLOW", visual.source_ref)
        found[visual.side] = (visual, icon, height * icon.viewport[0] / icon.viewport[1], float(size * gap_ratio))
    return tuple(found[side] for side in ("leading", "trailing") if side in found)


def visual_target_placement_id(kind: str, selector: dict[str, str]) -> str:
    """Map the closed View target vocabulary to one Layout placement identity."""
    if kind == "title": return "title"
    if kind == "column" and "id" in selector: return f"column:{selector['id']}"
    if kind == "cell" and {"object", "column"} <= selector.keys(): return f"cell:{selector['object']}:{selector['column']}"
    if kind == "group-header" and "id" in selector: return f"group-header:{selector['id']}"
    if kind == "plot-label" and "id" in selector: return f"member-label:{selector['id']}"
    if kind == "annotation" and "id" in selector: return f"annotation-text:{selector['id']}"
    if kind == "note" and "id" in selector: return f"note:{selector['id']}"
    if kind == "note-index" and "id" in selector: return f"note-index:{selector['id']}"
    if kind == "group-detail" and "id" in selector: return f"group-detail:{selector['id']}"
    if kind == "legend" and "role" in selector: return f"legend:{selector['role']}"
    if kind == "summary" and "panel" in selector and "metric" not in selector: return f"summary:{selector['panel']}"
    if kind == "summary" and {"panel", "metric", "part"} <= selector.keys(): return f"summary:{selector['panel']}:{selector['metric']}:{selector['part']}"
    if kind == "milestone" and "id" in selector: return f"milestone:{selector['id']}"
    if kind == "as-of-label": return "as-of-label"
    if kind == "variance-label" and "object" in selector: return f"variance:{selector['object']}"
    if kind == "mark" and {"object", "facet"} <= selector.keys(): return f"{selector['facet']}:{selector['object']}"
    raise LayoutError("E_LAYOUT_VISUAL_TARGET", "/body/visuals")


def compose_surface_layout(request: SurfaceLayoutRequest) -> SurfaceLayoutComposition:
    """Resolve slots, rows, groups, temporal scale, and mark tracks in Layout."""
    projection = request.projection
    layout_manifest = request.layout_manifest
    measured_sources = request.measured_sources
    metric_values = getattr(measured_sources, "metric_values", None)
    if not isinstance(layout_manifest, LayoutManifest):
        raise LayoutError("E_PRESENTATION_LAYOUT_REQUIRED", "/layoutManifest")
    if not isinstance(metric_values, dict):
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources")
    decisions = {item.source: item for item in layout_manifest.decisions if item.source}
    required = tuple(slot.value for slot in REQUIRED_SLOTS)
    missing = next((name for name in required if name not in decisions), None)
    if missing is not None:
        raise LayoutError("E_PRESENTATION_PRIMITIVE_MISSING", f"/layoutManifest/sources/{missing}")
    start, end = projection.window
    if not isinstance(start, date) or not isinstance(end, date) or start >= end:
        raise LayoutError("E_PRESENTATION_PROJECTION_REQUIRED", "/projection/window")
    if ("timeline.row.minBlockSize" not in metric_values
            or "timeline.row.paddingBlock" not in metric_values
            or "timeline.mark.blockSize" not in metric_values):
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources/metricValues")
    slots = tuple(
        SlotPlacement(source, source, item.bounds, item.priority or "required",
                      item.overflow or "visible-overflow", "primary" if source in {"timeline", "timeline-axis"} else None)
        for source, item in sorted(decisions.items())
    )
    by_source = {slot.source_ref: slot for slot in slots}
    table = by_source["table"]
    timeline = by_source["timeline"]
    review_surface = SlotPlacement(
        "review-surface", "review-surface",
        Rect(table.bounds.inline, min(table.bounds.block, timeline.bounds.block),
             timeline.bounds.inline + timeline.bounds.inline_size - table.bounds.inline,
             max(table.bounds.block + table.bounds.block_size, timeline.bounds.block + timeline.bounds.block_size)
             - min(table.bounds.block, timeline.bounds.block)),
    )
    slots += (review_surface,)
    slot_ids = {slot.slot_id for slot in slots}

    def text_slot(item: Any) -> str:
        """Resolve a text host's Layout-owned slot before any visual uses it."""
        if item.slot_id in slot_ids:
            return item.slot_id
        if item.collision_domain.slot == "group-header":
            return table.slot_id
        raise LayoutError("E_LAYOUT_SLOT_OWNERSHIP_INVALID", item.placement_id)

    review_rows = projection.rows or tuple(
        type("_Row", (), {"row_id": item.object_id, "label": item.title, "group_id": item.group_id,
                            "table_subject_id": item.object_id, "items": (item,)})()
        for item in projection.items
    )
    timeline_bounds = _bounds(timeline.bounds)
    group_header_size = (float(metric_values["timeline.groupHeader.blockSize"])
                         if request.surface_content.group_presentation == "header" else 0.0)
    role_geometries = resolve_mark_geometries(request.theme_tokens)
    requirements = required_row_block_extents(
        review_rows=tuple(review_rows), row_minimum=float(metric_values["timeline.row.minBlockSize"]),
        row_padding=float(metric_values["timeline.row.paddingBlock"]),
        mark_block_size=float(metric_values["timeline.mark.blockSize"]), role_geometries=role_geometries,
    )
    raw_rows = place_rows(review_rows=tuple(review_rows), timeline_bounds=timeline_bounds,
                          group_header_size=group_header_size, required_block_sizes=requirements,
                          distribution=layout_manifest.row_distribution)
    rows = tuple(
        RowPlacement(item.row_id, item.table_subject_id, placement.group_id or "", _rect(placement.bounds),
                     depth=int(getattr(item, "depth", 0)))
        for item, placement in zip(review_rows, raw_rows, strict=True)
    )
    groups: list[GroupPlacement] = []
    table_bounds = _bounds(table.bounds)
    for row in rows:
        if groups and groups[-1].group_id == row.group_id:
            previous = groups[-1]
            content = Rect(previous.content_bounds.inline, previous.content_bounds.block,
                           previous.content_bounds.inline_size,
                           previous.content_bounds.block_size + row.bounds.block_size)
            groups[-1] = GroupPlacement(previous.group_id, content, previous.header_bounds)
        else:
            header = None
            if row.group_id and group_header_size:
                header = Rect(Decimal(str(table_bounds[0])), row.bounds.block - Decimal(str(group_header_size)),
                              Decimal(str(timeline_bounds[0] + timeline_bounds[2] - table_bounds[0])),
                              Decimal(str(group_header_size)))
            groups.append(GroupPlacement(row.group_id, row.bounds, header))
    if request.theme_tokens is None or request.font_metrics is None:
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources")
    def metric_for(typography_role: str) -> Any:
        return metric_for_role(request.theme_tokens, typography_role, request.font_metrics)
    body_treatment = request.theme_tokens.text_treatment("text")
    body_metrics = metric_for("text")
    body_size = float(body_treatment.font_size)
    title_input = measured_sources.inputs.get("title")
    title_measurement = measured_sources.measurements.get("title")
    if title_measurement is None:
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources/measurements/title")
    title = title_input.lines[0] if title_input and title_input.lines else ""
    text = [place_text(placement_id="title", source_ref="title", content=title,
                       inline=float(by_source["title"].bounds.inline),
                       baseline_block=float(by_source["title"].bounds.block) + float(title_measurement.first_baseline or 0),
                       typography_role="heading", theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                       collision_region="title", collision_domain=CollisionDomain("title", "content"),
                       source_content=title, available_inline_start=float(by_source["title"].bounds.inline),
                       available_inline_size=float(by_source["title"].bounds.inline_size))]
    table_columns = request.surface_content.table_columns
    table_cells = request.surface_content.table_cells
    def measure_table_text(content: str, typography_role: str, orientation: str = "horizontal") -> float:
        treatment = request.theme_tokens.text_treatment(typography_role)
        return (measure_text_width(content, font_size=float(treatment.font_size), font_metrics=metric_for(typography_role),
                                   letter_spacing=float(treatment.letter_spacing),
                                   text_transform=treatment.transform,
                                   numeric_spacing=treatment.numeric_spacing)
                if orientation == "horizontal" else float(treatment.font_size * treatment.line_height))
    columns = place_table_columns(columns=table_columns, cells=table_cells, bounds=table_bounds,
                                  measure_text=measure_table_text, minimum_inline=body_size,
                                  overflow=table.overflow,
                                  gutter=float(metric_values.get("table.column.gutter.inlineSize", 0)))
    positions = {item.column_id: (item.inline, item.inline_size) for item in columns}
    column_widths = {item.column_id: item.inline_size for item in columns}
    column_intents = {item.column_id: item for item in table_columns}

    def table_text(content: str, available_inline: float, typography_role: str) -> tuple[str, str]:
        if table.overflow != "ellipsize-with-source":
            return content, "fit"
        treatment = request.theme_tokens.text_treatment(typography_role)
        resolved = ellipsize_text(content, available_inline=available_inline, font_size=float(treatment.font_size),
                                  font_metrics=metric_for(typography_role), letter_spacing=float(treatment.letter_spacing),
                                  text_transform=treatment.transform,
                                  numeric_spacing=treatment.numeric_spacing)
        return resolved, "ellipsized" if resolved != content else "fit"

    def aligned_inline(content: str, column_id: str, start: float, available_inline: float,
                       typography_role: str, orientation: str = "horizontal") -> float:
        width = measure_table_text(content, typography_role, orientation)
        align = column_intents[column_id].align
        if align == "end":
            return start + max(0.0, available_inline - width)
        if align == "center":
            return start + max(0.0, (available_inline - width) / 2)
        return start

    for column in table_columns:
        column_id, label = column.column_id, column.header
        available = max(0.0, column_widths[column_id] - body_size)
        resolved, overflow = table_text(label, available, "text")
        header_width = measure_text_width(resolved, font_size=body_size, font_metrics=body_metrics,
                                          letter_spacing=float(body_treatment.letter_spacing),
                                          text_transform=body_treatment.transform,
                                          numeric_spacing=body_treatment.numeric_spacing)
        header_block = timeline_bounds[1] - table_bounds[1]
        if column.header_orientation == "rotate-cw":
            baseline = table_bounds[1]
        elif column.header_orientation == "rotate-ccw":
            baseline = table_bounds[1] + header_width
        else:
            baseline = table_bounds[1] + body_size
        text.append(place_text(placement_id=f"column:{column_id}", source_ref="view:tableColumns", content=resolved,
                               inline=aligned_inline(resolved, column_id, positions[column_id][0], available, "text", column.header_orientation), baseline_block=baseline,
                               typography_role="text", theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                               overflow=overflow, collision_region="table", collision_domain=CollisionDomain("table", "header"),
                               source_content=label, available_inline_start=positions[column_id][0],
                               available_inline_size=available, orientation=column.header_orientation))
        # A rotated header may need more block extent than its allocated table
        # header.  Its completed text remains visible; the warning and canvas
        # expansion are assembled with all other Layout geometry below.
    row_by_subject = {item.row_id: item for item in rows} | {item.object_id: item for item in rows}
    for cell in table_cells:
        object_id, column_id, content, typography_role = cell.object_id, cell.column_id, cell.content, cell.typography_role
        row = row_by_subject.get(object_id)
        position = positions.get(column_id)
        if row is not None and position is not None and column_id in column_intents:
            indent_token = metric_values.get("table.indent.inlineSize")
            if row.depth and indent_token is None:
                raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources/metricValues/table.indent.inlineSize")
            indent = ((body_size if row.group_id else 0) + float(indent_token or 0) * row.depth
                      if column_id == request.surface_content.table_hierarchy_column else 0)
            available = max(0.0, column_widths[column_id] - indent - body_size)
            resolved, overflow = table_text(content, available, typography_role)
            text.append(place_text(placement_id=f"cell:{object_id}:{column_id}", source_ref=object_id, content=resolved,
                                   inline=aligned_inline(resolved, column_id, position[0] + indent, available, typography_role),
                                   baseline_block=float(row.bounds.block + row.bounds.block_size / 2) + body_size / 2,
                                   typography_role=typography_role, theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                                   overflow=overflow, collision_region="table",
                                   collision_domain=CollisionDomain("table", f"row:{row.row_id}"), source_content=content,
                                   available_inline_start=position[0] + indent,
                                   available_inline_size=available, semantic_id=cell.semantic_id))
    labels = {row.group_id: next((item.group_label for item in review_row.items if item.group_label), row.group_id)
              for review_row, row in zip(review_rows, rows, strict=True) if row.group_id}
    for group in groups:
        if group.header_bounds is not None:
            text.append(place_text(placement_id=f"group-header:{group.group_id}", source_ref=group.group_id,
                                       content=labels[group.group_id], inline=float(group.header_bounds.inline),
                                       baseline_block=float(group.header_bounds.block) + body_size, typography_role="text",
                                   theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                                   collision_region=f"group:{group.group_id}",
                                   collision_domain=CollisionDomain("group-header", group.group_id),
                                   source_content=labels[group.group_id],
                                   available_inline_start=float(group.header_bounds.inline),
                                   available_inline_size=float(group.header_bounds.inline_size)))
    scale = ScalePlacement("table-timeline", "primary", start, end, timeline_bounds[0],
                           timeline_bounds[0] + timeline_bounds[2], timeline_bounds[0],
                           timeline_bounds[2] / max(1, (end - start).days))
    axis = by_source["timeline-axis"]
    axis_treatment = request.theme_tokens.text_treatment("axis")
    axis_metrics = metric_for("axis")
    axis_size = float(axis_treatment.font_size)
    shapes: list[ShapePlacement] = []
    axis_tier_outcomes: list[AxisTierOutcome] = []
    axis_decisions: list[PlacementDecision] = []
    axis_label_targets: dict[tuple[str, str, str], str] = {}
    axis_band_targets: dict[tuple[str, str, str], str] = {}
    diagnostics: list[str] = []
    visible_label_overflows: list[tuple[Any, LabelRect]] = []
    background_extents = layout_manifest.background_extents

    def background_shape(placement_id: str, source_ref: str, semantic_id: str, source_bounds: Rect) -> ShapePlacement:
        role = semantic_binding(semantic_id).scene_role
        _, paint_order = request.theme_tokens.background(role)
        bounds, slot_id = _background_bounds(semantic_id=semantic_id, extent=background_extents.get(semantic_id, ""), source_bounds=source_bounds,
                                             table_bounds=table_bounds, timeline_bounds=timeline_bounds)
        return ShapePlacement(placement_id, source_ref, "Rect", bounds, slot_id=slot_id,
                              paint_order=paint_order, semantic_id=semantic_id)

    decoration = request.surface_content.row_decoration
    if decoration == "alternate-rows":
        for index, row in enumerate(rows):
            if index % 2 == 0:
                shapes.append(background_shape(f"row-band:{row.row_id}", row.row_id, "rowBand", row.bounds))
    for index, group in enumerate(groups):
        if decoration in {"none", "alternate-groups"} and (decoration == "none" or index % 2 == 0):
            shapes.append(background_shape(f"group:{group.group_id}", group.group_id, "groupBand", group.content_bounds))
        if group.header_bounds is not None:
            shapes.append(background_shape(f"group-header-band:{group.group_id}", group.group_id,
                                           "groupHeaderBand", group.header_bounds))
    label_lane_offset = 0.0
    for tier_index, tier in enumerate(request.surface_content.axis_tiers):
        form = tier.label.form if tier.label else None
        requested_units = (tuple(candidate for candidate, _ in tier.label.candidate_forms)
                           if tier.unit == "auto" and tier.label else (tier.unit,))
        try:
            if tier.unit == "auto":
                selected = None
                forms = dict(tier.label.candidate_forms) if tier.label else {}
                for candidate in ("day", "week", "month", "quarter", "half", "year"):
                    if candidate not in forms:
                        continue
                    trial = axis_intervals(start, end, candidate, tick_step=tier.every,
                                           fiscal_start_month=request.surface_content.axis_fiscal_start_month)
                    fits_trial = all(axis_label_fits(content=format_axis_tier_label(item, forms[candidate], request.locale),
                                                      available_inline=(item.end - item.start).days * scale.unit_ratio,
                                                      font_size=axis_size, font_metrics=axis_metrics,
                                                      letter_spacing=float(axis_treatment.letter_spacing),
                                                      text_transform=axis_treatment.transform,
                                                      numeric_spacing=axis_treatment.numeric_spacing,
                                                      orientation=tier.label.orientation,
                                                      line_height=float(axis_treatment.line_height)) for item in trial)
                    if fits_trial or tier.label.overflow == "visible-overflow":
                        selected, form = trial, forms[candidate]
                        break
                if selected is None:
                    # An explicit thinning request is not a refusal mode.  If
                    # no candidate can be thinned legally, retain the first
                    # declared deterministic form as a visible overlap.
                    candidate = next(item for item in ("day", "week", "month", "quarter", "half", "year")
                                     if item in forms)
                    selected, form = axis_intervals(start, end, candidate, tick_step=tier.every,
                                                    fiscal_start_month=request.surface_content.axis_fiscal_start_month), forms[candidate]
                intervals = selected
            else:
                intervals = axis_intervals(start, end, tier.unit, tick_step=tier.every,
                                           fiscal_start_month=request.surface_content.axis_fiscal_start_month)
        except ValueError as error:
            raise LayoutError(str(error), "/view/body/axis/tiers") from error
        interval_outcomes: tuple[AxisIntervalOutcome, ...]
        if tier.role == "labels" and form is not None:
            interval_outcomes = tuple(
                AxisIntervalOutcome(f"axis-label:{tier_index}:{interval.index}", interval.start, interval.end,
                                    interval.natural_start, interval.natural_end,
                                    format_axis_tier_label(interval, form, request.locale),
                                    axis_label_fits(content=format_axis_tier_label(interval, form, request.locale),
                                                   available_inline=max(0.0, _coordinate(interval.end, scale) - _coordinate(interval.start, scale)),
                                                   font_size=axis_size, font_metrics=axis_metrics,
                                                   letter_spacing=float(axis_treatment.letter_spacing),
                                                   text_transform=axis_treatment.transform,
                                                   numeric_spacing=axis_treatment.numeric_spacing,
                                                   orientation=tier.label.orientation,
                                                   line_height=float(axis_treatment.line_height)))
                for interval in intervals
            )
            fits = tuple(bool(item.label_fits) for item in interval_outcomes)
            if not all(fits):
                if tier.label.overflow == "thin-with-record":
                    try:
                        schedule = thinning_schedule(fits)
                    except ValueError as error:
                        interval_outcomes = tuple(replace(item, disposition="placed") for item in interval_outcomes)
                    else:
                        retained = set(schedule.retained_positions)
                        resolved_outcomes: list[AxisIntervalOutcome] = []
                        for position, outcome in enumerate(interval_outcomes):
                            if position in retained:
                                resolved_outcomes.append(replace(outcome, disposition="placed"))
                            else:
                                reason = "label-does-not-fit" if not outcome.label_fits else "thinning-stride"
                                resolved_outcomes.append(replace(outcome, disposition="thinned", reason=reason))
                                diagnostics.append(f"W_LAYOUT_AXIS_LABEL_THINNED:{outcome.candidate_id}:{reason}")
                                axis_decisions.append(PlacementDecision(outcome.candidate_id, f"/view/body/axis/tiers/{tier_index}",
                                                                        ("thin-with-record", "suppress"), "suppress", "suppressed"))
                        interval_outcomes = tuple(resolved_outcomes)
                        diagnostics.append(f"W_LAYOUT_AXIS_DENSITY:axis-tier:{tier_index}:stride={schedule.stride}:phase={schedule.phase}")
                else:
                    interval_outcomes = tuple(replace(
                        item, disposition="placed",
                        reason=None if item.label_fits else "visible-overflow")
                        for item in interval_outcomes)
            else:
                interval_outcomes = tuple(replace(item, disposition="placed") for item in interval_outcomes)
        else:
            interval_outcomes = tuple(
                AxisIntervalOutcome(f"axis-tier:{tier_index}:{interval.index}", interval.start, interval.end,
                                    interval.natural_start, interval.natural_end)
                for interval in intervals
            )
        axis_tier_outcomes.append(AxisTierOutcome(
            tier_index, f"/view/body/axis/tiers/{tier_index}", tier.role, requested_units,
            intervals[0].level if intervals else (tier.unit if tier.unit != "auto" else ""), tier.every, form,
            interval_outcomes,
        ))
        if tier.role == "band":
            for interval in intervals:
                x, x2 = _coordinate(interval.start, scale), _coordinate(interval.end, scale)
                placement_id = f"axis-band-rect:{tier_index}:{interval.index}"
                axis_band_targets[("axis-band", interval.level, str(interval.index))] = placement_id
                shapes.append(ShapePlacement(placement_id, "timeline-axis", "Rect",
                                              Rect(Decimal(str(x)), axis.bounds.block, Decimal(str(max(0.0, x2 - x))), axis.bounds.block_size),
                                              semantic_id="axisBandDecoration"))
        elif tier.role in {"grid-major", "grid-minor"}:
            semantic_id = "axisGrid" if tier.role == "grid-major" else "axisGridMinor"
            for interval in intervals:
                x = _coordinate(interval.start, scale)
                shapes.append(ShapePlacement(f"axis-grid:{tier_index}:{interval.index}", "timeline-axis", "Path",
                                              Rect(Decimal(str(x)), timeline.bounds.block, Decimal(0), timeline.bounds.block_size),
                                              ((x, float(timeline.bounds.block)), (x, float(timeline.bounds.block + timeline.bounds.block_size))),
                                              semantic_id=semantic_id))
        elif tier.role == "labels" and form is not None:
            orientation = tier.label.orientation
            label_widths = tuple(
                measure_text_width(outcome.label or "", font_size=axis_size, font_metrics=axis_metrics,
                                   letter_spacing=float(axis_treatment.letter_spacing),
                                   text_transform=axis_treatment.transform,
                                   numeric_spacing=axis_treatment.numeric_spacing)
                for outcome in interval_outcomes if outcome.disposition == "placed"
            )
            lane_size = (axis_size if orientation == "horizontal" else max(label_widths, default=0.0))
            lane_overflow = label_lane_offset + lane_size > float(axis.bounds.block_size)
            for interval, outcome in zip(intervals, interval_outcomes, strict=True):
                if outcome.disposition == "thinned":
                    continue
                axis_label_targets[("axis-label", interval.level, str(interval.index))] = outcome.candidate_id
                x, x2 = _coordinate(interval.start, scale), _coordinate(interval.end, scale)
                available = max(0.0, x2 - x)
                label = outcome.label
                if label is None or outcome.disposition != "placed":
                    raise LayoutError("E_PRESENTATION_AXIS_OVERFLOW", f"/view/body/axis/tiers/{tier_index}",
                                      detail=outcome.candidate_id)
                width = measure_text_width(label, font_size=axis_size, font_metrics=axis_metrics,
                                           letter_spacing=float(axis_treatment.letter_spacing),
                                           text_transform=axis_treatment.transform,
                                           numeric_spacing=axis_treatment.numeric_spacing)
                occupied_inline = width if orientation == "horizontal" else axis_size * float(axis_treatment.line_height)
                inline = x if tier.label.align == "start" else x + (available - occupied_inline) / 2
                baseline = float(axis.bounds.block) + label_lane_offset + (
                    axis_size if orientation == "horizontal" else (0 if orientation == "rotate-cw" else width))
                placed = place_text(placement_id=f"axis-label:{tier_index}:{interval.index}", source_ref="timeline-axis",
                                    content=label, inline=inline, baseline_block=baseline,
                                    typography_role="axis", theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                                    collision_region="timeline-axis-label", collision_domain=CollisionDomain("timeline-axis", f"label-{tier_index}"),
                                    source_content=label, available_inline_start=x, available_inline_size=available,
                                    orientation=orientation,
                                    overflow="visible-overflow" if not outcome.label_fits or lane_overflow else "fit")
                placed = replace(placed, semantic_id="axisLabel")
                text.append(placed)
                if not outcome.label_fits or lane_overflow:
                    visible_label_overflows.append((placed, LabelRect(*_bounds(axis.bounds))))
            label_lane_offset += lane_size
        else:
            raise LayoutError("E_PRESENTATION_AXIS_INVALID", "/view/body/axis/tiers")
    contract = request.presentation_contract
    minimum_closed_day_width = metric_values.get("timeline.calendarClosed.minimumDayWidth")
    closed_days = contract.time.calendar_closed
    if minimum_closed_day_width is not None and scale.unit_ratio < float(minimum_closed_day_width):
        closed_days = contract.time.calendar_exceptions
    for closed_day in closed_days:
        if start <= closed_day < end:
            x1, x2 = _coordinate(closed_day, scale), _coordinate(closed_day.fromordinal(closed_day.toordinal() + 1), scale)
            shapes.append(background_shape(
                f"calendar-closed:{closed_day.isoformat()}", "project-calendar", "calendarClosed",
                Rect(Decimal(str(x1)), timeline.bounds.block,
                     Decimal(str(max(0.0, x2 - x1))), timeline.bounds.block_size),
            ))
    as_of_label: tuple[float, str] | None = None
    if contract.time.as_of is not None and start <= contract.time.as_of < end:
        x = _coordinate(contract.time.as_of, scale)
        shapes.append(ShapePlacement("as-of", "actual-set", "Path",
                                     Rect(Decimal(str(x)), timeline.bounds.block, Decimal(0), timeline.bounds.block_size),
                                     ((x, float(timeline.bounds.block)), (x, float(timeline.bounds.block + timeline.bounds.block_size)))))
        as_of_label = (x, f"{contract.time.as_of_label} {contract.time.as_of.isoformat()}")
    tracks = place_mark_tracks(review_rows=tuple(review_rows), row_placements=raw_rows,
                               mark_block_size=float(metric_values["timeline.mark.blockSize"]), role_geometries=role_geometries)
    track_by_id = {item.instance_id: item for item in tracks}
    marks: list[MarkPlacement] = []

    def place_mark(placement_id: str, source_ref: str, bounds: Rect,
                   start_port: tuple[float, float], end_port: tuple[float, float], *, shape: str,
                   semantic_id: str, end_treatment: str = "closed") -> MarkPlacement:
        geometry = role_geometries[semantic_id]
        radius = min(geometry.corner_radius * float(min(bounds.inline_size, bounds.block_size)),
                     float(min(bounds.inline_size, bounds.block_size)) / 2)
        commands = (open_span_path(inline=float(bounds.inline), block=float(bounds.block),
                                   inline_size=float(bounds.inline_size), block_size=float(bounds.block_size), radius=radius)
                    if shape == "open-span" else
                    rounded_diamond_path(inline=float(bounds.inline), block=float(bounds.block),
                                         inline_size=float(bounds.inline_size), block_size=float(bounds.block_size), radius=radius)
                    if shape == "point" and radius > 0 else ())
        return MarkPlacement(placement_id, source_ref, bounds, start_port, end_port,
                             mark_shape=shape, corner_radius=radius, path_commands=commands,
                             slot_id=timeline.slot_id, semantic_id=semantic_id, paint_order=geometry.paint_order,
                             end_treatment=end_treatment)
    for review_row in review_rows:
        members = sorted(
            enumerate(review_row.items),
            key=lambda pair: shared_track_member_key(pair[1], pair[0]),
        )
        for _, item in members:
            layout_id = f"{review_row.row_id}:{item.item_id or item.object_id}"
            instance_id = layout_id if projection.rows else item.object_id
            track = track_by_id[layout_id]
            source_kind = item.source_kind if projection.rows else "combined"
            planned = item.planned
            planned_semantic = "snapshot" if source_kind in {"snapshot", "scenario"} else "planned"
            planned_block, planned_size = mark_bounds(track, role_geometries[planned_semantic])
            actual_block, actual_size = mark_bounds(track, role_geometries["actual"])
            missing_block, missing_size = mark_bounds(track, role_geometries["missing-actual"])
            if source_kind != "actual" and item.source_type == "point":
                x = _coordinate(planned["at"], scale)
                bounds = Rect(Decimal(str(x - planned_size / 2)), Decimal(str(planned_block)),
                              Decimal(str(planned_size)), Decimal(str(planned_size)))
                port = (x, planned_block + planned_size / 2)
                marks.append(place_mark(f"planned:{instance_id}", item.object_id, bounds, port, port, shape="point",
                                        semantic_id=planned_semantic))
            elif source_kind != "actual":
                x1, x2 = _coordinate(planned["start"], scale), _coordinate(planned["end"], scale)
                bounds = Rect(Decimal(str(x1)), Decimal(str(planned_block)),
                              Decimal(str(max(1.0, x2 - x1))), Decimal(str(planned_size)))
                marks.append(place_mark(f"planned:{instance_id}", item.object_id, bounds,
                                        (x1, planned_block + planned_size / 2),
                                        (x2, planned_block + planned_size / 2), shape="span", semantic_id=planned_semantic))
            actual = item.actual or {}
            open_actual = (source_kind in {"actual", "combined"} and item.source_type == "span"
                           and actual.get("openUntil") == "asOf" and isinstance(actual.get("start"), date)
                           and contract.time.as_of is not None)
            if source_kind in {"actual", "combined"} and item.source_type == "span" and isinstance(actual.get("start"), date) and isinstance(actual.get("finish"), date):
                x1, x2 = _coordinate(actual["start"], scale), _coordinate(actual["finish"], scale)
                bounds = Rect(Decimal(str(x1)), Decimal(str(actual_block)),
                              Decimal(str(max(1.0, x2 - x1))), Decimal(str(actual_size)))
                marks.append(place_mark(f"actual:{instance_id}", item.object_id, bounds,
                                        (x1, actual_block + actual_size / 2),
                                        (x2, actual_block + actual_size / 2), shape="span", semantic_id="actual"))
            elif open_actual:
                x1, x2 = _coordinate(actual["start"], scale), _coordinate(contract.time.as_of, scale)
                if x2 <= x1:
                    diagnostics.append(f"W_LAYOUT_OPEN_ACTUAL_INVALID:{item.object_id}")
                else:
                    bounds = Rect(Decimal(str(x1)), Decimal(str(actual_block)),
                                  Decimal(str(x2 - x1)), Decimal(str(actual_size)))
                    mark = place_mark(f"actual:{instance_id}", item.object_id, bounds,
                                      (x1, actual_block + actual_size / 2),
                                      (x2, actual_block + actual_size / 2), shape="open-span", semantic_id="actual",
                                      end_treatment="open")
                    marks.append(mark)
            elif source_kind in {"actual", "combined"} and item.source_type == "point" and isinstance(actual.get("at"), date):
                x = _coordinate(actual["at"], scale)
                bounds = Rect(Decimal(str(x - actual_size / 2)), Decimal(str(actual_block)),
                              Decimal(str(actual_size)), Decimal(str(actual_size)))
                port = (x, actual_block + actual_size / 2)
                marks.append(place_mark(f"actual:{instance_id}", item.object_id, bounds, port, port, shape="point", semantic_id="actual"))
            elif source_kind in {"actual", "combined"}:
                if (actual.get("openUntil") == "asOf" and isinstance(actual.get("start"), date)
                        and contract.time.as_of is None):
                    diagnostics.append(f"W_LAYOUT_OPEN_ACTUAL_AS_OF_REQUIRED:{item.object_id}")
                    continue
                # An observation that is incomplete for this mark policy is
                # still an observation.  A missing-actual treatment is only
                # truthful when the projection has no actual object at all.
                if actual:
                    diagnostics.append(f"W_LAYOUT_ACTUAL_INCOMPLETE:{item.object_id}")
                    continue
                anchor = planned.get("end", planned.get("at"))
                if isinstance(anchor, date):
                    x = _coordinate(anchor, scale)
                    bounds = Rect(Decimal(str(x)), Decimal(str(missing_block)),
                                  Decimal(str(max(1.0, missing_size * 1.5))), Decimal(str(missing_size)))
                    marks.append(place_mark(f"missing-actual:{instance_id}", item.object_id, bounds,
                                            (x, missing_block), (x, missing_block), shape="span", semantic_id="missing-actual"))
    # A group-header target is a real GroupPlacement extent, not a synthetic table row.
    group_by_id = {group.group_id: group for group in groups}
    visible_group_header_overflows: list[tuple[str, Rect, float]] = []
    folded_by_group: dict[str, list[Any]] = {}
    for folded in getattr(projection, "folded_points", ()):
        folded_by_group.setdefault(folded.group_id, []).append(folded)
    for group_id, folded_points in folded_by_group.items():
        group = group_by_id.get(group_id)
        if group is None or group.header_bounds is None:
            folded = folded_points[0]
            raise LayoutError("E_REVIEW_POINT_GROUP_HEADER_UNAVAILABLE", f"/projection/foldedPoints/{folded.item.object_id}")
        block_size = float(metric_values["timeline.mark.blockSize"])
        capacity = int(float(group.header_bounds.block_size) // block_size)
        occupied = len(folded_points) * block_size
        if occupied > float(group.header_bounds.block_size):
            # Folded marks retain their stable stack order.  Extend the real
            # group-header host rather than inventing a synthetic row or
            # suppressing excess milestones.
            expanded_header = Rect(group.header_bounds.inline, group.header_bounds.block,
                                   group.header_bounds.inline_size, Decimal(str(occupied)))
            replacement = GroupPlacement(group.group_id, group.content_bounds, expanded_header)
            groups[groups.index(group)] = replacement
            group_by_id[group_id] = replacement
            shapes = [replace(shape, bounds=expanded_header)
                      if shape.placement_id == f"group-header-band:{group_id}" else shape
                      for shape in shapes]
            visible_group_header_overflows.append((group_id, expanded_header,
                                                   float(group.header_bounds.block_size)))
            group = replacement
        first_block = float(group.header_bounds.block) + max(0.0, (float(group.header_bounds.block_size) - occupied) / 2)
        for track_index, folded in enumerate(sorted(folded_points, key=lambda point: (point.item.planned.get("at"), point.item.object_id))):
            block = first_block + track_index * block_size
            members = sorted(enumerate(folded.all_items),
                             key=lambda pair: shared_track_member_key(pair[1], pair[0]))
            for _, item in members:
                instance_id = _folded_instance_id(folded, item)
                planned_at = item.planned.get("at")
                planned_semantic = "snapshot" if item.source_kind in {"snapshot", "scenario"} else "planned"
                planned_geometry = role_geometries[planned_semantic]
                planned_block = block + block_size * planned_geometry.offset
                planned_size = block_size * planned_geometry.height
                actual_geometry = role_geometries["actual"]
                actual_block = block + block_size * actual_geometry.offset
                actual_size = block_size * actual_geometry.height
                if item.source_kind != "actual" and isinstance(planned_at, date):
                    x = _coordinate(planned_at, scale)
                    bounds = Rect(Decimal(str(x - planned_size / 2)), Decimal(str(planned_block)), Decimal(str(planned_size)), Decimal(str(planned_size)))
                    port = (x, planned_block + planned_size / 2)
                    marks.append(place_mark(f"planned:{instance_id}", item.object_id, bounds, port, port, shape="point", semantic_id=planned_semantic))
                actual_at = (item.actual or {}).get("at")
                if item.source_kind in {"actual", "combined"} and isinstance(actual_at, date):
                    x = _coordinate(actual_at, scale)
                    bounds = Rect(Decimal(str(x - actual_size / 2)), Decimal(str(actual_block)), Decimal(str(actual_size)), Decimal(str(actual_size)))
                    port = (x, actual_block + actual_size / 2)
                    marks.append(place_mark(f"actual:{instance_id}", item.object_id, bounds, port, port, shape="point", semantic_id="actual"))
    mark_by_id = {item.placement_id: item for item in marks}
    progress_source = request.surface_content.progress_fill_source
    if progress_source is not None:
        for review_row in review_rows:
            for item in review_row.items:
                if progress_source == "actual":
                    fraction = (item.actual or {}).get("progress")
                    host_prefix = "actual"
                else:
                    fraction = getattr(item, "planned_progress", None)
                    host_prefix = "planned"
                if not isinstance(fraction, (int, float)) or isinstance(fraction, bool) or not 0 <= fraction <= 1:
                    continue
                layout_id = f"{review_row.row_id}:{item.item_id or item.object_id}"
                instance_id = layout_id if projection.rows else item.object_id
                host = mark_by_id.get(f"{host_prefix}:{instance_id}")
                if host is None or fraction == 0:
                    continue
                bounds = progress_fill_bounds(host.bounds, float(fraction))
                if bounds is not None and bounds.inline_size > 0:
                    shapes.append(ShapePlacement(f"progress-fill:{host.placement_id}", item.object_id,
                                                 "Rect", bounds, required=False, slot_id=host.slot_id,
                                                 clip_host_id=host.placement_id,
                                                 paint_order=host.paint_order + 1))
    for review_row, row in zip(review_rows, rows, strict=True):
        if getattr(review_row, "rollup_presentation", "none") != "bar":
            continue
        subject = next((item for item in review_row.items
                        if item.item_id == review_row.table_subject_id and item.source_kind != "actual"), None)
        if subject is None or subject.source_type != "span":
            continue
        start_at, end_at = subject.planned.get("start"), subject.planned.get("end")
        if not isinstance(start_at, date) or not isinstance(end_at, date):
            continue
        x1, x2 = _coordinate(start_at, scale), _coordinate(end_at, scale)
        height = float(request.theme_tokens.summary_bar_height("summary-bar")) * float(metric_values["timeline.mark.blockSize"])
        shapes.append(ShapePlacement(f"summary-bar:{review_row.row_id}", subject.object_id, "Rect",
                                     Rect(Decimal(str(x1)), row.bounds.block,
                                          Decimal(str(max(1.0, x2 - x1))), Decimal(str(height)))))
    placement_decisions: list[PlacementDecision] = list(axis_decisions)
    label_requests: list[LabelRequest] = []
    candidate_icons: list[IconPlacement] = []
    handled_candidate_visuals: set[str] = set()
    if as_of_label is not None:
        x, content = as_of_label
        label_requests.append(LabelRequest(
            "as-of-label", "actual-set", content,
            LabelRect(x, timeline_bounds[1], 0.0, body_size), ("end", "start", "below"),
            "text", "timeline-as-of", CollisionDomain("timeline", "overlay"), "suppress",
        ))
    if contract.labels.enabled:
        for review_row in review_rows:
            for item in review_row.items:
                layout_id = f"{review_row.row_id}:{item.item_id or item.object_id}"
                instance_id = layout_id if projection.rows else item.object_id
                planned = item.planned
                start_at, end_at = planned.get("start", planned.get("at")), planned.get("end", planned.get("at"))
                if not isinstance(start_at, date) and not isinstance(end_at, date):
                    continue
                parts = []
                if "title" in contract.labels.content:
                    parts.append(item.title)
                if "finishDelta" in contract.labels.content and item.finish_delta is not None:
                    parts.append(f"{item.finish_delta:+d}d")
                if not parts:
                    continue
                host_kind = "actual" if item.source_kind == "actual" else "planned"
                host_mark_id = f"{host_kind}:{instance_id}"
                mark = mark_by_id.get(host_mark_id)
                if item.source_kind == "actual" and mark is None:
                    raise LayoutError("E_LAYOUT_LABEL_HOST_UNAVAILABLE", f"/placement/member-label:{instance_id}")
                track = track_by_id[layout_id]
                anchor = LabelRect(*_bounds(mark.bounds)) if mark is not None else LabelRect(
                    _coordinate(end_at if isinstance(end_at, date) else start_at, scale), track.block,
                    max(1.0, track.block_size), track.block_size)
                default_ladder = (request.surface_content.label_fallback or (("above", "below", "start", "end") if contract.labels.side == "auto" else (contract.labels.side,)))
                intent = getattr(item, "presentation", None) or {}
                preferred_side = (intent.get("label") or {}).get("side") if isinstance(intent, dict) else None
                wrap = ((intent.get("text") or {}).get("wrap", "forbid") if isinstance(intent, dict) else "forbid")
                ladder = ((preferred_side,) + tuple(side for side in default_ladder if side != preferred_side)
                          if preferred_side else default_ladder)
                sides = tuple(side for side in ladder if side != "suppress")
                label_requests.append(LabelRequest(f"member-label:{instance_id}", item.object_id, " ".join(parts),
                                                   anchor, sides, "text", "plot-label", CollisionDomain("timeline", "overlay"),
                                                   "suppress" if "suppress" in ladder else contract.labels.overflow,
                                                   wrap, inside_host_obstacle_id=host_mark_id if mark is not None else None))
        for folded in getattr(projection, "folded_points", ()):
            instance_id = _folded_instance_id(folded, folded.item)
            host_kind = "actual" if folded.item.source_kind == "actual" else "planned"
            mark = mark_by_id.get(f"{host_kind}:{instance_id}")
            group = group_by_id.get(folded.group_id)
            if folded.item.source_kind == "actual" and mark is None:
                raise LayoutError("E_LAYOUT_LABEL_HOST_UNAVAILABLE", f"/placement/member-label:group-header:{folded.group_id}:{folded.item.object_id}")
            if mark is None or group is None or group.header_bounds is None:
                continue
            default_ladder = ("end", "start") if contract.labels.side == "auto" else (contract.labels.side,)
            label_requests.append(LabelRequest(
                f"member-label:group-header:{folded.group_id}:{folded.item.object_id}", folded.item.object_id,
                folded.item.title, LabelRect(*_bounds(mark.bounds)), default_ladder, "groupHeader", "group-header-point",
                CollisionDomain("group-header", folded.group_id), "visible-overflow", bounds=LabelRect(*_bounds(group.header_bounds)),
                inside_host_obstacle_id=mark.placement_id))
    # The remaining text and routes are part of the same completed Layout closure.
    # Scene may select their semantic roles, but it must never remeasure or route them.
    for review_row in review_rows:
        for item in review_row.items:
            layout_id = f"{review_row.row_id}:{item.item_id or item.object_id}"
            instance_id = layout_id if projection.rows else item.object_id
            if not projection.rows and item.source_kind != "combined":
                continue
            if item.finish_delta is None or "finishDelta" in contract.labels.content:
                continue
            mark = mark_by_id.get(f"actual:{instance_id}") or mark_by_id.get(f"planned:{instance_id}")
            track = track_by_id[layout_id]
            actual = item.actual or {}
            anchor = actual.get("finish", item.planned.get("end", item.planned.get("at")))
            if isinstance(anchor, date):
                anchor_bounds = LabelRect(*_bounds(mark.bounds)) if mark is not None else LabelRect(
                    _coordinate(anchor, scale), track.block, max(1.0, track.block_size), track.block_size)
                label_requests.append(LabelRequest(f"variance:{instance_id}", item.object_id, f"{item.finish_delta:+d}d",
                                                   anchor_bounds, ("above", "below", "end", "start"), "summary",
                                                   f"variance:{instance_id}", CollisionDomain("timeline", "overlay"),
                                                   request.surface_content.label_overflow))

    timeline_rect = LabelRect(*timeline_bounds)
    for label_request in label_requests:
        label_treatment = request.theme_tokens.text_treatment(label_request.typography_role)
        label_metrics = metric_for(label_request.typography_role)
        font_size, line_height = label_treatment.font_size, label_treatment.line_height
        visuals = candidate_label_visuals(label_request.placement_id, label_request.typography_role, request)
        handled_candidate_visuals.update(visual.source_ref for visual, _, _, _ in visuals)
        leading = geometry_sum(width + gap for visual, icon, width, gap in visuals if visual.side == "leading")
        trailing = geometry_sum(width + gap for visual, icon, width, gap in visuals if visual.side == "trailing")
        available = max(1.0, timeline_rect.width * 0.4 - leading - trailing)
        lines = (wrap_text(label_request.content, available_inline=available,
                           font_size=float(font_size), font_metrics=label_metrics,
                           letter_spacing=float(label_treatment.letter_spacing),
                           text_transform=label_treatment.transform)
                 if label_request.wrap == "allow" else (label_request.content,))
        placement_bounds = label_request.bounds or timeline_rect
        text_width = max(measure_text_width(line, font_size=float(font_size), font_metrics=label_metrics,
                                            letter_spacing=float(label_treatment.letter_spacing),
                                            text_transform=label_treatment.transform) for line in lines)
        label_size = (leading + text_width + trailing,
                      float(font_size) * float(line_height) * len(lines))
        # Mark labels remain subject to every completed mark.  ``place_label``
        # alone exempts this request's declared host for an ``inside``
        # candidate; a comparison sibling or another row is never an implicit
        # host.
        obstacles = [LabelObstacle(item.placement_id, LabelRect(*_bounds(item.bounds))) for item in marks]
        obstacles.extend(LabelObstacle(item.placement_id, LabelRect(*_bounds(item.bounds))) for item in text
                         if item.required and item.overflow != "suppressed")
        candidate = (place_label(label_request.anchor, label_size, label_request.candidates, bounds=placement_bounds,
                                 obstacles=obstacles, gap=max(1.0, float(font_size) * 0.25),
                                 inside_host_obstacle_id=label_request.inside_host_obstacle_id,
                                 required=label_request.overflow == "diagnose", overflow=label_request.overflow)
                     if label_request.candidates else None)
        provisional = place_text(placement_id=label_request.placement_id, source_ref=label_request.source_ref,
                                 content=label_request.content, inline=0, baseline_block=float(font_size),
                                 typography_role=label_request.typography_role, theme_tokens=request.theme_tokens,
                                 font_metrics=request.font_metrics, collision_region=label_request.collision_region,
                                 collision_domain=label_request.collision_domain)
        if candidate is None:
            ladder = label_request.candidates + (("suppress",) if label_request.overflow == "suppress" else ())
            if not ladder:
                raise LayoutError("E_PRESENTATION_LABEL_UNPLACEABLE", f"/placement/{label_request.placement_id}")
            text.append(replace(provisional, overflow="suppressed", required=False,
                                fallback_ladder=ladder,
                                selected_rung="suppress"))
            placement_decisions.append(PlacementDecision(label_request.placement_id, label_request.source_ref,
                                                         ladder, "suppress", "suppressed"))
            diagnostics.append(f"W_LAYOUT_LABEL_SUPPRESSED:{label_request.placement_id}")
        else:
            placed_text = replace(place_text(placement_id=provisional.placement_id, source_ref=provisional.source_ref,
                                   content=provisional.content, inline=candidate.bounds.x + leading,
                                   baseline_block=candidate.bounds.y + float(font_size),
                                   typography_role=provisional.typography_role, theme_tokens=request.theme_tokens,
                                   font_metrics=request.font_metrics, collision_region=provisional.collision_region,
                                   collision_domain=provisional.collision_domain,
                                   overflow="visible-overflow" if candidate.visible_overflow else "fit",
                                   lines=lines), fallback_ladder=label_request.candidates, selected_rung=candidate.side)
            text.append(placed_text)
            if candidate.visible_overflow:
                visible_label_overflows.append((placed_text, placement_bounds))
            if visuals:
                if not hasattr(label_metrics, "cap_height_at"):
                    raise LayoutError("E_FONT_METRICS_CAP_HEIGHT", next(visual.source_ref for visual, _, _, _ in visuals))
                cap_height = float(label_metrics.cap_height_at(float(font_size)))
                for visual, icon, width, gap in visuals:
                    inline = (candidate.bounds.x if visual.side == "leading"
                              else candidate.bounds.x + leading + text_width + trailing - gap - width)
                    bounds = Rect(Decimal(str(inline)), Decimal(str(placed_text.baseline[1] - cap_height
                                                                       + (cap_height - float(font_size)) / 2)),
                                  Decimal(str(width)), Decimal(str(float(font_size))))
                    candidate_icons.append(IconPlacement(f"visual:{placed_text.placement_id}:{visual.side}",
                                                         placed_text.source_ref, visual.source_ref, icon.icon_id,
                                                         icon.kind, icon.content_identity, icon.viewport, icon.payload,
                                                         icon.alternative, visual.decorative, bounds, "labelVisual",
                                                         width / icon.viewport[0], text_slot(placed_text)))
            placement_decisions.append(PlacementDecision(label_request.placement_id, label_request.source_ref,
                                                         label_request.candidates, candidate.side, "placed"))

    relations: list[RelationPlacement] = []
    visible_route_fallbacks: list[RelationPlacement] = []
    instance_anchors: dict[str, list[tuple[str, tuple[float, float]]]] = {}
    instance_rows: dict[str, str] = {}
    for review_row, row in zip(review_rows, rows, strict=True):
        fallback = (float(row.bounds.inline + row.bounds.inline_size),
                    float(row.bounds.block + row.bounds.block_size / 2))
        for item in review_row.items:
            instance_id = f"{review_row.row_id}:{item.item_id or item.object_id}" if projection.rows else item.object_id
            instance_anchors.setdefault(item.object_id, []).append((instance_id, fallback))
            instance_rows[instance_id] = row.row_id
    for folded in getattr(projection, "folded_points", ()):
        instance_id = _folded_instance_id(folded, folded.item)
        mark = next((item for item in marks if item.placement_id == f"planned:{instance_id}"), None)
        if mark is not None:
            instance_anchors.setdefault(folded.item.object_id, []).append((instance_id, mark.end_port))
            instance_rows[instance_id] = f"group-header:{folded.group_id}"
    mark_ports = {mark.placement_id.removeprefix("planned:"): (mark.start_port, mark.end_port)
                  for mark in marks if mark.placement_id.startswith("planned:")}
    route_top = min((float(group.header_bounds.block) for group in groups if group.header_bounds is not None),
                    default=timeline_bounds[1])
    route_bottom = max((timeline_bounds[1] + timeline_bounds[3],
                        *(float(group.header_bounds.block + group.header_bounds.block_size)
                          for group in groups if group.header_bounds is not None)))
    for relation in request.surface_content.relations:
        source, target, relation_id = relation.source_object_id, relation.target_object_id, relation.relation_id
        for source_id, source_anchor in instance_anchors.get(str(source), ()):
            for target_id, target_anchor in instance_anchors.get(str(target), ()):
                source_ports = mark_ports.get(source_id, (source_anchor, source_anchor))
                target_ports = mark_ports.get(target_id, (target_anchor, target_anchor))
                source_port = source_ports[0] if relation.source_endpoint in {"start", "at"} else source_ports[1]
                target_port = target_ports[0] if relation.target_endpoint in {"start", "at"} else target_ports[1]
                scene_id = f"relation:{relation_id}:{source_id}:{target_id}" if projection.rows else f"relation:{relation_id}"
                source_port_id = f"{source_id}:{relation.source_endpoint}"
                target_port_id = f"{target_id}:{relation.target_endpoint}"
                if source_port == target_port:
                    if request.surface_content.relation_overflow == "suppress":
                        relations.append(RelationPlacement(scene_id, source_port_id, target_port_id,
                                                           suppressed=True, diagnostic="W_LAYOUT_RELATION_SUPPRESSED"))
                        diagnostics.append(f"W_LAYOUT_RELATION_SUPPRESSED:{scene_id}")
                        continue
                    # A direct zero-length path is not inspectable, so retain
                    # a deterministic one-point inline stub for coincident
                    # endpoints.  Scene still receives completed geometry.
                    fallback = (source_port, (source_port[0] + 1.0, source_port[1]))
                    placed = RelationPlacement(scene_id, source_port_id, target_port_id, fallback,
                                               semantic_id=relation.semantic_id, source_ref=relation_id)
                    relations.append(placed)
                    visible_route_fallbacks.append(placed)
                    continue
                endpoint_rows = {instance_rows.get(source_id), instance_rows.get(target_id)}
                obstacles = tuple((float(row.bounds.inline), float(row.bounds.block),
                                   float(row.bounds.inline + row.bounds.inline_size),
                                   float(row.bounds.block + row.bounds.block_size))
                                  for row in rows if row.row_id not in endpoint_rows)
                fallback = False
                try:
                    points = place_relation_route(source_port=source_port, target_port=target_port, obstacles=obstacles,
                                                  bounds=(timeline_bounds[0], route_top,
                                                          timeline_bounds[0] + timeline_bounds[2], route_bottom))
                except ValueError as error:
                    if request.surface_content.relation_overflow == "suppress":
                        relations.append(RelationPlacement(scene_id, source_port_id, target_port_id,
                                                           suppressed=True, diagnostic="W_LAYOUT_RELATION_SUPPRESSED"))
                        diagnostics.append(f"W_LAYOUT_RELATION_SUPPRESSED:{scene_id}")
                        continue
                    points = (source_port, target_port)
                    fallback = True
                if not relation_route_quality(tuple(points), max_bends=layout_manifest.relation_max_bends,
                                              max_detour_ratio=layout_manifest.relation_max_detour_ratio):
                    if request.surface_content.relation_overflow == "suppress":
                        relations.append(RelationPlacement(scene_id, source_port_id, target_port_id,
                                                           suppressed=True, diagnostic="W_LAYOUT_RELATION_SUPPRESSED"))
                        diagnostics.append(f"W_LAYOUT_RELATION_SUPPRESSED:{scene_id}")
                        continue
                    points = (source_port, target_port)
                    fallback = True
                relation_radius = float(metric_values.get("timeline.relation.cornerRadius", 0))
                placed = RelationPlacement(scene_id, source_port_id, target_port_id, tuple(points),
                                           semantic_id=relation.semantic_id,
                                           corner_radius=relation_radius,
                                           path_commands=(rounded_orthogonal_path(tuple(points), relation_radius)
                                                          if relation_radius > 0 and not fallback else ()),
                                           marker_start=marker_geometry(request.theme_tokens.marker("relationSourceTerminal")),
                                           marker_end=marker_geometry(request.theme_tokens.marker("relationTargetTerminal")),
                                           label_content=relation_label_content(relation), source_ref=relation_id)
                relations.append(placed)
                if fallback:
                    visible_route_fallbacks.append(placed)

    # Relation labels are routed facts, not a Scene or adapter policy.  They run
    # after relation paths exist so their anchor is a stable completed segment.
    for placed_relation in relations:
        if placed_relation.suppressed:
            continue
        content = placed_relation.label_content
        if not content:
            continue
        relation_treatment = request.theme_tokens.text_treatment("annotation")
        relation_metrics = metric_for("annotation")
        font_size, line_height = relation_treatment.font_size, relation_treatment.line_height
        size = (measure_text_width(content, font_size=float(font_size), font_metrics=relation_metrics,
                                   letter_spacing=float(relation_treatment.letter_spacing),
                                   text_transform=relation_treatment.transform),
                float(font_size) * float(line_height))
        relation_text_id = f"relation-label:{placed_relation.relation_id.removeprefix('relation:')}"
        obstacles = [LabelObstacle(item.placement_id, LabelRect(*_bounds(item.bounds))) for item in marks]
        obstacles.extend(LabelObstacle(item.placement_id, LabelRect(*_bounds(item.bounds))) for item in text
                         if item.required and item.overflow != "suppressed")
        candidate = place_label(relation_label_anchor(placed_relation.points), size, ("above", "below", "start", "end"),
                                bounds=timeline_rect, obstacles=obstacles, gap=max(1.0, float(font_size) * 0.25),
                                required=False, overflow=request.surface_content.relation_overflow)
        if candidate is None:
            diagnostics.append(f"W_LAYOUT_RELATION_LABEL_SUPPRESSED:{placed_relation.relation_id}")
            continue
        placed_text = replace(place_text(placement_id=relation_text_id, source_ref=placed_relation.source_ref,
                                       content=content, inline=candidate.bounds.x,
                                       baseline_block=candidate.bounds.y + float(font_size), typography_role="annotation",
                                       theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                                       collision_region="relation-label", collision_domain=CollisionDomain("timeline", "overlay")),
                            fallback_ladder=("above", "below", "start", "end"), selected_rung=candidate.side)
        text.append(placed_text)
        if candidate.visible_overflow:
            visible_label_overflows.append((placed_text, timeline_rect))

    legend = by_source.get("legend")
    if legend:
        legend_treatment = request.theme_tokens.text_treatment("legend")
        legend_size = float(legend_treatment.font_size)
        legend_step = legend_size * float(legend_treatment.line_height)
        swatch_size = max(2.0, legend_size * 0.8)
        for index, (role, label) in enumerate(request.surface_content.legend_entries):
            baseline = float(legend.bounds.block) + (index + 1) * legend_step
            shapes.append(ShapePlacement(f"legend-swatch:{role}", role, "Rect",
                                         Rect(legend.bounds.inline, Decimal(str(baseline - swatch_size)),
                                              Decimal(str(swatch_size)), Decimal(str(swatch_size)))))
            text.append(place_text(placement_id=f"legend:{role}", source_ref=role, content=label,
                                   inline=float(legend.bounds.inline) + swatch_size * 1.5, baseline_block=baseline,
                                   typography_role="legend", theme_tokens=request.theme_tokens,
                                   font_metrics=request.font_metrics, collision_region="legend",
                                   collision_domain=CollisionDomain("legend", "content"), source_content=label,
                                   available_inline_start=float(legend.bounds.inline) + swatch_size * 1.5,
                                   available_inline_size=max(0.0, float(legend.bounds.inline_size) - swatch_size * 1.5)))
    for slot_name, values, prefix, purpose, typography in (
        ("notes", request.surface_content.notes, "note", "project-note", "text"),
        ("group-details", request.surface_content.group_details, "group-detail", "group-detail", "text"),
        ("milestones", request.surface_content.milestones, "milestone", "milestone-digest-entry", "text"),
    ):
        slot = by_source.get(slot_name)
        if slot:
            for index, value in enumerate(values):
                if slot_name == "group-details":
                    source, content = value[0], f"{value[1]}: {value[2]}"
                elif slot_name == "milestones":
                    source, content = value[0], f"{value[1]} — {value[2].isoformat()}"
                else:
                    source, content = value
                text.append(place_text(placement_id=f"{prefix}:{source}", source_ref=source, content=content,
                                       inline=float(slot.bounds.inline),
                                       baseline_block=float(slot.bounds.block) + (index + 1) * body_size,
                                       typography_role=typography, theme_tokens=request.theme_tokens,
                                       font_metrics=request.font_metrics,
                                       collision_region=f"{slot_name}:{source}",
                                       collision_domain=CollisionDomain(slot_name, f"line:{index}"), source_content=content,
                                       available_inline_start=float(slot.bounds.inline),
                                       available_inline_size=float(slot.bounds.inline_size)))
    summary_slot = by_source.get("summary")
    if summary_slot:
        cursor = float(summary_slot.bounds.block)
        for run in request.surface_content.summary.runs:
            summary_treatment = request.theme_tokens.text_treatment(run.typography_role)
            font_size, line_height = summary_treatment.font_size, summary_treatment.line_height
            text.append(place_text(placement_id=run.placement_id, source_ref=run.source_ref, content=run.content,
                                   inline=float(summary_slot.bounds.inline), baseline_block=cursor + float(font_size),
                                   typography_role=run.typography_role, theme_tokens=request.theme_tokens,
                                   font_metrics=request.font_metrics, collision_region="summary",
                                   collision_domain=CollisionDomain("summary", "content"), source_content=run.content,
                                   available_inline_start=float(summary_slot.bounds.inline),
                                   available_inline_size=float(summary_slot.bounds.inline_size)))
            cursor += float(font_size) * float(line_height)

    annotation_slot = by_source.get("annotations")
    if annotation_slot:
        annotation_marks = _comparison_marks(projection)
        placed_boxes: list[LabelRect] = []
        for index, annotation in enumerate(request.surface_content.annotations):
            presentation = annotation_presentation(annotation.purpose)
            annotation_id, content = annotation.annotation_id, annotation.content
            content = f"{annotation.number}. {content}" if annotation.number is not None else content
            annotation_visuals = candidate_label_visuals(f"annotation-text:{annotation_id}", "annotation", request)
            handled_candidate_visuals.update(visual.source_ref for visual, _, _, _ in annotation_visuals)
            annotation_leading = geometry_sum(width + gap for visual, icon, width, gap in annotation_visuals if visual.side == "leading")
            annotation_trailing = geometry_sum(width + gap for visual, icon, width, gap in annotation_visuals if visual.side == "trailing")
            resolved = resolve_annotation_anchor(annotation, annotation_marks)
            matching = [(review_row, row) for review_row, row in zip(review_rows, rows, strict=True)
                        if any(item.object_id == resolved.object_id for item in review_row.items)]
            anchor = annotation.anchor
            row_id, item_id = anchor.get("rowId"), anchor.get("itemId")
            if row_id is not None or item_id is not None:
                matching = [(review_row, row) for review_row, row in matching
                            if (row_id is None or review_row.row_id == row_id)
                            and (item_id is None or any(item.item_id == item_id and item.object_id == resolved.object_id for item in review_row.items))]
            folded_matches = [(folded, mark_by_id.get(f"{resolved.facet}:{_folded_instance_id(folded, folded.item)}"))
                              for folded in getattr(projection, "folded_points", ())
                              if folded.item.object_id == resolved.object_id]
            if row_id is not None or item_id is not None:
                folded_matches = [(folded, mark) for folded, mark in folded_matches
                                  if (row_id is None or row_id == f"group-header:{folded.group_id}:{folded.item.object_id}")
                                  and (item_id is None or item_id == folded.item.item_id)]
            if len(matching) + len(folded_matches) > 1:
                raise LayoutError("E_PRESENTATION_ROW_ANCHOR_AMBIGUOUS", f"/annotations/{index}/anchor")
            if matching:
                anchor_bounds = _annotation_anchor_bounds(resolved.mark, resolved.endpoint, matching[0][1], scale)
                selected_items = tuple(item for item in matching[0][0].items
                                       if item.object_id == resolved.object_id and (item_id is None or item.item_id == item_id))
            elif folded_matches and folded_matches[0][1] is not None:
                folded, mark = folded_matches[0]
                anchor_bounds = LabelRect(*_bounds(mark.bounds))
                selected_items = (folded.item,)
            else:
                raise LayoutError("E_PRESENTATION_ANCHOR_MISSING", f"/annotations/{index}/anchor")
            annotation_text_role = semantic_binding(presentation.text_semantic_id).theme_role
            annotation_treatment = request.theme_tokens.text_treatment(annotation_text_role)
            annotation_metrics = metric_for(annotation_text_role)
            size, line_height = float(annotation_treatment.font_size), float(annotation_treatment.line_height)
            text_available = max(1.0, float(annotation_slot.bounds.inline_size) - annotation_leading - annotation_trailing)
            text_width = min(text_available, max(size * 4, measure_text_width(
                content, font_size=size, font_metrics=annotation_metrics,
                letter_spacing=float(annotation_treatment.letter_spacing), text_transform=annotation_treatment.transform)))
            width = annotation_leading + text_width + annotation_trailing
            annotation_lines = (content,)
            try:
                if annotation.purpose in {"callout", "highlight", "note", "explanatory-arrow"}:
                    intent = selected_items[0].presentation if selected_items else None
                    preferred = ((intent or {}).get("callout") or {}).get("placement") if isinstance(intent, dict) else None
                    wrap = ((intent or {}).get("text") or {}).get("wrap", "forbid") if isinstance(intent, dict) else "forbid"
                    annotation_lines = (wrap_text(content, available_inline=text_available, font_size=size, font_metrics=annotation_metrics,
                                                  letter_spacing=float(annotation_treatment.letter_spacing),
                                                  text_transform=annotation_treatment.transform)
                                        if wrap == "allow" else (content,))
                    text_width = max(measure_text_width(line, font_size=size, font_metrics=annotation_metrics,
                                                        letter_spacing=float(annotation_treatment.letter_spacing),
                                                        text_transform=annotation_treatment.transform)
                                     for line in annotation_lines)
                    annotation_size = (annotation_leading + text_width + annotation_trailing,
                                       size * line_height * len(annotation_lines))
                    default_ladder = annotation.fallback_ladder or ("rail",)
                    ladder = ((preferred,) + tuple(rung for rung in default_ladder if rung != preferred)
                              if preferred else default_ladder)
                    box, selected_rung = None, None
                    for rung in (rung for rung in ladder if rung != "suppress"):
                        if rung == "rail":
                            candidate_box = place_annotation_rail(
                                annotation, resolved, anchor_y=anchor_bounds.y + anchor_bounds.height / 2,
                                text_size=annotation_size, rail=LabelRect(*_bounds(annotation_slot.bounds)),
                                obstacles=placed_boxes, overflow="clip-optional", required=False)
                        else:
                            candidate_box = project_annotation_box(
                                annotation, resolved, anchor_bounds=anchor_bounds, text_size=annotation_size,
                                candidate_sides=(rung,), viewport=LabelRect(*_bounds(annotation_slot.bounds)),
                                obstacles=placed_boxes, overflow="clip-optional", required=False)
                        if candidate_box is not None:
                            box, selected_rung = candidate_box, rung
                            break
                    if box is None:
                        if "suppress" in ladder:
                            placement_decisions.append(PlacementDecision(f"annotation:{annotation_id}", annotation_id,
                                                                         tuple(ladder), "suppress", "suppressed"))
                            diagnostics.append(f"W_LAYOUT_ANNOTATION_SUPPRESSED:annotation:{annotation_id}")
                            continue
                        # A normal annotation is never silently suppressed or
                        # rejected.  Complete its first declared placement in
                        # visible-overflow mode after the explicit fit ladder
                        # has been exhausted.
                        selected_rung = next(rung for rung in ladder if rung != "suppress")
                        if selected_rung == "rail":
                            box = place_annotation_rail(
                                annotation, resolved, anchor_y=anchor_bounds.y + anchor_bounds.height / 2,
                                text_size=annotation_size, rail=LabelRect(*_bounds(annotation_slot.bounds)),
                                obstacles=placed_boxes, overflow="visible-overflow", required=True)
                        else:
                            box = project_annotation_box(
                                annotation, resolved, anchor_bounds=anchor_bounds, text_size=annotation_size,
                                candidate_sides=(selected_rung,), viewport=LabelRect(*_bounds(annotation_slot.bounds)),
                                obstacles=placed_boxes, overflow="visible-overflow", required=True)
                        if box is None:  # Defensive: visible-overflow is a total Layout policy.
                            raise LayoutError("E_PRESENTATION_LABEL_UNPLACEABLE", f"/annotations/{index}")
                    placement_decisions.append(PlacementDecision(f"annotation:{annotation_id}", annotation_id,
                                                                 tuple(ladder), selected_rung, "placed"))
                else:
                    box = project_annotation_box(annotation, resolved, anchor_bounds=anchor_bounds, text_size=(width, size * line_height),
                                                 candidate_sides=(annotation.side,),
                                                 viewport=LabelRect(*_bounds(annotation_slot.bounds)), obstacles=placed_boxes,
                                                 overflow=annotation_slot.overflow, required=annotation_slot.priority == "required")
            except ValueError as error:
                raise LayoutError(str(error), f"/annotations/{index}") from error
            if box is None:
                continue
            placed_boxes.append(box.placement.bounds)
            bounds = box.placement.bounds
            shapes.append(ShapePlacement(f"annotation-box:{annotation_id}", annotation_id, "Rect",
                                         Rect(Decimal(str(bounds.x)), Decimal(str(bounds.y)), Decimal(str(bounds.width)), Decimal(str(bounds.height))),
                                         semantic_id=presentation.box_semantic_id, annotation=presentation))
            placed_annotation = place_text(placement_id=f"annotation-text:{annotation_id}", source_ref=annotation_id, content=content,
                                           inline=bounds.x + annotation_leading, baseline_block=bounds.y + size, typography_role=annotation_text_role,
                                           theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                                           collision_region="annotations", collision_domain=CollisionDomain("annotations", "content"),
                                           lines=annotation_lines, semantic_id=presentation.text_semantic_id,
                                           annotation=presentation)
            text.append(placed_annotation)
            if box.placement.visible_overflow:
                visible_label_overflows.append((placed_annotation, LabelRect(*_bounds(annotation_slot.bounds))))
            if annotation_visuals:
                if not hasattr(annotation_metrics, "cap_height_at"):
                    raise LayoutError("E_FONT_METRICS_CAP_HEIGHT", next(visual.source_ref for visual, _, _, _ in annotation_visuals))
                cap_height = float(annotation_metrics.cap_height_at(size))
                for visual, icon, icon_width, gap in annotation_visuals:
                    inline = (bounds.x if visual.side == "leading"
                              else bounds.x + annotation_leading + text_width + annotation_trailing - gap - icon_width)
                    icon_bounds = Rect(Decimal(str(inline)), Decimal(str(placed_annotation.baseline[1] - cap_height
                                                                          + (cap_height - size) / 2)),
                                       Decimal(str(icon_width)), Decimal(str(size)))
                    candidate_icons.append(IconPlacement(f"visual:{placed_annotation.placement_id}:{visual.side}",
                                                         annotation_id, visual.source_ref, icon.icon_id, icon.kind,
                                                         icon.content_identity, icon.viewport, icon.payload, icon.alternative,
                                                         visual.decorative, icon_bounds, "labelVisual",
                                                         icon_width / icon.viewport[0], annotation_slot.slot_id))
            if annotation.number is not None:
                note_index_visuals = candidate_label_visuals(f"note-index:{annotation_id}", "annotation", request)
                handled_candidate_visuals.update(visual.source_ref for visual, _, _, _ in note_index_visuals)
                note_index_leading = geometry_sum(width + gap for visual, _, width, gap in note_index_visuals
                                                  if visual.side == "leading")
                note_index_trailing = geometry_sum(width + gap for visual, _, width, gap in note_index_visuals
                                                   if visual.side == "trailing")
                note_index_content = str(annotation.number)
                note_index_width = measure_text_width(note_index_content, font_size=size, font_metrics=annotation_metrics,
                                                      letter_spacing=float(annotation_treatment.letter_spacing),
                                                      text_transform=annotation_treatment.transform)
                note_index_size = (note_index_leading + note_index_width + note_index_trailing, size * line_height)
                note_index_obstacles = [LabelObstacle(item.placement_id, LabelRect(*_bounds(item.bounds)))
                                        for item in text
                                        if item.required and item.overflow != "suppressed"
                                        and item.collision_domain == CollisionDomain("timeline", "overlay")]
                note_index = place_label(
                    anchor_bounds, note_index_size, ("end", "start", "above", "below"),
                    bounds=LabelRect(*timeline_bounds), obstacles=note_index_obstacles,
                    gap=max(1.0, size * 0.25), required=False, overflow="suppress",
                )
                if note_index is None:
                    diagnostics.append(f"W_LAYOUT_NOTE_INDEX_SUPPRESSED:{annotation_id}")
                    continue
                note_index_inline = note_index.bounds.x
                note_index_text = place_text(placement_id=f"note-index:{annotation_id}", source_ref=annotation_id,
                                             content=note_index_content, inline=note_index_inline + note_index_leading,
                                             baseline_block=note_index.bounds.y + size, typography_role="annotation",
                                             theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                                             collision_region="annotations",
                                             collision_domain=CollisionDomain("timeline", "overlay"))
                text.append(note_index_text)
                if note_index_visuals:
                    if not hasattr(annotation_metrics, "cap_height_at"):
                        raise LayoutError("E_FONT_METRICS_CAP_HEIGHT", next(visual.source_ref for visual, _, _, _ in note_index_visuals))
                    cap_height = float(annotation_metrics.cap_height_at(size))
                    for visual, icon, icon_width, gap in note_index_visuals:
                        inline = (note_index.bounds.x if visual.side == "leading"
                                  else note_index.bounds.x + note_index_leading + note_index_width + note_index_trailing - gap - icon_width)
                        icon_bounds = Rect(Decimal(str(inline)), Decimal(str(note_index_text.baseline[1] - cap_height
                                                                              + (cap_height - size) / 2)),
                                           Decimal(str(icon_width)), Decimal(str(size)))
                        candidate_icons.append(IconPlacement(f"visual:note-index:{annotation_id}:{visual.side}",
                                                             annotation_id, visual.source_ref, icon.icon_id, icon.kind,
                                                             icon.content_identity, icon.viewport, icon.payload, icon.alternative,
                                                             visual.decorative, icon_bounds, "labelVisual",
                                                             icon_width / icon.viewport[0], annotation_slot.slot_id))
            if box.leader_required and presentation.leader_semantic_id is not None:
                target = nearest_box_port(bounds, (anchor_bounds.x + anchor_bounds.width / 2, anchor_bounds.y + anchor_bounds.height / 2))
                source = (anchor_bounds.x + anchor_bounds.width / 2, anchor_bounds.y + anchor_bounds.height / 2)
                leader_fallback = False
                try:
                    points = route_annotation_leader(source, target, obstacles=placed_boxes[:-1], limit=1024)
                except ValueError:
                    points, leader_fallback = (source, target), True
                if not relation_route_quality(tuple(points), max_bends=layout_manifest.annotation_max_bends,
                                              max_detour_ratio=layout_manifest.annotation_max_detour_ratio):
                    points, leader_fallback = (source, target), True
                leader_semantic_id = presentation.leader_semantic_id
                marker_end = (marker_geometry(request.theme_tokens.marker(semantic_binding(leader_semantic_id).theme_role))
                              if presentation.purpose == "explanatory-arrow" else None)
                placed_leader = RelationPlacement(f"annotation-leader:{annotation_id}",
                                                  f"{resolved.object_id}:{resolved.facet}:{resolved.endpoint}",
                                                  f"annotation-box:{annotation_id}", tuple(points),
                                                  semantic_id=leader_semantic_id, marker_end=marker_end,
                                                  annotation=presentation, source_ref=annotation_id)
                relations.append(placed_leader)
                if leader_fallback:
                    visible_route_fallbacks.append(placed_leader)
    text = [replace(item, slot_id=text_slot(item)) for item in text]
    text, icons = resolve_text_visual_requests(text, request, handled_sources=handled_candidate_visuals,
                                                axis_label_targets=axis_label_targets)
    icons.extend(candidate_icons)
    icons.extend(resolve_mark_visual_requests(marks, request))

    # Slot ownership is completed here with the rest of Layout geometry.  Scene
    # projection receives the relation verbatim and must never reconstruct it
    # from primitive purpose, identity, or containment.
    def shape_slot(item: Any) -> str:
        if item.semantic_id in BACKGROUND_SEMANTIC_IDS:
            return item.slot_id
        if item.placement_id.startswith("legend-swatch:"):
            return by_source["legend"].slot_id
        if item.placement_id.startswith("summary-bar:"):
            return by_source.get("summary", timeline).slot_id
        if item.placement_id.startswith("annotation-box:"):
            return by_source["annotations"].slot_id
        if item.source_ref == "timeline-axis":
            return axis.slot_id
        return timeline.slot_id
    shapes = [replace(item, slot_id=shape_slot(item)) for item in shapes]
    icons.extend(resolve_axis_band_visual_requests(shapes, request, axis_band_targets))
    relations = [replace(item, slot_id=(by_source["annotations"].slot_id
                                        if item.relation_id.startswith("annotation-leader:")
                                        else timeline.slot_id)) for item in relations]
    column_placements = tuple(
        ColumnPlacement(item.column_id, column.header,
                        Rect(Decimal(str(item.inline)), Decimal(str(table_bounds[1])),
                             Decimal(str(item.inline_size)), Decimal(str(table_bounds[3]))))
        for item, column in zip(columns, table_columns, strict=True)
    )
    _validate_background_shapes(shapes, request.theme_tokens)

    # Complete the observable fallback records at the same point as completed
    # geometry.  Neither Scene nor an adapter gets a policy question to answer.
    fit_warnings: list[FitWarning] = []
    warned_placement_ids: set[str] = set()
    timeline_end = timeline.bounds.block + timeline.bounds.block_size
    header_start = Decimal(str(table_bounds[1]))
    header_end = Decimal(str(timeline_bounds[1]))
    row_by_id = {row.row_id: row for row in rows}
    table_end = table.bounds.inline + table.bounds.inline_size
    for column in column_placements:
        if column.bounds.inline + column.bounds.inline_size > table_end + GEOMETRY_TOLERANCE:
            placement_id = f"column:{column.column_id}"
            fit_warnings.append(FitWarning(
                "W_LAYOUT_VISIBLE_OVERFLOW", placement_id, "view:tableColumns",
                "table-text", "visible-overflow", float(column.bounds.inline_size),
                float(column.bounds.block_size), max(0.0, float(table_end - column.bounds.inline)),
                float(column.bounds.block_size),
            ))
            warned_placement_ids.add(placement_id)
    for item in text:
        if (not item.placement_id.startswith(("column:", "cell:")) or item.overflow != "fit"
                or item.placement_id in warned_placement_ids):
            continue
        inline_overflow = (item.available_inline_size is not None
                           and item.bounds.inline_size > Decimal(str(item.available_inline_size)) + GEOMETRY_TOLERANCE)
        if item.placement_id.startswith("column:"):
            block_available = max(0.0, float(header_end - header_start))
            block_overflow = not _contains_block_interval(
                container_start=header_start, container_end=header_end,
                item_start=item.bounds.block, item_end=item.bounds.block + item.bounds.block_size,
            )
        else:
            object_id = item.placement_id.split(":", 2)[1]
            row = row_by_id.get(object_id) or next((candidate for candidate in rows if candidate.object_id == object_id), None)
            block_available = float(row.bounds.block_size) if row is not None else 0.0
            block_overflow = row is not None and not _contains_block_interval(
                container_start=row.bounds.block, container_end=row.bounds.block + row.bounds.block_size,
                item_start=item.bounds.block, item_end=item.bounds.block + item.bounds.block_size,
            )
        if inline_overflow or block_overflow:
            fit_warnings.append(FitWarning(
                "W_LAYOUT_VISIBLE_OVERFLOW", item.placement_id, item.source_ref,
                "table-text", "visible-overflow", float(item.bounds.inline_size),
                float(item.bounds.block_size), float(item.available_inline_size or 0), block_available,
            ))
    for row in rows:
        if row.bounds.block + row.bounds.block_size > timeline_end + GEOMETRY_TOLERANCE:
            fit_warnings.append(FitWarning(
                "W_LAYOUT_ROW_DENSITY", f"row:{row.row_id}", row.object_id,
                "review-row-density", "visible-overflow", float(row.bounds.inline_size),
                float(row.bounds.block_size), float(timeline.bounds.inline_size),
                max(0.0, float(timeline_end - row.bounds.block)),
            ))
    for mark in marks:
        if mark.bounds.block + mark.bounds.block_size > timeline_end + GEOMETRY_TOLERANCE:
            fit_warnings.append(FitWarning(
                "W_LAYOUT_MARK_OVERFLOW", mark.placement_id, mark.source_ref,
                "mark-containment", "visible-overflow", float(mark.bounds.inline_size),
                float(mark.bounds.block_size), float(timeline.bounds.inline_size),
                max(0.0, float(timeline_end - mark.bounds.block)),
            ))
    for item, available in visible_label_overflows:
        fit_warnings.append(FitWarning(
            "W_LAYOUT_LABEL_OVERFLOW", item.placement_id, item.source_ref,
            "label-collision", "visible-overflow", float(item.bounds.inline_size),
            float(item.bounds.block_size), available.width, available.height,
        ))
    for relation in visible_route_fallbacks:
        fit_warnings.append(FitWarning(
            "W_LAYOUT_ROUTE_FALLBACK", relation.relation_id, relation.source_ref,
            "relation-route", "direct-path", 0.0, 0.0,
            float(timeline.bounds.inline_size), float(timeline.bounds.block_size),
        ))
    for group_id, header, available_block in visible_group_header_overflows:
        fit_warnings.append(FitWarning(
            "W_LAYOUT_GROUP_HEADER_OVERFLOW", f"group-header:{group_id}", group_id,
            "group-header-density", "visible-overflow", float(header.inline_size),
            float(header.block_size), float(header.inline_size), available_block,
        ))
    canvas = _completed_canvas(
        requested=request.layout_manifest.viewport,
        rectangles=(tuple(slot.bounds for slot in slots) + tuple(row.bounds for row in rows)
                    + tuple(column.bounds for column in column_placements)
                    + tuple(group.content_bounds for group in groups)
                    + tuple(group.header_bounds for group in groups if group.header_bounds is not None)
                    + tuple(item.bounds for item in text) + tuple(item.bounds for item in marks)
                    + tuple(item.bounds for item in shapes) + tuple(item.bounds for item in icons)),
        paths=tuple(item.points for item in relations),
    )
    placement = SurfacePlacement(text=tuple(text), slots=slots, rows=rows, columns=column_placements,
                                 groups=tuple(groups), scale=scale,
                                 marks=tuple(marks), shapes=tuple(shapes), relations=tuple(relations),
                                 decisions=tuple(placement_decisions),
                                 axis_tier_outcomes=tuple(axis_tier_outcomes),
                                 diagnostics=tuple(diagnostics), icons=tuple(icons),
                                 canvas_bounds=canvas, fit_warnings=tuple(fit_warnings))
    placement.assert_valid()
    return SurfaceLayoutComposition(placement, tuple(review_rows), tracks)


def _rect(bounds: tuple[float, float, float, float]) -> Rect:
    return Rect(*(Decimal(str(value)) for value in bounds))


def _bounds(rect: Rect) -> tuple[float, float, float, float]:
    return (float(rect.inline), float(rect.block), float(rect.inline_size), float(rect.block_size))


def _coordinate(value: date, scale: ScalePlacement) -> float:
    return scale.origin + (value - scale.domain_start).days * scale.unit_ratio


def _folded_instance_id(folded: Any, item: Any) -> str:
    """Keep a header point's comparison members addressable without inventing rows."""
    return f"group-header:{folded.group_id}:{item.item_id or item.object_id}"


def _comparison_marks(projection: Any) -> tuple[ComparisonMark, ...]:
    marks: list[ComparisonMark] = []
    for item in projection.items:
        for facet, value in (("planned", item.planned), ("actual", item.actual)):
            if not value:
                continue
            if item.source_type == "point" and isinstance(value.get("at"), date):
                marks.append(ComparisonMark(item.object_id, facet, "point", at=value["at"]))
            elif item.source_type == "span" and isinstance(value.get("start"), date) and isinstance(value.get("end", value.get("finish")), date):
                marks.append(ComparisonMark(item.object_id, facet, "span", start=value["start"], end=value.get("end", value.get("finish"))))
    return tuple(marks)


def _annotation_anchor_bounds(mark: ComparisonMark, endpoint: str, row: RowPlacement,
                              scale: ScalePlacement) -> LabelRect:
    if endpoint == "start":
        at = mark.start
    elif endpoint == "finish":
        at = mark.end
    elif endpoint == "at":
        at = mark.at
    elif endpoint == "body":
        at = mark.at or (mark.start + (mark.end - mark.start) / 2 if mark.start and mark.end else None)
    else:
        at = None
    if not isinstance(at, date):
        raise LayoutError("E_PRESENTATION_ANCHOR_MISSING", "/annotations/anchor")
    return LabelRect(_coordinate(at, scale), float(row.bounds.block + row.bounds.block_size * Decimal("0.35")),
                     1.0, max(2.0, float(row.bounds.block_size) * 0.2))
