"""Owns table column, header and cell placement; reads the closed surface base and Table content."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any

from chrona.presentation.layout.presentation import (
    TableColumnPlacement, header_group_cell_indent, table_cell_indent, table_text_measurer, place_table_columns,
)
from chrona.presentation.layout.group_tags import header_child_lead
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.surface_base import SurfaceBaseGeometry
from chrona.presentation.layout.surface_quality import (
    CollisionDomain, ColumnPlacement, SlotPlacement, SurfaceLayoutRequest, TextPlacement, FitWarning,
)
from chrona.presentation.layout.text import (centred_text_baseline, ellipsize_text, ellipsized_text_warning, measure_text_width,
                                             metric_for_role, place_text)
from chrona.presentation.layout.table_measurement import BoundedTableMeasurement


@dataclass(frozen=True)
class SurfaceTablePlacements:
    """Ordered table columns and their completed header/cell text placements."""
    layout_columns: tuple[TableColumnPlacement, ...]
    columns: tuple[ColumnPlacement, ...]
    text: tuple[TextPlacement, ...]
    warnings: tuple[FitWarning, ...] = ()


@dataclass(frozen=True)
class SurfaceTableHeaderSeed:
    """Native columns and headers, closed independently of final row positions."""

    table_slot: SlotPlacement
    group_tag_inline_size: float
    table_bounds: tuple[float, float, float, float]
    layout_columns: tuple[TableColumnPlacement, ...]
    columns: tuple[ColumnPlacement, ...]
    header_text: tuple[TextPlacement, ...]
    cell_indents: tuple[tuple[str, float], ...]
    header_end_block: Decimal | None
    bounded_table: BoundedTableMeasurement | None = None


@dataclass(frozen=True)
class TableRowIndentIntent:
    """The row identity and hierarchy facts that affect measured table columns."""

    row_id: str
    table_subject_id: str
    group_id: str
    depth: int


def table_row_indent_intents(rows: tuple[Any, ...]) -> tuple[TableRowIndentIntent, ...]:
    """Reduce projected rows to the semantic facts needed before base row placement."""
    return tuple(TableRowIndentIntent(row.row_id, row.table_subject_id, row.group_id,
                                     int(getattr(row, "depth", 0)))
                 for row in rows)


def _table_resources(request: SurfaceLayoutRequest) -> tuple[Any, Any]:
    tokens, font_metrics = request.theme_tokens, request.font_metrics
    if tokens is None or font_metrics is None:
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources")
    return tokens, font_metrics


def prepare_table_header_seed(*, request: SurfaceLayoutRequest, table: SlotPlacement,
                              review_rows: tuple[TableRowIndentIntent, ...], metric_values: Mapping[str, Any],
                              group_tag_inline_size: float) -> SurfaceTableHeaderSeed:
    """Close native table columns/headers from allocation facts, before placed rows exist."""
    tokens, font_metrics = _table_resources(request)
    columns_intent = request.surface_content.table_columns
    cells = request.surface_content.table_cells
    table_bounds = (float(table.bounds.inline), float(table.bounds.block),
                    float(table.bounds.inline_size), float(table.bounds.block_size))
    if group_tag_inline_size:
        table_bounds = (table_bounds[0] + group_tag_inline_size, table_bounds[1],
                        table_bounds[2] - group_tag_inline_size, table_bounds[3])
    body_size = float(tokens.text_treatment("text").font_size)
    measure_table_text = table_text_measurer(tokens, font_metrics)
    header_role = tokens.table_header_role()
    header_treatment = tokens.text_treatment(header_role)
    header_size = float(header_treatment.font_size)
    header_metrics = metric_for_role(tokens, header_role, font_metrics)
    indent_token = metric_values.get("table.indent.inlineSize")
    cell_indents: dict[str, float] = {}
    hierarchy_column = request.surface_content.table_hierarchy_column
    header_lead = (header_child_lead(tokens, first_column=bool(columns_intent)
                                     and columns_intent[0].column_id == hierarchy_column)
                   if request.surface_content.table_indent_under_headers else None)
    for row in review_rows:
        indent_step = float(indent_token) if indent_token is not None else None
        row_indent = (header_group_cell_indent(grouped=bool(row.group_id), indent=indent_step, lead=header_lead)
                      if request.surface_content.table_indent_under_headers
                      else table_cell_indent(grouped=bool(row.group_id), depth=row.depth, inset=body_size,
                                             indent=indent_step))
        cell_indents[row.row_id] = cell_indents[row.table_subject_id] = row_indent
    bounded = getattr(request.measured_sources, "bounded_tables", {}).get("table")
    if bounded is not None:
        if (bounded.available_inline != table.bounds.inline_size
                or bounded.reserved_inline != Decimal(str(group_tag_inline_size))):
            raise LayoutError("E_LAYOUT_TABLE_OVERFLOW", "/table",
                              detail="bounded source closure does not match allocated table geometry")
        if tuple(item.column_id for item in bounded.columns) != tuple(item.column_id for item in columns_intent):
            raise LayoutError("E_LAYOUT_TABLE_OVERFLOW", "/table", detail="bounded source columns disagree")
        layout_columns = tuple(replace(item, inline=float(table.bounds.inline) + item.inline)
                               for item in bounded.columns)
        cell_indents = dict(bounded.cell_indents)
    else:
        layout_columns = place_table_columns(
            columns=columns_intent, cells=cells, bounds=table_bounds,
            measure_text=measure_table_text, minimum_inline=body_size,
            overflow=table.overflow,
            gutter=float(metric_values.get("table.column.gutter.inlineSize", 0)),
            hierarchy_column=hierarchy_column,
            cell_indents=cell_indents, header_role=header_role)
    positions = {item.column_id: (item.inline, item.inline_size) for item in layout_columns}
    column_widths = {item.column_id: item.inline_size for item in layout_columns}
    column_intents = {item.column_id: item for item in columns_intent}
    header_text: list[TextPlacement] = []
    closed_headers = {item.column_id: item for item in bounded.headers} if bounded is not None else {}
    for column in columns_intent:
        column_id, label = column.column_id, column.header
        available = max(0.0, column_widths[column_id] - body_size)
        closed = closed_headers.get(column_id)
        if closed is not None:
            resolved, overflow = closed.fit.content, "ellipsized" if closed.fit.ellipsized else "fit"
        else:
            resolved, overflow = _resolve_table_text(
                label, available, header_role, table.overflow, tokens, font_metrics)
        header_width = closed.fit.inline_size if closed is not None else measure_text_width(
            resolved, font_size=header_size, font_metrics=header_metrics,
            letter_spacing=float(header_treatment.letter_spacing),
            text_transform=header_treatment.transform,
            numeric_spacing=header_treatment.numeric_spacing)
        if column.header_orientation == "rotate-cw":
            baseline = table_bounds[1]
        elif column.header_orientation == "rotate-ccw":
            baseline = table_bounds[1] + header_width
        else:
            baseline = table_bounds[1] + header_size
        header_text.append(place_text(
            placement_id=f"column:{column_id}", source_ref="view:tableColumns", content=resolved,
            inline=_aligned_inline(resolved, column_id, positions[column_id][0], available,
                                   header_role, column.header_orientation, measure_table_text, column_intents,
                                   measured_width=(float(header_treatment.font_size * header_treatment.line_height)
                                                   if column.header_orientation != "horizontal" else closed.fit.inline_size)
                                   if closed is not None else None),
            baseline_block=baseline, typography_role=header_role, theme_tokens=tokens,
            font_metrics=font_metrics, overflow=overflow, collision_region="table",
            collision_domain=CollisionDomain("table", "header"), source_content=label,
            available_inline_start=positions[column_id][0], available_inline_size=available,
            orientation=column.header_orientation,
            lines=closed.fit.lines if closed is not None else None))
    column_placements = tuple(
        ColumnPlacement(item.column_id, column.header,
                        Rect(Decimal(str(item.inline)), Decimal(str(table_bounds[1])),
                             Decimal(str(item.inline_size)), Decimal(str(table_bounds[3]))))
        for item, column in zip(layout_columns, columns_intent, strict=True)
    )
    end = max((item.bounds.block + item.bounds.block_size for item in header_text), default=None)
    return SurfaceTableHeaderSeed(table, group_tag_inline_size, table_bounds,
                                  tuple(layout_columns), column_placements,
                                  tuple(header_text), tuple(cell_indents.items()), end, bounded)


def compose_table(base: SurfaceBaseGeometry, *, seed: SurfaceTableHeaderSeed | None = None) -> SurfaceTablePlacements:
    """Place columns and table text from the completed row/slot geometry."""
    request = base.request
    tokens, font_metrics = _table_resources(request)
    columns_intent = request.surface_content.table_columns
    cells = request.surface_content.table_cells
    table = base.table
    rows = base.rows
    body_size = float(tokens.text_treatment("text").font_size)
    measure_table_text = table_text_measurer(tokens, font_metrics)
    seed = seed or prepare_table_header_seed(
        request=request, table=table, review_rows=table_row_indent_intents(base.review_rows),
        metric_values=base.metric_values, group_tag_inline_size=base.group_tag_inline_size)
    layout_columns = seed.layout_columns
    positions = {item.column_id: (item.inline, item.inline_size) for item in layout_columns}
    column_widths = {item.column_id: item.inline_size for item in layout_columns}
    column_intents = {item.column_id: item for item in columns_intent}
    cell_indents = dict(seed.cell_indents)
    text: list[TextPlacement] = list(seed.header_text)
    closed_cells = ({(item.source_ref, item.column_id): item for item in seed.bounded_table.cells}
                    if seed.bounded_table is not None else {})

    row_by_subject = {item.row_id: item for item in rows} | {item.object_id: item for item in rows}
    for cell in cells:
        object_id, column_id, content, typography_role = cell.object_id, cell.column_id, cell.content, cell.typography_role
        row = row_by_subject.get(object_id)
        position = positions.get(column_id)
        if row is not None and position is not None and column_id in column_intents:
            treatment = tokens.text_treatment(typography_role)
            indent = ((cell_indents.get(object_id, 0) if seed.bounded_table is not None else cell_indents[object_id])
                      if column_id == request.surface_content.table_hierarchy_column else 0)
            available = max(0.0, column_widths[column_id] - indent - body_size)
            closed = closed_cells.get((object_id, column_id))
            if closed is not None:
                resolved, overflow = closed.fit.content, "ellipsized" if closed.fit.ellipsized else "fit"
            else:
                resolved, overflow = _resolve_table_text(
                    content, available, typography_role, table.overflow, tokens, font_metrics)
            if closed is None and overflow == "ellipsized" and (cell.affix_prefix or cell.affix_suffix):
                # The state's affix survives an ellipsis (#588): only the formatted core is cut, within the
                # width the affixes leave; when they alone do not fit, the whole string stays ellipsized.
                affix_width = measure_table_text(cell.affix_prefix + cell.affix_suffix, typography_role, "horizontal")
                core = content[len(cell.affix_prefix):len(content) - len(cell.affix_suffix)]
                if available > affix_width:
                    cut, _ = _resolve_table_text(
                        core, available - affix_width, typography_role, table.overflow, tokens, font_metrics)
                    if cut not in ("", "…"):   # an affix beside a bare ellipsis says nothing: keep the whole-string cut
                        resolved = cell.affix_prefix + cut + cell.affix_suffix
            text.append(place_text(
                placement_id=f"cell:{object_id}:{column_id}", source_ref=object_id, content=resolved,
                inline=_aligned_inline(resolved, column_id, position[0] + indent, available,
                                       typography_role, "horizontal", measure_table_text, column_intents,
                                       measured_width=closed.fit.inline_size if closed is not None else None),
                baseline_block=centred_text_baseline(
                    row.bounds, font_size=treatment.font_size, line_height=treatment.line_height)
                    - (float(closed.block_size) - float(treatment.font_size * treatment.line_height)) / 2
                    if closed is not None else centred_text_baseline(
                        row.bounds, font_size=treatment.font_size, line_height=treatment.line_height),
                typography_role=typography_role, theme_tokens=tokens, font_metrics=font_metrics,
                overflow=overflow, collision_region="table",
                collision_domain=CollisionDomain("table", f"row:{row.row_id}"), source_content=content,
                available_inline_start=position[0] + indent, available_inline_size=available,
                semantic_id=cell.semantic_id, lines=closed.fit.lines if closed is not None else None))
    warnings = tuple(warning for item in text if (warning := ellipsized_text_warning(
        item, theme_tokens=tokens, font_metrics=font_metrics, failure_kind="table-text")) is not None
    ) if seed.bounded_table is not None else ()
    return SurfaceTablePlacements(tuple(layout_columns), seed.columns, tuple(text), warnings)


def _resolve_table_text(content: str, available_inline: float, typography_role: str,
                        overflow_policy: str, tokens: Any, font_metrics: Any) -> tuple[str, str]:
    if overflow_policy != "ellipsize-with-source":
        return content, "fit"
    treatment = tokens.text_treatment(typography_role)
    metrics = metric_for_role(tokens, typography_role, font_metrics)
    resolved = ellipsize_text(
        content, available_inline=available_inline, font_size=float(treatment.font_size),
        font_metrics=metrics, letter_spacing=float(treatment.letter_spacing),
        text_transform=treatment.transform, numeric_spacing=treatment.numeric_spacing)
    return resolved, "ellipsized" if resolved != content else "fit"


def _aligned_inline(content: str, column_id: str, start: float, available_inline: float,
                    typography_role: str, orientation: str, measure_table_text: Any,
                    column_intents: Mapping[str, Any], *, measured_width: float | None = None) -> float:
    width = measured_width if measured_width is not None else measure_table_text(content, typography_role, orientation)
    align = column_intents[column_id].align
    if align == "end":
        return start + max(0.0, available_inline - width)
    if align == "center":
        return start + max(0.0, (available_inline - width) / 2)
    return start
