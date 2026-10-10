"""Owns row/folded marks and progress/summary shapes; reads base geometry, projection and Theme tokens."""
from __future__ import annotations

from dataclasses import dataclass, replace
from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Callable

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.presentation import MarkBandFrame, MarkGeometry
from chrona.presentation.layout.mark_band_allocation import MarkBandAllocation, compose_mark_band
from chrona.presentation.layout.surface_groups import (
    GroupHeaderExtentUpdate, replace_group_header_extent,
)
from chrona.presentation.layout.surface_quality import GroupPlacement, MarkPlacement, ShapePlacement
from chrona.presentation.layout.mark_geometry import MarkFacetAbsence, compose_item_marks
from chrona.presentation.model.projection import shared_track_member_key
from chrona.presentation.layout.surface_geometry import coordinate_for_date
from chrona.presentation.layout.lane_projection import (
    folded_instance_id, lane_missing_actual_visible,
)
from chrona.presentation.layout.surface_mark_visibility import (
    MarkOccurrence, MarkOccurrenceKind,
)
from chrona.presentation.model.diagnostic_sources import DiagnosticProvenance, DiagnosticSubject

if TYPE_CHECKING:
    from chrona.presentation.layout.surface_base import SurfaceBaseGeometry

MARK_GEOMETRY_ROLES = ("planned", "actual", "snapshot", "scenario", "missing-actual")
MARK_PAINT_ORDER_BASE = 100


def resolve_mark_geometries(theme_tokens: Any) -> dict[str, MarkGeometry]:
    """Close each Theme mark role to lane-relative Layout geometry."""
    def aligned_offset(height: float, alignment: str) -> float:
        return 0.0 if alignment == "start" else 1.0 - height if alignment == "end" else (1.0 - height) / 2

    result = {}
    actual_explicit_offset = False
    for role in MARK_GEOMETRY_ROLES:
        height, offset, paint_order, corner_radius = theme_tokens.mark_geometry(role)
        symbol_height, symbol_offset = theme_tokens.symbol_geometry(role)
        if role == "actual":
            actual_explicit_offset = offset is not None
        alignment_reader = getattr(theme_tokens, "mark_alignment", None)
        alignment = alignment_reader(role) if alignment_reader is not None else "center"
        completed_offset = float(offset) if offset is not None else aligned_offset(float(height), alignment)
        if offset is None:
            if symbol_height is None:
                symbol_height = (max(float(height), result["planned"].symbol_extent[1])
                                 if role == "actual" else height)
            if symbol_offset is None:
                symbol_offset = aligned_offset(float(symbol_height), alignment)
        result[role] = MarkGeometry(
            float(height), completed_offset, paint_order, float(corner_radius),
            None if symbol_height is None else float(symbol_height),
            None if symbol_offset is None else float(symbol_offset),
            physical_corner_radius=theme_tokens.optional_token(role, "cornerRadius", "radius"))
    if actual_explicit_offset:
        result["actual"] = _default_actual_symbol(result["actual"], result["planned"])
    return result


def resolve_mark_band(theme_tokens: Any, track_size: float, *,
                      role_geometries: Mapping[str, MarkGeometry] | None = None) -> MarkBandAllocation:
    """The shared closure for natural requirements, provisional and final marks."""
    stack_reader = getattr(theme_tokens, "mark_stack", None)
    return compose_mark_band(track_size=track_size,
                             role_geometries=(role_geometries if role_geometries is not None
                                              else resolve_mark_geometries(theme_tokens)),
                             stack=stack_reader() if stack_reader is not None else None)


def _default_actual_symbol(actual: MarkGeometry, planned: MarkGeometry) -> MarkGeometry:
    """An actual gate is no smaller than the planned gate unless the Theme says otherwise (#1074).

    The actual band is a thin bar, so a point mark sized from it is a speck beside the planned gate. An absent
    `symbolHeight` is the larger of the band and the planned symbol; an absent `symbolOffset`, once the symbol is
    taller than the band, centres it on the planned symbol (else it stays the band's offset). A declared value
    is kept as declared: `symbolHeight` and `symbolOffset` equal to `markHeight` and `markOffset` restore the band.
    """
    planned_offset, planned_height = planned.symbol_extent
    height = actual.symbol_height if actual.symbol_height is not None else max(actual.height, planned_height)
    offset = actual.symbol_offset
    if offset is None:
        if height <= actual.height:
            offset = actual.offset
        elif height == planned_height:
            offset = planned_offset
        else:
            offset = min(max(planned_offset + planned_height / 2 - height / 2, 0.0), 1.0 - height)
    return replace(actual, symbol_height=height, symbol_offset=offset)


