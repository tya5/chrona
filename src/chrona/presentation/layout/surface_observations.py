"""Layout-owned measurement and placement for Review Detail observations."""
from __future__ import annotations

from dataclasses import dataclass, replace
from urllib.parse import quote

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.presentation import TableColumnPlacement, place_table_columns, table_text_measurer
from chrona.presentation.layout.surface_quality import CollisionDomain, FitWarning, SlotPlacement, SurfaceLayoutRequest, TextPlacement
from chrona.presentation.layout.text import ellipsize_text, metric_for_role, place_text, wrap_text
from chrona.presentation.model.surface_content import (
    SurfaceContentInput, TableCellContent, TableColumnContent, TableColumnWidth, TableContent,
)


@dataclass(frozen=True)
class SurfaceObservationsBatch:
    """Completed observation slot and its ordered native text primitives."""

    slot: SlotPlacement
    columns: tuple[TableColumnPlacement, ...] = ()
    text: tuple[TextPlacement, ...] = ()
    warnings: tuple[FitWarning, ...] = ()


def observations_table_content(content: SurfaceContentInput) -> TableContent:
    """Expose normalized observations as typed table facts for source premeasurement."""
    columns = tuple(TableColumnContent(column_id=column_id, header=label, align="start",
                                       width=TableColumnWidth("ellipsis", "fr", 1.0))
                    for column_id, label in content.observation_columns)
    cells = tuple(TableCellContent(object_id=row_id, column_id=column_id, content=value,
                                   semantic_id=_emphasis_semantic(emphasis))
                  for row_id, _source, emphasis, row_cells in content.observation_rows
                  for column_id, value in row_cells)
    return TableContent(columns, cells, (), None, (), False)


