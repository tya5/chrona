"""Bounded table source closure shared by allocation and native placement."""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from math import isfinite
from typing import Any, Mapping

from chrona.presentation.layout.group_tags import header_child_lead
from chrona.presentation.layout.model import LayoutError, Measurement
from chrona.presentation.layout.presentation import (
    TableColumnPlacement, header_group_cell_indent, measure_table_column_minima,
    place_table_columns, table_cell_indent, table_content_inline_size, table_text_measurer,
)
from chrona.presentation.layout.text import TextLineFit, fit_text_lines, measure_text_width, metric_for_role
from chrona.presentation.model.surface_content import TableContent


@dataclass(frozen=True, slots=True)
class MeasuredTableText:
    column_id: str
    source_ref: str
    source_content: str
    typography_role: str
    orientation: str
    fit: TextLineFit
    block_size: Decimal
    font_asset_identity: str


@dataclass(frozen=True, slots=True)
class BoundedTableMeasurement:
    """No placed rows: header demand and each subject's demand remain distinct."""

    measurement: Measurement
    columns: tuple[TableColumnPlacement, ...]
    column_minima: tuple[float, ...]
    headers: tuple[MeasuredTableText, ...]
    cells: tuple[MeasuredTableText, ...]
    row_text_blocks: tuple[tuple[str, Decimal], ...]
    header_block: Decimal
    cell_indents: tuple[tuple[str, float], ...]
    available_inline: Decimal
    reserved_inline: Decimal


def _fit_table_text(content: str, *, available: float, role: str, wrap: str,
                     tokens: Any, font_metrics: Any, prefix: str = "", suffix: str = "") -> TextLineFit:
    treatment = tokens.text_treatment(role)
    metrics = metric_for_role(tokens, role, font_metrics)
    kwargs = dict(font_size=float(treatment.font_size), font_metrics=metrics,
                  letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform,
                  numeric_spacing=treatment.numeric_spacing)
    fit = fit_text_lines(content, available_inline=available, wrap=wrap, **kwargs)
    if (prefix or suffix) and (fit is None or fit.ellipsized):
        if not content.startswith(prefix) or not content.endswith(suffix) or len(prefix) + len(suffix) > len(content):
            raise LayoutError("E_LAYOUT_TABLE_OVERFLOW", "/table/cells", detail="affixes disagree with source text")
        core = content[len(prefix):len(content) - len(suffix) if suffix else None]
        for count in range(max(0, len(core) - 1), -1, -1):
            candidate = prefix + core[:count] + "…" + suffix
            width = measure_text_width(candidate, **kwargs)
            if width <= available:
                return TextLineFit((candidate,), width, measure_text_width(content, **kwargs), True)
        fit = None
    if fit is None:
        raise LayoutError("E_LAYOUT_TABLE_OVERFLOW", "/table/cells",
                          detail="mandatory text or affixes cannot fit the allocated column")
    return fit


