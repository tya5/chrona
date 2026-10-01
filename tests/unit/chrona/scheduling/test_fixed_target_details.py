"""E_FIXED_TARGET_VIOLATION names the earliest feasible date and the relation that forces it (#788 slice 0)."""
import copy
import json

import pytest

from chrona.core.diagnostics import Diagnostic
from chrona.scheduling.scheduler import schedule
from chrona.usecases.failure_report import rejection_report


def _rel(rel_id, source, source_endpoint, target, target_endpoint, lag=None):
    relation = {"type": "dependency", "from": {"object": source, "endpoint": source_endpoint},
                "to": {"object": target, "endpoint": target_endpoint}}
    if rel_id is not None:
        relation["id"] = rel_id
    if lag is not None:
        relation["lag"] = lag
    return relation


def _project(objects, relations):
    return {
        "version": "timeline/v0.7", "project": {"id": "p", "calendar": "std"},
        "calendars": {"std": {"working_days": ["mon", "tue", "wed", "thu", "fri"],
                              "exceptions": [{"date": "2027-05-03", "working": False}]},
                      "six": {"working_days": ["mon", "tue", "wed", "thu", "fri", "sat"]}},
        "objects": objects, "relations": relations,
    }


def _issue_case(launch_at="2027-05-17"):
    """The case of the issue: a fixed-point gate behind a duration task."""
    objects = {
        "build": {"type": "task", "schedule": {"mode": "fixed-span", "start": "2027-04-26", "end": "2027-05-07"}},
        "qa": {"type": "task", "schedule": {"mode": "scheduled", "amount": "5wd"}},
        "launch": {"type": "gate", "schedule": {"mode": "fixed-point", "at": launch_at}},
    }
    return _project(objects, [_rel("build-qa", "build", "end", "qa", "start", "0d"),
                              _rel("qa-launch", "qa", "end", "launch", "at", "2wd")])


def _only(result):
    assert [item.id for item in result.diagnostics] == ["E_FIXED_TARGET_VIOLATION"]
    return result.diagnostics[0]


def test_gate_behind_a_duration_task_reports_the_date_to_write():
    result = schedule(_issue_case())
    item = _only(result)
    assert item.path == "/relations/qa-launch"
    assert item.message == (
        "launch.at is fixed at 2027-05-17, but relation qa-launch (qa.end 2027-05-14 + 2wd) requires 2027-05-18 "
        "or later. The earliest feasible date for launch.at is 2027-05-18 (forced by qa-launch)."
    )
    assert item.details == {
        "object": "launch", "endpoint": "at", "placed": "2027-05-17", "relation": "qa-launch",
        "from": {"object": "qa", "endpoint": "end", "value": "2027-05-14"}, "lag": "2wd",
        "required": "2027-05-18", "earliest": "2027-05-18", "forcedBy": "qa-launch",
    }


def test_the_reported_date_is_accepted_and_one_day_earlier_is_rejected_again():
    earliest = _only(schedule(_issue_case())).details["earliest"]
    accepted = schedule(_issue_case(earliest))
    assert accepted.ok and accepted.placements["launch"]["at"].isoformat() == earliest
    one_earlier = _only(schedule(_issue_case("2027-05-17")))
    assert one_earlier.details["earliest"] == earliest


def test_two_violating_relations_share_earliest_and_forced_by_and_keep_their_own_required():
    objects = {
        "a": {"type": "task", "schedule": {"mode": "fixed-span", "start": "2027-05-03", "end": "2027-05-10"}},
        "b": {"type": "task", "schedule": {"mode": "fixed-span", "start": "2027-05-03", "end": "2027-05-14"}},
        "g": {"type": "gate", "schedule": {"mode": "fixed-point", "at": "2027-05-09"}},
    }
    result = schedule(_project(objects, [_rel("a-g", "a", "end", "g", "at", "1d"), _rel("b-g", "b", "end", "g", "at", "0d")]))
    assert [item.path for item in result.diagnostics] == ["/relations/a-g", "/relations/b-g"]
    first, second = (item.details for item in result.diagnostics)
    assert (first["required"], second["required"]) == ("2027-05-11", "2027-05-14")
    assert first["earliest"] == second["earliest"] == "2027-05-14"
    assert first["forcedBy"] == second["forcedBy"] == "b-g"


def test_a_tie_is_forced_by_the_first_relation_in_declaration_order():
    objects = {
        "a": {"type": "task", "schedule": {"mode": "fixed-span", "start": "2027-05-03", "end": "2027-05-10"}},
        "b": {"type": "task", "schedule": {"mode": "fixed-span", "start": "2027-05-03", "end": "2027-05-09"}},
        "g": {"type": "gate", "schedule": {"mode": "fixed-point", "at": "2027-05-01"}},
    }
    result = schedule(_project(objects, [_rel("b-g", "b", "end", "g", "at", "1d"), _rel("a-g", "a", "end", "g", "at", "0d")]))
    assert len(result.diagnostics) == 2
    assert {item.details["forcedBy"] for item in result.diagnostics} == {"b-g"}


