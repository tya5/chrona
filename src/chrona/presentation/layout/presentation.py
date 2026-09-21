"""Measured presentation geometry handed from Layout to Scene."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TableColumnPlacement:
    column_id: str
    inline: float
    inline_size: float


@dataclass(frozen=True)
class RowPlacement:
    row_id: str
    group_id: str | None
    bounds: tuple[float, float, float, float]


@dataclass(frozen=True)
class TrackPlacement:
    row_id: str
    item_id: str
    inline: float
    block: float
    inline_size: float
    block_size: float


def place_table_columns(*, columns: tuple[tuple[str, str], ...],
                        cells: tuple[tuple[str, str, str], ...],
                        bounds: tuple[float, float, float, float],
                        font_metrics: Any, font_size: float) -> tuple[TableColumnPlacement, ...]:
    """Measure and place all columns before Scene text emission."""
    content_by_column = {column_id: [label] for column_id, label in columns}
    for _, column_id, cell in cells:
        content_by_column.setdefault(column_id, []).append(cell)
    natural_widths = tuple(
        max(font_size, max((font_metrics.width(item, font_size)
                            for item in content_by_column.get(column_id, (label,))),
                           default=font_size) + font_size)
        for column_id, label in columns
    )
    total = sum(natural_widths)
    scale = min(1.0, bounds[2] / total) if total else 1.0
    cursor = bounds[0]
    placements: list[TableColumnPlacement] = []
    for (column_id, _), width in zip(columns, natural_widths, strict=True):
        placed_width = width * scale
        placements.append(TableColumnPlacement(column_id, cursor, placed_width))
        cursor += placed_width
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