@dataclass(frozen=True)
class SurfaceMarksBatch:
    """Completed source marks, progress/summary shapes and folded-host updates."""
    marks: tuple[MarkPlacement, ...]
    progress_shapes: tuple[ShapePlacement, ...]
    summary_shapes: tuple[ShapePlacement, ...]
    groups: tuple[GroupPlacement, ...]
    group_header_updates: tuple[GroupHeaderExtentUpdate, ...]
    diagnostics: tuple[str, ...]
    absences: tuple[MarkFacetAbsence, ...]
    visible_group_header_overflows: tuple[tuple[str, Rect, float], ...]
    diagnostic_provenance: tuple[DiagnosticProvenance, ...] = ()


def progress_fill_bounds(host: Rect, fraction: float,
                         inset_ratio: Decimal = Decimal(0)) -> Rect | None:
    """Complete the optional progress submark inside its already-placed host."""
    if not 0 <= fraction <= 1:
        raise LayoutError("E_PRESENTATION_PROGRESS_INVALID", "/progressFill")
    if fraction == 0:
        return None
    if inset_ratio == 0:
        return Rect(host.inline, host.block, host.inline_size * Decimal(str(fraction)), host.block_size)
    block_inset = host.block_size * inset_ratio
    inline_inset = min(block_inset, host.inline_size / 4)
    return Rect(host.inline + inline_inset, host.block + block_inset,
                (host.inline_size - 2 * inline_inset) * Decimal(str(fraction)),
                host.block_size - 2 * block_inset)


