"""Display-only inclusive endpoints for View dateRange cells (#1293)."""
from datetime import date
from dataclasses import replace

import pytest

from chrona.presentation.contracts.resources import _view_input, freeze
from chrona.core.temporal import Calendar
from chrona.presentation.model.date_basis import ItemDateBasis
from chrona.presentation.model.projection import (
    FoldedPointProjection, ReviewItem, ReviewProjection, ReviewRowProjection,
)
from chrona.presentation.model.surface_content import display_value
from chrona.presentation.review.v05_content import normalize_v05_table_content


def test_date_range_end_display_formats_one_day_and_multiday_intervals():
    one_day = {"start": date(2027, 1, 4), "end": date(2027, 1, 5)}
    multi_day = {"start": date(2027, 1, 4), "end": date(2027, 1, 15)}

    assert display_value(one_day, "blank", "dateRange") == "04 Jan – 05 Jan"
    assert display_value(one_day, "blank", "dateRange", end_display="exclusive") == "04 Jan – 05 Jan"
    assert display_value(one_day, "blank", "dateRange", end_display="inclusive") == "04 Jan"
    assert display_value(multi_day, "blank", "dateRange", end_display="inclusive") == "04 Jan – 14 Jan"
    assert display_value(multi_day, "blank", "dateRange", end_display="exclusive") == "04 Jan – 15 Jan"


def test_inclusive_range_uses_the_displayed_endpoint_for_year_and_locale_formatting():
    crossing_year = {"start": date(2026, 12, 31), "end": date(2027, 1, 2)}
    one_day_across_year = {"start": date(2026, 12, 31), "end": date(2027, 1, 1)}

    assert display_value(crossing_year, "blank", "dateRange", end_display="inclusive") == \
        "31 Dec 2026 – 01 Jan 2027"
    assert display_value(one_day_across_year, "blank", "dateRange", end_display="inclusive") == "31 Dec"
    assert display_value({"start": date(2027, 1, 4), "end": date(2027, 1, 5)}, "blank", "dateRange",
                         locale="ja-JP", end_display="inclusive") == "1月4日"


@pytest.mark.parametrize("value,expected", [
    ({"start": date(2027, 1, 4), "end": date(2027, 1, 4)}, "04 Jan 2027"),
    ({"start": date(2027, 1, 5), "end": date(2027, 1, 4)}, "05 Jan – 04 Jan"),
    ({"start": date(2027, 1, 4), "end": None}, "04 Jan 2027 –"),
    ({"at": date(2027, 1, 4)}, "04 Jan 2027"),
])
def test_nonpositive_open_and_point_values_keep_legacy_date_range_formatting(value, expected):
    assert display_value(value, "blank", "dateRange", end_display="inclusive") == expected


def _typed_view(columns):
    columns = [{"align": "start", "width": "content", "headerOrientation": "horizontal", **column}
               for column in columns]
    body = freeze({
        "surface": "table-timeline",
        "rows": {"mode": "automatic"},
        "window": {"mode": "selected-planned"},
        "comparison": {"actual": "optional"},
        "visibility": {"labels": False, "relations": "none", "annotations": "none"},
        "tableColumns": columns,
    })
    return _view_input(body, "chrona/view/v0.28")


def test_view_column_parser_defaults_to_exclusive_and_retains_explicit_mode():
    columns = [
        {"id": "Plan", "source": {"facet": "planned"}, "format": "dateRange", "missing": "blank"},
        {"id": "Actual", "source": {"facet": "actual"}, "format": "dateRange", "missing": "blank",
         "endDisplay": "inclusive"},
    ]

    view = _typed_view(columns)

    assert [column.end_display for column in view.table_columns] == ["exclusive", "inclusive"]
    assert "endDisplay" not in columns[0]


