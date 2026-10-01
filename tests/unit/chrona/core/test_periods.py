"""A named period is a Project fact that validates statically and never schedules (#582).

Synthetic Projects only: no committed example is read.
"""
from __future__ import annotations

import copy
from typing import Any

import pytest

from chrona.core.periods import period_range_diagnostics, resolve_periods
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


# --- resolution against placements ------------------------------------------------------------------------


def _placements(project: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = schedule(project)
    assert result.ok, result.diagnostics
    return result.placements


def test_resolution_turns_literals_and_references_into_dates_in_project_order():
    periods = {
        "freeze": {"title": "Freeze", "start": {"object": "kickoff", "endpoint": "at"}, "end": "2027-03-01"},
        "build-window": {"start": {"object": "build", "endpoint": "start"}, "end": {"object": "build", "endpoint": "end"}},
        "rolled": {"start": {"object": "phase", "endpoint": "start"}, "end": {"object": "phase", "endpoint": "end"}},
        "derived-day": {"start": {"object": "derived", "endpoint": "at"}, "end": "2027-12-31"},
        "literal": {"start": "2027-10-22", "end": "2027-11-06"},
    }
    project = _project(periods)
    resolved = resolve_periods(project, _placements(project))
    assert [(item.period_id, item.title, item.start.isoformat(), item.end.isoformat()) for item in resolved] == [
        ("freeze", "Freeze", "2027-01-04", "2027-03-01"),
        ("build-window", "build-window", "2027-01-05", "2027-02-01"),
        ("rolled", "rolled", "2027-02-01", "2027-02-08"),
        ("derived-day", "derived-day", "2027-03-01", "2027-12-31"),
        ("literal", "literal", "2027-10-22", "2027-11-06"),
    ]


def test_a_reference_follows_the_plan_when_the_plan_moves():
    periods = {"window": {"start": {"object": "build", "endpoint": "end"}, "end": "2027-06-01"}}
    project = _project(periods)
    before = resolve_periods(project, _placements(project))[0]
    project["objects"]["build"]["schedule"]["end"] = "2027-02-15"
    after = resolve_periods(project, _placements(project))[0]
    assert (before.start.isoformat(), after.start.isoformat()) == ("2027-02-01", "2027-02-15")
    assert before.end == after.end


def test_resolution_of_a_project_without_periods_is_empty():
    project = _project()
    assert resolve_periods(project, _placements(project)) == ()
    assert period_range_diagnostics(project, _placements(project)) == ()


@pytest.mark.parametrize(("period", "resolved"), [
    ({"start": {"object": "build", "endpoint": "end"}, "end": "2027-02-01"}, ("2027-02-01", "2027-02-01")),
    ({"start": {"object": "build", "endpoint": "end"}, "end": "2027-01-10"}, ("2027-02-01", "2027-01-10")),
    ({"start": "2027-03-01", "end": {"object": "kickoff", "endpoint": "at"}}, ("2027-03-01", "2027-01-04")),
    ({"start": {"object": "build", "endpoint": "end"}, "end": {"object": "build", "endpoint": "start"}},
     ("2027-02-01", "2027-01-05")),
])
def test_a_reference_that_resolves_to_an_empty_or_inverted_range_is_rejected(period, resolved):
    project = _project({"p": period})
    assert validate_project(project) == []  # no dates are computed there
    (item,) = period_range_diagnostics(project, _placements(project))
    assert (item.id, item.path) == ("E_PROJECT_PERIOD_ORDER", "/periods/p")
    assert (item.details["start"], item.details["end"]) == resolved
    assert resolved[0] in item.message and resolved[1] in item.message


def test_a_reference_that_resolves_in_order_is_kept():
    project = _project({"p": {"start": {"object": "kickoff", "endpoint": "at"}, "end": {"object": "build", "endpoint": "end"}}})
    assert period_range_diagnostics(project, _placements(project)) == ()


def test_the_post_placement_check_leaves_literal_pairs_to_validation():
    # A literal pair that is out of order is reported once, by validate; the placement check adds nothing.
    project = _project({"p": {"start": "2027-11-06", "end": "2027-10-22"}})
    assert [item.id for item in validate_project(project)] == ["E_PROJECT_PERIOD_ORDER"]
    assert period_range_diagnostics(project, _placements(_project())) == ()
