"""Validated v0.5 Scene construction input boundary.

This module is intentionally renderer-neutral.  Primitive composition follows
in I27-R2; this seam ensures that it can only receive completed current inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from chrona.presentation.layout.model import LayoutError, LayoutManifest
from chrona.presentation.layout.surface_composer import compose_surface_layout
from chrona.presentation.layout.surface_quality import SurfaceLayoutRequest
from chrona.presentation.layout.sources import MeasuredSources
from chrona.presentation.model.surface_content import SurfaceContentInput
from chrona.presentation.model.presentation_contract import normalize_presentation_input
from chrona.presentation.model.semantic_registry import PrimitiveKind, semantic_binding
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.scene.model import SceneGroup, ScenePrimitive, SceneRow, SceneSlot, SceneSurface, SurfaceScaleManifest, TextLayout


class SceneBuildError(ValueError):
    """Stable diagnostic emitted before v0.5 primitive construction."""

    def __init__(self, diagnostic_id: str, path: str):
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id
        self.path = path


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
    locale: str = "en-US"


_REQUIRED_SOURCES = frozenset(("title", "table", "timeline", "timeline-axis"))


def build_scene_input(*, projection: Any, surface_content: SurfaceContentInput,
                      layout_manifest: LayoutManifest, resolved_theme: Mapping[str, Any],
                      font_metrics: Any, measured_sources: MeasuredSources,
                      capabilities: Mapping[str, bool], locale: str = "en-US") -> SceneBuildInput:
    """Bind validated v0.5 inputs without reopening authoring or legacy contracts."""
    if not isinstance(layout_manifest, LayoutManifest):
        raise SceneBuildError("E_PRESENTATION_LAYOUT_REQUIRED", "/layoutManifest")
    if not isinstance(measured_sources, MeasuredSources):
        raise SceneBuildError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources")
    sources = {decision.source for decision in layout_manifest.decisions if decision.source}
    missing = sorted(_REQUIRED_SOURCES - sources)
    if missing:
        raise SceneBuildError("E_PRESENTATION_PRIMITIVE_MISSING", "/layoutManifest/sources/" + missing[0])
    if not all(isinstance(name, str) and isinstance(enabled, bool) for name, enabled in capabilities.items()):
        raise SceneBuildError("E_PRESENTATION_CAPABILITY_SCHEMA", "/capabilities")
    return SceneBuildInput(projection, surface_content, layout_manifest,
                           ThemeTokenView(resolved_theme), font_metrics, measured_sources,
                           dict(capabilities), locale)


def compose_review_surface(value: SceneBuildInput) -> SceneSurface:
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
            capabilities=dict(value.capabilities),
        ))
    except LayoutError as error:
        raise SceneBuildError(error.diagnostic_id, error.path) from error
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
                         href: str | None = None, link_title: str | None = None) -> None:
        placed = layout_text[scene_id]
        layout = TextLayout((float(placed.bounds.inline), float(placed.bounds.block),
                             float(placed.bounds.inline_size), float(placed.bounds.block_size)),
                            placed.baseline or (float(placed.bounds.inline), float(placed.bounds.block)),
                            placed.lines, placed.font_family, placed.font_weight, placed.font_size,
                            placed.line_height, placed.font_asset_identity)
        primitives.append(ScenePrimitive(scene_id, PrimitiveKind.TEXT, placed.source_ref, "review", purpose, role, layout.bounds,
                                         text=placed.content, baseline=layout.baseline, text_layout=layout, z_order=len(primitives),
                                         href=href, link_title=link_title))
    def emit_semantic_text(scene_id: str, semantic_id: str, role: str | None = None,
                           href: str | None = None, link_title: str | None = None) -> None:
        binding = semantic_binding(semantic_id)
        emit_layout_text(scene_id, binding.purpose, role or binding.scene_role, href, link_title)

    emit_semantic_text("title", "titleText")
    for column_id, label in value.surface_content.table_columns:
        emit_semantic_text(f"column:{column_id}", "tableColumnLabel")
    for object_id, column_id, cell in value.surface_content.table_cells:
        if f"cell:{object_id}:{column_id}" in layout_text:
            href, link_title = link_for_cell(object_id, column_id)
            emit_semantic_text(f"cell:{object_id}:{column_id}", "tableCell", href=href, link_title=link_title)
    for group in groups:
        group_band = semantic_binding("groupBand")
        primitives.append(ScenePrimitive(f"group:{group.group_id}", PrimitiveKind.RECT, group.group_id, "group", group_band.purpose, group_band.scene_role,
                                         group.content_bounds, opacity=0.12, z_order=len(primitives)))
        if group.header_bounds is not None:
            header_band = semantic_binding("groupHeaderBand")
            primitives.append(ScenePrimitive(f"group-header-band:{group.group_id}", PrimitiveKind.RECT, group.group_id, "group", header_band.purpose, header_band.scene_role,
                                             group.header_bounds, opacity=0.2, z_order=len(primitives)))
            emit_semantic_text(f"group-header:{group.group_id}", "groupHeader", "text")
    calendar_binding = semantic_binding("calendarClosed")
    for placed in placed_surface.shapes:
        if placed.placement_id.startswith("calendar-closed:"):
            bounds = (float(placed.bounds.inline), float(placed.bounds.block), float(placed.bounds.inline_size), float(placed.bounds.block_size))
            primitives.append(ScenePrimitive(placed.placement_id, PrimitiveKind.RECT, "project-calendar", "calendar",
                                             calendar_binding.purpose, calendar_binding.scene_role, bounds,
                                             opacity=0.12, z_order=len(primitives)))
    mark_placements = {placement.placement_id: placement for placement in placed_surface.marks}
    for review_row, row in zip(review_rows, rows, strict=True):
      members = sorted(enumerate(review_row.items),
                       key=lambda pair: (0, {"snapshot": 0, "primary": 1, "actual": 2}.get(pair[1].source_kind, 3))
                       if pair[1].track == "shared" else (1, pair[0]))
      for _, item in members:
        layout_instance_id = f"{review_row.row_id}:{item.item_id or item.object_id}"
        instance_id = (layout_instance_id if projection.rows else item.object_id)
        source_kind = item.source_kind if projection.rows else "combined"
        href, link_title = link_for_item(item, source_kind)
        planned = item.planned
        planned_binding = semantic_binding("snapshot" if source_kind == "snapshot" else "planned")
        planned_role = planned_binding.scene_role
        planned_mark = mark_placements.get(f"planned:{instance_id}")
        if planned_mark is not None:
            bounds = (float(planned_mark.bounds.inline), float(planned_mark.bounds.block),
                      float(planned_mark.bounds.inline_size), float(planned_mark.bounds.block_size))
            if item.source_type == "point":
                primitives.append(ScenePrimitive(f"planned:{instance_id}", PrimitiveKind.SYMBOL, item.object_id, "object", planned_binding.purpose, planned_role,
                                                 bounds, projection_instance_id=instance_id, shape="diamond", z_order=len(primitives),
                                                 href=href, link_title=link_title))
            else:
                primitives.append(ScenePrimitive(f"planned:{instance_id}", PrimitiveKind.RECT, item.object_id, "object", planned_binding.purpose, planned_role,
                                                 bounds, projection_instance_id=instance_id, z_order=len(primitives),
                                                 href=href, link_title=link_title))
        actual = item.actual or {}
        actual_binding = semantic_binding("actual")
        actual_mark = mark_placements.get(f"actual:{instance_id}")
        if actual_mark is not None:
            bounds = (float(actual_mark.bounds.inline), float(actual_mark.bounds.block),
                      float(actual_mark.bounds.inline_size), float(actual_mark.bounds.block_size))
            if item.source_type == "span":
                primitives.append(ScenePrimitive(f"actual:{instance_id}", PrimitiveKind.RECT, item.object_id, "object", actual_binding.purpose, actual_binding.scene_role,
                                                 bounds, projection_instance_id=instance_id, z_order=len(primitives)))
            else:
                primitives.append(ScenePrimitive(f"actual:{instance_id}", PrimitiveKind.SYMBOL, item.object_id, "object", actual_binding.purpose, actual_binding.scene_role,
                                                 bounds, projection_instance_id=instance_id, shape="diamond", z_order=len(primitives)))
        missing_mark = mark_placements.get(f"missing-actual:{instance_id}")
        if missing_mark is not None and "missingActual" in (getattr(projection, "comparison_facets", ()) or ("missingActual",)):
            bounds = (float(missing_mark.bounds.inline), float(missing_mark.bounds.block),
                      float(missing_mark.bounds.inline_size), float(missing_mark.bounds.block_size))
            missing_binding = semantic_binding("missingActual")
            primitives.append(ScenePrimitive(f"missing-actual:{instance_id}", PrimitiveKind.RECT, item.object_id, "object", missing_binding.purpose, missing_binding.scene_role,
                                             bounds, projection_instance_id=instance_id, optional=True, z_order=len(primitives)))
        label_id = f"member-label:{instance_id}"
        if label_id in layout_text and layout_text[label_id].overflow != "suppressed":
            emit_semantic_text(label_id, "memberLabel", href=href, link_title=link_title)
        variance_id = f"variance:{instance_id}"
        if source_kind == "combined" and item.finish_delta is not None and variance_id in layout_text:
            role = "variance-behind" if item.finish_delta > 0 else "variance-ahead" if item.finish_delta < 0 else semantic_binding("finishDelta").scene_role
            emit_semantic_text(variance_id, "finishDelta", role, href, link_title)
    axis_band_binding = semantic_binding("axisBand")
    for placed in placed_surface.text:
        if placed.placement_id.startswith("axis-band:"):
            emit_semantic_text(placed.placement_id, "axisBand", "text")
    for placed in placed_surface.shapes:
        if placed.placement_id.startswith("axis:"):
            bounds = (float(placed.bounds.inline), float(placed.bounds.block), float(placed.bounds.inline_size), float(placed.bounds.block_size))
            axis_grid = semantic_binding("axisGrid")
            primitives.append(ScenePrimitive(placed.placement_id, PrimitiveKind.PATH, "timeline-axis", "axis", axis_grid.purpose, axis_grid.scene_role,
                                             bounds, points=placed.points, z_order=len(primitives)))
            label_id = "axis-label:" + placed.placement_id.removeprefix("axis:")
            if label_id in layout_text:
                emit_semantic_text(label_id, "axisLabel")
    for placed in placed_surface.shapes:
        if placed.placement_id == "as-of":
            as_of_binding = semantic_binding("asOf")
            primitives.append(ScenePrimitive("as-of", PrimitiveKind.PATH, "actual-set", "actual", as_of_binding.purpose, as_of_binding.scene_role,
                                             (float(placed.bounds.inline), float(placed.bounds.block), float(placed.bounds.inline_size), float(placed.bounds.block_size)),
                                             points=placed.points,
                                             z_order=len(primitives)))
            emit_semantic_text("as-of-label", "asOfLabel")
    annotation_binding = semantic_binding("annotation")
    legend_binding = semantic_binding("legendEntry")
    for relation in placed_surface.relations:
        if relation.suppressed or relation.relation_id.startswith("annotation-leader:"):
            continue
        source = relation.relation_id.removeprefix("relation:").split(":", 1)[0]
        dependency = semantic_binding(relation.semantic_id)
        primitives.append(ScenePrimitive(relation.relation_id, PrimitiveKind.PATH, source, "relation", dependency.purpose, dependency.scene_role,
                                         (0, 0, 0, 0), shape=str(value.theme_tokens.token("dependency", "marker", "marker")),
                                         points=relation.points, from_port_id=relation.source_port_id,
                                         to_port_id=relation.target_port_id, z_order=len(primitives)))
    for placed in placed_surface.shapes:
        bounds = (float(placed.bounds.inline), float(placed.bounds.block),
                  float(placed.bounds.inline_size), float(placed.bounds.block_size))
        if placed.placement_id.startswith("legend-swatch:"):
            primitives.append(ScenePrimitive(placed.placement_id, PrimitiveKind.RECT, placed.source_ref, "legend",
                                             legend_binding.purpose, placed.source_ref, bounds, z_order=len(primitives)))
        elif placed.placement_id.startswith("summary-bar:"):
            summary_bar = semantic_binding("summaryBar")
            primitives.append(ScenePrimitive(placed.placement_id, PrimitiveKind.RECT, placed.source_ref, "summary",
                                             summary_bar.purpose, summary_bar.scene_role, bounds, z_order=len(primitives)))
        elif placed.placement_id.startswith("annotation-box:"):
            annotation_box = semantic_binding("annotationBox")
            primitives.append(ScenePrimitive(placed.placement_id, PrimitiveKind.RECT, placed.source_ref, "annotation",
                                             annotation_box.purpose, annotation_box.scene_role,
                                             bounds, z_order=len(primitives)))
    text_roles = tuple(
        (prefix, semantic_binding(semantic_id).purpose, role or semantic_binding(semantic_id).scene_role)
        for prefix, semantic_id, role in (
            ("legend:", "legendLabel", None), ("note:", "projectNote", None),
            ("group-detail:", "groupDetail", None), ("milestone:", "milestoneDigestEntry", None),
            ("summary:", "summaryMetric", None), ("note-index:", "noteIndex", None),
            ("annotation-text:", "annotation", "annotation-text"),
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
        purpose, role, shape, layer = leader.purpose, leader.scene_role, None, "annotation"
        primitives.append(ScenePrimitive(relation.relation_id, PrimitiveKind.PATH, source, layer, purpose, role, (0, 0, 0, 0),
                                         shape=shape, points=relation.points, from_port_id=relation.source_port_id,
                                         to_port_id=relation.target_port_id, z_order=len(primitives)))
    return SceneSurface("table-timeline", slots, rows, groups, scale, tuple(primitives))