def test_table_normalization_applies_the_view_mode_to_planned_and_actual_once():
    item = ReviewItem(
        "task", "Task", "span",
        {"start": date(2027, 1, 4), "end": date(2027, 1, 5)},
        {"start": date(2027, 1, 4), "finish": date(2027, 1, 15)},
        None, (),
    )
    projection = ReviewProjection((item,), (date(2027, 1, 4), date(2027, 1, 15)), (), ())
    view = _typed_view([
        {"id": "Plan", "source": {"facet": "planned"}, "format": "dateRange", "missing": "em-dash",
         "endDisplay": "inclusive"},
        {"id": "Actual", "source": {"facet": "actual"}, "format": "dateRange", "missing": "em-dash",
         "endDisplay": "inclusive"},
    ])

    table = normalize_v05_table_content(projection, {}, view,
                                        actual_set={"body": {"asOf": "2027-01-15"}})

    assert [(cell.column_id, cell.content) for cell in table.cells] == [
        ("Plan", "04 Jan"),
        ("Actual", "04 Jan – 14 Jan"),
    ]


def _group_range_table(*, point_date=date(2027, 3, 6), span_end=date(2027, 3, 6),
                       start=date(2027, 3, 1), end_display="inclusive", basis=ItemDateBasis(), nested=False):
    task = ReviewItem("task", "Task", "span", {"start": start, "end": span_end}, None, None, (),
                      item_id="task", hierarchy_path=("phase", "task"), date_basis=basis)
    gate = ReviewItem("gate", "Gate", "point", {"at": point_date}, None, None, (),
                      item_id="gate", hierarchy_path=("phase", "gate"))
    group = ReviewItem("phase", "Phase", "span", {"start": start, "end": max(span_end, point_date)},
                       None, None, (), item_id="phase", hierarchy_path=("phase",), is_rollup=True)
    ordinary = (group, task)
    if nested:
        inner = replace(group, object_id="inner", item_id="inner", hierarchy_path=("phase", "inner"))
        task = replace(task, hierarchy_path=("phase", "inner", "task"))
        gate = replace(gate, hierarchy_path=("phase", "inner", "gate"))
        ordinary = (group, inner, task)
    # Neither an unlisted selected-source item nor a folded comparison ghost is
    # an eligible member of this resolved View's displayed group range.
    unlisted = replace(gate, object_id="unlisted", item_id="unlisted",
                       planned={"at": date(2027, 9, 1)}, hierarchy_path=("phase", "unlisted"))
    ghost = replace(gate, item_id="snapshot:gate", source_kind="snapshot",
                    planned={"at": date(2027, 10, 1)})
    rows = tuple(ReviewRowProjection(item.item_id, item.title, "phase", item.item_id, (item,))
                 for item in ordinary)
    projection = ReviewProjection((group, task, gate, unlisted), (start, date(2027, 11, 1)), (), (),
                                  rows=rows, rows_resolved=True,
                                  folded_points=(FoldedPointProjection(gate, "phase", members=(ghost,)),))
    view = _typed_view([{"id": "Plan", "source": {"facet": "planned"}, "format": "dateRange",
                         "missing": "blank", "endDisplay": end_display}])
    original = dict(group.planned)
    table = normalize_v05_table_content(projection, {}, view)
    assert group.planned == original
    return next(cell.content for cell in table.cells if cell.object_id == "phase")


@pytest.mark.parametrize("end_display", ["inclusive", "exclusive"])
def test_group_range_keeps_a_folded_point_tied_with_the_span_endpoint(end_display):
    assert _group_range_table(end_display=end_display) == "01 Mar – 06 Mar"


def test_group_range_keeps_a_folded_point_after_the_last_span():
    assert _group_range_table(point_date=date(2027, 3, 8)) == "01 Mar – 08 Mar"


@pytest.mark.parametrize("point_date,expected", [(date(2027, 6, 11), "07 Jun – 11 Jun"),
                                               (date(2027, 6, 12), "07 Jun – 12 Jun")])
def test_group_range_closes_each_work_span_before_comparing_point_dates(point_date, expected):
    basis = ItemDateBasis(True, Calendar.from_mapping({"working_days": ["mon", "tue", "wed", "thu", "fri"]}))
    assert _group_range_table(start=date(2027, 6, 7), span_end=date(2027, 6, 14),
                              point_date=point_date, basis=basis) == expected


