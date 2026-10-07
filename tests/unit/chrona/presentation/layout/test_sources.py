from decimal import Decimal

import pytest

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.presentation import place_table_columns, table_text_measurer
from chrona.presentation.layout.sources import SourceInput, SourceTextRun, measure_sources, resolve_theme_metrics
from chrona.presentation.layout.text import place_text
from chrona.presentation.model.surface_content import (
    TableCellContent, TableColumnContent, TableColumnWidth, TableContent, TableRowLevel,
)
from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView


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


def test_an_unbound_track_size_is_the_row_less_a_padding_on_each_side_and_a_bound_one_wins():
    value = theme()
    assert resolve_theme_metrics(value)["timeline.mark.blockSize"] == Decimal(8)
    del value["body"]["metrics"]["timeline.mark.blockSize"]
    assert resolve_theme_metrics(value)["timeline.mark.blockSize"] == Decimal(24)
    value["body"]["values"]["metric.3"]["value"] = 50
    assert resolve_theme_metrics(value)["timeline.mark.blockSize"] == Decimal(34)
    value["body"]["values"]["metric.4"]["value"] = 60
    with pytest.raises(LayoutError, match="E_LAYOUT_METRIC_REQUIRED"):
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


def test_measured_block_width_uses_the_runs_declared_numeric_spacing():
    class Metrics:
        content_identity = "sha256:test"
        def ensure_numeric_spacing(self, mode):
            assert mode in {"proportional", "tabular"}
        def width(self, value, size, letter_spacing=0, numeric_spacing="proportional"):
            return len(value) * size / (1 if numeric_spacing == "tabular" else 2)
        def baseline(self, top, size, line_height): return top + size

    resolved = theme()
    resolved["body"]["values"]["numeric-spacing"]["value"] = "tabular"
    source = SourceInput(runs=(SourceTextRun("11", "heading", "title"),), run_flow="block")
    measured = measure_sources({"title": source}, resolved, font_metrics=Metrics())
    assert measured.run_measurements["title"][0].numeric_spacing == "tabular"
    assert measured.run_measurements["title"][0].inline_size == Decimal(68)
    assert measured.measurements["title"].preferred_inline == Decimal(68)
    placed = place_text(placement_id="title", source_ref="title", content="11", inline=0,
                        baseline_block=float(measured.block_stacks["title"].baselines[0]),
                        typography_role="heading", theme_tokens=ThemeTokenView(resolved), font_metrics=Metrics())
    assert placed.numeric_spacing == "tabular"
    assert placed.bounds.inline_size == measured.run_measurements["title"][0].inline_size


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


def test_default_stack_flow_is_unaffected_by_an_unused_kicker_gap():
    class Metrics:
        content_identity = "sha256:test"
        def width(self, value, size): return len(value) * size / 2
        def baseline(self, top, size, line_height): return top + size

    source = {"title": SourceInput(("Controller Z",), typography_role="heading")}
    without_gap = theme()
    with_gap = theme()
    with_gap["body"]["values"]["kicker-gap"] = {"type": "number", "value": 7}
    with_gap["body"]["roles"]["kicker"] = {
        **with_gap["body"]["roles"]["heading"], "blockGap": "kicker-gap",
    }
    old_measurement = measure_sources(source, without_gap, font_metrics=Metrics())
    new_measurement = measure_sources(source, with_gap, font_metrics=Metrics())

    assert old_measurement.measurements == new_measurement.measurements
    assert old_measurement.run_measurements == new_measurement.run_measurements
    assert old_measurement.block_stacks == new_measurement.block_stacks == {}
    title = old_measurement.measurements["title"]
    assert title.preferred_block == Decimal("40.8")
    assert title.first_baseline == Decimal(34)