def test_a_relation_without_an_id_is_pointed_at_by_index_and_named_by_pointer():
    objects = {
        "a": {"type": "task", "schedule": {"mode": "fixed-span", "start": "2027-05-03", "end": "2027-05-10"}},
        "x": {"type": "task", "schedule": {"mode": "fixed-span", "start": "2027-05-03", "end": "2027-05-04"}},
        "g": {"type": "gate", "schedule": {"mode": "fixed-point", "at": "2027-05-10"}},
    }
    result = schedule(_project(objects, [_rel(None, "x", "end", "x", "end"), _rel(None, "a", "end", "g", "at", "1d")]))
    item = _only(result)
    assert item.path == "/relations/1"
    assert item.message.startswith("g.at is fixed at 2027-05-10, but relation /relations/1 (a.end 2027-05-10 + 1d) requires 2027-05-11 or later.")
    assert item.message.endswith("(forced by /relations/1).")
    assert item.details["relation"] == item.details["forcedBy"] == "/relations/1"


def test_a_negative_lag_renders_with_a_minus_sign():
    objects = {
        "a": {"type": "task", "schedule": {"mode": "fixed-span", "start": "2027-05-03", "end": "2027-05-10"}},
        "g": {"type": "gate", "schedule": {"mode": "fixed-point", "at": "2027-05-07"}},
    }
    item = _only(schedule(_project(objects, [_rel("a-g", "a", "end", "g", "at", "-2d")])))
    assert "(a.end 2027-05-10 - 2d)" in item.message
    assert item.details["lag"] == "-2d" and item.details["required"] == item.details["earliest"] == "2027-05-08"


def test_a_lag_on_another_calendar_names_the_calendar_and_counts_its_working_days():
    def case(lag):
        objects = {
            "a": {"type": "task", "schedule": {"mode": "fixed-span", "start": "2027-05-03", "end": "2027-05-07"}},
            "g": {"type": "gate", "schedule": {"mode": "fixed-point", "at": "2027-05-07"}},
        }
        return _only(schedule(_project(objects, [_rel("a-g", "a", "end", "g", "at", lag)])))

    six = case({"value": "2wd", "calendar": "six"})
    assert "(a.end 2027-05-07 + 2wd in six)" in six.message
    assert six.details["lag"] == {"value": "2wd", "calendar": "six"}
    assert six.details["required"] == six.details["earliest"] == "2027-05-10"
    assert case("2wd").details["earliest"] == "2027-05-11"


def test_a_fixed_span_target_reports_the_earliest_date_for_the_violated_endpoint():
    objects = {
        "a": {"type": "task", "schedule": {"mode": "fixed-span", "start": "2027-05-03", "end": "2027-05-10"}},
        "b": {"type": "task", "schedule": {"mode": "fixed-span", "start": "2027-05-04", "end": "2027-05-20"}},
    }
    item = _only(schedule(_project(objects, [_rel("a-b", "a", "end", "b", "start", "0d")])))
    assert item.message.startswith("b.start is fixed at 2027-05-04, but relation a-b (a.end 2027-05-10 + 0d) requires 2027-05-10 or later.")
    assert item.details["object"] == "b" and item.details["endpoint"] == "start" and item.details["earliest"] == "2027-05-10"


def test_details_do_not_change_how_many_diagnostics_a_rejected_plan_gets():
    project = _issue_case()
    result = schedule(project)
    assert len(result.diagnostics) == 1
    assert schedule(copy.deepcopy(project)).diagnostics == result.diagnostics


def test_details_are_excluded_from_equality_and_hashing():
    plain, detailed = Diagnostic("E_X", "m", "/p"), Diagnostic("E_X", "m", "/p", details={"k": 1})
    assert plain == detailed and hash(plain) == hash(detailed)
    assert detailed.as_dict() == {"id": "E_X", "message": "m", "path": "/p", "details": {"k": 1}}
    assert plain.as_dict() == {"id": "E_X", "message": "m", "path": "/p"}


def test_the_failure_record_carries_details_after_message_and_only_when_present():
    report = rejection_report([Diagnostic("E_X", "m", "/p"), Diagnostic("E_Y", "n", "/q", details={"k": 1})])
    plain, detailed = report.diagnostics
    assert list(plain) == ["code", "severity", "component", "sourceRef", "revisionRefs", "message"]
    assert list(detailed) == ["code", "severity", "component", "sourceRef", "revisionRefs", "message", "details"]
    item = _only(schedule(_issue_case()))
    payload = json.loads(json.dumps(rejection_report([item]).payload()))
    assert payload["diagnostics"][0]["details"] == item.details


def _committed_projects():
    import yaml
    from pathlib import Path

    root = Path(__file__).resolve().parents[4]
    for folder in ("examples", "conformance", "tests/fixtures"):
        for path in sorted((root / folder).rglob("*.y*ml")):
            if "generated" in path.parts:
                continue
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
            except yaml.YAMLError:
                continue
            if isinstance(data, dict) and data.get("version") == "timeline/v0.7" and "objects" in data:
                yield path.name, data


@pytest.mark.corpus  # PR-path twin: the synthetic cases above (#657)
def test_every_fixed_target_rejection_in_the_committed_corpus_carries_resolvable_details():
    for name, project in _committed_projects():
        for item in schedule(project).diagnostics:
            if item.id == "E_FIXED_TARGET_VIOLATION":
                assert item.details and item.details["earliest"] >= item.details["required"], name
                assert item.path.startswith("/relations/"), name
