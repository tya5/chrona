from dataclasses import replace
from decimal import Decimal as D

import pytest

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.sources import SourceInput, measure_sources
from chrona.presentation.layout.table_measurement import measure_bounded_table
from chrona.presentation.model.surface_content import (
    TableCellContent, TableColumnContent, TableColumnWidth, TableContent, TableRowLevel,
)
from chrona.presentation.model.theme_tokens import ThemeTokenView
from tests.unit.chrona.presentation.layout.test_sources import theme


class Metrics:
    content_identity = "sha256:bounded-table-test"

    def width(self, text, size, **kwargs):
        return len(text) * size / 2

    def baseline(self, top, size, line_height):
        return top + size


def content(long="word " * 100, wrap="allow", orientation="horizontal", header="Task"):
    return TableContent(
        (TableColumnContent("task", header, "start", TableColumnWidth("content", "fr", 1), orientation, wrap),
         TableColumnContent("owner", "Owner", "start", TableColumnWidth("content", "content"))),
        (TableCellContent("a", "task", long, "tableCell"),
         TableCellContent("a", "owner", "Amy", "tableCell"),
         TableCellContent("b", "task", "Short", "tableCell")),
        (), None, (TableRowLevel(("a",), False), TableRowLevel(("b",), False)))


def close(table, width=300, **kwargs):
    resolved = theme()
    measured = measure_sources({"table": SourceInput(item_count=2, column_count=2, table=table)},
                               resolved, font_metrics=Metrics())
    return measure_bounded_table(table, available_inline=width, tokens=ThemeTokenView(resolved),
                                 font_metrics=Metrics(), metric_values=measured.metric_values,
                                 original=measured.measurements["table"], **kwargs), measured


def test_closed_word_lines_and_each_rows_own_tallest_cell_drive_source_height():
    result, original = close(content())
    long = next(cell for cell in result.cells if cell.source_ref == "a" and cell.column_id == "task")
    assert len(long.fit.lines) > 1
    assert not long.fit.ellipsized
    assert long.source_content == "word " * 100
    assert long.font_asset_identity == Metrics.content_identity
    rows = dict(result.row_text_blocks)
    assert rows["a"] > rows["b"] == D("19.6")
    assert result.header_block == 44
    assert result.measurement.preferred_block > original.measurements["table"].preferred_block
    assert result.measurement.min_inline <= result.measurement.preferred_inline <= 300
    assert result.columns[-1].inline + result.columns[-1].inline_size == 300


@pytest.mark.parametrize("wrap", ["allow", "forbid"])
def test_indivisible_long_unit_keeps_source_and_selects_ellipsis(wrap):
    result, _ = close(content("X" * 1000, wrap))
    cell = result.cells[0]
    assert cell.fit.ellipsized
    assert cell.fit.content.endswith("…")
    assert cell.source_content == "X" * 1000


def test_cjk_wrap_uses_existing_character_boundaries_without_ellipsis():
    result, _ = close(content("開発計画" * 100))
    assert len(result.cells[0].fit.lines) > 1
    assert not result.cells[0].fit.ellipsized


def test_header_prefix_does_not_inflate_short_rows():
    result, _ = close(content("Short", header="word " * 100))
    assert result.header_block > 44
    assert dict(result.row_text_blocks) == {"a": D("19.6"), "b": D("19.6")}


@pytest.mark.parametrize("orientation", ["rotate-cw", "rotate-ccw"])
def test_rotated_header_preserves_full_advance_and_reserves_it_as_block(orientation):
    header = "very long header " * 10
    result, _ = close(content("Short", orientation=orientation, header=header))
    closed = result.headers[0]
    assert closed.fit.content == header
    assert not closed.fit.ellipsized
    assert result.header_block == D(str(len(header) * 7))
    assert closed.block_size > result.columns[0].inline_size


def test_fitting_source_keeps_original_measurement_and_whitespace():
    table = content("  Short\t  ")
    result, original = close(table, width=1000)
    assert result.measurement == original.measurements["table"]
    assert result.cells[0].fit.content == "  Short\t  "
    assert result.cells[0].fit.lines == ("  Short\t  ",)


def test_hierarchy_indent_and_reserved_host_chrome_share_actual_column_budget():
    table = replace(content(), hierarchy_column="task",
                    row_levels=(TableRowLevel(("a",), True, 2), TableRowLevel(("b",), False)))
    result, _ = close(table, reserved_inline=16)
    assert result.columns[0].inline == 16
    assert dict(result.cell_indents)["a"] == 46
    assert result.column_minima[0] >= 46 + 14
    assert result.columns[-1].inline + result.columns[-1].inline_size <= 300


