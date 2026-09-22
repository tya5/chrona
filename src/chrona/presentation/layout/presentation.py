"""Measured presentation geometry handed from Layout to Scene."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
                      mark_block_size: float) -> tuple[TrackPlacement, ...]:
    """Allocate member tracks before Scene emits planned or actual marks."""
    placements: list[TrackPlacement] = []
    for review_row, row in zip(review_rows, row_placements, strict=True):
        stacked_total = max(1, sum(item.track != "shared" for item in review_row.items))
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
                block = row.bounds[1] + (row.bounds[3] - mark_block_size) / 2
                actual_block = block
            else:
                track_height = row.bounds[3] / stacked_total
                block = row.bounds[1] + stacked_index * track_height + track_height * 0.25
                actual_block = block + mark_block_size * 1.25
                stacked_index += 1
            instance_id = f"{review_row.row_id}:{item.item_id or item.object_id}"
            placements.append(TrackPlacement(instance_id, block, actual_block, mark_block_size))
    return tuple(placements)
