"""Owns final slot ownership, overflow evidence, canvas bounds, lane row anchors and catalogue patterns; reads every completed placement batch."""
from __future__ import annotations

from chrona.presentation.layout.stroke_alignment import complete_aligned_strokes

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from decimal import Decimal
from itertools import chain
from typing import Any
from chrona.presentation.layout.canvas_viewport import canvas_viewport_warning
from chrona.presentation.layout.icon_geometry import complete_icon_paths
from chrona.presentation.layout.mark_geometry import MarkFacetAbsence
from chrona.presentation.layout.model import (LayoutError, Rect)
from chrona.presentation.layout.pattern_placement import (PatternedPlacement, complete_pattern_placement)
from chrona.presentation.layout.presentation import TrackPlacement
from chrona.presentation.layout.surface_backgrounds import (
    BACKGROUND_SEMANTIC_IDS, validate_background_shapes, validate_group_header_strip_order,
)
from chrona.presentation.layout.surface_geometry import GEOMETRY_TOLERANCE
from chrona.presentation.layout.surface_lanes import build_lane_emissions, complete_hosted_text_identity
from chrona.presentation.layout.surface_quality import (
    AxisTierOutcome, ColumnPlacement, FitWarning, GroupPlacement, IconPlacement, LaneLabelSuppression,
    MarkPlacement, PlacementDecision, RelationPlacement, RowPlacement, ScalePlacement, ShapePlacement,
    SlotPlacement, SurfaceLayoutRequest, SurfacePlacement, TextPlacement,
)
from chrona.presentation.layout.canvas_texture import complete_canvas_texture
from chrona.presentation.layout.canvas_overlays import complete_canvas_overlays
from chrona.presentation.layout.frame_glyph import complete_frame_glyphs
from chrona.presentation.layout.region_frame import complete_region_frames
from chrona.presentation.layout.surface_visuals import place_axis_band_visuals
from chrona.presentation.layout.viewer_fit import stamp_surface_fits
from chrona.presentation.model.info_diagnostics import SuppressedPlotLabels
from chrona.presentation.model.semantic_registry import axis_band_semantic_ids
from chrona.presentation.model.diagnostic_sources import DiagnosticProvenance, DiagnosticSubject, table_row_subjects, review_row_subjects


@dataclass(frozen=True)
class SurfaceLayoutComposition:
    """Completed common surface geometry and the semantic rows it was derived from."""

    placement: SurfacePlacement
    review_rows: tuple[Any, ...]
    track_placements: tuple[TrackPlacement, ...]
    mark_absences: tuple[MarkFacetAbsence, ...] = ()


@dataclass(frozen=True)
class SurfaceCompletionContext:
    request: SurfaceLayoutRequest
    projection: Any
    layout_manifest: Any
    review_rows: tuple[Any, ...]
    rows: tuple[RowPlacement, ...]
    tracks: tuple[TrackPlacement, ...]
    groups: tuple[GroupPlacement, ...]
    scale: ScalePlacement
    slots: tuple[SlotPlacement, ...]
    by_source: Mapping[str, SlotPlacement]
    timeline: SlotPlacement
    axis: SlotPlacement
    table: SlotPlacement
    table_bounds: tuple[float, float, float, float]
    timeline_bounds: tuple[float, float, float, float]
    column_placements: tuple[ColumnPlacement, ...]
    text: list[TextPlacement]
    marks: list[MarkPlacement]
    shapes: list[ShapePlacement]
    relations: list[RelationPlacement]
    icons: list[IconPlacement]
    placement_decisions: list[PlacementDecision]
    axis_tier_outcomes: tuple[AxisTierOutcome, ...]
    diagnostics: list[str]
    mark_absences: tuple[Any, ...]
    axis_band_targets: Mapping[Any, Any]
    detail_panel_warnings: tuple[FitWarning, ...]
    side_content_warnings: list[FitWarning]
    text_visual_warnings: list[FitWarning]
    visible_label_overflows: list[Any]
    visible_route_fallbacks: list[RelationPlacement]
    visible_group_header_overflows: list[Any]
    lane_label_suppressions: list[LaneLabelSuppression]
    diagnostic_provenance: tuple[DiagnosticProvenance, ...] = ()
    visible_label_subjects: Mapping[str, tuple[DiagnosticSubject, ...]] = field(default_factory=dict)


