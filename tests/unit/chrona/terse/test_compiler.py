"""Mapping rules of Spec 65 section 4: each construct compiles to exactly one Project construct (#148)."""
from __future__ import annotations

import pytest

from chrona.core.validation import validate_project
from chrona.scheduling.scheduler import schedule
from chrona.terse import compile_terse, locate
from tests.support.terse_plans import compile_text

HEAD = "project p\n"


def project_of(text: str) -> dict:
    result = compile_text(text)
    assert result.ok, [item.as_dict() for item in result.diagnostics]
    return result.project


def test_lag_sign_is_preserved_and_changes_the_schedule():
    text = HEAD + "a task 5d from 2026-10-05\nb task 2d after a {lag}\n"
    lags = {}
    for written, emitted in (("+3d", "3d"), ("-2d", "-2d"), ("0d", "0d"), ("", "0d"), ("+0d", "0d")):
        project = project_of(text.format(lag=written))
        assert project["relations"][0]["lag"] == emitted
        lags[written] = schedule(project).placements["b"]["start"]
    # a ends 2026-10-10 (exclusive end); the lag moves b's start by exactly its signed value
    assert lags["-2d"] < lags[""] < lags["+3d"]
    assert (lags["+3d"] - lags[""]).days == 3 and (lags[""] - lags["-2d"]).days == 2


def test_fixed_span_end_is_the_written_exclusive_end():
    project = project_of(HEAD + "a task 2026-10-01..2026-10-31\n")
    assert project["objects"]["a"]["schedule"] == {"mode": "fixed-span", "start": "2026-10-01", "end": "2026-10-31"}
    placed = schedule(project).placements["a"]
    assert placed["start"].isoformat() == "2026-10-01" and placed["end"].isoformat() == "2026-10-31"


def test_relation_ids_are_from_to_and_collisions_get_a_numeric_suffix():
    text = HEAD + "a task 1d\nb-2 task 1d after a\nb task 1d after a, a\nc task 1d after b, b-2\n"
    ids = [relation["id"] for relation in project_of(text)["relations"]]
    # a->b-2 owns "a-b-2"; a->b is "a-b"; the second a->b would be "a-b-2" (taken), so it becomes "a-b-3"
    assert ids == ["a-b-2", "a-b", "a-b-3", "b-c", "b-2-c"]


def test_calendar_days_exceptions_and_work_dates_map_in_week_order():
    project = project_of(
        HEAD + "calendar c fri,mon-wed except 2026-12-25, 2026-12-28 work 2026-12-26\n"
        "calendar d sat,sun\nx task 2d\n")
    assert project["calendars"]["c"] == {
        "working_days": ["mon", "tue", "wed", "fri"],
        "exceptions": [{"date": "2026-12-25", "working": False}, {"date": "2026-12-28", "working": False},
                       {"date": "2026-12-26", "working": True}]}
    assert project["calendars"]["d"] == {"working_days": ["sat", "sun"]}
    reverse = project_of(HEAD + "calendar c mon-fri work 2026-12-26 except 2026-12-25\nx task 2d\n")
    assert reverse["calendars"]["c"]["exceptions"] == [{"date": "2026-12-26", "working": True}, {"date": "2026-12-25", "working": False}]


def test_a_single_declared_calendar_is_the_project_default_and_two_are_not():
    one = project_of(HEAD + "calendar c mon-fri\nx task 2wd\n")
    assert one["project"]["calendar"] == "c"
    two = compile_text(HEAD + "calendar c mon-fri\ncalendar d mon-sat\nx task 2wd\n")
    assert [item.id for item in two.diagnostics] == ["E_CALENDAR_REQUIRED"]
    explicit = project_of("project p calendar d\ncalendar c mon-fri\ncalendar d mon-sat\nx task 2wd\n")
    assert explicit["project"]["calendar"] == "d"


