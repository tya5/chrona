from datetime import date

import pytest

from chrona.presentation.model.date_basis import (
    DisplayDateRange,
    ItemDateBasis,
    date_range_display,
    endpoint_distance,
    inclusive_end,
)


def _project(amount="5wd", *, project_calendar="office", item_calendar=None):
    item = {"schedule": {"amount": amount}}
    if item_calendar is not None:
        item["calendar"] = item_calendar
    return {
        "project": {"calendar": project_calendar} if project_calendar is not None else {},
        "calendars": {
            "office": {"working_days": ["mon", "tue", "wed", "thu", "fri"]},
            "four-day": {
                "working_days": ["tue", "wed", "thu", "fri", "sat"],
                "exceptions": [{"date": "2027-06-10", "working": False}],
            },
        },
        "objects": {"item": item},
    }


def test_work_period_monday_five_closes_on_friday_before_exclusive_monday():
    basis = ItemDateBasis.from_project(_project("5wd"), "item")

    assert inclusive_end(date(2027, 6, 14), basis) == date(2027, 6, 11)


def test_work_period_closes_before_nonworking_days_immediately_before_exclusive_end():
    project = _project("4wd")
    # Friday is a declared holiday, and Saturday is outside the ordinary work week.
    project["calendars"]["office"]["exceptions"] = [{"date": "2027-06-11", "working": False}]
    basis = ItemDateBasis.from_project(project, "item")

    assert inclusive_end(date(2027, 6, 12), basis) == date(2027, 6, 10)


@pytest.mark.parametrize("amount", ["5d", "1w", "2w"])
def test_fixed_day_and_week_spans_keep_civil_inclusive_end_even_with_a_calendar(amount):
    basis = ItemDateBasis.from_project(_project(amount), "item")

    assert not basis.work_period
    assert inclusive_end(date(2027, 6, 14), basis) == date(2027, 6, 13)


def test_object_calendar_takes_precedence_over_project_calendar():
    basis = ItemDateBasis.from_project(_project("5wd", item_calendar="four-day"), "item")

    assert basis.calendar is not None
    assert basis.calendar.working_days == frozenset({"tue", "wed", "thu", "fri", "sat"})
    # Saturday is used by the object's calendar, while the Project calendar ends on Friday.
    assert inclusive_end(date(2027, 6, 14), basis) == date(2027, 6, 12)


def test_missing_calendar_falls_back_to_all_days_without_diagnostics():
    basis = ItemDateBasis.from_project(_project("5wd", project_calendar=None), "item")

    assert basis.calendar is None
    assert endpoint_distance(date(2027, 6, 5), date(2027, 6, 8), basis, "working-days") == 3


def test_weekend_to_monday_has_zero_working_day_endpoint_distance_in_both_directions():
    basis = ItemDateBasis.from_project(_project("5wd"), "item")

    assert endpoint_distance(date(2027, 6, 5), date(2027, 6, 7), basis, "working-days") == 0
    assert endpoint_distance(date(2027, 6, 7), date(2027, 6, 5), basis, "working-days") == 0


def test_working_day_endpoint_distance_is_signed_for_later_and_earlier_workdays():
    basis = ItemDateBasis.from_project(_project("5wd"), "item")
    friday, tuesday = date(2027, 6, 11), date(2027, 6, 15)

    assert endpoint_distance(friday, tuesday, basis, "working-days") == 2
    assert endpoint_distance(tuesday, friday, basis, "working-days") == -2


def test_calendar_day_delta_preserves_legacy_civil_distance_with_working_calendar():
    basis = ItemDateBasis.from_project(_project("5wd"), "item")

    assert endpoint_distance(date(2027, 6, 11), date(2027, 6, 15), basis, "calendar-days") == 4


def test_date_range_conversion_does_not_mutate_the_input_mapping():
    basis = ItemDateBasis.from_project(_project("5wd"), "item")
    value = {"start": date(2027, 6, 7), "finish": date(2027, 6, 14), "metadata": "kept"}
    original = value.copy()

    displayed = date_range_display(value, basis=basis, end_display="inclusive")

    assert displayed == DisplayDateRange(date(2027, 6, 7), date(2027, 6, 11))
    assert value == original


@pytest.mark.parametrize(
    "value",
    [
        {"at": date(2027, 6, 7)},
        {"start": date(2027, 6, 7)},
        {"finish": date(2027, 6, 14)},
    ],
)
def test_point_and_open_ranges_are_returned_unchanged(value):
    assert date_range_display(value, basis=ItemDateBasis(work_period=True), end_display="inclusive") is value
