"""Measured presentation geometry handed from Layout to Scene."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from typing import Any, Callable, Mapping

from chrona.presentation.layout.model import LayoutError, geometry_sum
from chrona.presentation.layout.lane_allocation import LaneCandidate, LaneMark, LanePlacement, allocate_lanes
from chrona.presentation.layout.text import measure_text_width, metric_for_role
from chrona.presentation.model.projection import ObservationState, ReviewItem, ReviewRowProjection, shared_track_member_key
from chrona.presentation.model.surface_content import TableCellContent, TableColumnContent


@dataclass(frozen=True)
class TableColumnPlacement:
    column_id: str
    inline: float
    inline_size: float
    natural_inline_size: float


@dataclass(frozen=True)
class RowPlacement:
    row_id: str
    group_id: str | None
    bounds: tuple[float, float, float, float]


@dataclass(frozen=True)
class TrackPlacement:
    instance_id: str
    block: float
    actual_block: float
    block_size: float


@dataclass(frozen=True)
class MarkGeometry:
    """One role's lane-slot-relative geometry, resolved before Scene."""

    height: float
    offset: float
    paint_order: int
    corner_radius: float

    def __post_init__(self) -> None:
        if self.height <= 0 or self.offset < 0 or self.offset + self.height > 1 or not 0 <= self.corner_radius <= 0.5:
            raise LayoutError("E_LAYOUT_MARK_OVERFLOW", "/theme/markGeometry",
                              detail=f"height={self.height}; offset={self.offset}")


def mark_bounds(track: TrackPlacement, geometry: MarkGeometry) -> tuple[float, float]:
    """Return one completed block coordinate and extent within an assigned slot."""
    return track.block + track.block_size * geometry.offset, track.block_size * geometry.height


def table_cell_indent(*, grouped: bool, depth: int, inset: float, indent: float | None) -> float:
    """Return the hierarchy-column indent that a table row's cell occupies."""
    if depth and indent is None:
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources/metricValues/table.indent.inlineSize")
    return (inset if grouped else 0.0) + float(indent or 0) * depth


def table_text_measurer(theme_tokens: Any, font_metrics: Any) -> Callable[[str, str, str], float]:
    """Measure table header and cell text in its own typography role."""
    def measure(content: str, typography_role: str, orientation: str = "horizontal") -> float:
        treatment = theme_tokens.text_treatment(typography_role)
        if orientation != "horizontal":
            return float(treatment.font_size * treatment.line_height)
        return measure_text_width(content, font_size=float(treatment.font_size),
                                  font_metrics=metric_for_role(theme_tokens, typography_role, font_metrics),
                                  letter_spacing=float(treatment.letter_spacing),
                                  text_transform=treatment.transform,
                                  numeric_spacing=treatment.numeric_spacing)
    return measure


def measure_table_columns(*, columns: tuple[TableColumnContent, ...],
                          cells: tuple[TableCellContent, ...],
                          measure_text: Callable[[str, str, str], float], minimum_inline: float,
                          hierarchy_column: str | None = None,
                          cell_indents: Mapping[str, float] | None = None) -> tuple[float, ...]:
    """Return each column's natural width; the one measure for slot and columns.

    A hierarchy-column cell's extent includes its row's indent, because that
    indent is consumed from the same column allocation at placement.
    """
    indents = cell_indents or {}
    content_by_column: dict[str, list[tuple[str, str, str, float]]] = {
        column.column_id: [(column.header, "text", column.header_orientation, 0.0)] for column in columns}
    for cell in cells:
        indent = indents.get(cell.object_id, 0.0) if cell.column_id == hierarchy_column else 0.0
        content_by_column.setdefault(cell.column_id, []).append((cell.content, cell.typography_role, "horizontal", indent))
    return tuple(
        max(minimum_inline, max((measure_text(item, role, orientation) + indent
                                 for item, role, orientation, indent in content_by_column[column.column_id]),
                                default=minimum_inline) + minimum_inline)
        for column in columns
    )


def table_content_inline_size(natural_widths: tuple[float, ...], gutter: float) -> float:
    """Return the inline extent of measured columns and the gutters between them."""
    return geometry_sum(natural_widths) + gutter * max(0, len(natural_widths) - 1)


