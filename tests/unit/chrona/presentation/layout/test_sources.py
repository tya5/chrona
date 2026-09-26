from decimal import Decimal

import pytest

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.presentation import place_table_columns, table_text_measurer
from chrona.presentation.layout.sources import SourceInput, SourceTextRun, measure_sources, resolve_theme_metrics
from chrona.presentation.model.surface_content import (
    TableCellContent, TableColumnContent, TableColumnWidth, TableContent, TableRowLevel,
)
from chrona.presentation.model.theme_tokens import ThemeTokenView


def theme():
    metrics = {
        "text.body.size": 14, "text.body.lineHeight": 1.4,
        "timeline.dayWidth": 12, "timeline.row.minBlockSize": 40, "timeline.row.paddingBlock": 8, "timeline.mark.blockSize": 8,
        "timeline.axis.blockSize": 48, "table.column.minInlineSize": 120, "table.column.gutter.inlineSize": 8,
        "table.header.blockSize": 44, "table.indent.inlineSize": 16,
        "network.node.minInlineSize": 120, "network.node.minBlockSize": 36, "network.rank.gap": 24,
    }
    values = {f"metric.{i}": {"type": "number", "value": value} for i, value in enumerate(metrics.values())}
    values |= {
        "family": {"type": "fontFamily", "value": "Nimbus Sans"},
        "weight": {"type": "fontWeight", "value": 400},
        "heading-size": {"type": "number", "value": 34},
        "heading-line": {"type": "number", "value": 1.2},
        "letter-spacing": {"type": "number", "value": 0},
        "text-transform": {"type": "textTransform", "value": "none"},
        "numeric-spacing": {"type": "numericSpacing", "value": "proportional"},
    }
    treatment = {"letterSpacing": "letter-spacing", "textTransform": "text-transform", "numericSpacing": "numeric-spacing"}
    text = {"fontFamily": "family", "fontWeight": "weight", "fontSize": "metric.0", "lineHeight": "metric.1"} | treatment
    heading = {"fontFamily": "family", "fontWeight": "weight", "fontSize": "heading-size", "lineHeight": "heading-line"} | treatment
    return {"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
            "body": {"values": values, "metrics": {name: f"metric.{i}" for i, name in enumerate(metrics)},
                     "roles": {"text": text, "heading": heading, "axis": text, "legend": text,
                               "annotation": text, "summary": text, "metric": heading}}}


def test_sources_are_measured_once_from_semantic_inputs_and_theme_metrics():
    class Metrics:
        content_identity = "sha256:test"
        def width(self, value, size): return len(value) * size / 2
        def baseline(self, top, size, line_height): return top + size
    measured = measure_sources({
        "title": SourceInput(("Controller Z",)),
        "table": SourceInput(item_count=5, column_count=3),
        "timeline": SourceInput(item_count=5, span_days=60),
        "timeline-axis": SourceInput(span_days=60),
    }, theme(), font_metrics=Metrics())
    assert measured.measurements["table"].preferred_inline == Decimal(360)
    assert measured.measurements["timeline"].preferred_inline == Decimal(720)
    assert measured.measurements["timeline-axis"].preferred_block == Decimal(48)
    assert measured.metric_values["text.body.size"] == Decimal(14)
    assert measured.metric_values["text.measuredAverageAdvance"] == Decimal(7)


def test_missing_unknown_and_wrong_type_metric_bindings_diagnose():
    class Metrics:
        content_identity = "sha256:test"
        def width(self, value, size): return len(value) * size / 2
        def baseline(self, top, size, line_height): return top + size
    value = theme(); del value["body"]["metrics"]["timeline.dayWidth"]
    with pytest.raises(LayoutError, match="E_LAYOUT_METRIC_REQUIRED"):
        measure_sources({}, value, font_metrics=Metrics())
    value = theme(); value["body"]["metrics"]["unknown.gap"] = "metric.0"
    with pytest.raises(LayoutError, match="E_LAYOUT_METRIC_UNKNOWN"):
        measure_sources({}, value, font_metrics=Metrics())
    value = theme(); value["body"]["values"]["metric.0"] = {"type": "color", "value": "#fff"}
    with pytest.raises(LayoutError, match="E_LAYOUT_TOKEN_TYPE"):
        measure_sources({}, value, font_metrics=Metrics())