def test_block_source_uses_theme_gap_and_closed_mixed_role_baselines_and_envelope():
    class Metrics:
        content_identity = "sha256:test"
        def width(self, value, size): return len(value) * size / 2
        def baseline(self, top, size, line_height): return top + size * 1.1

    resolved = theme()
    resolved["body"]["values"]["kicker-gap"] = {"type": "number", "value": 6}
    resolved["body"]["roles"]["kicker"] = {
        **resolved["body"]["roles"]["text"], "blockGap": "kicker-gap",
    }
    resolved["body"]["roles"]["subtitle"] = resolved["body"]["roles"]["text"]
    measured = measure_sources({"title": SourceInput(runs=(
        SourceTextRun("Kicker", "kicker"), SourceTextRun("Main title", "heading"),
        SourceTextRun("Subtitle", "subtitle"),
    ), run_flow="block")}, resolved, font_metrics=Metrics())

    stack = measured.block_stacks["title"]
    title = measured.measurements["title"]
    runs = measured.run_measurements["title"]
    assert title.first_baseline == stack.baselines[0]
    assert title.last_baseline == stack.baselines[-1]
    assert title.preferred_block == stack.block_size
    bounds = tuple(
        (baseline - Decimal(str(run.font_size)),
         baseline - Decimal(str(run.font_size)) + run.block_size)
        for run, baseline in zip(runs, stack.baselines)
    )
    assert min(top for top, _ in bounds) >= 0
    assert max(bottom for _, bottom in bounds) <= stack.block_size


@pytest.mark.parametrize(
    ("declared", "token_type"),
    [(-1, "number"), ("bad-number", "color")],
)
def test_text_block_gap_rejects_negative_and_non_number_tokens(declared, token_type):
    resolved = theme()
    resolved["body"]["values"]["block-gap"] = {"type": token_type, "value": declared}
    resolved["body"]["roles"]["kicker"] = {
        **resolved["body"]["roles"]["heading"], "blockGap": "block-gap",
    }

    with pytest.raises(ThemeTokenError, match="E_THEME_TOKEN_TYPE") as error:
        ThemeTokenView(resolved).text_block_gap("kicker")
    assert error.value.path == "/body/roles/kicker/blockGap"


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
    # #487: `minmax: {min: content}` is the table's measured columns and gutters,
    # never the widest row label; here the measured content exceeds the column
    # floor, so the minimum equals the (also content-driven) preferred size.
    assert measured.measurements["table"].min_inline == preferred


def test_table_minimum_falls_back_to_the_floor_and_label_basis_without_columns():
    """A table source with no typed columns has nothing to measure (#487); the
    #480 floor-and-label basis still applies."""
    measured = measure_sources({"table": SourceInput(("A",), 1, 2)}, theme(), font_metrics=_table_metrics())
    assert measured.measurements["table"].min_inline == min(Decimal(240), Decimal(7))


def test_table_column_floor_binds_when_the_measured_columns_are_narrower():
    measured = measure_sources({"table": SourceInput(("A",), 1, 2, table=_table("A"))}, theme(), font_metrics=_table_metrics())
    assert measured.measurements["table"].preferred_inline == Decimal(240)
    # #487: the floor is a `preferred_inline` bound only. The minimum is still
    # the narrower measured content, so `minmax: {min: content}` never asks for
    # more than the table actually needs, even though the column floor grows
    # `preferred_inline` past it.
    assert measured.measurements["table"].min_inline < Decimal(240)


def test_a_scaled_role_is_measured_compressed_and_the_run_carries_the_factor():
    class Metrics:
        content_identity = "sha256:test"
        def width(self, value, size, letter_spacing=0): return len(value) * size / 2
        def baseline(self, top, size, line_height): return top + size
    resolved = theme()
    resolved["body"]["values"]["squeeze"] = {"type": "number", "value": "0.5"}
    resolved["body"]["roles"]["heading"] = {**resolved["body"]["roles"]["heading"], "horizontalScale": "squeeze"}
    measured = measure_sources({"title": SourceInput(("Controller Z",), typography_role="heading")}, resolved,
                               font_metrics=Metrics())
    (run,) = measured.run_measurements["title"]
    assert measured.measurements["title"].preferred_inline == Decimal(102)  # 204 at natural width
    assert (run.inline_size, run.horizontal_scale) == (Decimal(102), 0.5)
    natural = measure_sources({"title": SourceInput(("Controller Z",), typography_role="heading")}, theme(),
                              font_metrics=Metrics())
    assert natural.run_measurements["title"][0].horizontal_scale == 1.0