def place_table_columns(*, columns: tuple[TableColumnContent, ...],
                        cells: tuple[TableCellContent, ...],
                        bounds: tuple[float, float, float, float],
                        measure_text: Callable[[str, str, str], float], minimum_inline: float,
                        overflow: str = "visible-overflow", gutter: float = 0.0,
                        hierarchy_column: str | None = None,
                        cell_indents: Mapping[str, float] | None = None,
                        ) -> tuple[TableColumnPlacement, ...]:
    """Allocate only declared-flexible columns after measured minima close."""
    natural_widths = measure_table_columns(columns=columns, cells=cells, measure_text=measure_text,
                                           minimum_inline=minimum_inline, hierarchy_column=hierarchy_column,
                                           cell_indents=cell_indents)
    if gutter < 0:
        raise LayoutError("E_LAYOUT_TABLE_OVERFLOW", "/layoutManifest/table")
    available = bounds[2] - gutter * max(0, len(natural_widths) - 1)
    if sum(column.width.maximum == "fill" for column in columns) > 1:
        raise LayoutError("E_LAYOUT_TABLE_OVERFLOW", "/layoutManifest/table")
    ellipsis_floor = max(minimum_inline, measure_text("…", "text", "horizontal")) + minimum_inline
    minima = tuple(natural if column.width.minimum == "content" else ellipsis_floor
                   for column, natural in zip(columns, natural_widths, strict=True))
    # A normal visible-overflow table retains natural measured columns even
    # when they exceed its requested slot.  Ellipsis remains the sole compact
    # disposition and therefore still needs finite minima inside the slot.
    preferred_total = geometry_sum(natural_widths)
    base = (minima if preferred_total > available and overflow == "ellipsize-with-source"
            else natural_widths)
    flexible = tuple(index for index, column in enumerate(columns) if column.width.flexible)
    # A declared compact representation is retained where it fits.  If even
    # its measured ellipsis minima exceed the requested slot, those minima are
    # still completed visibly rather than becoming a fit refusal.
    remaining = max(0.0, available - geometry_sum(base))
    weights = geometry_sum(columns[index].width.fraction for index in flexible)
    widths = tuple(width + (remaining * columns[index].width.fraction / weights
                            if index in flexible and weights else 0.0)
                   for index, width in enumerate(base))
    cursor = bounds[0]
    placements: list[TableColumnPlacement] = []
    for column, natural, width in zip(columns, natural_widths, widths, strict=True):
        placed_width = widths[len(placements)]
        placements.append(TableColumnPlacement(column.column_id, cursor, placed_width, natural))
        cursor += placed_width + gutter
    return tuple(placements)


def table_text_line_block(theme_tokens: Any, typography_roles: Any) -> float:
    """Return the tallest line block among the table cell roles a row holds."""
    return max((float(theme_tokens.text_treatment(role).font_size * theme_tokens.text_treatment(role).line_height)
                for role in sorted(set(typography_roles))), default=0.0)


@dataclass(frozen=True)
class LaneRowsResult:
    """Group-local collision-packed rows for `rows.mode: lanes` (#467).

    ``rows`` are synthetic :class:`ReviewRowProjection` values Layout derives
    (never a View or Projection fact); ``text_line_blocks`` is each row's own
    reserved label-row footprint, for :func:`required_row_block_extents`.
    ``placements`` is keyed by item object ID and holds the lane-local ladder
    decision (level and lane-local rect) that Scene never re-derives.
    """

    rows: tuple[ReviewRowProjection, ...]
    text_line_blocks: tuple[float, ...]
    placements: Mapping[str, LanePlacement]
    mark_row_height: float
    label_row_height: float


_UNGROUPED_LANE_GROUP_KEY = "lane-ungrouped"
"""Canonical #467 packing key for `grouping.by: none` (never a View group id)."""


def lane_label_content(item: ReviewItem, label_content: tuple[str, ...]) -> str:
    """Return one lane item's required label text: title, plus a selected delta.

    Combined in exactly one string so packing measures the same text Layout
    later places (#467): items without a delta show a title only.
    """
    parts = [item.title] if "title" in label_content else []
    if "finishDelta" in label_content and item.finish_delta is not None:
        parts.append(f"{item.finish_delta:+d}d")
    return " ".join(parts) or item.title