def contains_block_interval(*, container_start: Decimal, container_end: Decimal,
                             item_start: Decimal, item_end: Decimal) -> bool:
    """Apply the Layout coordinate tolerance to a physical containment test."""
    return item_start >= container_start - GEOMETRY_TOLERANCE and item_end <= container_end + GEOMETRY_TOLERANCE


def completed_canvas(*, requested: Rect, rectangles: tuple[Rect, ...],
                      paths: tuple[tuple[tuple[float, float], ...], ...]) -> Rect:
    """Expand the requested canvas to contain Layout's completed geometry.

    A requested viewport is a minimum allocation.  This deliberately lives in
    the composition layer rather than in Scene or a renderer: every target
    receives the identical, already-completed extent.
    """
    inline_start, block_start = requested.inline, requested.block
    inline_end = requested.inline + requested.inline_size
    block_end = requested.block + requested.block_size
    for bounds in rectangles:
        inline_start = min(inline_start, bounds.inline)
        block_start = min(block_start, bounds.block)
        inline_end = max(inline_end, bounds.inline + bounds.inline_size)
        block_end = max(block_end, bounds.block + bounds.block_size)
    for points in paths:
        for inline, block in points:
            inline_start = min(inline_start, Decimal(str(inline)))
            block_start = min(block_start, Decimal(str(block)))
            inline_end = max(inline_end, Decimal(str(inline)))
            block_end = max(block_end, Decimal(str(block)))
    return Rect(inline_start, block_start,
                inline_end - inline_start, block_end - block_start)


_RECT_PATTERN_THEME_ROLES = {
    "missing-actual": "missing-actual",
    "progressFill": "progress-fill",
    "summaryBar": "summary-bar",
    "annotationHighlightBox": "annotation-highlight-box",
    "axisBandDecoration": "axis-band-decoration",
    "axisBandDecoration2": "axis-band-decoration2",
    "periodBand": "period-band",
    "groupBand": "group-band",
    "rowBand": "row-band",
    "groupHeaderBand": "group-header-band",
    "groupHeaderStrip": "group-header-strip",
    "groupTab": "group-tab",
    "asOfLabelChip": "as-of-label-chip",
    "memberLabelChip": "member-label-chip",
    "finishDeltaChip": "finish-delta-chip",
}


def complete_catalog_patterns(marks: tuple[MarkPlacement, ...],
                               shapes: tuple[ShapePlacement, ...],
                               theme_tokens: Any) -> tuple[PatternedPlacement, ...]:
    """Attach only allowlisted catalogue patterns to completed Rect placements."""
    optional_pattern = getattr(theme_tokens, "optional_pattern", None)
    if not callable(optional_pattern):
        return ()
    result: list[PatternedPlacement] = []
    for shape in shapes:
        # A legend key is a miniature of its mark: it carries the mark's Theme role in `source_ref` (#991).
        role = (shape.source_ref if shape.placement_id.startswith("legend-swatch:")
                and shape.source_ref in _RECT_PATTERN_THEME_ROLES.values()
                else _RECT_PATTERN_THEME_ROLES.get(shape.semantic_id))
        if shape.kind != "Rect" or role is None:
            continue
        pattern = optional_pattern(role)
        if isinstance(pattern, Mapping) and pattern.get("kind") == "catalog":
            result.append(PatternedPlacement(
                shape.placement_id,
                complete_pattern_placement(pattern, shape.bounds, shape.corner_radius),
            ))
    for mark in marks:
        role = _RECT_PATTERN_THEME_ROLES.get(mark.semantic_id)
        if role is None or mark.mark_shape != "span":
            continue
        pattern = optional_pattern(role)
        if isinstance(pattern, Mapping) and pattern.get("kind") == "catalog":
            result.append(PatternedPlacement(
                mark.placement_id,
                complete_pattern_placement(pattern, mark.bounds, mark.corner_radius),
            ))
    return tuple(result)


