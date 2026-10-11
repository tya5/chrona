import pytest
import yaml

from chrona.core.validation import load_yaml
from chrona.usecases.project_checks import (
    schedule_project_file, schedule_project_mapping, validate_project_file, validate_project_mapping,
)

STARTER = """\
version: timeline/v0.7
project: {id: starter, title: Starter}
objects:
  design: {type: task, title: Design, schedule: {mode: fixed-span, start: '2026-10-01', end: '2026-10-31'}}
  build: {type: task, title: Build, schedule: {mode: scheduled, amount: 5d}}
  release: {type: gate, title: Release, schedule: {mode: fixed-point, at: '2026-12-18'}}
relations:
  - {id: d-b, type: dependency, from: {object: design, endpoint: end}, to: {object: build, endpoint: start}, lag: 0d}
  - {id: b-r, type: dependency, from: {object: build, endpoint: end}, to: {object: release, endpoint: at}, lag: 0d}
"""

CYCLE = """\
version: timeline/v0.7
project: {id: cyc, title: Cycle}
objects:
  a: {type: task, title: A, schedule: {mode: scheduled, amount: 2d}}
  b: {type: task, title: B, schedule: {mode: scheduled, amount: 2d}}
relations:
  - {id: a-b, type: dependency, from: {object: a, endpoint: end}, to: {object: b, endpoint: start}, lag: 0d}
  - {id: b-a, type: dependency, from: {object: b, endpoint: end}, to: {object: a, endpoint: start}, lag: 0d}
"""


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_validate_accepts_a_valid_project_and_reports_a_broken_one(tmp_path):
    assert validate_project_file(_write(tmp_path, "ok.yaml", STARTER)).ok
    broken = yaml.safe_load(STARTER)
    broken["relations"][0]["to"]["object"] = "ghost"
    outcome = validate_project_mapping(broken)
    assert not outcome.ok
    assert [item.id for item in outcome.diagnostics] == ["E_REFERENCE"]


def test_a_referenced_period_that_resolves_empty_is_rejected_by_schedule_but_not_by_validate(tmp_path):
    project = yaml.safe_load(STARTER)
    project["periods"] = {"p": {"start": {"object": "design", "endpoint": "end"}, "end": "2026-10-31"}}
    assert validate_project_mapping(project).ok  # validate computes no dates
    outcome = schedule_project_mapping(project)
    assert not outcome.ok
    assert [(item.id, item.path) for item in outcome.diagnostics] == [("E_PROJECT_PERIOD_ORDER", "/periods/p")]
    assert outcome.placements == {} and outcome.analysis is None and outcome.warnings == ()


def test_a_period_that_resolves_in_order_leaves_the_schedule_document_unchanged():
    plain = yaml.safe_load(STARTER)
    with_period = yaml.safe_load(STARTER)
    with_period["periods"] = {"p": {"start": {"object": "design", "endpoint": "end"}, "end": "2026-11-30"}}
    assert schedule_project_mapping(with_period).payload() == schedule_project_mapping(plain).payload()


def test_validate_reports_a_cycle_without_scheduling_and_schedule_reports_it_identically(tmp_path):
    path = _write(tmp_path, "cycle.yaml", CYCLE)
    validated = validate_project_file(path)
    assert not validated.ok
    assert {item.id for item in validated.diagnostics} == {"E_UNSUPPORTED_CYCLE"}
    outcome = schedule_project_file(path)
    assert not outcome.ok
    assert outcome.diagnostics == validated.diagnostics
    assert outcome.placements == {} and outcome.analysis is None


def test_schedule_document_keeps_the_published_key_order_and_object_order(tmp_path):
    outcome = schedule_project_file(_write(tmp_path, "ok.yaml", STARTER))
    assert outcome.ok
    document = outcome.payload()
    assert list(document) == ["placements", "diagnostics", "warnings", "analysis"]
    assert document["diagnostics"] == [] and document["warnings"] == []
    assert list(document["analysis"]) == ["criticalObjectIds", "totalFloat"]
    assert document["analysis"]["criticalObjectIds"] == []
    assert document["placements"] is outcome.placements


def test_a_missed_deadline_is_a_warning_record_beside_a_successful_schedule():
    project = yaml.safe_load(STARTER)
    project["objects"]["release"]["deadline"] = "2026-12-01"
    outcome = schedule_project_mapping(project)
    assert outcome.ok and [item.id for item in outcome.warnings] == ["W_DEADLINE"]
    document = outcome.payload()
    assert document["diagnostics"] == []
    (record,) = document["warnings"]
    assert list(record) == ["code", "severity", "component", "sourceRef", "revisionRefs", "message", "details"]
    assert (record["code"], record["severity"], record["component"]) == ("W_DEADLINE", "warning", "core")
    assert record["sourceRef"] == "/objects/release/deadline"
    assert record["details"]["daysLate"] == 17 and record["details"]["object"] == "release"


def test_a_rejected_schedule_carries_no_warnings():
    project = yaml.safe_load(CYCLE)
    project["objects"]["a"]["deadline"] = "2020-01-01"
    outcome = schedule_project_mapping(project)
    assert not outcome.ok and outcome.warnings == ()


def test_validate_does_not_judge_a_deadline_because_it_computes_no_placements():
    project = yaml.safe_load(STARTER)
    project["objects"]["release"]["deadline"] = "2026-12-01"
    assert validate_project_mapping(project).ok


def test_schedule_mapping_matches_the_file_form(tmp_path):
    path = _write(tmp_path, "ok.yaml", STARTER)
    assert schedule_project_mapping(load_yaml(path)).payload() == schedule_project_file(path).payload()


def test_the_checks_read_only_the_named_path_and_print_nothing(tmp_path, capsys):
    validate_project_file(_write(tmp_path, "ok.yaml", STARTER))
    schedule_project_file(tmp_path / "ok.yaml")
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""
    assert sorted(path.name for path in tmp_path.iterdir()) == ["ok.yaml"]


@pytest.mark.parametrize("check", [validate_project_file, schedule_project_file])
def test_an_unreadable_file_raises_the_library_error_for_the_failure_report(tmp_path, check):
    with pytest.raises(OSError):
        check(tmp_path / "missing.yaml")
    with pytest.raises(yaml.YAMLError):
        check(_write(tmp_path, "broken.yaml", "a: [unclosed\n"))


@pytest.mark.parametrize(("text", "found"), [("", "an empty document"), ("- a\n- b\n", "a list"), ("just text\n", "a str")])
@pytest.mark.parametrize("check", [validate_project_file, schedule_project_file])
def test_a_file_that_is_not_a_mapping_is_a_rejected_project_not_a_tool_failure(tmp_path, check, text, found):
    outcome = check(_write(tmp_path, "shape.yaml", text))
    assert not outcome.ok
    (finding,) = outcome.diagnostics
    assert (finding.id, finding.path) == ("E_SCHEMA", "/")
    assert finding.message == f"a Project must be a YAML mapping with version, project and objects; found {found}"