def compose_observations(*, slot: SlotPlacement, request: SurfaceLayoutRequest) -> SurfaceObservationsBatch:
    """Place declared observation headers, row-source lines, and measured cells.

    Observations are intentionally independent from the primary review table. Each row's
    provenance is visible as its own full-width line before that row's declared cells.
    """
    content = request.surface_content
    if not content.observation_rows:
        return SurfaceObservationsBatch(slot)
    tokens, font_metrics = request.theme_tokens, request.font_metrics
    if tokens is None or font_metrics is None:
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources")
    table = observations_table_content(content)
    columns, cells = table.columns, table.cells
    if not columns:
        # Profile validation should prevent this; fail closed if an invalid closed input is supplied.
        raise LayoutError("E_LAYOUT_TABLE_OVERFLOW", "/body/observations/columns")

    text_role = "text"
    text_treatment = tokens.text_treatment(text_role)
    font_size = float(text_treatment.font_size)
    header_role = tokens.table_header_role()
    header_treatment = tokens.text_treatment(header_role)
    header_size = float(header_treatment.font_size)
    measure = table_text_measurer(tokens, font_metrics)
    gutter = float(request.measured_sources.metric_values.get("table.column.gutter.inlineSize", 0))
    overflow_mode = slot.overflow
    # Use the native allocator, with equal flex shares once each measured content minimum closes.
    layout_columns = place_table_columns(
        columns=columns, cells=cells,
        bounds=(float(slot.bounds.inline), float(slot.bounds.block),
                float(slot.bounds.inline_size), float(slot.bounds.block_size)),
        measure_text=measure, minimum_inline=font_size, overflow=overflow_mode, gutter=gutter,
        header_role=header_role,
    )
    positions = {item.column_id: item.inline for item in layout_columns}
    widths = {item.column_id: item.inline_size for item in layout_columns}
    by_column = {column.column_id: column for column in columns}
    placed: list[TextPlacement] = []
    warnings: list[FitWarning] = []
    cursor = float(slot.bounds.block)
    inline_start = float(slot.bounds.inline)
    inline_size = float(slot.bounds.inline_size)

    def lines_for(raw: str, role: str, available: float) -> tuple[tuple[str, ...], str, float]:
        treatment = tokens.text_treatment(role)
        metrics = metric_for_role(tokens, role, font_metrics)
        lines = ((raw,) if available <= 0 else wrap_text(
            raw, available_inline=available, font_size=float(treatment.font_size), font_metrics=metrics,
            letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform,
            numeric_spacing=treatment.numeric_spacing))
        natural = max(measure(line, role, "horizontal") for line in lines)
        disposition = "fit"
        if natural > available:
            if overflow_mode == "clip-optional":
                disposition = "suppressed"
            elif (overflow_mode == "ellipsize-with-source"
                  and available >= measure("…", role, "horizontal")):
                lines = tuple(ellipsize_text(
                    line, available_inline=available, font_size=float(treatment.font_size), font_metrics=metrics,
                    letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform,
                    numeric_spacing=treatment.numeric_spacing) for line in lines)
                disposition = "ellipsized"
            else:
                disposition = "visible-overflow"
        return lines, disposition, natural

    def add_text(identifier: str, source_ref: str, raw: str, role: str, semantic: str,
                 start: float, available: float, top: float) -> float:
        lines, disposition, natural = lines_for(raw, role, available)
        treatment = tokens.text_treatment(role)
        size = float(treatment.font_size)
        if disposition == "suppressed":
            item = place_text(
                placement_id=identifier, source_ref=source_ref, content=raw, inline=start,
                baseline_block=top + size, typography_role=role, theme_tokens=tokens,
                font_metrics=font_metrics, overflow="suppressed", required=False,
                collision_region="observations", collision_domain=CollisionDomain(slot.slot_id, source_ref),
                source_content=raw, available_inline_start=start, available_inline_size=available,
                slot_id=slot.slot_id, semantic_id=semantic,
            )
            placed.append(item)
            warnings.append(FitWarning("W_LAYOUT_DETAIL_PANEL_CLIPPED", identifier, source_ref,
                                       "detail-panel", "clip-optional", natural,
                                       float(item.bounds.block_size), available,
                                       float(slot.bounds.block_size)))
            return 0.0
        line_height = size * float(treatment.line_height)
        baseline = top + size
        item = place_text(
            placement_id=identifier, source_ref=source_ref, content="\n".join(lines), inline=start,
            baseline_block=baseline, typography_role=role, theme_tokens=tokens, font_metrics=font_metrics,
            overflow=disposition, collision_region="observations",
            collision_domain=CollisionDomain(slot.slot_id, source_ref), source_content=raw, lines=lines,
            available_inline_start=start, available_inline_size=available, slot_id=slot.slot_id,
            semantic_id=semantic,
        )
        placed.append(item)
        if disposition == "visible-overflow":
            warnings.append(FitWarning(
                "W_LAYOUT_VISIBLE_OVERFLOW", identifier, source_ref, "observations", "visible-overflow",
                natural, float(item.bounds.block_size), available, float(slot.bounds.block_size)))
        return line_height * len(lines)

    # Headers are wrapped and measured with the Theme's existing table-header typography.
    header_heights: list[float] = []
    for column in columns:
        available = max(0.0, widths[column.column_id])
        lines, disposition, natural = lines_for(column.header, header_role, available)
        h = (0.0 if disposition == "suppressed" else
             header_size * float(header_treatment.line_height) * len(lines))
        if disposition == "suppressed":
            item = place_text(
                placement_id=f"observations:header:{_id(column.column_id)}", source_ref=column.column_id,
                content=column.header, inline=positions[column.column_id], baseline_block=cursor + header_size,
                typography_role=header_role, theme_tokens=tokens, font_metrics=font_metrics,
                overflow="suppressed", required=False, collision_region="observations",
                collision_domain=CollisionDomain(slot.slot_id, "headers"), source_content=column.header,
                available_inline_start=positions[column.column_id], available_inline_size=available,
                slot_id=slot.slot_id, semantic_id="tableColumnLabel")
            placed.append(item)
            warnings.append(FitWarning("W_LAYOUT_DETAIL_PANEL_CLIPPED", item.placement_id, column.column_id,
                                       "detail-panel", "clip-optional", natural, h, available,
                                       float(slot.bounds.block_size)))
            header_heights.append(0.0)
            continue
        item = place_text(
            placement_id=f"observations:header:{_id(column.column_id)}", source_ref=column.column_id,
            content="\n".join(lines), inline=positions[column.column_id], baseline_block=cursor + header_size,
            typography_role=header_role, theme_tokens=tokens, font_metrics=font_metrics,
            overflow=disposition, collision_region="observations",
            collision_domain=CollisionDomain(slot.slot_id, "headers"), source_content=column.header,
            lines=lines, available_inline_start=positions[column.column_id], available_inline_size=available,
            slot_id=slot.slot_id, semantic_id="tableColumnLabel")
        placed.append(item)
        header_heights.append(h)
        if disposition == "visible-overflow":
            warnings.append(FitWarning("W_LAYOUT_VISIBLE_OVERFLOW", item.placement_id, column.column_id,
                                       "observations", "visible-overflow", natural, h, available,
                                       float(slot.bounds.block_size)))
    cursor += max(header_heights, default=0.0)

    for row_id, source, emphasis, row_cells in content.observation_rows:
        row_key = _id(row_id)
        source_id = f"observations:row:{row_key}:source"
        cursor += add_text(source_id, row_id, source, text_role, "tableCell", inline_start,
                           inline_size, cursor)
        row_lines: list[tuple[TableColumnContent, str, tuple[str, ...], str, float]] = []
        row_height = 0.0
        for column_id, raw in row_cells:
            column = by_column[column_id]
            available = max(0.0, widths[column_id])
            lines, disposition, natural = lines_for(raw, text_role, available)
            line_height = font_size * float(text_treatment.line_height) * len(lines)
            row_height = max(row_height, line_height)
            row_lines.append((column, raw, lines, disposition, natural))
        for column, raw, lines, disposition, natural in row_lines:
            identifier = f"observations:row:{row_key}:cell:{_id(column.column_id)}"
            item = place_text(
                placement_id=identifier, source_ref=row_id, content="\n".join(lines),
                inline=positions[column.column_id], baseline_block=cursor + font_size,
                typography_role=text_role, theme_tokens=tokens, font_metrics=font_metrics,
                overflow=disposition, collision_region="observations",
                collision_domain=CollisionDomain(slot.slot_id, f"row:{row_key}"), source_content=raw,
                lines=lines, available_inline_start=positions[column.column_id],
                available_inline_size=max(0.0, widths[column.column_id]), slot_id=slot.slot_id,
                semantic_id=_emphasis_semantic(emphasis))
            placed.append(item)
            if disposition == "visible-overflow":
                warnings.append(FitWarning("W_LAYOUT_VISIBLE_OVERFLOW", identifier, row_id,
                                           "observations", "visible-overflow", natural,
                                           float(item.bounds.block_size), widths[column.column_id],
                                           float(slot.bounds.block_size)))
        cursor += row_height

    # Natural completion encloses the actual typed primitives, not a rounded float cursor.
    completed_end = max((slot.bounds.block + slot.bounds.block_size,
                        *(item.bounds.block + item.bounds.block_size for item in placed
                          if item.overflow != "suppressed")))
    completed_size = completed_end - slot.bounds.block
    completed_slot = replace(slot, bounds=Rect(slot.bounds.inline, slot.bounds.block,
                                                slot.bounds.inline_size, completed_size))
    if completed_size > slot.bounds.block_size:
        warnings.append(FitWarning(
            "W_LAYOUT_VISIBLE_OVERFLOW", "observations:slot", "observations", "observations",
            "visible-overflow", float(slot.bounds.inline_size), float(completed_size),
            float(slot.bounds.inline_size), float(slot.bounds.block_size)))
    return SurfaceObservationsBatch(completed_slot, tuple(layout_columns), tuple(placed), tuple(warnings))


def _id(value: str) -> str:
    """Percent-escape every delimiter so authored IDs cannot alias generated path segments."""
    return quote(value, safe="")


def _emphasis_semantic(emphasis: str) -> str:
    return {"normal": "tableCell", "attention": "tableVarianceAhead",
            "critical": "tableVarianceBehind"}[emphasis]