def complete_surface_layout(context: SurfaceCompletionContext) -> SurfaceLayoutComposition:
    """Complete slot ownership, evidence, canvas, lane anchors and patterns, then assemble the placement."""
    request = context.request
    projection = context.projection
    layout_manifest = context.layout_manifest
    review_rows = context.review_rows
    rows = context.rows
    tracks = context.tracks
    groups = context.groups
    scale = context.scale
    slots = context.slots
    by_source = context.by_source
    timeline = context.timeline
    axis = context.axis
    table = context.table
    table_bounds = context.table_bounds
    timeline_bounds = context.timeline_bounds
    column_placements = context.column_placements
    text = context.text
    marks = context.marks
    shapes = context.shapes
    relations = context.relations
    icons = list(context.icons)
    placement_decisions = context.placement_decisions
    axis_tier_outcomes = context.axis_tier_outcomes
    diagnostics = context.diagnostics
    mark_absences = context.mark_absences
    axis_band_targets = context.axis_band_targets
    detail_panel_warnings = context.detail_panel_warnings
    side_content_warnings = context.side_content_warnings
    text_visual_warnings = context.text_visual_warnings
    visible_label_overflows = context.visible_label_overflows
    visible_route_fallbacks = context.visible_route_fallbacks
    visible_group_header_overflows = context.visible_group_header_overflows
    lane_label_suppressions = context.lane_label_suppressions
    # Slot ownership is completed here with the rest of Layout geometry.  Scene
    # projection receives the relation verbatim and must never reconstruct it
    # from primitive purpose, identity, or containment.
    def shape_slot(item: Any) -> str:
        if item.semantic_id in axis_band_semantic_ids():
            return axis.slot_id
        if item.semantic_id in BACKGROUND_SEMANTIC_IDS:
            return item.slot_id
        if item.placement_id.startswith("legend-swatch:"):
            return by_source["legend"].slot_id
        if item.placement_id.startswith("summary-bar:"):
            return by_source.get("summary", timeline).slot_id
        if item.placement_id.startswith(("annotation-box:", "annotation-kind-")):
            return by_source.get("annotations", timeline).slot_id
        if item.source_ref == "timeline-axis":
            return axis.slot_id
        return timeline.slot_id
    shapes = [replace(item, slot_id=shape_slot(item)) for item in shapes]
    icons.extend(place_axis_band_visuals(tuple(shapes), request, targets=axis_band_targets).icons)
    relations = [replace(item, slot_id=(by_source.get("annotations", timeline).slot_id
                                        if item.relation_id.startswith("annotation-leader:")
                                        else by_source["legend"].slot_id
                                        if item.relation_id.startswith("legend-swatch:")
                                        else timeline.slot_id)) for item in relations]
    validate_group_header_strip_order(shapes, text)
    validate_background_shapes(shapes, request.theme_tokens)

    # Complete the observable fallback records at the same point as completed
    # geometry.  Neither Scene nor an adapter gets a policy question to answer.
    fit_warnings: list[FitWarning] = [*layout_manifest.fit_warnings, *detail_panel_warnings,
                                      *side_content_warnings, *text_visual_warnings]
    cell_subjects = table_row_subjects(context.review_rows)
    row_subjects = review_row_subjects(context.review_rows)
    project_cell_ids = {cell.object_id for cell in getattr(
        getattr(request, "surface_content", None), "table_cells", ())}
    annotation_subjects = {
        annotation.annotation_id: (DiagnosticSubject.project_object(
            annotation.subject_id, annotation.subject or None),)
        for annotation in getattr(getattr(request, "surface_content", None), "annotations", ())
        if annotation.subject_id
    }
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
            block_overflow = not contains_block_interval(
                container_start=header_start, container_end=header_end,
                item_start=item.bounds.block, item_end=item.bounds.block + item.bounds.block_size,
            )
        else:
            object_id = item.placement_id.split(":", 2)[1]
            row = row_by_id.get(object_id) or next((candidate for candidate in rows if candidate.object_id == object_id), None)
            block_available = float(row.bounds.block_size) if row is not None else 0.0
            block_overflow = row is not None and not contains_block_interval(
                container_start=row.bounds.block, container_end=row.bounds.block + row.bounds.block_size,
                item_start=item.bounds.block, item_end=item.bounds.block + item.bounds.block_size,
            )
        if inline_overflow or block_overflow:
            fit_warnings.append(FitWarning(
                "W_LAYOUT_VISIBLE_OVERFLOW", item.placement_id, item.source_ref,
                "table-text", "visible-overflow", float(item.bounds.inline_size),
                float(item.bounds.block_size), float(item.available_inline_size or 0), block_available,
                subjects=((cell_subjects[item.source_ref],)
                          if item.placement_id.startswith("cell:") and item.source_ref in cell_subjects
                          and item.source_ref in project_cell_ids else ()),
            ))
    for row in rows:
        if row.bounds.block + row.bounds.block_size > timeline_end + GEOMETRY_TOLERANCE:
            fit_warnings.append(FitWarning(
                "W_LAYOUT_ROW_DENSITY", f"row:{row.row_id}", row.object_id,
                "review-row-density", "visible-overflow", float(row.bounds.inline_size),
                float(row.bounds.block_size), float(timeline.bounds.inline_size),
                max(0.0, float(timeline_end - row.bounds.block)),
                subjects=row_subjects.get(row.row_id, ()),
            ))
    for mark in marks:
        # A legend swatch drawn as the real point-shaped primitive (#427) lives in
        # the legend slot below the plot by construction, not in the timeline; it
        # is never meant to fit inside `timeline_end` and checking it here always
        # reports a spurious overflow with `available` clamped to 0. The legend's
        # own row-height accounting is the swatch's actual containment check.
        if mark.placement_id.startswith("legend-swatch:"):
            continue
        if mark.bounds.block + mark.bounds.block_size > timeline_end + GEOMETRY_TOLERANCE:
            fit_warnings.append(FitWarning(
                "W_LAYOUT_MARK_OVERFLOW", mark.placement_id, mark.source_ref,
                "mark-containment", "visible-overflow", float(mark.bounds.inline_size),
                float(mark.bounds.block_size), float(timeline.bounds.inline_size),
                max(0.0, float(timeline_end - mark.bounds.block)),
                subjects=mark.subjects,
            ))
    for item, available in visible_label_overflows:
        fit_warnings.append(FitWarning(
            "W_LAYOUT_LABEL_OVERFLOW", item.placement_id, item.source_ref,
            "label-collision", "visible-overflow", float(item.bounds.inline_size),
            float(item.bounds.block_size), available.width, available.height,
            subjects=context.visible_label_subjects.get(
                item.placement_id, annotation_subjects.get(item.source_ref, ())),
        ))
    for relation in visible_route_fallbacks:
        fit_warnings.append(FitWarning(
            "W_LAYOUT_ROUTE_FALLBACK", relation.relation_id, relation.source_ref,
            "relation-route", "direct-path", 0.0, 0.0,
            float(timeline.bounds.inline_size), float(timeline.bounds.block_size),
            subjects=(annotation_subjects.get(relation.source_ref, ())
                      if relation.annotation is not None else ()),
        ))
    for group_id, header, available_block in visible_group_header_overflows:
        fit_warnings.append(FitWarning(
            "W_LAYOUT_GROUP_HEADER_OVERFLOW", f"group-header:{group_id}", group_id,
            "group-header-density", "visible-overflow", float(header.inline_size),
            float(header.block_size), float(header.inline_size), available_block,
        ))
    # Region frames (#889) are completed from the arranged profile; the canvas grows to contain one, never the reverse.
    frames = complete_region_frames(request.theme_tokens, layout_manifest.decisions)
    glyph_frames = complete_frame_glyphs(request.theme_tokens, layout_manifest.decisions)
    canvas_rectangles = (
        tuple((slot.slot_id, slot.bounds) for slot in slots)
        + tuple((timeline.slot_id, row.bounds) for row in rows)
        + tuple((slot.slot_id, extent) for slot, extent in zip(frames.slots, frames.extents, strict=True))
        + tuple((slot.slot_id, extent) for slot, extent in zip(glyph_frames.slots, glyph_frames.extents, strict=True))
        + tuple((table.slot_id, column.bounds) for column in column_placements)
        + tuple((timeline.slot_id, group.content_bounds) for group in groups)
        + tuple((table.slot_id, group.header_bounds) for group in groups if group.header_bounds is not None)
        + tuple((item.slot_id, item.bounds) for item in text)
        + tuple((item.slot_id, item.bounds) for item in marks)
        + tuple((item.slot_id, item.bounds) for item in shapes)
        + tuple((item.slot_id, item.bounds) for item in icons))
    canvas = completed_canvas(
        requested=request.layout_manifest.viewport,
        rectangles=tuple(bounds for _, bounds in canvas_rectangles),
        paths=tuple(item.points for item in relations),
    )
    canvas_warning = canvas_viewport_warning(
        surface_id="table-timeline", declared=request.declared_viewport, actual=canvas,
        contributors=chain(canvas_rectangles,
                           ((relation.slot_id, Rect(Decimal(str(inline)), Decimal(str(block)), Decimal(0), Decimal(0)))
                            for relation in relations for inline, block in relation.points)))
    suppressed_plot_labels = sum(item.semantic_id == "memberLabel" and item.overflow == "suppressed" for item in text)
    completed_icons = tuple(replace(icon, completed_paths=complete_icon_paths(
        icon.payload, (float(icon.bounds.inline), float(icon.bounds.block),
                       float(icon.bounds.inline_size), float(icon.bounds.block_size)), icon.stroke_scale))
        if icon.kind == "vector" else icon for icon in icons)
    if projection.lane_membership is not None:
        lane_mark_blocks: dict[str, Decimal] = {}
        for mark in marks:
            if mark.lane_row_id is not None:
                lane_mark_blocks[mark.lane_row_id] = min(
                    lane_mark_blocks.get(mark.lane_row_id, mark.bounds.block), mark.bounds.block)
        if any(row.row_id not in lane_mark_blocks for row in rows):
            raise LayoutError("E_LAYOUT_LANE_ROW_ANCHOR_INVALID", "/layout/rows")
        try:
            rows = tuple(replace(row, lane_mark_band_block=lane_mark_blocks[row.row_id]) for row in rows)
        except ValueError as error:
            raise LayoutError("E_LAYOUT_LANE_ROW_ANCHOR_INVALID", "/layout/rows",
                              "completed lane mark band falls outside its row bounds") from error
    lane_emissions = build_lane_emissions(projection, tuple(review_rows), marks, text,
                                     shapes, completed_icons, request.theme_tokens)
    # Abstract mark IDs remain Layout anchors; hosted text needs the actual
    # Scene primitive ID completed by this typed lane-emission closure.
    completed_text = complete_hosted_text_identity(tuple(text), tuple(marks), lane_emissions)
    completed_text, completed_shapes = stamp_surface_fits(
        completed_text, tuple(shapes), completed_icons, request.theme_tokens, request.font_metrics)
    shapes = list(completed_shapes)
    patterns = complete_catalog_patterns(tuple(marks), tuple(shapes), request.theme_tokens)
    # The canvas texture is ground: completed over the final canvas; Scene emits it first.
    texture = complete_canvas_texture(request.theme_tokens, canvas)
    completed_overlays = complete_canvas_overlays(request.theme_tokens, canvas)
    canvas_overlays = completed_overlays if (
        completed_overlays.pattern is not None or completed_overlays.radial is not None) else None
    # Keep each node's panel then glyph border together in profile pre-order:
    # a child's panel must not be painted below its parent's glyphs.
    frame_order = {f"layout-node:{decision.node_id}": index
                   for index, decision in enumerate(layout_manifest.decisions)}
    frame_shapes = sorted((*frames.shapes, *glyph_frames.shapes),
                          key=lambda item: frame_order[item.source_ref])
    shapes = [*frame_shapes, *shapes]
    patterns = (*frames.patterns, *patterns)
    slots = (*slots, *frames.slots, *glyph_frames.slots)
    diagnostics = [*diagnostics, *frames.diagnostics, *glyph_frames.diagnostics]
    if texture is not None:
        shapes = [texture.shape, *shapes]
        patterns = (texture.pattern, *patterns)
        slots = (*slots, texture.slot)
    placement = SurfacePlacement(text=completed_text, slots=slots, rows=rows, columns=column_placements,
                                 groups=tuple(groups), scale=scale,
                                 marks=tuple(marks), shapes=tuple(shapes), relations=tuple(relations),
                                 decisions=tuple(placement_decisions),
                                 axis_tier_outcomes=tuple(axis_tier_outcomes),
                                 diagnostics=tuple(diagnostics), icons=completed_icons,
                                 canvas_bounds=canvas, fit_warnings=tuple(fit_warnings),
                                 info_diagnostics=((SuppressedPlotLabels("table-timeline", suppressed_plot_labels),)
                                                   if suppressed_plot_labels else ()),
                                 lane_emissions=lane_emissions, patterns=patterns,
                                 lane_label_suppressions=tuple(lane_label_suppressions),
                                 aligned_strokes=complete_aligned_strokes(tuple(marks), tuple(shapes),
                                                                        lane_emissions, request.theme_tokens),
                                 canvas_overlays=canvas_overlays,
                                 diagnostic_provenance=context.diagnostic_provenance,
                                 canvas_warning=canvas_warning)
    placement.assert_valid()
    return SurfaceLayoutComposition(placement, tuple(review_rows), tracks, tuple(mark_absences))