def compose_surface_marks(base: SurfaceBaseGeometry, *,
                          lane_owner: Callable[[Any, Any], tuple[str, str] | None]) -> SurfaceMarksBatch:
    """Place row and folded marks, then progress fills and summary span bars."""
    request = base.request
    projection = request.projection
    review_rows = base.review_rows
    rows, tracks = base.rows, base.tracks
    scale, timeline = base.scale, base.timeline
    role_geometries = base.role_geometries
    mark_block_size = base.mark_block_size
    contract = request.presentation_contract
    visibility_index = getattr(request, "mark_visibility_index", None)

    def prepared_selection(item: Any, *, kind: MarkOccurrenceKind,
                           container_id: str, source_kind: str, as_of: date | None):
        if visibility_index is None:
            return None
        occurrence = MarkOccurrence(kind, container_id, item.item_id or item.object_id,
                                    item.object_id, source_kind)
        return visibility_index.lookup(occurrence, projection=projection,
                                       as_of=as_of).selection

    diagnostics: list[str] = []
    diagnostic_provenance: list[DiagnosticProvenance] = []
    absences: list[MarkFacetAbsence] = []
    marks: list[MarkPlacement] = []
    track_by_id = {item.instance_id: item for item in tracks}
    allocation = getattr(base, "mark_band_allocation", None)
    if allocation is not None:
        diagnostics.extend(allocation.diagnostics)
    for review_row in review_rows:
        members = sorted(enumerate(review_row.items),
                         key=lambda pair: shared_track_member_key(pair[1], pair[0]))
        for _, item in members:
            layout_id = f"{review_row.row_id}:{item.item_id or item.object_id}"
            owner = lane_owner(review_row, item) if projection.lane_membership is not None else None
            instance_id = layout_id if projection.rows else item.object_id
            track = track_by_id[layout_id]
            frame = MarkBandFrame.from_track(track, scale, role_geometries, allocation)
            source_kind = item.source_kind if projection.rows else "combined"
            occurrence_kind = (MarkOccurrenceKind.LANE_FINAL if owner is not None else
                               MarkOccurrenceKind.ROW if projection.rows else MarkOccurrenceKind.AUTO)
            occurrence_container = owner[0] if owner is not None else (
                review_row.row_id if projection.rows else item.object_id)
            composition = compose_item_marks(
                item=item, instance_id=instance_id, source_kind=source_kind, frame=frame,
                as_of=contract.time.as_of, theme_tokens=request.theme_tokens,
                slot_id=timeline.slot_id, paint_order_base=MARK_PAINT_ORDER_BASE,
                emit_missing_actual=(lane_missing_actual_visible(projection)
                    if owner is not None else True),
                selection=prepared_selection(
                    item, kind=occurrence_kind, container_id=occurrence_container,
                    source_kind=source_kind, as_of=contract.time.as_of),
            )
            marks.extend(replace(mark, lane_row_id=owner[0], lane_member_id=owner[1],
                                 lane_source_kind=source_kind) if owner is not None else mark
                         for mark in composition.marks)
            diagnostics.extend(composition.diagnostics)
            diagnostic_provenance.extend(composition.diagnostic_provenance)
            absences.extend(composition.absences)

    groups = tuple(base.groups)
    group_by_id = {group.group_id: group for group in groups}
    updates: list[GroupHeaderExtentUpdate] = []
    visible_header_overflows: list[tuple[str, Rect, float]] = []
    folded_by_group: dict[str, list[Any]] = {}
    for folded in getattr(projection, "folded_points", ()):
        folded_by_group.setdefault(folded.group_id, []).append(folded)
    for group_id, folded_points in folded_by_group.items():
        group = group_by_id.get(group_id)
        if group is None or group.header_bounds is None:
            folded = folded_points[0]
            raise LayoutError("E_REVIEW_POINT_GROUP_HEADER_UNAVAILABLE",
                              f"/projection/foldedPoints/{folded.item.object_id}")
        pitch = allocation.outer_extent if allocation is not None else mark_block_size
        track_inset = -allocation.outer_bounds[0] if allocation is not None else 0.0
        occupied = len(folded_points) * pitch
        if occupied > float(group.header_bounds.block_size):
            expanded = Rect(group.header_bounds.inline, group.header_bounds.block,
                            group.header_bounds.inline_size, Decimal(str(occupied)))
            update = GroupHeaderExtentUpdate(group, expanded)
            updates.append(update)
            groups = replace_group_header_extent(groups, update)
            group = next(item for item in groups if item.group_id == group_id)
            group_by_id[group_id] = group
            visible_header_overflows.append((group_id, expanded,
                                             float(update.source.header_bounds.block_size)))
        first_block = float(group.header_bounds.block) + max(
            0.0, (float(group.header_bounds.block_size) - occupied) / 2)
        for track_index, folded in enumerate(sorted(
            folded_points, key=lambda point: (point.item.planned.get("at"), point.item.object_id))):
            block = first_block + track_index * pitch + track_inset
            members = sorted(enumerate(folded.all_items),
                             key=lambda pair: shared_track_member_key(pair[1], pair[0]))
            for _, item in members:
                instance_id = folded_instance_id(folded, item)
                frame = MarkBandFrame(scale, block, mark_block_size, role_geometries, allocation)
                composition = compose_item_marks(
                    item=item, instance_id=instance_id, source_kind=item.source_kind, frame=frame,
                    as_of=contract.time.as_of, theme_tokens=request.theme_tokens,
                    slot_id=timeline.slot_id, paint_order_base=MARK_PAINT_ORDER_BASE,
                    emit_missing_actual=False, emit_diagnostics=False,
                    selection=prepared_selection(
                        item, kind=MarkOccurrenceKind.FOLDED, container_id=folded.group_id,
                        source_kind=item.source_kind, as_of=contract.time.as_of),
                )
                marks.extend(composition.marks)
                diagnostics.extend(composition.diagnostics)
                diagnostic_provenance.extend(composition.diagnostic_provenance)
                absences.extend(composition.absences)

    mark_by_id = {item.placement_id: item for item in marks}
    progress_shapes: list[ShapePlacement] = []
    progress_source = request.surface_content.progress_fill_source
    if progress_source is not None:
        progress_inset, progress_radius = request.theme_tokens.progress_track("progress-fill")
        for review_row in review_rows:
            for item in review_row.items:
                if progress_source == "actual":
                    fraction, host_prefix = (item.actual or {}).get("progress"), "actual"
                else:
                    fraction, host_prefix = getattr(item, "planned_progress", None), "planned"
                if (not isinstance(fraction, (int, float)) or isinstance(fraction, bool)
                        or not 0 <= fraction <= 1):
                    continue
                layout_id = f"{review_row.row_id}:{item.item_id or item.object_id}"
                owner = lane_owner(review_row, item) if projection.lane_membership is not None else None
                instance_id = layout_id if projection.rows else item.object_id
                host = mark_by_id.get(f"{host_prefix}:{instance_id}")
                if host is None or fraction == 0:
                    continue
                bounds = progress_fill_bounds(host.bounds, float(fraction), progress_inset)
                if bounds is not None and bounds.inline_size > 0:
                    radius = float(progress_radius) * float(min(bounds.inline_size, bounds.block_size))
                    progress_shapes.append(ShapePlacement(
                        f"progress-fill:{host.placement_id}", item.object_id, "Rect", bounds,
                        required=False, slot_id=host.slot_id, clip_host_id=host.placement_id,
                        paint_order=host.paint_order + 1, corner_radius=radius,
                        semantic_id="progressFill", lane_row_id=owner[0] if owner else None,
                        lane_member_id=owner[1] if owner else None,
                        subjects=(DiagnosticSubject.project_object(item.object_id, item.title),)))

    summary_shapes: list[ShapePlacement] = []
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
        x1, x2 = coordinate_for_date(start_at, scale), coordinate_for_date(end_at, scale)
        height = float(request.theme_tokens.summary_bar_height("summary-bar")) * float(
            base.metric_values["timeline.mark.blockSize"])
        summary_shapes.append(ShapePlacement(
            f"summary-bar:{review_row.row_id}", subject.object_id, "Rect",
            Rect(Decimal(str(x1)), row.bounds.block, Decimal(str(max(1.0, x2 - x1))), Decimal(str(height))),
            semantic_id="summaryBar"))
    return SurfaceMarksBatch(tuple(marks), tuple(progress_shapes), tuple(summary_shapes), groups,
                             tuple(updates), tuple(diagnostics), tuple(absences),
                             tuple(visible_header_overflows), tuple(diagnostic_provenance))
