"""Strict column minima/allocation; full surface and migration gates are separate."""
from decimal import Decimal as D
from random import Random

import pytest

from chrona.presentation.layout.model import LayoutError, geometry_sum
from chrona.presentation.layout.presentation import measure_table_column_minima, place_table_columns
from chrona.presentation.layout.tracks import resolve_flexible_tracks
from chrona.presentation.model.surface_content import TableCellContent, TableColumnContent, TableColumnWidth


def column(name, maximum="fr", fraction=1, orientation="horizontal"):
    return TableColumnContent(name, name, "start", TableColumnWidth("content", maximum, fraction), orientation)


def measure(content, role, orientation="horizontal"):
    if orientation != "horizontal":
        return 14.0
    return len(content) * (30.0 if role == "numeric" else 10.0)


def allocate(columns, cells, width, *, gutter=0, **extra):
    minima = measure_table_column_minima(columns=columns, cells=cells, measure_text=measure,
                                         minimum_inline=10, **extra)
    return place_table_columns(columns=columns, cells=cells, bounds=(0, 0, width, 100),
                                measure_text=measure, minimum_inline=10, gutter=gutter,
                                mandatory_inline=minima, **extra)


def test_each_cell_floor_uses_its_own_role_affixes_and_hierarchy_indent():
    columns = (column("task"), column("delta"))
    cells = (TableCellContent("a", "task", "long title", "tableCell"),
             TableCellContent("a", "delta", "+123d", "tableCell", "numeric", "+", "d"))
    minima = measure_table_column_minima(columns=columns, cells=cells, measure_text=measure,
                                         minimum_inline=10, hierarchy_column="delta", cell_indents={"a": 15})
    assert minima == (20, 115)


def test_empty_value_and_fitting_single_character_do_not_require_an_ellipsis():
    columns = (TableColumnContent("empty", "", "start", TableColumnWidth("content", "content")),
               TableColumnContent("one", "1", "start", TableColumnWidth("content", "content")))
    assert measure_table_column_minima(columns=columns, cells=(), measure_text=measure,
                                       minimum_inline=10) == (10, 20)


@pytest.mark.parametrize("orientation", ["rotate-cw", "rotate-ccw", "vertical-rl", "vertical-lr"])
def test_native_header_inline_thickness_is_not_horizontal_label_advance(orientation):
    columns = (TableColumnContent("task", "a very long heading", "start",
                                  TableColumnWidth("content", "fr", 1), orientation),)
    assert measure_table_column_minima(columns=columns, cells=(), measure_text=measure,
                                       minimum_inline=10) == (24,)


def test_long_title_cannot_push_nonflexible_short_owner_or_columns_outside_slot():
    columns = (column("task"), column("owner", "content"))
    cells = (TableCellContent("a", "task", "word " * 1000, "tableCell"),
             TableCellContent("a", "owner", "Amy", "tableCell"))
    result = allocate(columns, cells, 200, gutter=8)
    assert tuple(item.inline_size for item in result) == (132, 60)
    assert result[0].natural_inline_size > 200
    assert result[1].inline == 140
    assert result[-1].inline + result[-1].inline_size == 200


def test_content_columns_share_shortage_with_individual_floors_not_uniform_shrink():
    columns = (column("first", "content"), column("second", "content"))
    cells = (TableCellContent("a", "first", "x" * 100, "tableCell"),
             TableCellContent("a", "second", "+123d", "tableCell", "numeric", "+", "d"))
    result = allocate(columns, cells, 160)
    assert tuple(item.inline_size for item in result) == (60, 100)
    assert geometry_sum(item.inline_size for item in result) == 160


def test_declared_fraction_weights_act_after_content_columns_and_required_floors():
    columns = (column("fixed", "content"), column("one", fraction=1), column("three", fraction=3))
    cells = tuple(TableCellContent("a", name, "x" * 100, "tableCell") for name in ("one", "three"))
    result = allocate(columns, cells, 260)
    assert tuple(item.inline_size for item in result) == (60, 50, 150)


def test_fill_has_unit_weight_even_without_a_normalized_fraction_operand():
    columns = (column("fill", "fill", 0), column("three", fraction=3))
    cells = tuple(TableCellContent("a", name, "x" * 100, "tableCell") for name in ("fill", "three"))
    assert tuple(item.inline_size for item in allocate(columns, cells, 200)) == (50, 150)


def test_infeasible_mandatory_columns_and_gutters_fail_instead_of_overflowing():
    columns = (column("first"), column("second"))
    with pytest.raises(LayoutError, match="E_LAYOUT_TABLE_OVERFLOW"):
        allocate(columns, (), 47, gutter=8)


@pytest.mark.parametrize("overflow", ["visible-overflow", "ellipsize-with-source"])
def test_fitting_natural_columns_retain_exact_legacy_placements(overflow):
    columns = (column("task"), column("owner", "content"))
    cells = (TableCellContent("a", "task", "Short", "tableCell"),)
    kwargs = dict(columns=columns, cells=cells, bounds=(12, 4, 500, 100), measure_text=measure,
                  minimum_inline=10, gutter=8, overflow=overflow)
    minima = measure_table_column_minima(columns=columns, cells=cells, measure_text=measure, minimum_inline=10)
    assert place_table_columns(**kwargs, mandatory_inline=minima) == place_table_columns(**kwargs)


@pytest.mark.parametrize("upper,expected", [(1, [D(99), D(1)]), (30, [D(80), D(20)])])
def test_simultaneous_minimum_and_maximum_constraints_do_not_lose_or_invent_space(upper, expected):
    assert resolve_flexible_tracks([(D(80), None, D(1)), (D(0), D(upper), D(1))], D(100)) == expected


def test_bounded_track_random_feasible_vectors_respect_every_floor_cap_and_total():
    rng = Random(1295)
    for _ in range(1000):
        bases = []
        for _ in range(rng.randint(1, 10)):
            minimum = rng.randint(0, 100)
            bases.append((D(minimum), D(minimum + rng.randint(0, 200)), D(rng.randint(1, 8))))
        low = sum((base[0] for base in bases), D(0))
        high = sum((base[1] for base in bases), D(0))
        available = D(rng.randint(int(low), int(high)))
        result = resolve_flexible_tracks(bases, available)
        assert all(low <= size <= high for size, (low, high, _) in zip(result, bases))
        assert abs(sum(result, D(0)) - available) < D("1e-23")
