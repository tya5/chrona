"""Display-only inclusive endpoints for View dateRange cells (#1293)."""
from datetime import date

import pytest

from chrona.presentation.contracts.resources import _view_input, freeze
from chrona.presentation.model.projection import ReviewItem, ReviewProjection
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

    table = normalize_v05_table_content(projection, {}, view)

    assert [(cell.column_id, cell.content) for cell in table.cells] == [
        ("Plan", "04 Jan"),
        ("Actual", "04 Jan – 14 Jan"),
    ]
