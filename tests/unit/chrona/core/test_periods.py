"""A named period is a Project fact that validates statically and never schedules (#582).

Synthetic Projects only: no committed example is read.
"""
from __future__ import annotations

import copy
from typing import Any

import pytest

from chrona.core.validation import validate_project
from chrona.scheduling.scheduler import schedule


def _project(periods: dict[str, Any] | None = None) -> dict[str, Any]:
    project: dict[str, Any] = {
        "version": "timeline/v0.7",
        "project": {"id": "synthetic", "calendar": "standard"},
        "calendars": {"standard": {"working_days": ["mon", "tue", "wed", "thu", "fri"]}},
        "objects": {
            "kickoff": {"type": "gate", "schedule": {"mode": "fixed-point", "at": "2027-01-04"}},
            "build": {"type": "task", "schedule": {"mode": "fixed-span", "start": "2027-01-05", "end": "2027-02-01"}},
            "phase": {"type": "group", "schedule": {"mode": "rollup"}},
            "phase-step": {"type": "task", "parent": "phase",
                           "schedule": {"mode": "fixed-span", "start": "2027-02-01", "end": "2027-02-08"}},
            "derived": {"type": "gate", "schedule": {"mode": "scheduled-point", "constraints": {"at": {"min": "2027-03-01"}}}},
        },
    }
    if periods is not None:
        project["periods"] = periods
    return project


def _codes(project: dict[str, Any]) -> list[tuple[str, str | None]]:
    return [(item.id, item.path) for item in validate_project(project)]


def test_a_literal_and_a_referenced_period_validate():
    periods = {
        "window": {"title": "Launch window", "start": "2027-10-22", "end": "2027-11-06"},
        "freeze": {"start": {"object": "kickoff", "endpoint": "at"}, "end": "2027-03-01"},
        "span-edges": {"start": {"object": "build", "endpoint": "start"}, "end": {"object": "build", "endpoint": "end"}},
        "rolled": {"start": {"object": "phase", "endpoint": "start"}, "end": {"object": "phase", "endpoint": "end"}},
        "derived-day": {"start": {"object": "derived", "endpoint": "at"}, "end": "2027-12-31"},
    }
    assert _codes(_project(periods)) == []


def test_a_project_without_periods_validates_as_before():
    assert "periods" not in _project()
    assert _codes(_project()) == []
    assert _codes(_project({})) == []


@pytest.mark.parametrize(("period", "expected"), [
    ({"start": "2027-11-06", "end": "2027-10-22"}, [("E_PROJECT_PERIOD_ORDER", "/periods/p")]),
    ({"start": "2027-10-22", "end": "2027-10-22"}, [("E_PROJECT_PERIOD_ORDER", "/periods/p")]),
    ({"start": {"object": "nowhere", "endpoint": "at"}, "end": "2027-10-22"},
     [("E_PROJECT_PERIOD_OBJECT_UNKNOWN", "/periods/p/start/object")]),
    ({"start": "2027-10-22", "end": {"object": "nowhere", "endpoint": "end"}},
     [("E_PROJECT_PERIOD_OBJECT_UNKNOWN", "/periods/p/end/object")]),
    ({"start": {"object": "build", "endpoint": "at"}, "end": "2027-10-22"},
     [("E_PROJECT_PERIOD_ENDPOINT_UNAVAILABLE", "/periods/p/start/endpoint")]),
    ({"start": "2027-01-01", "end": {"object": "kickoff", "endpoint": "end"}},
     [("E_PROJECT_PERIOD_ENDPOINT_UNAVAILABLE", "/periods/p/end/endpoint")]),
    ({"start": "2027-02-30", "end": "2027-03-01"}, [("E_SCHEMA", "/periods/p/start")]),
    ({"start": "2027-03-01", "end": "2027-13-01"}, [("E_SCHEMA", "/periods/p/end")]),
])
def test_each_static_defect_has_its_own_code_and_pointer(period, expected):
    assert _codes(_project({"p": period})) == expected


def test_a_reference_on_either_side_defers_ordering_to_the_placements():
    # kickoff is on 2027-01-04; the literal end is earlier. Without placements the order is unknown, so
    # validation reports nothing; the post-placement check owns it.
    period = {"start": {"object": "kickoff", "endpoint": "at"}, "end": "2026-01-01"}
    assert _codes(_project({"p": period})) == []


def test_the_order_message_names_both_dates_and_the_exclusive_end():
    (item,) = validate_project(_project({"p": {"start": "2027-11-06", "end": "2027-10-22"}}))
    assert item.id == "E_PROJECT_PERIOD_ORDER"
    assert "2027-11-06" in item.message and "2027-10-22" in item.message and "exclusive" in item.message
    assert dict(item.details or {}) == {"period": "p", "start": "2027-11-06", "end": "2027-10-22"}


def test_the_endpoint_message_names_what_the_schedule_offers():
    (point,) = validate_project(_project({"p": {"start": {"object": "build", "endpoint": "at"}, "end": "2027-10-22"}}))
    assert point.message.endswith("its schedule offers start, end")
    (span,) = validate_project(_project({"p": {"start": {"object": "kickoff", "endpoint": "start"}, "end": "2027-10-22"}}))
    assert span.message.endswith("its schedule offers at")


@pytest.mark.parametrize("period", [
    {"start": "2027-10-22"},
    {"end": "2027-10-22"},
    {"start": "2027-10-22", "end": "2027-11-06", "color": "red"},
    {"title": "", "start": "2027-10-22", "end": "2027-11-06"},
    {"start": {"object": "build"}, "end": "2027-11-06"},
    {"start": {"object": "build", "endpoint": "middle"}, "end": "2027-11-06"},
])
def test_the_period_object_is_closed_and_complete(period):
    (item,) = validate_project(_project({"p": period}))
    assert item.id == "E_SCHEMA" and (item.path or "").startswith("/periods/p")


def test_a_period_never_changes_a_placement():
    periods = {"window": {"start": {"object": "kickoff", "endpoint": "at"}, "end": "2027-03-01"}}
    with_periods, without = _project(periods), _project()
    assert schedule(with_periods).ok and schedule(without).ok
    assert schedule(with_periods).placements == schedule(without).placements
    assert schedule(with_periods).analysis == schedule(without).analysis


def test_each_period_is_checked_independently_in_project_order():
    periods = {
        "b": {"start": "2027-05-01", "end": "2027-04-01"},
        "ok": {"start": "2027-01-01", "end": "2027-02-01"},
        "a": {"start": {"object": "gone", "endpoint": "at"}, "end": "2027-02-01"},
    }
    assert _codes(_project(periods)) == [("E_PROJECT_PERIOD_ORDER", "/periods/b"),
                                         ("E_PROJECT_PERIOD_OBJECT_UNKNOWN", "/periods/a/start/object")]


def test_validation_does_not_mutate_the_project():
    periods = {"window": {"start": {"object": "kickoff", "endpoint": "at"}, "end": "2027-03-01"}}
    project = _project(periods)
    before = copy.deepcopy(project)
    validate_project(project)
    assert project == before