def build_lane_rows(*, items: tuple[ReviewItem, ...], relations: tuple[Any, ...],
                    coordinate: Callable[[date], float], label_text_width: Callable[[str], float],
                    label_content: tuple[str, ...], mark_row_height: float, label_row_height: float,
                    true_mark_block_size: float,
                    clearance: float = 0.0, canvas_left: float | None = None,
                    canvas_right: float | None = None) -> LaneRowsResult:
    """Pack selected primary items into group-local lanes (#467 L2 engine).

    Predecessor preference uses only immediate finish-to-start relations
    (``source_endpoint == "end"`` and ``target_endpoint == "start"``); every
    other relation kind is ignored for packing, matching the selected design.
    A point item (``start == end``) gets a minimal finite mark width for
    packing purposes only (its own square glyph footprint approximation);
    real mark geometry is unaffected, since Scene projects it independently.

    ``mark_row_height`` sizes the packing/ladder decision only (#467 L2); the
    rendered mark uses ``true_mark_block_size`` (the same
    ``timeline.mark.blockSize`` metric `place_mark_tracks` centers within a
    row). `place_mark_tracks` always *centers* a shared mark within its
    row's full block extent, splitting the row's slack evenly above and
    below it — so each lane's own required extent must reserve *twice* its
    label rows' height (``2 * label_rows_used * label_row_height``) plus the
    true mark size, or that even split pushes a lane's own label rows into
    the row above it. This is exactly what keeps the label ladder's
    lane-local frame aligned with where the mark actually renders.
    """
    by_object_id = {item.object_id: item for item in items}
    predecessors: dict[str, list[tuple[str, str]]] = {item.object_id: [] for item in items}
    for relation in relations:
        if (relation.source_endpoint == "end" and relation.target_endpoint == "start"
                and relation.target_object_id in predecessors):
            predecessors[relation.target_object_id].append((relation.relation_id, relation.source_object_id))
    candidates: list[LaneCandidate] = []
    for item in items:
        planned = item.planned
        start_at = planned.get("start", planned.get("at"))
        end_at = planned.get("end", planned.get("at"))
        if not isinstance(start_at, date) or not isinstance(end_at, date):
            continue
        # The admitted footprint is the union of planned and actual bounds
        # (#467 design, "Identity, grouping and stable assignment"): an
        # actual observation that overruns its plan is a real geometric fact
        # the packer must not silently under-measure. Ordering stays planned
        # only, per the design's declared traversal key.
        actual = item.actual or {}
        actual_start = actual.get("start", actual.get("at"))
        actual_end = actual.get("finish", actual.get("at"))
        footprint_start = min(start_at, actual_start) if isinstance(actual_start, date) else start_at
        footprint_end = max(end_at, actual_end) if isinstance(actual_end, date) else end_at
        left, right = coordinate(footprint_start), coordinate(footprint_end)
        if right <= left:
            right = left + mark_row_height
        label_width = label_text_width(lane_label_content(item, label_content))
        # `grouping.by: none` leaves `group_id` as "" (no group header); the
        # lane allocator itself requires a non-empty, collision-free group
        # key (#467's canonical ungrouped sentinel), translated back to ""
        # below so downstream group-header logic is unaffected.
        group_key = item.group_id or _UNGROUPED_LANE_GROUP_KEY
        candidates.append(LaneCandidate(item.object_id, group_key, (start_at, end_at, item.object_id, item.object_id),
                                        LaneMark(left, right), label_width, None,
                                        tuple(predecessors.get(item.object_id, ()))))
    result = allocate_lanes(candidates, mark_row_height=mark_row_height, label_row_height=label_row_height,
                            clearance=clearance, canvas_left=canvas_left, canvas_right=canvas_right)
    rows: list[ReviewRowProjection] = []
    text_line_blocks: list[float] = []
    placements: dict[str, LanePlacement] = {}
    for lane in result.lanes:
        # Every member of a lane shares one mark level (#467): the allocator
        # already guarantees their marks do not overlap horizontally, so
        # `place_mark_tracks` must not additionally stack them into separate
        # subtracks the way default `track: stacked` items are.
        member_items = tuple(replace(by_object_id[member_id], track="shared") for member_id in lane.members)
        group_id = "" if lane.group_key == _UNGROUPED_LANE_GROUP_KEY else lane.group_key
        rows.append(ReviewRowProjection(lane.lane_id, "", group_id, lane.representative_id, member_items))
        # `place_mark_tracks` centers the shared mark within the row's full
        # extent, splitting slack evenly above and below it (see the
        # docstring above): reserve twice the label-row height so the half
        # that lands above the mark still fully covers them.
        text_line_blocks.append(2 * lane.label_rows_used * label_row_height + true_mark_block_size)
        placements.update(lane.placements)
    return LaneRowsResult(tuple(rows), tuple(text_line_blocks), placements, mark_row_height, label_row_height)


