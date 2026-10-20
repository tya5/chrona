from math import nextafter

import pytest

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.presentation import table_text_fits_column, table_text_required_inline
from chrona.presentation.layout.surface_table import _resolve_table_text
from chrona.presentation.layout.sources import SourceInput, measure_sources
from chrona.presentation.layout.table_measurement import _fit_table_text, measure_bounded_table
from chrona.presentation.model.surface_content import (
    TableCellContent, TableColumnContent, TableColumnWidth, TableContent, TableRowLevel,
)
from chrona.presentation.model.theme_tokens import ThemeTokenView
from tests.unit.chrona.presentation.layout.test_sources import theme


class FractionalMetrics:
    content_identity = "sha256:table-forward-fit"

    def width(self, text, size, **kwargs):
        if text == "A B":
            return 753.6933920895333
        if text in {"H", "X", "(X)"}:
            return {"H": 14.02754960192089, "X": 14.02754960192089,
                    "(X)": 14.02754960192089}[text]
        if text == "…":
            return 1.0
        return len(text) * size / 2

    def baseline(self, top, size, line_height):
        return top + size


def _table(*, content="X", header="H", depth=0, required=False, wrap="forbid", affixes=("", "")):
    return TableContent(
        (TableColumnContent("task", header, "start", TableColumnWidth("content", "content"),
                            text_wrap=wrap),),
        (TableCellContent("a", "task", content, "tableCell", "text", affixes[0], affixes[1], required),),
        (), "task", (TableRowLevel(("a",), False, depth),),
    )


def _closed(table):
    resolved = theme()
    metrics = FractionalMetrics()
    measured = measure_sources({"table": SourceInput(item_count=1, column_count=1, table=table)},
                               resolved, font_metrics=metrics)
    return measure_bounded_table(table, available_inline=500, tokens=ThemeTokenView(resolved),
                                 font_metrics=metrics, metric_values=measured.metric_values,
                                 original=measured.measurements["table"])


@pytest.mark.parametrize("kind", ["header", "cell"])
def test_fractional_natural_width_equality_keeps_full_text_in_measurement_and_placement(kind):
    table = _table()
    closed = _closed(table)
    text = closed.headers[0] if kind == "header" else closed.cells[0]
    assert text.fit.content == (table.columns[0].header if kind == "header" else table.cells[0].content)
    assert not text.fit.ellipsized

    role_tokens = ThemeTokenView(theme())
    resolved, overflow = _resolve_table_text(
        "X", 14.027549601920889, "text", "ellipsize-with-source", role_tokens,
        FractionalMetrics(), column_inline_size=28.02754960192089, inset=14.0)
    assert (resolved, overflow) == ("X", "fit")


def test_forward_width_composes_fractional_indent_and_inset_in_one_order():
    advance, indent, inset = 14.02754960192089, 16.0, 14.0
    required = table_text_required_inline(advance, indent=indent, inset=inset)
    assert required == 44.02754960192089
    assert table_text_fits_column(advance, required, indent=indent, inset=inset)
    assert not table_text_fits_column(advance, nextafter(required, float("-inf")),
                                      indent=indent, inset=inset)


def test_bounded_cell_with_hierarchy_indent_keeps_fractional_equality():
    table = _table(depth=1)
    closed = _closed(table)
    assert dict(closed.cell_indents)["a"] == 16
    assert closed.columns[0].natural_inline_size == table_text_required_inline(
        14.02754960192089, indent=16.0, inset=14.0)
    assert closed.cells[0].fit.content == "X"
    assert not closed.cells[0].fit.ellipsized


def test_affixed_text_uses_full_source_advance_for_equality_admission():
    tokens = ThemeTokenView(theme())
    fit = _fit_table_text("(X)", available=14.027549601920889, role="text", wrap="forbid",
                          tokens=tokens, font_metrics=FractionalMetrics(), prefix="(", suffix=")",
                          column_inline_size=28.02754960192089, inset=14.0)
    assert fit.content == "(X)"
    assert not fit.ellipsized


def test_wrappable_fractional_equality_does_not_introduce_an_unneeded_wrap_or_ellipsis():
    tokens = ThemeTokenView(theme())
    fit = _fit_table_text("X", available=14.027549601920889, role="text", wrap="allow",
                          tokens=tokens, font_metrics=FractionalMetrics(),
                          column_inline_size=28.02754960192089, inset=14.0)
    assert fit.lines == ("X",)
    assert not fit.ellipsized


def test_required_forbid_text_still_rejects_a_true_one_ulp_shortage():
    tokens = ThemeTokenView(theme())
    required = table_text_required_inline(14.02754960192089, inset=14.0)
    with pytest.raises(LayoutError, match="E_LAYOUT_TABLE_OVERFLOW"):
        _fit_table_text("X", available=nextafter(required, float("-inf")) - 14.0,
                        role="text", wrap="forbid", tokens=tokens,
                        font_metrics=FractionalMetrics(), required=True,
                        column_inline_size=nextafter(required, float("-inf")), inset=14.0)


def test_inverse_subtraction_that_rounds_up_cannot_admit_short_full_text():
    advance = 753.6933920895333
    indent, inset = 79.93001136936257, 8.314399955454803
    column_width = 841.9378034143506  # one representable float below the shared forward requirement
    inverse_available = column_width - indent - inset
    assert inverse_available == advance
    assert not table_text_fits_column(advance, column_width, indent=indent, inset=inset)

    tokens = ThemeTokenView(theme())
    resolved, overflow = _resolve_table_text(
        "A B", inverse_available, "text", "ellipsize-with-source", tokens,
        FractionalMetrics(), column_inline_size=column_width, indent=indent, inset=inset)
    assert resolved != "A B"
    assert overflow == "ellipsized"

    wrapped = _fit_table_text("A B", available=inverse_available, role="text", wrap="allow",
                              tokens=tokens, font_metrics=FractionalMetrics(),
                              column_inline_size=column_width, indent=indent, inset=inset)
    assert wrapped.lines == ("A", "B")
    assert not wrapped.ellipsized