def test_nested_group_display_endpoints_are_not_closed_twice():
    basis = ItemDateBasis(True, Calendar.from_mapping({"working_days": ["mon", "tue", "wed", "thu", "fri"]}))
    assert _group_range_table(start=date(2027, 6, 7), span_end=date(2027, 6, 14),
                              point_date=date(2027, 6, 12), basis=basis, nested=True) == "07 Jun – 12 Jun"


def test_comparison_rollup_table_subject_keeps_its_own_date_range():
    group = ReviewItem("phase", "Phase", "span", {"start": date(2027, 3, 1), "end": date(2027, 3, 6)},
                       None, None, (), item_id="phase", hierarchy_path=("phase",), is_rollup=True)
    gate = ReviewItem("gate", "Gate", "point", {"at": date(2027, 3, 6)}, None, None, (),
                      item_id="gate", hierarchy_path=("phase", "gate"))
    snapshot = replace(group, item_id="snapshot:phase", source_kind="snapshot",
                       planned={"start": date(2027, 3, 1), "end": date(2027, 3, 9)})
    rows = tuple(ReviewRowProjection(item.item_id, item.title, "phase", item.item_id, (item,))
                 for item in (group, gate, snapshot))
    projection = ReviewProjection((group, gate), (date(2027, 3, 1), date(2027, 3, 10)), (), (),
                                  rows=rows, rows_resolved=True)
    view = _typed_view([{"id": "Plan", "source": {"facet": "planned"}, "format": "dateRange",
                         "missing": "blank", "endDisplay": "inclusive"}])
    table = normalize_v05_table_content(projection, {}, view)
    assert next(cell.content for cell in table.cells if cell.object_id == snapshot.item_id) == "01 Mar – 08 Mar"


def test_years_visible_puts_the_year_on_every_date_range_date_and_locale_form():
    a = {"start": date(2027, 4, 27), "end": date(2027, 5, 3)}
    b = {"start": date(2028, 2, 22), "end": date(2028, 3, 1)}
    one_day = {"start": date(2028, 2, 22), "end": date(2028, 2, 23)}

    assert display_value(a, "blank", "dateRange") == "27 Apr – 03 May"  # default: unchanged (#1724)
    assert display_value(a, "blank", "dateRange", years_visible=True) == "27 Apr 2027 – 03 May 2027"
    assert display_value(b, "blank", "dateRange", years_visible=True) == "22 Feb 2028 – 01 Mar 2028"
    assert display_value(one_day, "blank", "dateRange", end_display="inclusive", years_visible=True) == "22 Feb 2028"
    assert display_value(a, "blank", "dateRange", locale="ja-JP", years_visible=True) == "2027年4月27日 – 2027年5月3日"
    assert display_value(a, "blank", "dateRange", locale="ja-JP") == "4月27日 – 5月3日"


def _window_table(window, planned):
    from tests.unit.chrona.presentation.review.test_v05_content import typed_view
    item = ReviewItem("t", "Task", "span", planned, None, None, (), item_id="t")
    projection = ReviewProjection((item,), window, (), (),
                                  rows=(ReviewRowProjection("row", "", "t", "t", (item,)),))
    view = typed_view({"body": {"tableColumns": [
        {"id": "Plan", "source": {"facet": "planned"}, "format": "dateRange", "missing": "em-dash"}]}})
    return normalize_v05_table_content(projection, {}, view).cells[0].content


def test_table_dates_carry_the_year_only_when_the_visible_window_spans_years():
    planned = {"start": date(2027, 4, 27), "end": date(2027, 5, 3)}
    assert _window_table((date(2027, 1, 1), date(2029, 6, 1)), planned) == "27 Apr 2027 – 03 May 2027"
    # the plan may span years, but a window that shows one year keeps the short form
    assert _window_table((date(2027, 1, 1), date(2028, 1, 1)), planned) == "27 Apr – 03 May"
    assert _window_table((date(2027, 3, 1), date(2027, 8, 1)), planned) == "27 Apr – 03 May"