def required_row_block_extents(*, review_rows: tuple[Any, ...], row_minimum: float,
                               row_padding: float, mark_block_size: float,
                               role_geometries: Mapping[str, MarkGeometry] | None = None,
                               text_line_block: float = 0.0,
                               text_line_blocks: tuple[float, ...] | None = None) -> tuple[float, ...]:
    """Close each row's minimum before any surplus distribution occurs.

    ``row_padding`` is the row's total block padding.  It is added once to the
    mark tracks and once to the table text line the row holds (Specification
    24 section 2.1). ``text_line_block`` is the one table-wide value every row
    shares (the original #480 contract). ``text_line_blocks`` is an optional
    per-row override (#467 lane rows: each lane's own reserved label-row
    footprint differs); when given, it replaces ``text_line_block`` row by
    row and must have one entry per ``review_rows`` member.
    """
    if row_minimum <= 0 or row_padding < 0 or text_line_block < 0:
        raise LayoutError("E_LAYOUT_ROW_REQUIREMENT", "/measuredSources/metricValues/timeline.row")
    if text_line_blocks is not None and (len(text_line_blocks) != len(review_rows)
                                         or any(value < 0 for value in text_line_blocks)):
        raise LayoutError("E_LAYOUT_ROW_REQUIREMENT", "/measuredSources/metricValues/timeline.row")
    def text_requirement(index: int) -> float:
        value = text_line_blocks[index] if text_line_blocks is not None else text_line_block
        return value + row_padding if value else 0.0
    return tuple(max(row_minimum, text_requirement(index), minimum_track_block_extent(
        review_row=row, mark_block_size=mark_block_size, role_geometries=role_geometries,
    ) + row_padding) for index, row in enumerate(review_rows))


def place_rows(*, review_rows: tuple[Any, ...], timeline_bounds: tuple[float, float, float, float],
               group_header_size: float, required_block_sizes: tuple[float, ...],
               distribution: str) -> tuple[RowPlacement, ...]:
    """Allocate completed row requirements and only then distribute surplus."""
    if len(required_block_sizes) != len(review_rows) or any(size <= 0 for size in required_block_sizes):
        raise LayoutError("E_LAYOUT_ROW_REQUIREMENT", "/layoutManifest/timeline")
    if distribution not in {"pack", "fill"}:
        raise LayoutError("E_LAYOUT_ROW_DISTRIBUTION", "/layoutManifest/reviewSurface/rowDistribution")
    group_starts = tuple(
        index for index, row in enumerate(review_rows)
        if row.group_id and (index == 0 or review_rows[index - 1].group_id != row.group_id)
    )
    available = timeline_bounds[3] - group_header_size * len(group_starts)
    required = geometry_sum(required_block_sizes)
    # Requirements remain P1 geometry.  A requested timeline is a minimum
    # allocation, not a refusal boundary: surplus can be distributed only when
    # it exists, otherwise rows naturally extend the completed surface.
    surplus = ((available - required) / len(review_rows)
               if distribution == "fill" and review_rows and available >= required else 0.0)
    cursor = timeline_bounds[1]
    placements: list[RowPlacement] = []
    for index, row in enumerate(review_rows):
        if index in group_starts:
            cursor += group_header_size
        height = required_block_sizes[index] + surplus
        placements.append(RowPlacement(row.row_id, row.group_id,
                                       (timeline_bounds[0], cursor, timeline_bounds[2], height)))
        cursor += height
    return tuple(placements)


