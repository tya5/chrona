"""Properties of the derived point over generated acyclic plans (#788 slice 1, design 5.1 and 11.3).

I1 twin substitution, I2 minimality, I3 monotonicity, I4 order independence, and a derived point is never rejected
as a fixed target. The repository has no `hypothesis` (see tests/unit/chrona/terse/test_properties.py), so the plans
come from a deterministic `random.Random(788)` walk. A counterexample is a design defect of the date rule, not a
test to loosen.
"""
from __future__ import annotations

import copy
import random
from datetime import date, timedelta

from chrona.scheduling.scheduler import schedule

CASES = 250
_ROOT = date(2027, 4, 26)


def _lag(rng: random.Random):
    text = f"{rng.randint(0, 9)}{rng.choice(['d', 'w', 'wd'])}"
    if text.endswith("wd") and rng.random() < 0.5:
        return {"value": text, "calendar": "six"}
    return text


def _plan(rng: random.Random) -> dict:
    """A root span and a sequence of derived points and scheduled spans, each fed only by earlier objects."""
    start = _ROOT + timedelta(days=rng.randint(0, 40))
    objects = {"root": {"type": "task", "schedule": {"mode": "fixed-span", "start": start.isoformat(),
                                                      "end": (start + timedelta(days=rng.randint(1, 20))).isoformat()}}}
    relations: list[dict] = []
    names, kinds = ["root"], {"root": "span"}
    for index in range(rng.randint(1, 6)):
        name = f"n{index}"
        kind = rng.choice(["point", "point", "span"])
        if kind == "point":
            point = {"mode": "scheduled-point"}
            if rng.random() < 0.5:
                point["constraints"] = {"at": {"min": (_ROOT + timedelta(days=rng.randint(0, 120))).isoformat()}}
            objects[name] = {"type": "gate", "schedule": point}
        else:
            objects[name] = {"type": "task", "schedule": {"mode": "scheduled", "amount": f"{rng.randint(1, 8)}{rng.choice(['d', 'wd'])}"}}
        kinds[name] = kind
        for source in rng.sample(names, rng.randint(1, min(3, len(names)))):
            relations.append({"id": f"{source}-{name}", "type": "dependency",
                              "from": {"object": source, "endpoint": "at" if kinds[source] == "point" else "end"},
                              "to": {"object": name, "endpoint": "at" if kind == "point" else "start"}, "lag": _lag(rng)})
        names.append(name)
    return {
        "version": "timeline/v0.7", "project": {"id": "p", "calendar": "std"},
        "calendars": {"std": {"working_days": ["mon", "tue", "wed", "thu", "fri"],
                              "exceptions": [{"date": "2027-05-03", "working": False}]},
                      "six": {"working_days": ["mon", "tue", "wed", "thu", "fri", "sat"]}},
        "objects": objects, "relations": relations,
    }


def _plans():
    rng = random.Random(788)
    return [(_plan(rng), random.Random(index)) for index in range(CASES)]


def _points(project):
    return [name for name, item in project["objects"].items() if item["schedule"]["mode"] == "scheduled-point"]


def _twin(project, result, only=None):
    out = copy.deepcopy(project)
    for name in _points(project):
        if only is None or name in only:
            out["objects"][name]["schedule"] = {"mode": "fixed-point", "at": result.placements[name]["at"].isoformat()}
    return out


def test_the_generator_reaches_derived_points_floors_and_calendar_lags():
    plans = [plan for plan, _ in _plans()]
    assert sum(bool(_points(plan)) for plan in plans) > CASES * 0.8
    assert any("constraints" in item["schedule"] for plan in plans for item in plan["objects"].values())
    assert any(isinstance(relation["lag"], dict) for plan in plans for relation in plan["relations"])


def test_the_properties_run_on_the_real_analysis_pass():
    """No stub: every generated plan is analysed by the scheduler's own backward pass (#810)."""
    for project, _ in _plans():
        result = schedule(project)
        assert result.ok and result.analysis is not None, project
        assert all(value.value >= 0 for value in result.analysis.total_float.values()), project


def test_i1_a_derived_plan_is_accepted_and_its_fixed_twin_places_identically():
    for project, _ in _plans():
        result = schedule(project)
        assert result.ok, (project, result.diagnostics)
        twinned = schedule(_twin(project, result))
        assert twinned.ok and twinned.placements == result.placements, project


def test_i2_one_day_earlier_is_rejected_and_the_reported_earliest_is_the_derived_date():
    checked = 0
    for project, rng in _plans():
        unfloored = [name for name in _points(project) if "constraints" not in project["objects"][name]["schedule"]]
        if not unfloored:
            continue
        name = rng.choice(unfloored)
        result = schedule(project)
        derived = result.placements[name]["at"]
        probe = _twin(project, result, only={name})
        probe["objects"][name]["schedule"]["at"] = (derived - timedelta(days=1)).isoformat()
        violations = [item for item in schedule(probe).diagnostics
                      if item.id == "E_FIXED_TARGET_VIOLATION" and item.details["object"] == name]
        assert violations and all(item.details["earliest"] == derived.isoformat() for item in violations), project
        checked += 1
    assert checked > CASES // 3


def test_i3_a_later_predecessor_never_makes_a_derived_point_earlier():
    for project, rng in _plans():
        before = schedule(project).placements
        later = copy.deepcopy(project)
        root = later["objects"]["root"]["schedule"]
        days = rng.randint(1, 30)
        for key in ("start", "end"):
            root[key] = (date.fromisoformat(root[key]) + timedelta(days=days)).isoformat()
        after = schedule(later)
        assert after.ok
        for name in _points(project):
            assert after.placements[name]["at"] >= before[name]["at"], (project, days)


def test_i4_placements_do_not_depend_on_object_or_relation_order():
    for project, rng in _plans():
        expected = schedule(project).placements
        shuffled = copy.deepcopy(project)
        names = list(shuffled["objects"])
        rng.shuffle(names)
        shuffled["objects"] = {name: project["objects"][name] for name in names}
        rng.shuffle(shuffled["relations"])
        result = schedule(shuffled)
        assert result.ok and result.placements == expected, project


def test_a_derived_point_is_never_rejected_as_a_fixed_target():
    for project, _ in _plans():
        assert not [item for item in schedule(project).diagnostics if item.id == "E_FIXED_TARGET_VIOLATION"], project
