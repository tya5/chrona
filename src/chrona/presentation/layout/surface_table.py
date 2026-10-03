"""Owns table column, header and cell placement; reads the closed surface base and Table content."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from chrona.presentation.layout.presentation import (
    TableColumnPlacement, header_group_cell_indent, table_cell_indent, table_text_measurer, place_table_columns,
)
from chrona.presentation.layout.group_tags import header_child_lead
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.surface_base import SurfaceBaseGeometry
from chrona.presentation.layout.surface_quality import (
    CollisionDomain, ColumnPlacement, TextPlacement,
)
from chrona.presentation.layout.text import ellipsize_text, measure_text_width, metric_for_role, place_text


@dataclass(frozen=True)
class SurfaceTablePlacements:
    """Ordered table columns and their completed header/cell text placements."""
    layout_columns: tuple[TableColumnPlacement, ...]
    columns: tuple[ColumnPlacement, ...]
    text: tuple[TextPlacement, ...]


def compose_table(base: SurfaceBaseGeometry) -> SurfaceTablePlacements:
    """Place columns and table text from the completed row/slot geometry."""
    request = base.request
    tokens, font_metrics = request.theme_tokens, request.font_metrics
    if tokens is None or font_metrics is None:
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources")
    columns_intent = request.surface_content.table_columns
    cells = request.surface_content.table_cells
    table = base.table
    rows = base.rows
    table_bounds = base.table_bounds
    if base.group_tag_inline_size:
        # The vertical group tag column takes the table's start edge; columns are laid out in what remains (#585).
        tag = base.group_tag_inline_size
        table_bounds = (table_bounds[0] + tag, table_bounds[1], table_bounds[2] - tag, table_bounds[3])
    body_size = float(tokens.text_treatment("text").font_size)
    measure_table_text = table_text_measurer(tokens, font_metrics)
    header_role = tokens.table_header_role()
    header_treatment = tokens.text_treatment(header_role)
    header_size = float(header_treatment.font_size)
    header_metrics = metric_for_role(tokens, header_role, font_metrics)
    indent_token = base.metric_values.get("table.indent.inlineSize")
    cell_indents: dict[str, float] = {}
    hierarchy_column = request.surface_content.table_hierarchy_column
    header_lead = (header_child_lead(tokens, first_column=bool(columns_intent)
                                     and columns_intent[0].column_id == hierarchy_column)
                   if request.surface_content.table_indent_under_headers else None)
    for row in rows:
        indent_step = float(indent_token) if indent_token is not None else None
        row_indent = (header_group_cell_indent(grouped=bool(row.group_id), indent=indent_step, lead=header_lead)
                      if request.surface_content.table_indent_under_headers
                      else table_cell_indent(grouped=bool(row.group_id), depth=row.depth, inset=body_size,
                                             indent=indent_step))
        cell_indents[row.row_id] = cell_indents[row.object_id] = row_indent
    layout_columns = place_table_columns(
        columns=columns_intent, cells=cells, bounds=table_bounds,
        measure_text=measure_table_text, minimum_inline=body_size,
        overflow=table.overflow,
        gutter=float(base.metric_values.get("table.column.gutter.inlineSize", 0)),
        hierarchy_column=request.surface_content.table_hierarchy_column,
        cell_indents=cell_indents, header_role=header_role)
    positions = {item.column_id: (item.inline, item.inline_size) for item in layout_columns}
    column_widths = {item.column_id: item.inline_size for item in layout_columns}
    column_intents = {item.column_id: item for item in columns_intent}

    def metric_for(typography_role: str) -> Any:
        return metric_for_role(tokens, typography_role, font_metrics)

    def table_text(content: str, available_inline: float, typography_role: str) -> tuple[str, str]:
        if table.overflow != "ellipsize-with-source":
            return content, "fit"
        treatment = tokens.text_treatment(typography_role)
        resolved = ellipsize_text(
            content, available_inline=available_inline, font_size=float(treatment.font_size),
            font_metrics=metric_for(typography_role), letter_spacing=float(treatment.letter_spacing),
            text_transform=treatment.transform, numeric_spacing=treatment.numeric_spacing)
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

    text: list[TextPlacement] = []
    for column in columns_intent:
        column_id, label = column.column_id, column.header
        available = max(0.0, column_widths[column_id] - body_size)
        resolved, overflow = table_text(label, available, header_role)
        header_width = measure_text_width(
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
        text.append(place_text(
            placement_id=f"column:{column_id}", source_ref="view:tableColumns", content=resolved,
            inline=aligned_inline(resolved, column_id, positions[column_id][0], available, header_role,
                                 column.header_orientation), baseline_block=baseline,
            typography_role=header_role, theme_tokens=tokens, font_metrics=font_metrics,
            overflow=overflow, collision_region="table", collision_domain=CollisionDomain("table", "header"),
            source_content=label, available_inline_start=positions[column_id][0],
            available_inline_size=available, orientation=column.header_orientation))

    row_by_subject = {item.row_id: item for item in rows} | {item.object_id: item for item in rows}
    for cell in cells:
        object_id, column_id, content, typography_role = cell.object_id, cell.column_id, cell.content, cell.typography_role
        row = row_by_subject.get(object_id)
        position = positions.get(column_id)
        if row is not None and position is not None and column_id in column_intents:
            indent = (cell_indents[object_id]
                      if column_id == request.surface_content.table_hierarchy_column else 0)
            available = max(0.0, column_widths[column_id] - indent - body_size)
            resolved, overflow = table_text(content, available, typography_role)
            if overflow == "ellipsized" and (cell.affix_prefix or cell.affix_suffix):
                # The state's affix survives an ellipsis (#588): only the formatted core is cut, within the
                # width the affixes leave; when they alone do not fit, the whole string stays ellipsized.
                affix_width = measure_table_text(cell.affix_prefix + cell.affix_suffix, typography_role, "horizontal")
                core = content[len(cell.affix_prefix):len(content) - len(cell.affix_suffix)]
                if available > affix_width:
                    cut, _ = table_text(core, available - affix_width, typography_role)
                    if cut not in ("", "…"):   # an affix beside a bare ellipsis says nothing: keep the whole-string cut
                        resolved = cell.affix_prefix + cut + cell.affix_suffix
            text.append(place_text(
                placement_id=f"cell:{object_id}:{column_id}", source_ref=object_id, content=resolved,
                inline=aligned_inline(resolved, column_id, position[0] + indent, available, typography_role),
                baseline_block=_centred_cell_baseline(row.bounds, tokens.text_treatment(typography_role)),
                typography_role=typography_role, theme_tokens=tokens, font_metrics=font_metrics,
                overflow=overflow, collision_region="table",
                collision_domain=CollisionDomain("table", f"row:{row.row_id}"), source_content=content,
                available_inline_start=position[0] + indent, available_inline_size=available,
                semantic_id=cell.semantic_id))
    column_placements = tuple(
        ColumnPlacement(item.column_id, column.header,
                        Rect(Decimal(str(item.inline)), Decimal(str(table_bounds[1])),
                             Decimal(str(item.inline_size)), Decimal(str(table_bounds[3]))))
        for item, column in zip(layout_columns, columns_intent, strict=True)
    )
    return SurfaceTablePlacements(tuple(layout_columns), column_placements, tuple(text))


def _centred_cell_baseline(row: Any, treatment: Any) -> float:
    """Centre a table cell's line box in its row, using that cell's own role."""
    line_block = float(treatment.font_size * treatment.line_height)
    return float(row.block) + (float(row.block_size) - line_block) / 2 + float(treatment.font_size)