def place_mark_tracks(*, review_rows: tuple[Any, ...], row_placements: tuple[RowPlacement, ...],
                      mark_block_size: float, role_geometries: Mapping[str, MarkGeometry] | None = None) -> tuple[TrackPlacement, ...]:
    """Allocate member tracks whose completed marks are contained by their row."""
    geometries = role_geometries or {
        "planned": MarkGeometry(1.0, 0.0, 0, 0.0),
        "actual": MarkGeometry(1.0, 0.0, 1, 0.0),
        "missing-actual": MarkGeometry(1.0, 0.0, 1, 0.0),
        "snapshot": MarkGeometry(1.0, 0.0, 0, 0.0),
        "scenario": MarkGeometry(1.0, 0.0, 0, 0.0),
    }

    def require_contained(row: RowPlacement, block: float, block_size: float, *, instance_id: str, role: str) -> None:
        row_start, row_size = row.bounds[1], row.bounds[3]
        if (mark_block_size <= 0 or block < row_start or block + block_size > row_start + row_size):
            raise LayoutError("E_LAYOUT_MARK_OVERFLOW", "/theme/roles/" + role, instance_id,
                              detail=f"role={role}; block={block}; extent={block_size}")

    def has_actual(item: Any) -> bool:
        actual = getattr(item, "actual", None) or {}
        return bool((actual.get("start") is not None and actual.get("finish") is not None)
                    or (actual.get("start") is not None and actual.get("openUntil") == "asOf")
                    or actual.get("at") is not None)

    placements: list[TrackPlacement] = []
    for review_row, row in zip(review_rows, row_placements, strict=True):
        stacked_total = max(1, sum(item.track != "shared" for item in review_row.items))
        if row.bounds[3] < stacked_total * mark_block_size:
            raise LayoutError("E_LAYOUT_MARK_OVERFLOW", "/measuredSources/metricValues/timeline.mark.blockSize",
                              detail=f"lanes={stacked_total}; extent={stacked_total * mark_block_size}")
        lane_origin = row.bounds[1] + (row.bounds[3] - stacked_total * mark_block_size) / 2
        stacked_index = 0
        members = sorted(
            enumerate(review_row.items),
            key=lambda pair: shared_track_member_key(pair[1], pair[0]),
        )
        for _, item in members:
            if item.track == "shared":
                block = lane_origin
                actual_block = block
            else:
                # A lane has a fixed base mark extent.  Role geometry is
                # relative to this lane slot, never to the spare row space:
                # rows may be taller for labels, group treatment, or viewport
                # allocation without silently stretching marks.
                block = lane_origin + stacked_index * mark_block_size
                actual_block = block
                stacked_index += 1
            instance_id = f"{review_row.row_id}:{item.item_id or item.object_id}"
            source_kind = getattr(item, "source_kind", "primary")
            roles = (("actual",) if has_actual(item) else ()) if source_kind == "actual" else (
                "snapshot" if source_kind in {"snapshot", "scenario"} else "planned",)
            if source_kind == "combined" and has_actual(item):
                roles += ("actual",)
            elif source_kind in {"primary", "combined"} and item.observation_state == ObservationState.DUE_UNOBSERVED:
                roles += ("missing-actual",)
            slot_size = mark_block_size
            for role in roles:
                geometry = geometries[role]
                role_block = block + slot_size * geometry.offset
                require_contained(row, role_block, slot_size * geometry.height, instance_id=instance_id, role=role)
            placements.append(TrackPlacement(instance_id, block, actual_block, slot_size))
    return tuple(placements)


def minimum_track_block_extent(*, review_row: Any, mark_block_size: float,
                               role_geometries: Mapping[str, MarkGeometry] | None = None) -> float:
    """Find the smallest integral row block accepted by the track planner.

    This deliberately invokes ``place_mark_tracks`` rather than re-encoding
    planned/actual, milestone, shared, or stacked containment arithmetic.
    """
    def fits(block_size: float) -> bool:
        try:
            place_mark_tracks(review_rows=(review_row,), row_placements=(
                RowPlacement(str(review_row.row_id), getattr(review_row, "group_id", None),
                             (0.0, 0.0, 1.0, block_size)),
            ), mark_block_size=mark_block_size, role_geometries=role_geometries)
        except LayoutError as error:
            if error.diagnostic_id != "E_LAYOUT_MARK_OVERFLOW":
                raise
            return False
        return True

    if mark_block_size <= 0:
        raise LayoutError("E_LAYOUT_MARK_OVERFLOW", "/measuredSources/metricValues/timeline.mark.blockSize")
    upper = mark_block_size
    while not fits(upper):
        upper *= 2
    lower = 0.0
    for _ in range(48):
        middle = (lower + upper) / 2
        if fits(middle):
            upper = middle
        else:
            lower = middle
    # Render viewport dimensions are integral; round upward so the final
    # placement never loses a fractional containment boundary.
    return float(int(upper) if upper.is_integer() else int(upper) + 1)