def measure_bounded_table(table: TableContent, *, available_inline: float | Decimal,
                           tokens: Any, font_metrics: Any, metric_values: Mapping[str, Decimal],
                           original: Measurement, reserved_inline: float = 0.0) -> BoundedTableMeasurement:
    """Close actual header/cell lines before row, prefix or source allocation.

    ``reserved_inline`` is already measured host chrome (for example group
    tabs), not guessed from the viewport. Original source values are immutable;
    unchanged block demand retains its exact baseline and block measurements.
    """
    if (not isfinite(available_inline) or not isfinite(reserved_inline)
            or reserved_inline < 0 or available_inline <= reserved_inline):
        raise LayoutError("E_LAYOUT_TABLE_OVERFLOW", "/table", detail="no finite content inline budget")
    content_inline = float(available_inline) - reserved_inline
    inset = float(tokens.text_treatment("text").font_size)
    step = metric_values.get("table.indent.inlineSize")
    lead = (header_child_lead(tokens, first_column=bool(table.columns)
                              and table.columns[0].column_id == table.hierarchy_column)
            if table.indent_under_headers else None)
    indents = {}
    for level in table.row_levels:
        indent = (header_group_cell_indent(grouped=level.grouped, indent=float(step) if step is not None else None, lead=lead)
                  if table.indent_under_headers else
                  table_cell_indent(grouped=level.grouped, depth=level.depth, inset=inset,
                                    indent=float(step) if step is not None else None))
        indents.update((key, indent) for key in level.keys)
    header_role = tokens.table_header_role()
    measure = table_text_measurer(tokens, font_metrics)
    minima = measure_table_column_minima(columns=table.columns, cells=table.cells, measure_text=measure,
                                         minimum_inline=inset, hierarchy_column=table.hierarchy_column,
                                         cell_indents=indents, header_role=header_role)
    gutter = float(metric_values.get("table.column.gutter.inlineSize", 0))
    placed = place_table_columns(columns=table.columns, cells=table.cells,
                                 bounds=(reserved_inline, 0, content_inline, 0), measure_text=measure,
                                 minimum_inline=inset, gutter=gutter, hierarchy_column=table.hierarchy_column,
                                 cell_indents=indents, header_role=header_role, mandatory_inline=minima)
    widths = {column.column_id: column.inline_size for column in placed}
    intents = {column.column_id: column for column in table.columns}
    headers = []
    for column in table.columns:
        treatment = tokens.text_treatment(header_role)
        metrics = metric_for_role(tokens, header_role, font_metrics)
        available = widths[column.column_id] - inset
        if column.header_orientation != "horizontal":
            # The rotated text advances along block; inline only holds its
            # native line-box thickness. Never ellipsize it to column width.
            if float(treatment.font_size * treatment.line_height) > available:
                raise LayoutError("E_LAYOUT_TABLE_OVERFLOW", "/table/header", column.column_id)
            available = measure(column.header, header_role, "horizontal")
        fit = _fit_table_text(column.header, available=available, role=header_role,
                              wrap=column.text_wrap, tokens=tokens, font_metrics=font_metrics)
        block = (Decimal(str(fit.inline_size)) if column.header_orientation != "horizontal"
                 else treatment.font_size * treatment.line_height * len(fit.lines))
        headers.append(MeasuredTableText(column.column_id, "view:tableColumns", column.header,
                                         header_role, column.header_orientation, fit, block, str(metrics.content_identity)))
    cells = []
    row_blocks: dict[str, Decimal] = {}
    for cell in table.cells:
        column = intents[cell.column_id]
        indent = indents.get(cell.object_id, 0.0) if cell.column_id == table.hierarchy_column else 0.0
        treatment = tokens.text_treatment(cell.typography_role)
        metrics = metric_for_role(tokens, cell.typography_role, font_metrics)
        fit = _fit_table_text(cell.content, available=widths[cell.column_id] - indent - inset,
                              role=cell.typography_role, wrap=column.text_wrap,
                              tokens=tokens, font_metrics=font_metrics,
                              prefix=cell.affix_prefix, suffix=cell.affix_suffix)
        block = treatment.font_size * treatment.line_height * len(fit.lines)
        cells.append(MeasuredTableText(cell.column_id, cell.object_id, cell.content, cell.typography_role,
                                       "horizontal", fit, block, str(metrics.content_identity)))
        row_blocks[cell.object_id] = max(row_blocks.get(cell.object_id, Decimal(0)), block)
    header_floor = metric_values["table.header.blockSize"]
    header_block = max(header_floor, max((header.block_size for header in headers), default=Decimal(0)))
    text_demands = ([max((row_blocks.get(key, Decimal(0)) for key in level.keys), default=Decimal(0))
                     for level in table.row_levels] if table.row_levels else list(row_blocks.values()))
    padding = metric_values["timeline.row.paddingBlock"]
    row_floor = metric_values["timeline.row.minBlockSize"]
    extra = header_block - header_floor + sum((max(Decimal(0), block + padding - row_floor)
                                               for block in text_demands), Decimal(0))
    mandatory = Decimal(str(table_content_inline_size(minima, gutter) + reserved_inline))
    budget = Decimal(str(available_inline))
    minimum = max(original.min_inline, mandatory) if original.min_inline <= budget else mandatory
    measurement = replace(original, min_inline=minimum,
                           preferred_inline=max(minimum, min(original.preferred_inline, budget)),
                           max_inline=max(minimum, min(original.max_inline, budget)),
                           preferred_block=original.preferred_block + extra,
                           max_block=original.max_block + 2 * extra)
    return BoundedTableMeasurement(measurement, placed, minima, tuple(headers), tuple(cells),
                                    tuple(row_blocks.items()), header_block, tuple(indents.items()),
                                    budget, Decimal(str(reserved_inline)))
