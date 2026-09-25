"""Measured presentation geometry handed from Layout to Scene."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from chrona.presentation.layout.model import LayoutError


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


def place_table_columns(*, columns: tuple[tuple[str, str], ...],
                        cells: tuple[tuple[str, str, str], ...],
                        bounds: tuple[float, float, float, float],
                        font_metrics: Any, font_size: float,
                        overflow: str = "diagnose", gutter: float = 0.0) -> tuple[TableColumnPlacement, ...]:
    """Measure and place columns without shrinking required text below its bounds."""
    content_by_column = {column_id: [label] for column_id, label in columns}
    for _, column_id, cell in cells:
        content_by_column.setdefault(column_id, []).append(cell)
    natural_widths = tuple(
        max(font_size, max((font_metrics.width(item, font_size)
                            for item in content_by_column.get(column_id, (label,))),
                           default=font_size) + font_size)
        for column_id, label in columns
    )
    if gutter < 0:
        raise LayoutError("E_LAYOUT_TABLE_OVERFLOW", "/layoutManifest/table")
    available = bounds[2] - gutter * max(0, len(natural_widths) - 1)
    total = sum(natural_widths)
    if available < 0 or (total > available and overflow == "diagnose"):
        raise LayoutError("E_LAYOUT_TABLE_OVERFLOW", "/layoutManifest/table")
    if total > available and overflow != "ellipsize-with-source":
        raise LayoutError("E_LAYOUT_TABLE_OVERFLOW_POLICY", "/layoutManifest/table")
    if total <= available:
        widths = natural_widths
    else:
        minimum = font_size * 2
        if minimum * len(natural_widths) > available:
            raise LayoutError("E_LAYOUT_TABLE_OVERFLOW", "/layoutManifest/table")
        remaining = available - minimum * len(natural_widths)
        excess = sum(max(0.0, width - minimum) for width in natural_widths)
        widths = tuple(minimum + remaining * max(0.0, width - minimum) / excess
                       if excess else minimum for width in natural_widths)
    cursor = bounds[0]
    placements: list[TableColumnPlacement] = []
    for (column_id, _), width in zip(columns, natural_widths, strict=True):
        placed_width = widths[len(placements)]
        placements.append(TableColumnPlacement(column_id, cursor, placed_width, width))
        cursor += placed_width + gutter
    return tuple(placements)


def place_rows(*, review_rows: tuple[Any, ...], timeline_bounds: tuple[float, float, float, float],
               group_header_size: float) -> tuple[RowPlacement, ...]:
    """Allocate group headers and rows without allowing Scene to infer geometry."""
    group_starts = tuple(
        index for index, row in enumerate(review_rows)
        if row.group_id and (index == 0 or review_rows[index - 1].group_id != row.group_id)
    )
    available = timeline_bounds[3] - group_header_size * len(group_starts)
    height = available / max(1, len(review_rows))
    cursor = timeline_bounds[1]
    placements: list[RowPlacement] = []
    for index, row in enumerate(review_rows):
        if index in group_starts:
            cursor += group_header_size
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
            key=lambda pair: (
                0,
                {"snapshot": 0, "scenario": 1, "primary": 2, "actual": 3}.get(pair[1].source_kind, 4),
            ) if pair[1].track == "shared" else (1, pair[0]),
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
            roles = ("actual",) if source_kind == "actual" else ("snapshot" if source_kind in {"snapshot", "scenario"} else "planned",)
            if source_kind in {"primary", "combined"}:
                roles += ("actual" if has_actual(item) else "missing-actual",)
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
