from datetime import date

import pytest

from chrona.presentation.presentation_axis import axis_intervals, format_axis_label


def interval_values(intervals):
    return [(item.start, item.end, item.label, item.index) for item in intervals]


def test_month_and_quarter_intervals_clip_but_keep_natural_labels():
    assert interval_values(axis_intervals(date(2027, 1, 15), date(2027, 3, 15), "month")) == [
        (date(2027, 1, 15), date(2027, 2, 1), "2027-01", 0),
        (date(2027, 2, 1), date(2027, 3, 1), "2027-02", 1),
        (date(2027, 3, 1), date(2027, 3, 15), "2027-03", 2),
    ]


def test_year_intervals_keep_the_natural_bucket_at_clipped_edges():
    assert interval_values(axis_intervals(date(2026, 9, 1), date(2028, 2, 1), "year")) == [
        (date(2026, 9, 1), date(2027, 1, 1), "2026", 0),
        (date(2027, 1, 1), date(2028, 1, 1), "2027", 1),
        (date(2028, 1, 1), date(2028, 2, 1), "2028", 2),
    ]


@pytest.mark.parametrize("style,expected", [
    ("short-month-year", "Jan 2027"),
    ("long-month-year", "January 2027"),
    ("numeric-year-month", "2027-01"),
    ("short-month", "Jan"),
    ("long-month", "January"),
    ("numeric-month", "01"),
])
def test_month_format_catalog_is_closed_and_process_locale_independent(style, expected):
    interval = axis_intervals(date(2027, 1, 15), date(2027, 2, 1), "month")[0]
    assert format_axis_label(interval, {"month": style, "quarter": "quarter-year", "date": "iso-date"}, "en-US") == expected


@pytest.mark.parametrize("style,expected", [
    ("quarter-year", "Q1 2027"),
    ("year-quarter", "2027 Q1"),
    ("quarter", "Q1"),
])
def test_quarter_format_catalog_is_closed(style, expected):
    interval = axis_intervals(date(2027, 1, 15), date(2027, 2, 1), "quarter")[0]
    assert format_axis_label(interval, {"month": "short-month-year", "quarter": style, "date": "iso-date"}, "en-US") == expected
    assert interval_values(axis_intervals(date(2027, 1, 15), date(2027, 4, 2), "quarter")) == [
        (date(2027, 1, 15), date(2027, 4, 1), "2027-Q1", 0),
        (date(2027, 4, 1), date(2027, 4, 2), "2027-Q2", 1),
    ]


def test_iso_weeks_start_on_monday_and_keep_week_year_at_window_edge():
    intervals = axis_intervals(date(2027, 1, 1), date(2027, 1, 12), "week")
    assert interval_values(intervals) == [
        (date(2027, 1, 1), date(2027, 1, 4), "2026-W53", 0),
        (date(2027, 1, 4), date(2027, 1, 11), "2027-W01", 1),
        (date(2027, 1, 11), date(2027, 1, 12), "2027-W02", 2),
    ]


def test_day_intervals_are_half_open_and_tick_step_only_filters_buckets():
    all_days = axis_intervals(date(2027, 2, 1), date(2027, 2, 6), "day")
    every_second = axis_intervals(date(2027, 2, 1), date(2027, 2, 6), "day", tick_step=2)
    assert [item.label for item in all_days] == ["2027-02-01", "2027-02-02", "2027-02-03", "2027-02-04", "2027-02-05"]
    assert interval_values(every_second) == [
        (date(2027, 2, 1), date(2027, 2, 2), "2027-02-01", 0),
        (date(2027, 2, 3), date(2027, 2, 4), "2027-02-03", 2),
        (date(2027, 2, 5), date(2027, 2, 6), "2027-02-05", 4),
    ]
    assert axis_intervals(date(2027, 2, 1), date(2027, 2, 6), "day") == all_days


@pytest.mark.parametrize("start,end,level,tick_step", [
    (date(2027, 2, 1), date(2027, 2, 1), "day", 1),
    (date(2027, 2, 2), date(2027, 2, 1), "day", 1),
    (date(2027, 2, 1), date(2027, 2, 2), "decade", 1),
    (date(2027, 2, 1), date(2027, 2, 2), "week", 0),
    (date(2027, 2, 1), date(2027, 2, 2), "week", True),
])
def test_invalid_axis_input_is_diagnosed(start, end, level, tick_step):
    with pytest.raises(ValueError, match="E_PRESENTATION_AXIS_INVALID"):
        axis_intervals(start, end, level, tick_step=tick_step)