def test_view_required_optional_metric_is_a_theme_diagnostic():
    class Metrics:
        content_identity = "sha256:test"
        def width(self, value, size): return len(value) * size / 2
        def baseline(self, top, size, line_height): return top + size
    with pytest.raises(LayoutError, match="E_THEME_METRIC_REQUIRED") as error:
        measure_sources({}, theme(), font_metrics=Metrics(), required_metrics=("timeline.groupHeader.blockSize",))
    assert error.value.path == "/body/metrics/timeline.groupHeader.blockSize"
    assert "timeline.groupHeader.blockSize" not in measure_sources({}, theme(), font_metrics=Metrics()).metric_values


def test_corner_radius_metrics_are_optional_and_explicitly_allow_zero():
    value = theme()
    assert "timeline.mark.cornerRadius" not in resolve_theme_metrics(value)
    value["body"]["values"]["mark-radius"] = {"type": "number", "value": 0}
    value["body"]["metrics"]["timeline.mark.cornerRadius"] = "mark-radius"
    assert resolve_theme_metrics(value)["timeline.mark.cornerRadius"] == Decimal(0)
    value["body"]["values"]["mark-radius"]["value"] = -1
    with pytest.raises(LayoutError, match="E_LAYOUT_TOKEN_TYPE"):
        resolve_theme_metrics(value)


def test_heading_source_uses_heading_extent_and_baseline():
    class Metrics:
        content_identity = "sha256:test"
        def width(self, value, size): return len(value) * size / 2
        def baseline(self, top, size, line_height): return top + size
    measured = measure_sources({"title": SourceInput(("Controller Z",), typography_role="heading")}, theme(), font_metrics=Metrics())
    title = measured.measurements["title"]
    assert title.preferred_inline == Decimal(204)
    assert title.preferred_block == Decimal("40.8")
    assert title.first_baseline == Decimal(34)


def test_mixed_typography_runs_measure_their_actual_cumulative_height():
    class Metrics:
        content_identity = "sha256:test"
        def width(self, value, size): return len(value) * size / 2
        def baseline(self, top, size, line_height): return top + size
    measured = measure_sources({"summary": SourceInput(runs=(
        SourceTextRun("Key figures", "summary"), SourceTextRun("2026-03-04", "heading"),
        SourceTextRun("as of", "summary"),
    ))}, theme(), font_metrics=Metrics())
    summary = measured.measurements["summary"]
    assert summary.preferred_block == Decimal("80.0")
    assert summary.preferred_inline == Decimal(170)


def _table_metrics():
    class Metrics:
        content_identity = "sha256:test"
        def width(self, value, size): return len(value) * size / 2
        def baseline(self, top, size, line_height): return top + size
    return Metrics()


def _table(cell_text: str) -> TableContent:
    width = TableColumnWidth("content", "content")
    columns = (TableColumnContent("name", "Name", "start", width), TableColumnContent("delta", "Δ", "end", width))
    cells = (TableCellContent("a", "name", cell_text, "tableCell"), TableCellContent("a", "delta", "+12", "tableCell"))
    return TableContent(columns, cells, (), None, (TableRowLevel(("a",), False),))


def test_content_sized_table_slot_is_its_measured_columns_and_gutters():
    """#480: the slot measure and column placement are one computation."""
    table = _table("A work package name much wider than the column floor")
    measured = measure_sources({"table": SourceInput(("A",), 1, 2, table=table)}, theme(), font_metrics=_table_metrics())
    preferred = measured.measurements["table"].preferred_inline
    assert preferred > Decimal(240)  # wider than 2 x table.column.minInlineSize
    placed = place_table_columns(columns=table.columns, cells=table.cells, bounds=(0.0, 0.0, float(preferred), 20.0),
                                 measure_text=table_text_measurer(ThemeTokenView(theme()), _table_metrics()),
                                 minimum_inline=14.0, gutter=8.0)
    assert placed[-1].inline + placed[-1].inline_size == pytest.approx(float(preferred))
    # `min: content` keeps its floor-and-label basis until #487.
    assert measured.measurements["table"].min_inline == min(Decimal(240), Decimal(7))


def test_table_column_floor_binds_when_the_measured_columns_are_narrower():
    measured = measure_sources({"table": SourceInput(("A",), 1, 2, table=_table("A"))}, theme(), font_metrics=_table_metrics())
    assert measured.measurements["table"].preferred_inline == Decimal(240)
