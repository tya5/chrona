"""Pure source measurement inputs shared by layout and Scene composition."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from chrona.presentation.layout.model import LayoutError, Measurement
from chrona.presentation.model.theme_tokens import ThemeTokenView


@dataclass(frozen=True)
class SourceTextRun:
    """Text and declared typography to measure as one source line."""

    content: str
    typography_role: str


@dataclass(frozen=True)
class SourceInput:
    """Semantic content facts needed to measure one closed presentation source."""

    lines: tuple[str, ...] = ()
    item_count: int = 0
    column_count: int = 1
    span_days: int = 1
    typography_role: str = "text"
    runs: tuple[SourceTextRun, ...] = ()

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


REQUIRED_METRICS = (
    "text.body.size", "text.body.lineHeight",
    "timeline.dayWidth", "timeline.row.minBlockSize", "timeline.mark.blockSize", "timeline.axis.blockSize",
    "table.column.minInlineSize", "table.column.gutter.inlineSize", "table.header.blockSize",
)

OPTIONAL_METRICS = ("timeline.groupHeader.blockSize",)


def resolve_theme_metrics(theme: Mapping[str, Any]) -> dict[str, Decimal]:
    body = theme.get("body", {})
    bindings, values = body.get("metrics", {}), body.get("values", {})
    resolved: dict[str, Decimal] = {}
    unknown = set(bindings) - set(REQUIRED_METRICS) - set(OPTIONAL_METRICS)
    if unknown:
        raise LayoutError("E_LAYOUT_METRIC_UNKNOWN", "/body/metrics/" + sorted(unknown)[0])
    for name in REQUIRED_METRICS + OPTIONAL_METRICS:
        token = bindings.get(name)
        if not isinstance(token, str):
            if name in OPTIONAL_METRICS:
                continue
            raise LayoutError("E_LAYOUT_METRIC_REQUIRED", "/body/metrics/" + name)
        declared = values.get(token)
        if not isinstance(declared, Mapping) or declared.get("type") != "number":
            raise LayoutError("E_LAYOUT_TOKEN_TYPE", "/body/metrics/" + name)
        try:
            value = Decimal(str(declared["value"]))
        except (InvalidOperation, KeyError) as error:
            raise LayoutError("E_LAYOUT_TOKEN_TYPE", "/body/metrics/" + name) from error
        if not value.is_finite() or value <= 0:
            raise LayoutError("E_LAYOUT_TOKEN_TYPE", "/body/metrics/" + name)
        resolved[name] = value
    return resolved


def measure_sources(inputs: Mapping[str, SourceInput], theme: Mapping[str, Any], *, font_metrics: Any) -> MeasuredSources:
    """Measure every declared source once without reading Layout or renderer state."""
    metric = resolve_theme_metrics(theme)
    typography = ThemeTokenView(theme)
    _, _, body_size, _ = typography.typography("text")
    metric["text.measuredAverageAdvance"] = Decimal(str(font_metrics.width("M", float(body_size))))
    result: dict[str, Measurement] = {}
    for source, value in sorted(inputs.items()):
        runs = value.text_runs()
        first_role = runs[0].typography_role if runs else value.typography_role
        _, _, font_size, line_height = typography.typography(first_role)
        text_line = font_size * line_height
        average_advance = Decimal(str(font_metrics.width("M", float(font_size))))
        measured_width = max((Decimal(str(font_metrics.width(run.content, float(typography.typography(run.typography_role)[2])))) for run in runs), default=average_advance)
        text_block = sum((typography.typography(run.typography_role)[2] * typography.typography(run.typography_role)[3] for run in runs), Decimal(0))
        if not runs:
            text_block = text_line
        text_inline = max(average_advance, measured_width)
        if source == "table":
            preferred_inline = Decimal(max(1, value.column_count)) * metric["table.column.minInlineSize"]
            preferred_block = metric["table.header.blockSize"] + Decimal(max(1, value.item_count)) * metric["timeline.row.minBlockSize"]
        elif source == "timeline":
            preferred_inline = Decimal(max(1, value.span_days)) * metric["timeline.dayWidth"]
            preferred_block = Decimal(max(1, value.item_count)) * metric["timeline.row.minBlockSize"]
        elif source == "timeline-axis":
            preferred_inline = Decimal(max(1, value.span_days)) * metric["timeline.dayWidth"]
            preferred_block = metric["timeline.axis.blockSize"]
        else:
            preferred_inline, preferred_block = text_inline, text_block
        result[source] = Measurement(
            min(preferred_inline, text_inline), preferred_inline, preferred_inline * 2,
            min(preferred_block, text_block), preferred_block, preferred_block * 2,
            Decimal(str(font_metrics.baseline(0, float(font_size), float(line_height)))),
            Decimal(str(font_metrics.baseline(0, float(font_size), float(line_height)))),
        )
    return MeasuredSources(result, dict(inputs), metric)
