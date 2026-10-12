"""The backward pass inverts a lag the way the forward pass applies it (#810, work record sections 1 and 4).

A working-day `advance` counts days strictly after its start, so `retreat` is not its inverse when the endpoint is not
a working day of the lag's calendar. These plans mix calendar-day spans, points and working-day lags.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

from chrona.core.temporal import Calendar, advance, latest_start_for
from chrona.scheduling.scheduler import schedule

_CALENDARS = {"std": {"working_days": ["mon", "tue", "wed", "thu", "fri"]},
              "six": {"working_days": ["mon", "tue", "wed", "thu", "fri", "sat"]}}
_STD = Calendar.from_mapping(_CALENDARS["std"])
_SIX = Calendar.from_mapping(_CALENDARS["six"])
_STD_HOLIDAYS = Calendar.from_mapping({**_CALENDARS["std"], "exceptions": [{"date": "2027-05-03", "working": False},
                                                                           {"date": "2027-05-04", "working": False}]})


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
    assert {key: value.value for key, value in analysis.total_float.items()} == {"root": 0, "s": 0, "a": 0}
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
    assert result.analysis.total_float["s"].value == 0
    assert result.analysis.latest_placements["s"]["start"] == date(2027, 5, 20)


def test_the_latest_start_of_a_working_day_span_is_a_working_date():
    """The gate is fixed on Monday: a Friday start still ends on it, a Sunday start is not a working date."""
    project = _plan(
        {"root": {"type": "task", "schedule": {"mode": "fixed-point", "at": "2027-05-20"}},
         "s": {"type": "task", "schedule": {"mode": "scheduled", "amount": "1wd"}},
         "g": {"type": "gate", "schedule": {"mode": "fixed-point", "at": "2027-05-24"}}},
        [_dep("r0", "root", "at", "s", "start"), _dep("r", "s", "end", "g", "at")])
    result = schedule(project)
    assert result.ok and result.placements["s"] == {"start": date(2027, 5, 20), "end": date(2027, 5, 21)}
    assert result.analysis.latest_placements["s"] == {"start": date(2027, 5, 21), "end": date(2027, 5, 24)}
    assert result.analysis.total_float["s"].value == 1


def _amounts(rng):
    count = rng.randint(-9, 9)
    return rng.choice([f"{count}wd", f"{count}d", f"{count}w", f"{abs(count) % 4}mo"])


def test_latest_start_for_is_the_greatest_preimage_of_advance():
    rng = random.Random(810)
    for _ in range(3000):
        calendar = rng.choice([_STD_HOLIDAYS, _SIX])
        amount = _amounts(rng)
        target = date(2027, 4, 20) + timedelta(days=rng.randint(0, 120))
        start = latest_start_for(target, amount, calendar)
        assert advance(start, amount, calendar) <= target, (amount, target, start)
        assert advance(start + timedelta(days=1), amount, calendar) > target, (amount, target, start)


def test_latest_start_for_inverts_a_forward_advance_from_any_date():
    rng = random.Random(8101)
    for _ in range(3000):
        calendar = rng.choice([_STD_HOLIDAYS, _SIX])
        amount = _amounts(rng)
        source = date(2027, 4, 20) + timedelta(days=rng.randint(0, 120))
        reached = advance(source, amount, calendar)
        latest = latest_start_for(reached, amount, calendar)
        assert latest >= source and advance(latest, amount, calendar) == reached, (amount, source)


def _random_plan(rng):
    """A fixed root, calendar-day and working-day spans, derived and fixed points, lags on either calendar."""
    objects = {"root": {"type": "task", "schedule": {"mode": "fixed-span", "start": "2027-05-17", "end": "2027-05-23"}}}
    relations, names, kinds = [], ["root"], {"root": "span"}
    for index in range(rng.randint(2, 7)):
        name, kind = f"n{index}", rng.choice(["span", "span", "point", "fixed"])
        if kind == "span":
            amount = f"{rng.randint(1, 9)}{rng.choice(['d', 'wd', 'w'])}"
            objects[name] = {"type": "task", "schedule": {"mode": "scheduled", "amount": amount}}
        elif kind == "point":
            objects[name] = {"type": "gate", "schedule": {"mode": "scheduled-point"}}
        else:
            fixed = date(2030, 1, 1) + timedelta(days=rng.randint(0, 40))  # far enough that no chain reaches it
            objects[name] = {"type": "gate", "schedule": {"mode": "fixed-point", "at": fixed.isoformat()}}
        kinds[name] = "span" if kind == "span" else "point"
        for source in rng.sample(names, rng.randint(1, min(2, len(names)))):  # a fixed gate is terminal
            amount = f"{rng.randint(0, 6)}{rng.choice(['d', 'wd', 'wd', 'w'])}"
            lag = amount
            if amount.endswith("wd") and rng.random() < 0.6:
                lag = {"value": amount, "calendar": rng.choice(["six", "std"])}
            relations.append(_dep(f"{source}-{name}", source, "at" if kinds[source] == "point" else "end", name,
                                  "at" if kinds[name] == "point" else "start", lag))
        if kind != "fixed":
            names.append(name)
    return _plan(objects, relations)


def test_the_real_analysis_pass_never_raises_and_every_latest_date_is_reachable_forward():
    rng = random.Random(8102)
    with_float = 0
    for _ in range(400):
        project = _random_plan(rng)
        result = schedule(project)
        assert result.ok, (project, result.diagnostics)
        analysis = result.analysis
        assert analysis is not None and all(value.value >= 0 for value in analysis.total_float.values()), project
        with_float += any(value.value for value in analysis.total_float.values())
        for relation in project["relations"]:
            source, target, lag = relation["from"], relation["to"], relation["lag"]
            amount = lag if isinstance(lag, str) else lag["value"]
            calendar_id = (lag.get("calendar") if isinstance(lag, dict) else None) or "std"
            calendar = {"std": _STD, "six": _SIX}[calendar_id] if amount.endswith("wd") else None
            latest_source = analysis.latest_placements[source["object"]][source["endpoint"]]
            latest_target = analysis.latest_placements[target["object"]][target["endpoint"]]
            assert advance(latest_source, amount, calendar) <= latest_target, (project, relation)
    assert with_float > 100
