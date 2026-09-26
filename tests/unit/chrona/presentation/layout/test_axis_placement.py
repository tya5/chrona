from datetime import date
import ast
import inspect

import pytest

from chrona.presentation.layout.axis import axis_intervals, axis_label_fits, format_axis_tier_label, thinning_schedule
from chrona.presentation.layout.surface_composer import compose_surface_layout
from chrona.presentation.model.axis_names import axis_name_table


class _Font:
    def width(self, content, size):
        return len(content) * size


def test_axis_label_fit_is_a_layout_decision():
    assert axis_label_fits(content="Jan", available_inline=30, font_size=10, font_metrics=_Font())


def test_axis_label_path_has_no_language_code_branch():
    for function in (format_axis_tier_label, compose_surface_layout):
        syntax = ast.parse(inspect.getsource(function))
        assert not any(isinstance(node, ast.Name) and node.id in {"locale", "language"}
                       for node in ast.walk(syntax))
        assert not any(isinstance(node, ast.Attribute) and node.attr == "locale"
                       for node in ast.walk(syntax))
        assert not any(isinstance(node, ast.Constant) and node.value in {"ja", "en", "ja-JP", "en-US"}
                       for node in ast.walk(syntax))


def test_half_year_and_fiscal_quarter_buckets_are_calendar_owned():
    fiscal_quarters = axis_intervals(date(2027, 1, 1), date(2027, 8, 1), "quarter", fiscal_start_month=4)
    assert [(item.natural_start, item.label) for item in fiscal_quarters] == [
        (date(2027, 1, 1), "2026-Q4"), (date(2027, 4, 1), "2027-Q1"), (date(2027, 7, 1), "2027-Q2"),
    ]
    halves = axis_intervals(date(2027, 1, 1), date(2028, 1, 1), "half", fiscal_start_month=4)
    assert [format_axis_tier_label(item, "half-year", axis_name_table("ja-JP")) for item in halves] == ["2026-H2", "2027-H1", "2027-H2"]


def test_every_n_retains_natural_interval_index_without_changing_the_window():
    intervals = axis_intervals(date(2026, 1, 1), date(2026, 7, 1), "month", tick_step=2)
    assert [(item.index, item.start, item.end) for item in intervals] == [
        (0, date(2026, 1, 1), date(2026, 2, 1)), (2, date(2026, 3, 1), date(2026, 4, 1)), (4, date(2026, 5, 1), date(2026, 6, 1)),
    ]


def test_thinning_schedule_retains_every_fitting_candidate_and_thins_the_rest():
    schedule = thinning_schedule((False, True, False, True))
    assert schedule.retained_positions == (1, 3)
    assert schedule.thinned_positions == (0, 2)


def test_thinning_schedule_keeps_every_fitting_label_for_one_colliding_edge_label():
    # One colliding candidate at the window edge must not force any other
    # fitting candidate to be dropped, however many candidates there are.
    fits = (False,) + (True,) * 8
    schedule = thinning_schedule(fits)
    assert schedule.retained_positions == (1, 2, 3, 4, 5, 6, 7, 8)
    assert schedule.thinned_positions == (0,)


def test_thinning_schedule_raises_when_nothing_fits():
    with pytest.raises(ValueError):
        thinning_schedule((False, False, False))