def test_ellipsis_keeps_complete_affixes_around_longest_source_core_prefix():
    table = content("Short", wrap="forbid")
    full = "(" + "X" * 1000 + ")"
    table = replace(table, cells=(replace(table.cells[0], content=full, affix_prefix="(", affix_suffix=")"),))
    result, _ = close(table)
    cell = result.cells[0]
    assert cell.fit.ellipsized
    assert cell.fit.content.startswith("(") and cell.fit.content.endswith("…)")
    assert cell.source_content == full


def test_duplicate_subject_aliases_have_independent_row_demands():
    table = replace(content(), row_levels=(TableRowLevel(("row-a", "a"), False),
                                           TableRowLevel(("row-b", "a"), False)))
    result, original = close(table)
    row = dict(result.row_text_blocks)["a"]
    extra = row + 8 - 40
    assert result.measurement.preferred_block == original.measurements["table"].preferred_block + 2 * extra


def test_mandatory_columns_or_reserved_chrome_cannot_fit_and_fail_closed():
    with pytest.raises(LayoutError, match="E_LAYOUT_TABLE_OVERFLOW"):
        close(content(), width=20)
    with pytest.raises(LayoutError, match="E_LAYOUT_TABLE_OVERFLOW"):
        close(content(), reserved_inline=300)


def test_public_source_measurement_uses_one_closed_table_when_budget_is_supplied():
    inputs = {"table": SourceInput(item_count=2, column_count=2, table=content())}
    original = measure_sources(inputs, theme(), font_metrics=Metrics())
    bounded = measure_sources(inputs, theme(), font_metrics=Metrics(), table_inline=300,
                               table_reserved_inline=16)
    assert not original.bounded_tables
    closed = bounded.bounded_tables["table"]
    assert bounded.measurements["table"] == closed.measurement
    assert closed.available_inline == 300 and closed.reserved_inline == 16
    assert closed.columns[0].inline == 16
    assert bounded.inputs == original.inputs
    assert bounded.run_measurements == original.run_measurements
    assert closed.cells[0].fit.lines and len(closed.cells[0].fit.lines) > 1


def test_empty_selected_source_does_not_create_phantom_bounded_table_content():
    inputs = {"table": SourceInput(table=content(), content_present=False)}
    closed = measure_sources(inputs, theme(), font_metrics=Metrics(), table_inline=300)
    assert closed.measurements["table"].preferred_block == 0
    assert not closed.bounded_tables


def test_actual_text_source_closure_drives_engine_width_and_height_at_final_fr_share():
    from chrona.presentation.layout.engine import LayoutSizingContext, solve_layout
    from tests.unit.chrona.presentation.layout.test_table_inline_budget import container, measurement, profile, probe, slot

    table = content()
    inputs = {"table": SourceInput(item_count=2, column_count=2, table=table)}
    resolved_theme = theme()
    original = measure_sources(inputs, resolved_theme, font_metrics=Metrics())
    resolved = profile(container("row", [slot(inlineSize={"minmax": {"min": "content", "max": {"fr": 3}}}),
                                         slot("other", share=None, source="timeline", inlineSize={"fr": 7}, blockSize="fill")]))
    sources = {"table": original.measurements["table"], "other": measurement(30)}
    budgets = probe(resolved, sources)
    closed_by_width = {}

    def at_width(slot_id, inline):
        assert slot_id == "table"
        closed = measure_bounded_table(table, available_inline=float(inline), tokens=ThemeTokenView(resolved_theme),
                                       font_metrics=Metrics(), metric_values=original.metric_values,
                                       original=original.measurements["table"])
        closed_by_width[inline] = closed
        return closed.measurement

    final = solve_layout(resolved, viewport_inline=1000, viewport_block=500, measurements=sources,
                         sizing=LayoutSizingContext(budgets, at_width))
    placed = {item.node_id: item.bounds for item in final.decisions}
    assert placed["table"].inline_size == 288 < budgets["table"].ceiling == 384
    assert placed["other"].inline_size == 672
    closed = closed_by_width[placed["table"].inline_size]
    assert len(closed.cells[0].fit.lines) > 1
    assert closed.columns[-1].inline + closed.columns[-1].inline_size == 288
    assert placed["table"].block_size == closed.measurement.preferred_block
    assert not final.fit_warnings
