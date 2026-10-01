"""The backward pass inverts a lag the way the forward pass applies it (#810, work record sections 1 and 4).

A working-day `advance` counts days strictly after its start, so `retreat` is not its inverse when the endpoint is not
a working day of the lag's calendar. These plans mix calendar-day spans, points and working-day lags.
"""
from __future__ import annotations

from datetime import date

from chrona.scheduling.scheduler import schedule

_CALENDARS = {"std": {"working_days": ["mon", "tue", "wed", "thu", "fri"]},
              "six": {"working_days": ["mon", "tue", "wed", "thu", "fri", "sat"]}}


def _plan(objects, relations):
    return {"version": "timeline/v0.7", "project": {"id": "p", "calendar": "std"}, "calendars": _CALENDARS,
            "objects": objects, "relations": relations}


def _dep(name, source, endpoint, target, target_endpoint, lag=None):
    item = {"id": name, "type": "dependency", "from": {"object": source, "endpoint": endpoint},
            "to": {"object": target, "endpoint": target_endpoint}}
    if lag is not None:
        item["lag"] = lag
    return item


def test_a_lag_read_from_a_non_working_source_end_does_not_raise():
    """The issue's shape: a calendar-day span ends on a Sunday, a `1wd` lag on a six-day calendar follows it."""
    project = _plan(
        {"root": {"type": "task", "schedule": {"mode": "fixed-point", "at": "2027-05-21"}},
         "s": {"type": "task", "schedule": {"mode": "scheduled", "amount": "2d"}},
         "a": {"type": "task", "schedule": {"mode": "scheduled", "amount": "5d"}}},
        [_dep("r0", "root", "at", "s", "start"),
         _dep("r", "s", "end", "a", "start", {"value": "1wd", "calendar": "six"})])
    result = schedule(project)
    assert result.ok
    assert result.placements["s"] == {"start": date(2027, 5, 21), "end": date(2027, 5, 23)}
    assert result.placements["a"] == {"start": date(2027, 5, 24), "end": date(2027, 5, 29)}
    analysis = result.analysis
    assert analysis is not None
    assert analysis.total_float == {"root": 0, "s": 0, "a": 0}
    assert analysis.latest_placements["s"] == result.placements["s"]


def test_a_working_day_span_before_a_non_working_target_has_no_phantom_float():
    """`s` (1wd) ends Friday, the gate is fixed on Sunday: the latest start is Thursday, since a Friday start ends Monday."""
    project = _plan(
        {"root": {"type": "task", "schedule": {"mode": "fixed-point", "at": "2027-05-20"}},
         "s": {"type": "task", "schedule": {"mode": "scheduled", "amount": "1wd"}},
         "g": {"type": "gate", "schedule": {"mode": "fixed-point", "at": "2027-05-23"}}},
        [_dep("r0", "root", "at", "s", "start"), _dep("r", "s", "end", "g", "at")])
    result = schedule(project)
    assert result.ok
    assert result.placements["s"] == {"start": date(2027, 5, 20), "end": date(2027, 5, 21)}
    assert result.analysis.total_float["s"] == 0
    assert result.analysis.latest_placements["s"]["start"] == date(2027, 5, 20)