def test_default_endpoints_follow_the_predecessor_schedule_form():
    project = project_of(
        HEAD + "pt gate 2026-10-01\nsp task 3d after pt\ng group\n  c task 2d after sp\n"
        "t1 task 1d after pt.at\nt2 task 1d after sp.start\nt3 task 1d after g\ng2 gate 2026-11-01 after sp\n")
    ends = {relation["id"]: (relation["from"]["endpoint"], relation["to"]["endpoint"]) for relation in project["relations"]}
    assert ends["pt-sp"] == ("at", "start")      # fixed point predecessor: at
    assert ends["sp-c"] == ("end", "start")      # span predecessor: end
    assert ends["pt-t1"] == ("at", "start")
    assert ends["sp-t2"] == ("start", "start")   # explicit modifier
    assert ends["g-t3"] == ("end", "start")      # group predecessor: end
    assert ends["sp-g2"] == ("end", "at")        # fixed point successor: at


def test_nesting_becomes_parent_and_groups_become_rollups():
    project = project_of(HEAD + "g group\n  a task 1d\n  h group\n    b task 1d\n  c task 1d\nz task 1d\n")
    objects = project["objects"]
    assert objects["g"] == {"type": "group", "schedule": {"mode": "rollup"}}
    assert [objects[name].get("parent") for name in ("a", "h", "b", "c", "z")] == ["g", "g", "h", "g", None]
    assert list(objects) == ["g", "a", "h", "b", "c", "z"]  # document order, parent before children


def test_anchors_bounds_and_object_calendar_map_to_schedule_properties():
    project = project_of(
        HEAD + "calendar c mon-fri\na task 5wd from 2026-10-05\nb task 5wd until 2026-12-18 calendar c\n"
        "x task 5wd start >= 2026-11-02 end <= 2026-11-30\n")
    assert project["objects"]["a"]["schedule"]["anchor"] == {"start": "2026-10-05"}
    assert project["objects"]["b"]["schedule"]["anchor"] == {"end": "2026-12-18"}
    assert project["objects"]["b"]["calendar"] == "c"
    assert project["objects"]["x"]["schedule"]["constraints"] == {"start": {"min": "2026-11-02"}, "end": {"max": "2026-11-30"}}


def test_lag_calendar_is_a_calendar_qualified_lag():
    project = project_of(HEAD + "calendar c mon-fri\ncalendar d mon-sun\na task 1d from 2026-10-05\nb task 1d after a +2wd in d\n")
    assert project["relations"][0]["lag"] == {"value": "2wd", "calendar": "d"}


def test_the_compiler_emits_only_the_schedule_and_structure_sections():
    project = project_of(HEAD + "a \"A\" task 3d\n")
    assert set(project) == {"version", "project", "objects"}
    assert set(project["objects"]["a"]) == {"type", "title", "schedule"}


def test_an_unaccepted_plan_never_yields_a_project():
    result = compile_terse("project p\na task 5d\nb tsak 3d\n")
    assert result.project is None and result.diagnostics


def test_core_findings_keep_their_core_code_and_gain_a_position():
    result = compile_text(HEAD + "a task 2026-10-01..2026-10-01\n")
    (finding,) = result.diagnostics
    assert finding.id == "E_INVALID_SPAN" and finding.component == "core"
    assert (finding.range.line, finding.range.column) == (2, 8)
    assert finding.path == "/objects/a/schedule"


def test_source_map_falls_back_to_the_nearest_ancestor_pointer():
    result = compile_terse(HEAD + "a task 5d after a\n")
    assert result.project is not None
    assert locate(result.source_map, "/objects/a/schedule/anchor").line == 2
    assert locate(result.source_map, "/relations/a-a/lag") is not None
    assert locate(result.source_map, "/relations/0") == locate(result.source_map, "/relations/a-a")
    assert locate(result.source_map, "/nothing/here") == result.source_map["/"]


def test_a_compiled_project_is_always_core_valid():
    for text in (HEAD, HEAD + "a task 1d\n", "terse 0.1\nproject p\n"):
        assert validate_project(project_of(text)) == []


@pytest.mark.parametrize("name", ["on", "no", "yes", "off", "true", "false", "null", "y", "n"])
def test_yaml_special_words_are_valid_object_names(name):
    project = project_of(HEAD + f"{name} task 1d\n")
    assert list(project["objects"]) == [name]
