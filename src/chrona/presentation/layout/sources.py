"""Pure source measurement inputs shared by layout and Scene composition."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from chrona.presentation.layout.model import LayoutError, Measurement
from chrona.presentation.layout.presentation import (
    measure_table_columns, table_cell_indent, table_content_inline_size, table_text_measurer,
)
from chrona.presentation.layout.text import measure_text_width, metric_for_role, paint_text
from chrona.presentation.model.surface_content import TableContent
from chrona.presentation.model.theme_tokens import ThemeTokenView


@dataclass(frozen=True)
class SourceTextRun:
    """Text and declared typography to measure as one source line."""

    content: str
    typography_role: str
    source_ref: str | None = None
    inline_advance: Decimal = Decimal(0)


@dataclass(frozen=True)
class MeasuredTextRun:
    """One closed text measurement addressable by its source fact."""

    source_ref: str | None
    content: str
    typography_role: str
    inline_size: Decimal
    block_size: Decimal
    baseline: Decimal
    font_family: str
    font_weight: int
    font_size: float
    line_height: float
    font_asset_identity: str
    letter_spacing: float = 0.0
    text_transform: str = "none"
    numeric_spacing: str = "proportional"


@dataclass(frozen=True)
class SourceInput:
    """Semantic content facts needed to measure one closed presentation source."""

    lines: tuple[str, ...] = ()
    item_count: int = 0
    column_count: int = 1
    span_days: int = 1
    typography_role: str = "text"
    runs: tuple[SourceTextRun, ...] = ()
    table: TableContent | None = None

    def text_runs(self) -> tuple[SourceTextRun, ...]:
        if self.runs:
            return self.runs
        return tuple(SourceTextRun(line, self.typography_role) for line in self.lines)


@dataclass(frozen=True)
class MeasuredSources:
    """Frozen result consumed unchanged by arrangement and composition."""

    measurements: Mapping[str, Measurement]
    inputs: Mapping[str, SourceInput]
    metric_values: Mapping[str, Decimal]
    run_measurements: Mapping[str, tuple[MeasuredTextRun, ...]] = field(default_factory=dict)


REQUIRED_METRICS = (
    "text.body.size", "text.body.lineHeight",
    "timeline.dayWidth", "timeline.row.minBlockSize", "timeline.row.paddingBlock", "timeline.mark.blockSize", "timeline.axis.blockSize",
    "table.column.minInlineSize", "table.column.gutter.inlineSize", "table.header.blockSize",
    "table.indent.inlineSize",
    "network.node.minInlineSize", "network.node.minBlockSize", "network.rank.gap",
)

OPTIONAL_METRICS = (
    "timeline.groupHeader.blockSize", "timeline.calendarClosed.minimumDayWidth",
    "timeline.mark.cornerRadius", "timeline.point.cornerRadius", "timeline.relation.cornerRadius",
)

_NON_NEGATIVE_METRICS = frozenset((
    "timeline.mark.cornerRadius", "timeline.point.cornerRadius", "timeline.relation.cornerRadius",
))


def resolve_theme_metrics(theme: Mapping[str, Any], *, required_metrics: tuple[str, ...] = ()) -> dict[str, Decimal]:
    body = theme.get("body", {})
    bindings, values = body.get("metrics", {}), body.get("values", {})
    resolved: dict[str, Decimal] = {}
    unknown = set(bindings) - set(REQUIRED_METRICS) - set(OPTIONAL_METRICS)
    if unknown:
        raise LayoutError("E_LAYOUT_METRIC_UNKNOWN", "/body/metrics/" + sorted(unknown)[0])
    required = REQUIRED_METRICS + tuple(name for name in required_metrics if name not in REQUIRED_METRICS)
    if any(name not in OPTIONAL_METRICS and name not in REQUIRED_METRICS for name in required_metrics):
        raise LayoutError("E_LAYOUT_METRIC_UNKNOWN", "/body/metrics/" + sorted(set(required_metrics) - set(REQUIRED_METRICS) - set(OPTIONAL_METRICS))[0])
    for name in REQUIRED_METRICS + OPTIONAL_METRICS:
        token = bindings.get(name)
        if not isinstance(token, str):
            if name not in required:
                continue
            diagnostic = "E_THEME_METRIC_REQUIRED" if name in required_metrics else "E_LAYOUT_METRIC_REQUIRED"
            raise LayoutError(diagnostic, "/body/metrics/" + name)
        declared = values.get(token)
        if not isinstance(declared, Mapping) or declared.get("type") != "number":
            raise LayoutError("E_LAYOUT_TOKEN_TYPE", "/body/metrics/" + name)
        try:
            value = Decimal(str(declared["value"]))
        except (InvalidOperation, KeyError) as error:
            raise LayoutError("E_LAYOUT_TOKEN_TYPE", "/body/metrics/" + name) from error
        if (not value.is_finite() or value < 0
                or (value == 0 and name not in _NON_NEGATIVE_METRICS)):
            raise LayoutError("E_LAYOUT_TOKEN_TYPE", "/body/metrics/" + name)
        resolved[name] = value
    return resolved


def measure_sources(inputs: Mapping[str, SourceInput], theme: Mapping[str, Any], *, font_metrics: Any,
                    required_metrics: tuple[str, ...] = ()) -> MeasuredSources:
    """Measure every declared source once without reading Layout or renderer state."""
    metric = resolve_theme_metrics(theme, required_metrics=required_metrics)
    typography = ThemeTokenView(theme)
    body_treatment = typography.text_treatment("text")
    body_metrics = metric_for_role(typography, "text", font_metrics)
    body_size = body_treatment.font_size
    metric["text.measuredAverageAdvance"] = Decimal(str(measure_text_width(
        "M", font_size=float(body_size), font_metrics=body_metrics,
        letter_spacing=float(body_treatment.letter_spacing), text_transform=body_treatment.transform)))
    result: dict[str, Measurement] = {}
    run_measurements: dict[str, tuple[MeasuredTextRun, ...]] = {}
    for source, value in sorted(inputs.items()):
        runs = value.text_runs()
        first_role = runs[0].typography_role if runs else value.typography_role
        first_treatment = typography.text_treatment(first_role)
        first_metrics = metric_for_role(typography, first_role, font_metrics)
        font_size, line_height = first_treatment.font_size, first_treatment.line_height
        text_line = font_size * line_height
        average_advance = Decimal(str(measure_text_width(
            "M", font_size=float(font_size), font_metrics=first_metrics,
            letter_spacing=float(first_treatment.letter_spacing), text_transform=first_treatment.transform)))
        measured_runs = []
        for run in runs:
            treatment = typography.text_treatment(run.typography_role)
            run_metrics = metric_for_role(typography, run.typography_role, font_metrics)
            family, weight, run_size, run_line_height = (treatment.family, treatment.weight,
                                                         treatment.font_size, treatment.line_height)
            width = Decimal(str(measure_text_width(
                run.content, font_size=float(run_size), font_metrics=run_metrics,
                letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform))) + run.inline_advance
            baseline = Decimal(str(run_metrics.baseline(0, float(run_size), float(run_line_height))))
            measured_runs.append(MeasuredTextRun(
                run.source_ref, paint_text(run.content, text_transform=treatment.transform), run.typography_role, width,
                run_size * run_line_height, baseline, family, int(weight),
                float(run_size), float(run_line_height), str(run_metrics.content_identity),
                float(treatment.letter_spacing), treatment.transform, treatment.numeric_spacing))
        run_measurements[source] = tuple(measured_runs)
        measured_width = max((run.inline_size for run in measured_runs), default=average_advance)
        text_block = sum((typography.text_treatment(run.typography_role).font_size
                          * typography.text_treatment(run.typography_role).line_height for run in runs), Decimal(0))
        if not runs:
            text_block = text_line
        text_inline = max(average_advance, measured_width)
        if source == "table":
            # One measure sizes the slot and places its columns (Specification 24 section 2.1).
            # The metric is a per-column floor for a content-sized slot.
            # Its minimum keeps the floor-and-label basis; #487 owns `min: content`.
            column_floor = Decimal(max(1, value.column_count)) * metric["table.column.minInlineSize"]
            minimum_inline = min(column_floor, text_inline)
            preferred_inline = column_floor
            if value.table is not None:
                preferred_inline = max(column_floor, _table_content_inline(value.table, typography, font_metrics,
                                                                           metric, float(body_size)))
            preferred_block = metric["table.header.blockSize"] + Decimal(max(1, value.item_count)) * metric["timeline.row.minBlockSize"]
        elif source == "timeline":
            preferred_inline = Decimal(max(1, value.span_days)) * metric["timeline.dayWidth"]
            preferred_block = Decimal(max(1, value.item_count)) * metric["timeline.row.minBlockSize"]
        elif source == "timeline-axis":
            preferred_inline = Decimal(max(1, value.span_days)) * metric["timeline.dayWidth"]
            preferred_block = metric["timeline.axis.blockSize"]
        else:
            preferred_inline, preferred_block = text_inline, text_block
        if source != "table":
            minimum_inline = min(preferred_inline, text_inline)
        result[source] = Measurement(
            minimum_inline, preferred_inline, preferred_inline * 2,
            min(preferred_block, text_block), preferred_block, preferred_block * 2,
            Decimal(str(first_metrics.baseline(0, float(font_size), float(line_height)))),
            Decimal(str(first_metrics.baseline(0, float(font_size), float(line_height)))),
        )
    return MeasuredSources(result, dict(inputs), metric, run_measurements)


def _table_content_inline(table: TableContent, typography: ThemeTokenView, font_metrics: Any,
                          metric: Mapping[str, Decimal], inset: float) -> Decimal:
    """Measure the table exactly as Layout will place its columns."""
    indent = metric.get("table.indent.inlineSize")
    cell_indents = {
        key: table_cell_indent(grouped=level.grouped, depth=level.depth, inset=inset,
                               indent=float(indent) if indent is not None else None)
        for level in table.row_levels for key in level.keys
    }
    natural = measure_table_columns(columns=table.columns, cells=table.cells,
                                    measure_text=table_text_measurer(typography, font_metrics),
                                    minimum_inline=inset, hierarchy_column=table.hierarchy_column,
                                    cell_indents=cell_indents)
    return Decimal(str(table_content_inline_size(natural, float(metric["table.column.gutter.inlineSize"]))))
