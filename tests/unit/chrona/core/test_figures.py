"""Derived figures are a closed set of derivations over declared facts (#586).

Synthetic Projects only: no committed example is read.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from chrona.core.figures import (
    AsOfFact, FigureSpec, GroupStartFact, ObjectFact, PeriodFact, calendar_days_until, resolve_figures, working_days_in,
    working_days_until)
from chrona.core.periods import ResolvedPeriod
from chrona.core.temporal import Calendar, advance

D = date.fromisoformat
WEEK = Calendar.from_mapping({"working_days": ["mon", "tue", "wed", "thu", "fri"]})
# 2027-01-01 is a Friday; 2027-01-04 a Monday.
HOLIDAY = Calendar.from_mapping({"working_days": ["mon", "tue", "wed", "thu", "fri"],
                                 "exceptions": [{"date": "2027-01-05", "working": False},
                                                {"date": "2027-01-09", "working": True}]})


@pytest.mark.parametrize(("origin", "target", "expected"), [
    ("2027-08-20", "2027-10-22", 63),
    ("2027-03-01", "2027-03-01", 0),
    ("2027-03-01", "2027-03-02", 1),
    ("2027-03-02", "2027-03-01", -1),
    ("2027-01-31", "2027-03-01", 29),
    ("2027-12-31", "2028-01-01", 1),
    ("2028-02-28", "2028-03-01", 2),
    ("2027-02-28", "2027-03-01", 1),
])
def test_calendar_days_until(origin, target, expected):
    assert calendar_days_until(D(origin), D(target)) == expected


@pytest.mark.parametrize(("origin", "target", "calendar", "expected"), [
    ("2027-01-04", "2027-01-04", WEEK, 0),            # same day
    ("2027-01-04", "2027-01-05", WEEK, 1),            # Monday -> Tuesday
    ("2027-01-01", "2027-01-04", WEEK, 1),            # Friday -> Monday skips the weekend
    ("2027-01-04", "2027-01-11", WEEK, 5),            # a full week
    ("2027-01-04", "2027-01-09", WEEK, 4),            # target on a Saturday: the last working day counts
    ("2027-01-02", "2027-01-04", WEEK, 1),            # origin on a Saturday
    ("2027-01-02", "2027-01-03", WEEK, 0),            # a weekend alone
    ("2027-01-11", "2027-01-04", WEEK, -5),           # a past target is negative
    ("2027-01-04", "2027-01-01", WEEK, -1),
    ("2027-01-04", "2027-01-08", HOLIDAY, 3),         # Tuesday 5th is a declared holiday
    ("2027-01-04", "2027-01-11", HOLIDAY, 5),         # holiday (-1) and working Saturday 9th (+1) cancel
    ("2027-01-08", "2027-01-09", HOLIDAY, 1),         # a declared working Saturday counts
])
def test_working_days_until(origin, target, calendar, expected):
    assert working_days_until(D(origin), D(target), calendar) == expected


@pytest.mark.parametrize("calendar", [WEEK, HOLIDAY])
def test_working_days_until_inverts_advance(calendar):
    """The figure and the scheduler agree on what a working day is: advance by k, count k."""
    for offset in range(0, 21):
        origin = D("2027-01-01") + timedelta(days=offset)
        for count in range(0, 16):
            assert working_days_until(origin, advance(origin, f"{count}wd", calendar), calendar) == count


def test_working_days_until_is_antisymmetric():
    for offset in range(0, 15):
        origin = D("2027-01-01") + timedelta(days=offset)
        target = origin + timedelta(days=9)
        assert working_days_until(target, origin, HOLIDAY) == -working_days_until(origin, target, HOLIDAY)


@pytest.mark.parametrize(("start", "end", "calendar", "expected"), [
    ("2027-01-04", "2027-01-05", WEEK, 1),            # a one-day period counts its start day
    ("2027-01-04", "2027-01-11", WEEK, 5),
    ("2027-01-02", "2027-01-04", WEEK, 0),            # a weekend: no working day, a value not an error
    ("2027-01-04", "2027-01-09", WEEK, 5),            # the exclusive end is not counted
    ("2027-01-04", "2027-01-10", WEEK, 5),
    ("2027-01-04", "2027-01-10", HOLIDAY, 5),         # holiday Tue 5th out, working Sat 9th in
])
def test_working_days_in(start, end, calendar, expected):
    assert working_days_in(D(start), D(end), calendar) == expected


# ---------------------------------------------------------------- resolution

PERIODS = (ResolvedPeriod("window", "Launch window", D("2027-10-22"), D("2027-11-06")),
           ResolvedPeriod("one-day", "One day", D("2027-10-22"), D("2027-10-23")))
PLACEMENTS = {
    "launch": {"at": D("2027-10-22")},
    "build": {"start": D("2027-01-05"), "end": D("2027-02-01")},
    "phase": {"start": D("2027-02-01"), "end": D("2027-02-08")},
}
CALENDARS = {"standard": WEEK, "holiday": HOLIDAY}


def _resolve(*specs, as_of=D("2027-08-20"), periods=PERIODS, placements=PLACEMENTS, calendars=CALENDARS,
             default="standard"):
    return resolve_figures(specs, as_of=as_of, placements=placements, periods=periods, calendars=calendars,
                           default_calendar=default)


def _codes(result):
    return [item.id for item in result.diagnostics]


def test_a_countdown_to_a_period_start_is_the_calendar_days_from_the_as_of():
    result = _resolve(FigureSpec("launch-countdown", "daysUntil", to=PeriodFact("window", "start")))
    assert dict(result.values) == {"launch-countdown": 63} and result.diagnostics == ()


@pytest.mark.parametrize(("start", "end", "as_of", "expected"), [
    ("2027-01-04", "2027-01-05", "2027-01-04", 0),
    ("2027-12-31", "2028-01-02", "2027-12-31", 1),
    ("2028-02-28", "2028-03-01", "2028-02-28", 1),
    ("2027-03-01", "2027-03-04", "2027-03-05", -2),
])
def test_period_last_is_the_final_covered_calendar_day(start, end, as_of, expected):
    periods = (ResolvedPeriod("p", "Period", D(start), D(end)),)
    result = _resolve(FigureSpec("last", "daysUntil", to=PeriodFact("p", "last")),
                      FigureSpec("end", "daysUntil", to=PeriodFact("p", "end")),
                      periods=periods, as_of=D(as_of))
    assert result.diagnostics == ()
    assert result.values == {"last": expected, "end": expected + 1}


def test_period_last_can_be_the_origin_and_never_moves_to_a_working_day():
    # Last is Sunday Jan 10; the holiday calendar makes Saturday Jan 9 a working day.
    periods = (ResolvedPeriod("p", "Period", D("2027-01-04"), D("2027-01-11")),)
    result = _resolve(
        FigureSpec("last-to-monday", "daysUntil", origin=PeriodFact("p", "last"),
                   to=AsOfFact(), days="working", calendar_id="holiday"),
        FigureSpec("to-last", "daysUntil", to=PeriodFact("p", "last")),
        as_of=D("2027-01-11"), periods=periods)
    assert result.diagnostics == ()
    assert result.values == {"last-to-monday": 1, "to-last": -1}


def test_period_last_reports_a_missing_period_at_the_declaration():
    result = _resolve(FigureSpec("last", "daysUntil", to=PeriodFact("absent", "last"),
                                 path="/body/figures/0"))
    assert result.values == {}
    assert _codes(result) == ["E_FIGURE_PERIOD_UNKNOWN"]
    assert result.diagnostics[0].path == "/body/figures/0/to/period"


def test_core_reads_only_the_injected_group_start_date():
    spec = FigureSpec("group", "daysUntil", to=GroupStartFact(), scope="group")
    result = resolve_figures((spec,), as_of=D("2028-02-28"), placements={}, periods=(),
                             calendars={}, default_calendar=None, group_first_start=D("2028-03-01"))
    assert result.values == {"group": 2}
    assert result.diagnostics == ()


def test_an_unavailable_group_start_is_not_zero():
    result = _resolve(FigureSpec("group", "daysUntil", to=GroupStartFact(),
                                 scope="group", path="/body/figures/0"))
    assert result.values == {}
    assert _codes(result) == ["E_FIGURE_GROUP_START_MISSING"]
    assert result.diagnostics[0].path == "/body/figures/0/to/group"


def test_each_fact_form_resolves():
    result = _resolve(
        FigureSpec("period-end", "daysUntil", to=PeriodFact("window", "end")),
        FigureSpec("point", "daysUntil", to=ObjectFact("launch", "at")),
        FigureSpec("span-start", "daysUntil", origin=ObjectFact("build", "start"), to=ObjectFact("build", "end")),
        FigureSpec("rollup-end", "daysUntil", origin=PeriodFact("window", "start"), to=ObjectFact("phase", "end")),
        FigureSpec("as-of", "daysUntil", origin=ObjectFact("launch", "at"), to=AsOfFact()))
    assert dict(result.values) == {"period-end": 78, "point": 63, "span-start": 27, "rollup-end": -256, "as-of": -63}
    assert result.diagnostics == ()


def test_a_past_target_is_negative_and_never_clamped():
    result = _resolve(FigureSpec("late", "daysUntil", to=ObjectFact("launch", "at")), as_of=D("2027-10-25"))
    assert result.values["late"] == -3


def test_working_days_use_the_declared_calendar_else_the_project_default():
    spec = dict(kind="daysUntil", to=ObjectFact("build", "end"), origin=ObjectFact("build", "start"), days="working")
    result = _resolve(FigureSpec("default", **spec), FigureSpec("holiday", calendar_id="holiday", **spec))
    # Jan 6..Feb 1: 19 weekdays; the holiday calendar adds the working Saturday of Jan 9.
    assert result.values["default"] == 19
    assert result.values["holiday"] == 20


def test_days_in_a_period_counts_the_days_it_covers():
    result = _resolve(
        FigureSpec("calendar", "daysIn", period_id="window"),
        FigureSpec("working", "daysIn", period_id="window", days="working"),
        FigureSpec("one", "daysIn", period_id="one-day"),
        FigureSpec("one-working", "daysIn", period_id="one-day", days="working"))
    assert dict(result.values) == {"calendar": 15, "working": 11, "one": 1, "one-working": 1}


def test_a_period_with_no_working_day_is_zero_not_an_error():
    weekend = (ResolvedPeriod("weekend", "Weekend", D("2027-01-02"), D("2027-01-04")),)
    result = _resolve(FigureSpec("w", "daysIn", period_id="weekend", days="working"), periods=weekend)
    assert dict(result.values) == {"w": 0} and result.diagnostics == ()


# ---------------------------------------------------------------- missing facts


def test_an_undeclared_period_is_a_diagnostic_listing_the_declared_ones():
    result = _resolve(FigureSpec("f", "daysUntil", to=PeriodFact("nowhere", "start"), path="/body/figures/0"))
    assert "f" not in result.values and _codes(result) == ["E_FIGURE_PERIOD_UNKNOWN"]
    item = result.diagnostics[0]
    assert "nowhere" in item.message and "window, one-day" in item.message and item.path == "/body/figures/0/to/period"


def test_days_in_an_undeclared_period_is_a_diagnostic():
    result = _resolve(FigureSpec("f", "daysIn", period_id="nowhere", path="/body/figures/1"))
    assert _codes(result) == ["E_FIGURE_PERIOD_UNKNOWN"] and result.diagnostics[0].path == "/body/figures/1/period"


def test_no_declared_periods_says_none():
    result = _resolve(FigureSpec("f", "daysUntil", to=PeriodFact("window", "start")), periods=())
    assert "declared: none" in result.diagnostics[0].message


def test_an_unknown_object_is_a_diagnostic():
    result = _resolve(FigureSpec("f", "daysUntil", to=ObjectFact("ghost", "at"), path="/body/figures/0"))
    assert _codes(result) == ["E_FIGURE_OBJECT_UNKNOWN"] and "ghost" in result.diagnostics[0].message
    assert result.diagnostics[0].path == "/body/figures/0/to/object"


def test_an_endpoint_the_schedule_does_not_offer_lists_the_offered_ones():
    result = _resolve(FigureSpec("f", "daysUntil", to=ObjectFact("launch", "start")),
                      FigureSpec("g", "daysUntil", to=ObjectFact("build", "at")))
    assert _codes(result) == ["E_FIGURE_ENDPOINT_UNAVAILABLE"] * 2
    assert "offers at" in result.diagnostics[0].message and "offers start, end" in result.diagnostics[1].message


def test_a_missing_as_of_is_a_diagnostic_not_a_blank():
    result = _resolve(FigureSpec("f", "daysUntil", to=PeriodFact("window", "start")), as_of=None)
    assert "f" not in result.values and _codes(result) == ["E_FIGURE_ASOF_MISSING"]


def test_an_explicit_origin_needs_no_as_of():
    result = _resolve(FigureSpec("f", "daysUntil", origin=ObjectFact("build", "start"), to=ObjectFact("build", "end")),
                      as_of=None)
    assert dict(result.values) == {"f": 27}


def test_working_days_without_a_calendar_is_a_diagnostic():
    spec = FigureSpec("f", "daysIn", period_id="window", days="working")
    assert _codes(_resolve(spec, default=None)) == ["E_FIGURE_CALENDAR_UNAVAILABLE"]
    named = FigureSpec("f", "daysIn", period_id="window", days="working", calendar_id="ghost")
    result = _resolve(named)
    assert _codes(result) == ["E_FIGURE_CALENDAR_UNAVAILABLE"] and "ghost" in result.diagnostics[0].message
    assert "standard, holiday" in result.diagnostics[0].message


def test_a_working_figure_with_no_calendar_never_falls_back_to_calendar_days():
    until = FigureSpec("u", "daysUntil", to=PeriodFact("window", "start"), days="working")
    inside = FigureSpec("i", "daysIn", period_id="window", days="working")
    result = _resolve(until, inside, default=None)
    assert dict(result.values) == {} and _codes(result) == ["E_FIGURE_CALENDAR_UNAVAILABLE"] * 2


def test_a_calendar_figure_never_reads_a_calendar():
    result = _resolve(FigureSpec("f", "daysIn", period_id="window"), calendars={}, default=None)
    assert dict(result.values) == {"f": 15}


def test_every_finding_is_reported_and_only_the_failed_figures_lose_their_value():
    result = _resolve(FigureSpec("ok", "daysUntil", to=PeriodFact("window", "start")),
                      FigureSpec("bad-period", "daysUntil", to=PeriodFact("x", "start")),
                      FigureSpec("bad-object", "daysUntil", to=ObjectFact("y", "at")))
    assert dict(result.values) == {"ok": 63}
    assert _codes(result) == ["E_FIGURE_PERIOD_UNKNOWN", "E_FIGURE_OBJECT_UNKNOWN"]


def test_both_facts_of_one_figure_are_reported():
    result = _resolve(FigureSpec("f", "daysUntil", origin=ObjectFact("y", "at"), to=PeriodFact("x", "start")))
    assert _codes(result) == ["E_FIGURE_OBJECT_UNKNOWN", "E_FIGURE_PERIOD_UNKNOWN"]
