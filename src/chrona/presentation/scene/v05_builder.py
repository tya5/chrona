"""Validated v0.5 Scene construction input boundary.

This module is intentionally renderer-neutral.  Primitive composition follows
in I27-R2; this seam ensures that it can only receive completed current inputs.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping

from chrona.presentation.layout.dependency_network import compose_dependency_network_layout
from chrona.presentation.layout.model import LayoutError, LayoutManifest
from chrona.presentation.layout.surface_composer import compose_surface_layout
from chrona.presentation.layout.surface_quality import SurfaceLayoutRequest
from chrona.presentation.layout.sources import MeasuredSources
from chrona.presentation.model.surface_content import SurfaceContentInput
from chrona.presentation.model.presentation_contract import normalize_presentation_input
from chrona.presentation.model.semantic_registry import PrimitiveKind, inside_member_label_semantic, semantic_binding
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.scene.mark_geometry import pattern_geometry, pattern_kind, symbol_geometry
from chrona.presentation.scene.model import SceneColumn, SceneGroup, SceneIconPath, ScenePrimitive, SceneRow, SceneSlot, SceneSurface, SurfaceScaleManifest, TextLayout
from chrona.presentation.scene.paint import PaintFamily, ScenePaintError, resolve_scene_paint
from chrona.presentation.scene.visual_capabilities import VisualProfile


class SceneBuildError(ValueError):
    """Stable diagnostic emitted before v0.5 primitive construction."""

    def __init__(self, diagnostic_id: str, path: str, detail: str | None = None):
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id
        self.path = path
        self.detail = detail


@dataclass(frozen=True)
class SceneBuildInput:
    """Closed current-runtime inputs for one v0.5 Scene construction."""

    projection: Any
    surface_content: SurfaceContentInput
    layout_manifest: LayoutManifest
    theme_tokens: ThemeTokenView
    font_metrics: Any
    measured_sources: MeasuredSources
    capabilities: Mapping[str, bool]
    visual_profile: VisualProfile | None = None
    locale: str = "en-US"
    viewport: tuple[float, float] = (0.0, 0.0)
    icon_assets: dict[str, Any] | None = None
    visual_requests: tuple[Any, ...] = ()


_REQUIRED_SOURCES = {
    "table-timeline": frozenset(("title", "table", "timeline", "timeline-axis")),
    "dependency-network": frozenset(("title", "network")),
}


def _paint_family(primitive: ScenePrimitive, tokens: ThemeTokenView) -> PaintFamily:
    if primitive.kind == PrimitiveKind.TEXT:
        return PaintFamily.TEXT
    if primitive.kind == PrimitiveKind.PATH:
        return PaintFamily.PATH
    pattern = tokens.optional_pattern(primitive.visual_role)
    if pattern is not None and pattern_kind(pattern) == "outline":
        return PaintFamily.OUTLINE
    if pattern is not None and pattern_kind(pattern) == "diagonal-hatch":
        return PaintFamily.HATCH
    return PaintFamily.SOLID


def _complete_surface_paint(surface: SceneSurface, tokens: ThemeTokenView, visual_profile: VisualProfile | None = None,
                            viewport: tuple[float, float] = (0.0, 0.0),
                            *, scale_target_role: str | None = None,
                            scale_paints: Mapping[str, str] | None = None,
                            scale_legend_paints: Mapping[str, str] | None = None) -> SceneSurface:
    """Attach the sole adapter-ready paint payload to every completed primitive."""
    try:
        primitives = tuple(_complete_primitive_paint(
            primitive, tokens, visual_profile, scale_target_role, scale_paints or {}, scale_legend_paints or {})
                           for primitive in surface.primitives)
        canvas = resolve_scene_paint(tokens, "background", PaintFamily.CANVAS,
                                     visual_capabilities=visual_profile.capabilities if visual_profile else None,
                                     optional_omission=visual_profile.optional_omission if visual_profile else False,
                                     gradient_bounds=(0.0, 0.0, *viewport))
    except ScenePaintError as error:
        raise SceneBuildError(error.diagnostic_id, error.path, error.detail) from error
    return replace(surface, primitives=primitives, canvas_paint=canvas)


def _complete_primitive_paint(primitive: ScenePrimitive, tokens: ThemeTokenView, visual_profile: VisualProfile | None,
                              scale_target_role: str | None, scale_paints: Mapping[str, str],
                              scale_legend_paints: Mapping[str, str]) -> ScenePrimitive:
    paint = resolve_scene_paint(tokens, primitive.visual_role, _paint_family(primitive, tokens),
                                visual_capabilities=visual_profile.capabilities if visual_profile else None,
                                optional_omission=visual_profile.optional_omission if visual_profile else False,
                                gradient_bounds=primitive.bounds)
    override = (scale_paints.get(primitive.source_ref)
                if primitive.visual_role == scale_target_role else None)
    if primitive.source_kind == "legend":
        override = scale_legend_paints.get(primitive.source_ref, override)
    completed = replace(paint, fill=override) if override is not None else paint
    treatment = tokens.optional_pattern(primitive.visual_role)
    result = replace(primitive, paint=completed,
                     pattern=pattern_geometry(treatment) if treatment is not None else None)
    if result.kind == "Icon" and result.icon_kind == "vector":
        return replace(result, icon_paths=_complete_icon_paths(result, completed),
                       icon_vector=None, icon_stroke_scale=None)
    return result


def _complete_icon_paths(primitive: ScenePrimitive, paint: Any) -> tuple[SceneIconPath, ...]:
    """Close normalized icon geometry and appearance before adapter projection."""
    vector = primitive.icon_vector
    if vector is None or primitive.icon_stroke_scale is None:
        raise SceneBuildError("E_PRESENTATION_PRIMITIVE_INVALID", primitive.scene_id)
    vx, vy = vector.viewport
    x, y, width, height = primitive.bounds
    if vx <= 0 or vy <= 0 or paint.fill is None:
        raise SceneBuildError("E_PRESENTATION_PRIMITIVE_INVALID", primitive.scene_id)
    paths = []
    for path in vector.paths:
        commands = tuple((command.kind, tuple((x + px * width / vx, y + py * height / vy)
                                               for px, py in command.points))
                         for command in path.commands)
        if path.paint == "fill":
            paths.append(SceneIconPath(commands, paint.fill, None, None, opacity=paint.opacity))
        elif (path.paint == "stroke" and path.stroke_width is not None
              and path.line_cap in {"butt", "round", "square"}
              and path.line_join in {"miter", "round", "bevel"}):
            paths.append(SceneIconPath(commands, None, paint.fill,
                                       path.stroke_width * primitive.icon_stroke_scale,
                                       path.line_cap, path.line_join, paint.opacity))
        else:
            raise SceneBuildError("E_PRESENTATION_PRIMITIVE_INVALID", primitive.scene_id)
    return tuple(paths)


def build_scene_input(*, projection: Any, surface_content: SurfaceContentInput,
                      layout_manifest: LayoutManifest, resolved_theme: Mapping[str, Any],
                      font_metrics: Any, measured_sources: MeasuredSources,
                      capabilities: Mapping[str, bool], locale: str = "en-US",
                      visual_profile: VisualProfile | None = None,
                      viewport: tuple[float, float] = (0.0, 0.0),
                      icon_assets: dict[str, Any] | None = None,
                      visual_requests: tuple[Any, ...] = ()) -> SceneBuildInput:
    """Bind validated v0.5 inputs without reopening authoring or legacy contracts."""
    if not isinstance(layout_manifest, LayoutManifest):
        raise SceneBuildError("E_PRESENTATION_LAYOUT_REQUIRED", "/layoutManifest")
    if not isinstance(measured_sources, MeasuredSources):
        raise SceneBuildError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources")
    surface = getattr(projection, "surface", "table-timeline")
    if surface not in _REQUIRED_SOURCES:
        raise SceneBuildError("E_PRESENTATION_SURFACE_UNSUPPORTED", "/projection/surface")
    required_sources = {decision.source for decision in layout_manifest.decisions
                        if decision.source and decision.priority in {None, "required"}}
    missing = sorted(_REQUIRED_SOURCES[surface] - required_sources)
    if missing:
        raise SceneBuildError("E_PRESENTATION_PRIMITIVE_MISSING", "/layoutManifest/sources/" + missing[0])
    if surface == "dependency-network":
        table_sources = {"table", "timeline", "timeline-axis"}
        if required_sources & table_sources:
            raise SceneBuildError("E_PRESENTATION_SURFACE_SLOT_SET", "/layoutManifest/sources")
    if not all(isinstance(name, str) and isinstance(enabled, bool) for name, enabled in capabilities.items()):
        raise SceneBuildError("E_PRESENTATION_CAPABILITY_SCHEMA", "/capabilities")
    return SceneBuildInput(projection, surface_content, layout_manifest,
                           ThemeTokenView(resolved_theme), font_metrics, measured_sources,
                           dict(capabilities), visual_profile, locale, viewport, icon_assets, visual_requests)


def compose_review_surface(value: SceneBuildInput) -> SceneSurface:
    """Dispatch a typed surface intent to an adapter of completed Layout output."""
    surface = getattr(value.projection, "surface", "table-timeline")
    if surface == "table-timeline":
        return _complete_surface_paint(_compose_table_timeline_surface(value), value.theme_tokens, value.visual_profile, value.viewport,
                                       scale_target_role=value.surface_content.scale_target_role,
                                       scale_paints=dict(value.surface_content.scale_paints),
                                       scale_legend_paints=dict(value.surface_content.scale_legend_paints))
    if surface == "dependency-network":
        return _complete_surface_paint(_compose_dependency_network_surface(value), value.theme_tokens, value.visual_profile, value.viewport)
    raise SceneBuildError("E_PRESENTATION_SURFACE_UNSUPPORTED", "/projection/surface")


def _compose_table_timeline_surface(value: SceneBuildInput) -> SceneSurface:
    """Build the core, fully measured table/timeline surface from the frozen closure."""
    projection = value.projection
    if not hasattr(projection, "items") or not hasattr(projection, "window"):
        raise SceneBuildError("E_PRESENTATION_PROJECTION_REQUIRED", "/projection")
    metric = value.measured_sources.metric_values
    contract = normalize_presentation_input(value.surface_content)
    if "text.body.size" not in metric or "text.body.lineHeight" not in metric:
        raise SceneBuildError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources/metricValues")
    try:
        composition = compose_surface_layout(SurfaceLayoutRequest(
            projection=projection, presentation_contract=contract,
            surface_content=value.surface_content, layout_manifest=value.layout_manifest,
            measured_sources=value.measured_sources, theme_tokens=value.theme_tokens,
            font_metrics=value.font_metrics, locale=value.locale,
            capabilities=dict(value.capabilities), icon_assets=value.icon_assets or {},
            visual_requests=value.visual_requests,
        ))
    except LayoutError as error:
        raise SceneBuildError(error.diagnostic_id, error.path, error.detail) from error
    placed_surface = composition.placement
    slots = tuple(SceneSlot(item.slot_id, item.source_ref, item.scale_id,
                            (float(item.bounds.inline), float(item.bounds.block),
                             float(item.bounds.inline_size), float(item.bounds.block_size)),
                            item.priority, item.overflow)
                  for item in placed_surface.slots)
    by_source = {slot.source: slot for slot in slots}
    table, timeline, axis, title_slot = (by_source[name] for name in ("table", "timeline", "timeline-axis", "title"))
    review_rows = composition.review_rows
    rows = tuple(
        SceneRow(placement.object_id, placement.group_id,
                 (float(placement.bounds.inline), float(placement.bounds.block),
                  float(placement.bounds.inline_size), float(placement.bounds.block_size)), placement.row_id)
        for placement in placed_surface.rows
    )
    columns = tuple(
        SceneColumn(placement.column_id, placement.label,
                    (float(placement.bounds.inline), float(placement.bounds.block),
                     float(placement.bounds.inline_size), float(placement.bounds.block_size)))
        for placement in placed_surface.columns
    )
    groups = tuple(
        SceneGroup(item.group_id,
                   None if item.header_bounds is None else (float(item.header_bounds.inline), float(item.header_bounds.block),
                                                             float(item.header_bounds.inline_size), float(item.header_bounds.block_size)),
                   (float(item.content_bounds.inline), float(item.content_bounds.block),
                    float(item.content_bounds.inline_size), float(item.content_bounds.block_size)))
        for item in placed_surface.groups
    )
    if placed_surface.scale is None:
        raise SceneBuildError("E_PRESENTATION_LAYOUT_REQUIRED", "/layoutManifest")
    scale = SurfaceScaleManifest(placed_surface.scale.surface_id, placed_surface.scale.scale_id,
                                 placed_surface.scale.domain_start, placed_surface.scale.domain_end,
                                 placed_surface.scale.range_start, placed_surface.scale.range_end,
                                 placed_surface.scale.origin, placed_surface.scale.unit_ratio)
    primitives: list[ScenePrimitive] = []
    layout_text = {item.placement_id: item for item in placed_surface.text}
    primary_links = {
        item.object_id: item.link for item in projection.items
        if item.link is not None
    }
    table_cells = {
        (row_id, column_id): (object_id, is_primary)
        for row_id, column_id, object_id, is_primary in value.surface_content.table_cell_objects
    }

    def link_for_item(item: Any, source_kind: str) -> tuple[str | None, str | None]:
        """Return row-mode metadata for a selected current item only."""
        if value.surface_content.link_mode != "row" or source_kind not in {"primary", "combined"}:
            return None, None
        link = primary_links.get(item.object_id)
        return ((link or {}).get("href"), (link or {}).get("title"))

    def link_for_cell(row_id: str, column_id: str) -> tuple[str | None, str | None]:
        """Return table metadata without inspecting placement or source geometry."""
        object_id, is_primary = table_cells.get((row_id, column_id), (None, False))
        if not is_primary:
            return None, None
        if value.surface_content.link_mode == "title" and column_id not in value.surface_content.title_link_columns:
            return None, None
        if value.surface_content.link_mode not in {"title", "row"}:
            return None, None
        link = primary_links.get(object_id)
        return ((link or {}).get("href"), (link or {}).get("title"))

    def emit_layout_text(scene_id: str, purpose: str, role: str,
                         href: str | None = None, link_title: str | None = None,
                         table_row_id: str | None = None, table_column_id: str | None = None) -> None:
        placed = layout_text[scene_id]
        layout = TextLayout((float(placed.bounds.inline), float(placed.bounds.block),
                             float(placed.bounds.inline_size), float(placed.bounds.block_size)),
                            placed.baseline or (float(placed.bounds.inline), float(placed.bounds.block)),
                            placed.lines, placed.font_family, placed.font_weight, placed.font_size,
                            placed.line_height, placed.font_asset_identity)
        primitives.append(ScenePrimitive(scene_id, PrimitiveKind.TEXT, placed.source_ref, "review", purpose, role, layout.bounds,
                                         text=placed.content, baseline=layout.baseline, text_layout=layout,
                                         href=href, link_title=link_title, table_row_id=table_row_id,
                                         table_column_id=table_column_id))
    def emit_semantic_text(scene_id: str, semantic_id: str, role: str | None = None,
                           href: str | None = None, link_title: str | None = None,
                           table_row_id: str | None = None, table_column_id: str | None = None) -> None:
        binding = semantic_binding(semantic_id)
        emit_layout_text(scene_id, binding.purpose, role or binding.scene_role, href, link_title,
                         table_row_id, table_column_id)

    emit_semantic_text("title", "titleText")
    for column_id, label in value.surface_content.table_columns:
        emit_semantic_text(f"column:{column_id}", "tableColumnLabel", table_column_id=column_id)
    row_ids = {row.object_id: row.row_id for row in rows} | {row.row_id: row.row_id for row in rows}
    for object_id, column_id, cell in value.surface_content.table_cells:
        if f"cell:{object_id}:{column_id}" in layout_text:
            href, link_title = link_for_cell(object_id, column_id)
            row_id = row_ids.get(object_id)
            if row_id is None:
                raise SceneBuildError("E_PRESENTATION_PRIMITIVE_INVALID", f"cell:{object_id}:{column_id}")
            emit_semantic_text(f"cell:{object_id}:{column_id}", "tableCell", href=href, link_title=link_title,
                               table_row_id=row_id, table_column_id=column_id)
    for group in groups:
        group_band = semantic_binding("groupBand")
        primitives.append(ScenePrimitive(f"group:{group.group_id}", PrimitiveKind.RECT, group.group_id, "group", group_band.purpose, group_band.scene_role,
                                         group.content_bounds))
        if group.header_bounds is not None:
            header_band = semantic_binding("groupHeaderBand")
            primitives.append(ScenePrimitive(f"group-header-band:{group.group_id}", PrimitiveKind.RECT, group.group_id, "group", header_band.purpose, header_band.scene_role,
                                             group.header_bounds))
            emit_semantic_text(f"group-header:{group.group_id}", "groupHeader", "text")
    calendar_binding = semantic_binding("calendarClosed")
    for placed in placed_surface.shapes:
        if placed.placement_id.startswith("calendar-closed:"):
            bounds = (float(placed.bounds.inline), float(placed.bounds.block), float(placed.bounds.inline_size), float(placed.bounds.block_size))
            primitives.append(ScenePrimitive(placed.placement_id, PrimitiveKind.RECT, "project-calendar", "calendar",
                                             calendar_binding.purpose, calendar_binding.scene_role, bounds))
    mark_placements = {placement.placement_id: placement for placement in placed_surface.marks}
    for review_row, row in zip(review_rows, rows, strict=True):
      members = sorted(enumerate(review_row.items),
                       key=lambda pair: (0, {"snapshot": 0, "scenario": 1, "primary": 2, "actual": 3}.get(pair[1].source_kind, 4))
                       if pair[1].track == "shared" else (1, pair[0]))
      for _, item in members:
        layout_instance_id = f"{review_row.row_id}:{item.item_id or item.object_id}"
        instance_id = (layout_instance_id if projection.rows else item.object_id)
        source_kind = item.source_kind if projection.rows else "combined"
        href, link_title = link_for_item(item, source_kind)
        planned = item.planned
        planned_binding = semantic_binding("snapshot" if source_kind in {"snapshot", "scenario"} else "planned")
        planned_role = planned_binding.scene_role
        planned_mark = mark_placements.get(f"planned:{instance_id}")
        if planned_mark is not None:
            bounds = (float(planned_mark.bounds.inline), float(planned_mark.bounds.block),
                      float(planned_mark.bounds.inline_size), float(planned_mark.bounds.block_size))
            if item.source_type == "point":
                primitives.append(ScenePrimitive(f"planned:{instance_id}", PrimitiveKind.SYMBOL, item.object_id, "object", planned_binding.purpose, planned_role,
                                                 bounds, symbol=symbol_geometry(value.theme_tokens.symbol(), bounds, planned_mark.path_commands),
                                                 corner_radius=planned_mark.corner_radius,
                                                 path_commands=planned_mark.path_commands,
                                                 href=href, link_title=link_title, slot_id=planned_mark.slot_id,
                                                 paint_order=planned_mark.paint_order, end_treatment=planned_mark.end_treatment))
            else:
                primitives.append(ScenePrimitive(f"planned:{instance_id}", PrimitiveKind.RECT, item.object_id, "object", planned_binding.purpose, planned_role,
                                                 bounds,
                                                 corner_radius=planned_mark.corner_radius,
                                                 href=href, link_title=link_title, slot_id=planned_mark.slot_id,
                                                 paint_order=planned_mark.paint_order, end_treatment=planned_mark.end_treatment))
        actual = item.actual or {}
        actual_binding = semantic_binding("actual")
        actual_mark = mark_placements.get(f"actual:{instance_id}")
        if actual_mark is not None:
            bounds = (float(actual_mark.bounds.inline), float(actual_mark.bounds.block),
                      float(actual_mark.bounds.inline_size), float(actual_mark.bounds.block_size))
            if item.source_type == "span":
                if actual_mark.mark_shape == "open-span":
                    primitives.append(ScenePrimitive(f"actual:{instance_id}", PrimitiveKind.SYMBOL, item.object_id, "object", actual_binding.purpose, actual_binding.scene_role,
                                                     bounds, symbol=symbol_geometry(value.theme_tokens.symbol(), bounds, actual_mark.path_commands),
                                                     corner_radius=actual_mark.corner_radius, slot_id=actual_mark.slot_id,
                                                     paint_order=actual_mark.paint_order, end_treatment=actual_mark.end_treatment))
                else:
                    primitives.append(ScenePrimitive(f"actual:{instance_id}", PrimitiveKind.RECT, item.object_id, "object", actual_binding.purpose, actual_binding.scene_role,
                                                     bounds, corner_radius=actual_mark.corner_radius, slot_id=actual_mark.slot_id,
                                                     paint_order=actual_mark.paint_order, end_treatment=actual_mark.end_treatment))
            else:
                primitives.append(ScenePrimitive(f"actual:{instance_id}", PrimitiveKind.SYMBOL, item.object_id, "object", actual_binding.purpose, actual_binding.scene_role,
                                                 bounds, symbol=symbol_geometry(value.theme_tokens.symbol(), bounds, actual_mark.path_commands), corner_radius=actual_mark.corner_radius,
                                                 path_commands=actual_mark.path_commands, slot_id=actual_mark.slot_id,
                                                 paint_order=actual_mark.paint_order, end_treatment=actual_mark.end_treatment))
        missing_mark = mark_placements.get(f"missing-actual:{instance_id}")
        if missing_mark is not None and "missingActual" in (getattr(projection, "comparison_facets", ()) or ("missingActual",)):
            bounds = (float(missing_mark.bounds.inline), float(missing_mark.bounds.block),
                      float(missing_mark.bounds.inline_size), float(missing_mark.bounds.block_size))
            missing_binding = semantic_binding("missingActual")
            primitives.append(ScenePrimitive(f"missing-actual:{instance_id}", PrimitiveKind.RECT, item.object_id, "object", missing_binding.purpose, missing_binding.scene_role,
                                             bounds, corner_radius=missing_mark.corner_radius, slot_id=missing_mark.slot_id,
                                             paint_order=missing_mark.paint_order, end_treatment=missing_mark.end_treatment))
        label_id = f"member-label:{instance_id}"
        if label_id in layout_text and layout_text[label_id].overflow != "suppressed":
            semantic_id = inside_member_label_semantic(source_kind) if layout_text[label_id].selected_rung == "inside" else "memberLabel"
            emit_semantic_text(label_id, semantic_id, href=href, link_title=link_title)
        variance_id = f"variance:{instance_id}"
        if source_kind == "combined" and item.finish_delta is not None and variance_id in layout_text:
            role = (semantic_binding("varianceBehind").scene_role if item.finish_delta > 0
                    else semantic_binding("varianceAhead").scene_role if item.finish_delta < 0
                    else semantic_binding("finishDelta").scene_role)
            emit_semantic_text(variance_id, "finishDelta", role, href, link_title)
    for folded in getattr(projection, "folded_points", ()):
        for item in folded.all_items:
            instance_id = f"group-header:{folded.group_id}:{item.item_id or item.object_id}"
            source_kind = item.source_kind
            href, link_title = link_for_item(item, source_kind)
            planned_mark = mark_placements.get(f"planned:{instance_id}")
            if planned_mark is not None:
                binding = semantic_binding("snapshot" if source_kind in {"snapshot", "scenario"} else "planned")
                bounds = (float(planned_mark.bounds.inline), float(planned_mark.bounds.block),
                          float(planned_mark.bounds.inline_size), float(planned_mark.bounds.block_size))
                primitives.append(ScenePrimitive(f"planned:{instance_id}", PrimitiveKind.SYMBOL, item.object_id, "object",
                                                 binding.purpose, binding.scene_role, bounds, symbol=symbol_geometry(value.theme_tokens.symbol(), bounds, planned_mark.path_commands),
                                                 corner_radius=planned_mark.corner_radius,
                                                 path_commands=planned_mark.path_commands, href=href, link_title=link_title,
                                                 slot_id=planned_mark.slot_id, paint_order=planned_mark.paint_order,
                                                 end_treatment=planned_mark.end_treatment))
            actual_mark = mark_placements.get(f"actual:{instance_id}")
            if actual_mark is not None:
                binding = semantic_binding("actual")
                bounds = (float(actual_mark.bounds.inline), float(actual_mark.bounds.block),
                          float(actual_mark.bounds.inline_size), float(actual_mark.bounds.block_size))
                primitives.append(ScenePrimitive(f"actual:{instance_id}", PrimitiveKind.SYMBOL, item.object_id, "object",
                                                 binding.purpose, binding.scene_role, bounds, symbol=symbol_geometry(value.theme_tokens.symbol(), bounds, actual_mark.path_commands),
                                                 corner_radius=actual_mark.corner_radius,
                                                 path_commands=actual_mark.path_commands, slot_id=actual_mark.slot_id,
                                                 paint_order=actual_mark.paint_order, end_treatment=actual_mark.end_treatment))
        label_id = f"member-label:group-header:{folded.group_id}:{folded.item.object_id}"
        if label_id in layout_text:
            semantic_id = (inside_member_label_semantic(folded.item.source_kind)
                           if layout_text[label_id].selected_rung == "inside" else "memberLabel")
            emit_semantic_text(label_id, semantic_id)
    axis_band_binding = semantic_binding("axisBand")
    for placed in placed_surface.text:
        if placed.placement_id.startswith("axis-band:"):
            emit_semantic_text(placed.placement_id, "axisBand", "text")
    for placed in placed_surface.shapes:
        if placed.placement_id.startswith("axis-band-rect:"):
            band = semantic_binding("axisBandDecoration")
            primitives.append(ScenePrimitive(placed.placement_id, PrimitiveKind.RECT, "timeline-axis", "axis", band.purpose,
                                             band.scene_role,
                                             (float(placed.bounds.inline), float(placed.bounds.block),
                                              float(placed.bounds.inline_size), float(placed.bounds.block_size))))
        if placed.placement_id.startswith("axis-grid:"):
            bounds = (float(placed.bounds.inline), float(placed.bounds.block), float(placed.bounds.inline_size), float(placed.bounds.block_size))
            axis_grid = semantic_binding("axisGridMinor" if placed.placement_id.startswith("axis-grid:minor:") else "axisGrid")
            primitives.append(ScenePrimitive(placed.placement_id, PrimitiveKind.PATH, "timeline-axis", "axis", axis_grid.purpose, axis_grid.scene_role,
                                             bounds, points=placed.points))
            _, _, level, index = placed.placement_id.split(":", 3)
            label_id = f"axis-label:{level}:{index}"
            if label_id in layout_text:
                emit_semantic_text(label_id, "axisLabel")
    for placed in placed_surface.shapes:
        if placed.placement_id == "as-of":
            as_of_binding = semantic_binding("asOf")
            primitives.append(ScenePrimitive("as-of", PrimitiveKind.PATH, "actual-set", "actual", as_of_binding.purpose, as_of_binding.scene_role,
                                             (float(placed.bounds.inline), float(placed.bounds.block), float(placed.bounds.inline_size), float(placed.bounds.block_size)),
                                             points=placed.points))
            emit_semantic_text("as-of-label", "asOfLabel")
    annotation_binding = semantic_binding("annotation")
    legend_binding = semantic_binding("legendEntry")
    for relation in placed_surface.relations:
        if relation.suppressed or relation.relation_id.startswith("annotation-leader:"):
            continue
        source = relation.relation_id.removeprefix("relation:").split(":", 1)[0]
        dependency = semantic_binding(relation.semantic_id)
        primitives.append(ScenePrimitive(relation.relation_id, PrimitiveKind.PATH, source, "relation", dependency.purpose, dependency.scene_role,
                                         (0, 0, 0, 0), marker_start=relation.marker_start, marker_end=relation.marker_end,
                                         points=relation.points, path_commands=relation.path_commands))
    for placed in placed_surface.shapes:
        bounds = (float(placed.bounds.inline), float(placed.bounds.block),
                  float(placed.bounds.inline_size), float(placed.bounds.block_size))
        if placed.placement_id.startswith("legend-swatch:"):
            role = (semantic_binding("scaleLegendEntry").scene_role
                    if placed.source_ref.startswith("scale:") else placed.source_ref)
            primitives.append(ScenePrimitive(placed.placement_id, PrimitiveKind.RECT, placed.source_ref, "legend",
                                             legend_binding.purpose, role, bounds))
        elif placed.placement_id.startswith("progress-fill:"):
            progress = semantic_binding("progressFill")
            primitives.append(ScenePrimitive(placed.placement_id, PrimitiveKind.RECT, placed.source_ref, "object",
                                             progress.purpose, progress.scene_role, bounds, slot_id=placed.slot_id,
                                             paint_order=placed.paint_order, clip_source_id=placed.clip_host_id))
        elif placed.placement_id.startswith("summary-bar:"):
            summary_bar = semantic_binding("summaryBar")
            primitives.append(ScenePrimitive(placed.placement_id, PrimitiveKind.RECT, placed.source_ref, "summary",
                                             summary_bar.purpose, summary_bar.scene_role, bounds))
        elif placed.placement_id.startswith("annotation-box:"):
            annotation_box = semantic_binding("annotationBox")
            primitives.append(ScenePrimitive(placed.placement_id, PrimitiveKind.RECT, placed.source_ref, "annotation",
                                             annotation_box.purpose, annotation_box.scene_role,
                                             bounds))
    for placed in placed_surface.icons:
        bounds = (float(placed.bounds.inline), float(placed.bounds.block),
                  float(placed.bounds.inline_size), float(placed.bounds.block_size))
        icon_binding = semantic_binding(placed.semantic_id)
        primitives.append(ScenePrimitive(placed.placement_id, PrimitiveKind.ICON, placed.source_ref, "object", icon_binding.purpose, icon_binding.scene_role, bounds,
                                         icon_kind=placed.kind, icon_asset_identity=placed.asset_identity,
                                         icon_viewport=placed.viewport,
                                         icon_vector=placed.payload if placed.kind == "vector" else None,
                                         icon_raster=placed.payload if placed.kind == "raster" else None,
                                         icon_alternative=placed.alternative, icon_decorative=placed.decorative,
                                         icon_stroke_scale=placed.stroke_scale,
                                         visual_capability_source_ref=placed.visual_capability_source_ref,
                                         slot_id=placed.slot_id))
    text_roles = tuple(
        (prefix, semantic_binding(semantic_id).purpose, role or semantic_binding(semantic_id).scene_role)
        for prefix, semantic_id, role in (
            ("legend:", "legendLabel", None), ("note:", "projectNote", None),
            ("group-detail:", "groupDetail", None), ("milestone:", "milestoneDigestEntry", None),
            ("summary:", "summaryMetric", None), ("note-index:", "noteIndex", None),
            ("annotation-text:", "annotationText", None),
            ("relation-label:", "relationLabel", None),
        ))
    for placed in placed_surface.text:
        for prefix, purpose, role in text_roles:
            if placed.placement_id.startswith(prefix):
                if ":value" in placed.placement_id:
                    figure = semantic_binding("summaryFigureValue")
                    purpose, role = figure.purpose, figure.scene_role
                elif ":caption" in placed.placement_id:
                    caption = semantic_binding("summaryFigureCaption")
                    purpose, role = caption.purpose, caption.scene_role
                elif placed.placement_id.count(":") == 1 and placed.placement_id.startswith("summary:"):
                    purpose = semantic_binding("summaryHeader").purpose
                emit_layout_text(placed.placement_id, purpose, role)
                break
    for relation in placed_surface.relations:
        if relation.suppressed or not relation.relation_id.startswith("annotation-leader:"):
            continue
        source = relation.relation_id.removeprefix("annotation-leader:")
        leader = semantic_binding("annotationLeader")
        purpose, role, layer = leader.purpose, leader.scene_role, "annotation"
        primitives.append(ScenePrimitive(relation.relation_id, PrimitiveKind.PATH, source, layer, purpose, role, (0, 0, 0, 0),
                                         points=relation.points))
    ownership = {item.placement_id: item.slot_id for item in placed_surface.text}
    ownership.update({item.placement_id: item.slot_id for item in placed_surface.marks})
    ownership.update({item.placement_id: item.slot_id for item in placed_surface.shapes})
    ownership.update({item.relation_id: item.slot_id for item in placed_surface.relations})
    ownership.update({item.placement_id: item.slot_id for item in placed_surface.icons})
    for group in groups:
        ownership[f"group:{group.group_id}"] = table.slot_id
        ownership[f"group-header-band:{group.group_id}"] = table.slot_id
    try:
        completed_primitives = tuple(replace(item, slot_id=ownership[item.scene_id]) for item in primitives)
    except KeyError as error:
        raise SceneBuildError("E_PRESENTATION_PRIMITIVE_INVALID", str(error)) from error
    return SceneSurface("table-timeline", slots, rows, groups, scale, completed_primitives, columns=columns,
                        diagnostics=placed_surface.diagnostics)


def _compose_dependency_network_surface(value: SceneBuildInput) -> SceneSurface:
    """Project completed network placements; never measure, rank, or route here."""
    projection = value.projection
    network = getattr(projection, "network", None)
    if network is None:
        raise SceneBuildError("E_PRESENTATION_PROJECTION_REQUIRED", "/projection/network")
    decisions = tuple(item for item in value.layout_manifest.decisions if item.kind == "slot" and item.source)
    by_source = {item.source: item for item in decisions}
    try:
        title, network_slot = by_source["title"], by_source["network"]
    except KeyError as error:
        raise SceneBuildError("E_PRESENTATION_PRIMITIVE_MISSING", "/layoutManifest/sources/network") from error
    try:
        placed = compose_dependency_network_layout(
            network, title_bounds=title.bounds, bounds=network_slot.bounds,
            measured_sources=value.measured_sources, writing_mode=value.layout_manifest.writing_mode,
            max_bends=value.layout_manifest.relation_max_bends,
            max_detour_ratio=value.layout_manifest.relation_max_detour_ratio)
    except LayoutError as error:
        raise SceneBuildError(error.diagnostic_id, error.path) from error
    slots = tuple(SceneSlot(item.node_id, item.source, None,
                            (float(item.bounds.inline), float(item.bounds.block),
                             float(item.bounds.inline_size), float(item.bounds.block_size)),
                            item.priority or "required", item.overflow or "diagnose")
                  for item in decisions)
    primitives: list[ScenePrimitive] = []
    title_binding = semantic_binding("titleText")
    node_binding = semantic_binding("networkNode")
    edge_bindings = {"dependency": semantic_binding("networkEdge"),
                     "dependency-critical": semantic_binding("criticalEdge")}
    def emit_text(text: Any) -> None:
        binding = title_binding
        layout = TextLayout((float(text.bounds.inline), float(text.bounds.block),
                             float(text.bounds.inline_size), float(text.bounds.block_size)),
                            text.baseline or (float(text.bounds.inline), float(text.bounds.block)),
                            text.lines, text.font_family, text.font_weight, text.font_size,
                            text.line_height, text.font_asset_identity)
        primitives.append(ScenePrimitive(text.placement_id, PrimitiveKind.TEXT, text.source_ref, "network",
                                         binding.purpose, binding.scene_role, layout.bounds, text=text.content,
                                         baseline=layout.baseline, text_layout=layout))
    title_text = next(item for item in placed.text if item.placement_id == "title")
    emit_text(title_text)
    for relation in placed.relations:
        binding = edge_bindings[relation.semantic_id]
        primitives.append(ScenePrimitive(f"network-edge:{relation.relation_id}", PrimitiveKind.PATH,
                                         relation.relation_id, "network", binding.purpose, binding.scene_role,
                                         (0, 0, 0, 0), points=relation.points))
    for node in placed.nodes:
        bounds = (float(node.bounds.inline), float(node.bounds.block),
                  float(node.bounds.inline_size), float(node.bounds.block_size))
        primitives.append(ScenePrimitive(f"network-node:{node.object_id}", PrimitiveKind.RECT, node.object_id,
                                         "network", node_binding.purpose, node_binding.scene_role, bounds))
    for text in placed.text:
        if text.placement_id != "title":
            emit_text(text)
    ownership = {item.placement_id: item.slot_id for item in placed.text}
    ownership.update({item.relation_id: item.slot_id for item in placed.relations})
    ownership.update({f"network-node:{item.object_id}": item.slot_id for item in placed.nodes})
    ownership.update({f"network-edge:{item.relation_id}": item.slot_id for item in placed.relations})
    try:
        completed_primitives = tuple(replace(item, slot_id=ownership[item.scene_id]) for item in primitives)
    except KeyError as error:
        raise SceneBuildError("E_PRESENTATION_PRIMITIVE_INVALID", str(error)) from error
    return SceneSurface("dependency-network", slots, (), (), None, completed_primitives)
