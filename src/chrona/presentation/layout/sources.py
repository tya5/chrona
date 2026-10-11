"""Pure source measurement inputs shared by layout and Scene composition."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from chrona.presentation.layout.axis_lanes import derived_axis_block_size
from chrona.presentation.layout.group_tags import header_child_lead
from chrona.presentation.layout.model import LayoutError, Measurement
from chrona.presentation.layout.presentation import (
    header_group_cell_indent, measure_table_columns, place_table_columns, table_cell_indent, table_content_inline_size, table_text_measurer,
)
from chrona.presentation.layout.text import fit_text_lines, measure_text_width, metric_for_role, paint_text
from chrona.presentation.layout.text_stack import MeasuredTextStack, measure_text_stack
from chrona.presentation.layout.table_measurement import BoundedTableMeasurement, measure_bounded_table
from chrona.presentation.layout.summary_flow import MeasuredSummary, measure_summary
from chrona.presentation.model.surface_content import AxisTier, SummaryContent, TableContent
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
    horizontal_scale: float = 1.0
    lines: tuple[str, ...] = ()
    overflow: str = "fit"


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
    # How the runs lie in the slot: `stack` is one run per line (the widest run
    # sizes the slot), `line` is every run on one line, `run_gap` apart (#497).
    # `block` closes the stack's actual placement envelope and baselines.
    run_flow: str = "stack"
    run_gap: Decimal = Decimal(0)
    # A `grid` flow: the declared column count and the height of one row (#1290); entries fill the columns in order.
    columns: int | None = None
    row_block: Decimal = Decimal(0)
    # A producer-declared smallest inline size the content can shrink to; when
    # unset the smallest size is the preferred one (nothing shrinks).
    min_inline: Decimal | None = None
    summary: SummaryContent | None = None
    # The View's axis tiers, for deriving an unbound axis size from their lanes (#1150).
    axis_tiers: tuple[AxisTier, ...] = ()
    # A declared source may be available while its selected View part is empty.
    # Empty sources contribute no runs and have zero natural extent.
    content_present: bool = True
    text_wrap: str = "forbid"

    def text_runs(self) -> tuple[SourceTextRun, ...]:
        if not self.content_present:
            return ()
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
    block_stacks: Mapping[str, MeasuredTextStack] = field(default_factory=dict)
    summary_flows: Mapping[str, MeasuredSummary] = field(default_factory=dict)
    bounded_tables: Mapping[str, BoundedTableMeasurement] = field(default_factory=dict)


REQUIRED_METRICS = (
    "text.body.size", "text.body.lineHeight",
    "timeline.dayWidth", "timeline.row.minBlockSize", "timeline.row.paddingBlock", "timeline.mark.blockSize", "timeline.axis.blockSize",
    "table.column.minInlineSize", "table.column.gutter.inlineSize", "table.header.blockSize",
    "table.indent.inlineSize",
    "network.node.minInlineSize", "network.node.minBlockSize", "network.rank.gap",
)

# A metric a Theme may leave unbound: Layout derives it from other sizes (#1150). A bound value always wins.
# The axis and the header need the View's axis tiers, so `measure_sources` derives those two.
DERIVED_METRICS = ("timeline.mark.blockSize", "timeline.axis.blockSize", "table.header.blockSize")

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
            if name not in required or name in DERIVED_METRICS:
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
    if not isinstance(bindings.get("timeline.mark.blockSize"), str):
        resolved_track = derived_track_block_size(resolved)
        if resolved_track is None:
            raise LayoutError("E_LAYOUT_METRIC_REQUIRED", "/body/metrics/timeline.mark.blockSize")
        resolved["timeline.mark.blockSize"] = resolved_track
    return resolved


def derive_axis_metrics(metric: dict[str, Decimal], theme: Mapping[str, Any], inputs: Mapping[str, SourceInput],
                        typography: ThemeTokenView, font_metrics: Any) -> None:
    """Fill an unbound axis block size from the axis lanes and an unbound header from the axis (#1150)."""
    bindings = theme.get("body", {}).get("metrics", {})
    if "timeline.axis.blockSize" not in metric:
        axis = derived_axis_block_size(inputs["timeline-axis"].axis_tiers if "timeline-axis" in inputs else (),
                                       typography, font_metrics)
        if axis is None:
            raise LayoutError("E_LAYOUT_METRIC_REQUIRED", "/body/metrics/timeline.axis.blockSize")
        metric["timeline.axis.blockSize"] = axis
    if not isinstance(bindings.get("table.header.blockSize"), str):
        metric["table.header.blockSize"] = metric["timeline.axis.blockSize"]


def derived_track_block_size(metrics: Mapping[str, Decimal]) -> Decimal | None:
    """The mark track's default block size: the row block size less a padding on each side (#1150).

    The row keeps `timeline.row.paddingBlock` above and below the track, so the track is the row block
    size less twice it (CSS `box-sizing`: inner size from outer size and padding). The row's own
    requirement still adds `paddingBlock` once (Specification 24 section 2), so a derived track always
    fits with that padding to spare. None when the row, its padding or a positive remainder is missing.
    """
    row, padding = metrics.get("timeline.row.minBlockSize"), metrics.get("timeline.row.paddingBlock")
    if row is None or padding is None or row - 2 * padding <= 0:
        return None
    return row - 2 * padding


def measure_sources(inputs: Mapping[str, SourceInput], theme: Mapping[str, Any], *, font_metrics: Any,
                    required_metrics: tuple[str, ...] = (), table_inline: float | None = None,
                    table_reserved_inline: float = 0.0,
                    heading_inline: Mapping[str, Decimal] | None = None) -> MeasuredSources:
    """Close immutable source facts at optional independently allocated widths."""
    metric = resolve_theme_metrics(theme, required_metrics=required_metrics)
    typography = ThemeTokenView(theme)
    derive_axis_metrics(metric, theme, inputs, typography, font_metrics)
    body_treatment = typography.text_treatment("text")
    body_metrics = metric_for_role(typography, "text", font_metrics)
    body_size = body_treatment.font_size
    metric["text.measuredAverageAdvance"] = Decimal(str(measure_text_width(
        "M", font_size=float(body_size), font_metrics=body_metrics,
        letter_spacing=float(body_treatment.letter_spacing), text_transform=body_treatment.transform)))
    result: dict[str, Measurement] = {}
    run_measurements: dict[str, tuple[MeasuredTextRun, ...]] = {}
    block_stacks: dict[str, MeasuredTextStack] = {}
    summary_flows: dict[str, MeasuredSummary] = {}
    bounded_tables: dict[str, BoundedTableMeasurement] = {}
    for source, value in sorted(inputs.items()):
        if not value.content_present:
            result[source] = Measurement(*(Decimal(0) for _ in range(6)))
            run_measurements[source] = ()
            continue
        runs = value.text_runs()
        heading_budget = ((heading_inline or {}).get(source)
                          if source in {"title", "heading.title", "heading.kicker", "heading.subtitle"}
                          and value.text_wrap == "allow" else None)
        if heading_budget is not None and (not heading_budget.is_finite() or heading_budget <= 0):
            raise LayoutError("E_LAYOUT_TEXT_OVERFLOW", f"/sources/{source}", detail="no finite heading inline budget")
        first_role = runs[0].typography_role if runs else value.typography_role
        first_treatment = typography.text_treatment(first_role)
        first_metrics = metric_for_role(typography, first_role, font_metrics)
        font_size, line_height = first_treatment.font_size, first_treatment.line_height
        text_line = font_size * line_height
        average_advance = Decimal(str(measure_text_width(
            "M", font_size=float(font_size), font_metrics=first_metrics,
            letter_spacing=float(first_treatment.letter_spacing), text_transform=first_treatment.transform,
            numeric_spacing=(first_treatment.numeric_spacing if value.run_flow == "block" or value.summary is not None
                             else "proportional"))))
        measured_runs = []
        for run in runs:
            treatment = typography.text_treatment(run.typography_role)
            run_metrics = metric_for_role(typography, run.typography_role, font_metrics)
            family, weight, run_size, run_line_height = (treatment.family, treatment.weight,
                                                         treatment.font_size, treatment.line_height)
            width = Decimal(str(measure_text_width(
                run.content, font_size=float(run_size), font_metrics=run_metrics,
                letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform,
                numeric_spacing=(treatment.numeric_spacing if value.run_flow == "block" or value.summary is not None
                                 else "proportional")))) + run.inline_advance
            baseline = Decimal(str(run_metrics.baseline(0, float(run_size), float(run_line_height))))
            measured_runs.append(MeasuredTextRun(
                run.source_ref, paint_text(run.content, text_transform=treatment.transform), run.typography_role, width,
                run_size * run_line_height, baseline, family, int(weight),
                float(run_size), float(run_line_height), str(run_metrics.content_identity),
                float(treatment.letter_spacing), treatment.transform, treatment.numeric_spacing,
                float(treatment.horizontal_scale)))
            if heading_budget is not None:
                fit = fit_text_lines(run.content, available_inline=float(heading_budget - run.inline_advance),
                                     font_size=float(run_size), font_metrics=run_metrics, wrap="allow",
                                     letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform,
                                     numeric_spacing=treatment.numeric_spacing)
                if fit is None:
                    raise LayoutError("E_LAYOUT_TEXT_OVERFLOW", f"/sources/{source}", run.source_ref,
                                      "mandatory ellipsis and inline reservation cannot fit")
                if fit.content != run.content:
                    measured_runs[-1] = replace(
                        measured_runs[-1], content=paint_text(fit.content, text_transform=treatment.transform),
                        inline_size=Decimal(str(fit.inline_size)) + run.inline_advance,
                        block_size=run_size * run_line_height * len(fit.lines),
                        lines=tuple(paint_text(line, text_transform=treatment.transform) for line in fit.lines),
                        overflow="ellipsized" if fit.ellipsized else "fit")
        run_measurements[source] = tuple(measured_runs)
        grid_block: Decimal | None = None
        if value.run_flow == "grid" and measured_runs and value.columns:
            # A declared grid is exactly measurable here: each column is as wide as its widest entry, `run_gap` apart,
            # and the rows are known from the entry count (#1290).
            count = len(measured_runs)
            width_of = [max((measured_runs[index].inline_size for index in range(column, count, value.columns)),
                            default=Decimal(0)) for column in range(min(value.columns, count))]
            rows = -(-count // value.columns)
            measured_width = sum(width_of, Decimal(0)) + value.run_gap * (len(width_of) - 1)
            grid_block = value.row_block * rows + value.run_gap * (rows - 1)
        elif value.run_flow == "line" and measured_runs:
            measured_width = (sum((run.inline_size for run in measured_runs), Decimal(0))
                              + value.run_gap * (len(measured_runs) - 1))
        else:
            measured_width = max((run.inline_size for run in measured_runs), default=average_advance)
        # The block size stays the stack of every run for a `line` too: how many rows a
        # wrapping line needs depends on the inline size the slot is given, which is not
        # known here, so the slot keeps its conservative height (#497 changes inline size only).
        text_block = sum((run.block_size for run in measured_runs), Decimal(0))
        if not runs:
            text_block = text_line
        if grid_block is not None:
            text_block = grid_block
        # The preferred block of a wrapping line keeps the conservative stack (a content-sized slot is unchanged), but
        # its minimum is one row: how many rows it really needs is known only once the slot's inline size is, and
        # the legend placement pass checks that and reports the true required block (#1273).
        minimum_text_block = text_block
        if value.run_flow == "line" and runs:
            minimum_text_block = max(typography.text_treatment(run.typography_role).font_size
                                     * typography.text_treatment(run.typography_role).line_height for run in runs)
        stack = None
        if value.run_flow == "block" and measured_runs:
            stack = measure_text_stack(measured_runs, tuple(
                typography.text_block_gap(run.typography_role) for run in runs))
            block_stacks[source] = stack
            text_block = stack.block_size
        summary_flow = None
        if value.summary is not None:
            inline_roles = {run.typography_role for panel in value.summary.panels
                            if panel.arrangement == "inline" for run in panel.runs}
            summary_flow = measure_summary(value.summary,
                                           {run.source_ref: run for run in measured_runs},
                                           {role: typography.text_inline_gap(role) for role in sorted(inline_roles)})
            summary_flows[source] = summary_flow
            measured_width, text_block = summary_flow.inline_size, summary_flow.block_size
        text_inline = max(average_advance, measured_width)
        if heading_budget is not None:
            text_inline = min(text_inline, heading_budget)
        if source == "table":
            # One measure sizes the slot and places its columns (Specification 24 section 2.1).
            # The metric is a per-column floor for a content-sized slot.
            column_floor = Decimal(max(1, value.column_count)) * metric["table.column.minInlineSize"]
            minimum_inline = min(column_floor, text_inline)
            preferred_inline = column_floor
            if value.table is not None and value.table.columns:
                # `minmax: {min: content}` is the table's measured columns and gutters,
                # never the widest row label (#487, Specification 24 section 2.1).
                measured_content = _table_content_inline(value.table, typography, font_metrics,
                                                          metric, float(body_size))
                preferred_inline = max(column_floor, measured_content)
                minimum_inline = measured_content
            preferred_block = metric["table.header.blockSize"] + Decimal(max(1, value.item_count)) * metric["timeline.row.minBlockSize"]
        elif source == "observations" and value.table is not None and value.table.columns:
            table = value.table
            measured_content = _table_content_inline(table, typography, font_metrics, metric, float(body_size))
            measure_observation_text = table_text_measurer(typography, font_metrics)
            provenance_inline = Decimal(str(max(
                (measure_observation_text(source, "text", "horizontal") for source in value.lines), default=0.0)))
            preferred_inline = max(measured_content, provenance_inline)
            gutter = float(metric["table.column.gutter.inlineSize"])
            compact_columns = place_table_columns(columns=table.columns, cells=table.cells,
                bounds=(0.0, 0.0, 0.0, 0.0), measure_text=measure_observation_text,
                minimum_inline=float(body_size), gutter=gutter, overflow="ellipsize-with-source",
                header_role=typography.table_header_role())
            minimum_inline = Decimal(str(table_content_inline_size(
                tuple(column.inline_size for column in compact_columns), gutter)))
            header = typography.text_treatment(typography.table_header_role())
            body = typography.text_treatment("text")
            preferred_block = (header.font_size * header.line_height
                               + Decimal(value.item_count) * 2 * body.font_size * body.line_height)
        elif source == "timeline":
            preferred_inline = Decimal(max(1, value.span_days)) * metric["timeline.dayWidth"]
            preferred_block = Decimal(max(1, value.item_count)) * metric["timeline.row.minBlockSize"]
        elif source == "timeline-axis":
            preferred_inline = Decimal(max(1, value.span_days)) * metric["timeline.dayWidth"]
            preferred_block = metric["timeline.axis.blockSize"]
        else:
            preferred_inline, preferred_block = text_inline, text_block
        if source != "table" and not (source == "observations" and value.table is not None and value.table.columns):
            minimum_inline = min(preferred_inline, text_inline)
            if value.min_inline is not None:
                minimum_inline = min(preferred_inline, value.min_inline)
        result[source] = Measurement(
            minimum_inline, preferred_inline, preferred_inline * 2,
            min(preferred_block, minimum_text_block), preferred_block, preferred_block * 2,
            (summary_flow.runs[0].baseline if summary_flow and summary_flow.runs else
             stack.baselines[0] if stack else Decimal(str(first_metrics.baseline(0, float(font_size), float(line_height))))),
            (summary_flow.runs[-1].baseline if summary_flow and summary_flow.runs else
             stack.baselines[-1] if stack else Decimal(str(first_metrics.baseline(0, float(font_size), float(line_height))))),
        )
        if heading_budget is not None and measured_runs and any(run.lines for run in measured_runs):
            last = measured_runs[-1]
            last_baseline = stack.baselines[-1] if stack else last.baseline
            if stack is None and len(measured_runs) > 1:
                previous = measured_runs[0]
                previous_baseline = previous.baseline
                prefix = previous.block_size
                for run in measured_runs[1:]:
                    last_baseline = max(prefix + run.baseline,
                                        previous_baseline - Decimal(str(previous.font_size))
                                        + previous.block_size + Decimal(str(run.font_size)))
                    previous, previous_baseline = run, last_baseline
                    prefix += run.block_size
            last_baseline += (Decimal(str(last.font_size)) * Decimal(str(last.line_height))
                              * max(0, len(last.lines) - 1))
            result[source] = replace(result[source], last_baseline=last_baseline)
        if source == "table" and table_inline is not None and value.table is not None:
            closed = measure_bounded_table(value.table, available_inline=table_inline,
                                            tokens=typography, font_metrics=font_metrics,
                                            metric_values=metric, original=result[source],
                                            reserved_inline=table_reserved_inline)
            bounded_tables[source] = closed
            result[source] = closed.measurement
    return MeasuredSources(result, dict(inputs), metric, run_measurements, block_stacks, summary_flows, bounded_tables)


def _table_content_inline(table: TableContent, typography: ThemeTokenView, font_metrics: Any,
                          metric: Mapping[str, Decimal], inset: float) -> Decimal:
    """Measure the table exactly as Layout will place its columns."""
    indent = metric.get("table.indent.inlineSize")
    header_lead = (header_child_lead(typography, first_column=bool(table.columns)
                                     and table.columns[0].column_id == table.hierarchy_column)
                   if table.indent_under_headers else None)
    step = float(indent) if indent is not None else None
    cell_indents = {
        key: (header_group_cell_indent(grouped=level.grouped, indent=step, lead=header_lead)
              if table.indent_under_headers
              else table_cell_indent(grouped=level.grouped, depth=level.depth, inset=inset, indent=step))
        for level in table.row_levels for key in level.keys
    }
    natural = measure_table_columns(columns=table.columns, cells=table.cells,
                                    measure_text=table_text_measurer(typography, font_metrics),
                                    minimum_inline=inset, hierarchy_column=table.hierarchy_column,
                                    cell_indents=cell_indents, header_role=typography.table_header_role())
    return Decimal(str(table_content_inline_size(natural, float(metric["table.column.gutter.inlineSize"]))))
