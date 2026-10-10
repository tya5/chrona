"""Project validation names what is wrong, where, and all of it in one run (#1303).

Each case is one edit to a small Project written in flow style (a whole object on one line, as in the trial's plan).
"""
from __future__ import annotations

import copy
from datetime import date
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from chrona.core.suggestions import nearest, unknown_id_message
from chrona.usecases.project_checks import validate_project_file
from tests.support import synthetic_review as sr

BASE = sr.project({"build": sr.span("build", date(2027, 1, 4), 10, title="Build"),
                   "design": sr.span("design", date(2026, 12, 1), 10, title="Design")})
DEPENDENCY = {"type": "dependency", "from": {"object": "design", "endpoint": "end"},
              "to": {"object": "build", "endpoint": "start"}}


def _write(tmp_path, name, mutate) -> Path:
    data = copy.deepcopy(BASE)
    data["relations"] = [copy.deepcopy(DEPENDENCY)]
    mutate(data)
    path = tmp_path / f"{name}.yaml"
    path.write_text(yaml.safe_dump(json.loads(json.dumps(data, default=lambda value: value.isoformat())),
                                   default_flow_style=True, width=100000), encoding="utf-8")
    return path


def _validate(path):
    return validate_project_file(path).diagnostics


def test_a_date_written_the_wrong_way_is_named_with_its_value_at_the_date(tmp_path):
    path = _write(tmp_path, "date", lambda data: data["objects"]["build"]["schedule"].update(start="11/01/2027"))
    (found,) = _validate(path)

    assert found.id == "E_SCHEMA" and found.path == "/objects/build/schedule/start"
    assert "'11/01/2027'" in found.message and "YYYY-MM-DD" in found.message
    assert "mode=" not in found.message  # not the other modes


def test_an_unknown_schedule_key_is_named_with_the_nearest_key(tmp_path):
    def mutate(data):
        data["objects"]["press"] = {"type": "task", "title": "Press", "schedule": {"mode": "scheduled", "ammount": "10wd"}}

    found = _validate(_write(tmp_path, "typo", mutate))

    assert any("unexpected property 'ammount'; did you mean 'amount'?" in item.message
               and item.path == "/objects/press/schedule" for item in found)
    assert not any("mode='fixed-point'" in item.message for item in found)


def test_an_unknown_relation_target_names_the_id_and_the_nearest_object(tmp_path):
    def mutate(data):
        data["relations"][0]["to"]["object"] = "biuld"

    (found,) = _validate(_write(tmp_path, "ref", mutate))

    assert found.id == "E_REFERENCE" and found.path == "/relations/0/to/object"
    assert "'biuld'" in found.message and "did you mean 'build'?" in found.message


def test_an_unknown_parent_names_the_id_and_the_nearest_object(tmp_path):
    def mutate(data):
        data["objects"]["build"]["parent"] = "desing"

    found = _validate(_write(tmp_path, "parent", mutate))

    assert any(item.id == "E_PARENT_NOT_FOUND" and "'desing'" in item.message and "did you mean 'design'?" in item.message
               for item in found)


def test_three_independent_mistakes_are_three_diagnostics_in_one_run_in_a_stated_order(tmp_path):
    def mutate(data):
        data["objects"]["design"]["x"] = 1
        data["relations"][0]["to"]["object"] = "biuld"
        data["objects"]["build"]["deadline"] = "2027-02-30"

    found = _validate(_write(tmp_path, "multi", mutate))

    assert [(item.id, item.path) for item in found] == [
        ("E_SCHEMA", "/objects/design"), ("E_SCHEMA", "/objects/build/deadline"),
        ("E_REFERENCE", "/relations/0/to/object")]
    assert [item for item in found if "'x'" in item.message] and [item for item in found if "'biuld'" in item.message]


def test_every_diagnostic_of_a_yaml_project_carries_a_source_range_whose_line_holds_its_node(tmp_path):
    def mutate(data):
        data["objects"]["design"]["x"] = 1
        data["relations"][0]["to"]["object"] = "biuld"
        data["objects"]["build"]["schedule"]["start"] = "11/01/2027"

    path = _write(tmp_path, "ranges", mutate)
    lines = path.read_text(encoding="utf-8").splitlines()
    found = _validate(path)

    assert len(found) == 3
    for item in found:
        located = item.source_range
        assert located is not None and {"line", "column", "endLine", "endColumn"} <= set(located)
        text = lines[located["line"] - 1][located["column"] - 1:located["endColumn"] - 1]
        assert text in {"x", "object", "start"}, (item.path, text)


def test_block_style_ranges_point_at_the_member_line(tmp_path):
    path = tmp_path / "block.yaml"
    data = copy.deepcopy(BASE)
    data["objects"]["build"]["bogus"] = True
    path.write_text(yaml.safe_dump(json.loads(json.dumps(data, default=lambda value: value.isoformat())),
                                   default_flow_style=False, sort_keys=False), encoding="utf-8")
    (found,) = _validate(path)

    assert path.read_text(encoding="utf-8").splitlines()[found.source_range["line"] - 1].strip() == "bogus: true"


def test_the_cli_prints_the_range_and_the_named_value(tmp_path):
    path = _write(tmp_path, "cli", lambda data: data["relations"][0]["to"].update(object="biuld"))
    result = subprocess.run([sys.executable, "-c", "from chrona.app.cli import main; main()", "validate", str(path)], capture_output=True, text=True)
    report = json.loads(result.stdout)
    (item,) = report["diagnostics"]

    assert result.returncode == 1 and item["code"] == "E_REFERENCE"
    assert "'biuld'" in item["message"] and item["sourceRange"]["line"] == 1


def test_the_nearest_name_rule_is_the_terse_compilers():
    assert nearest("biuld", ["design", "build"]) == "build"
    assert nearest("zzzzzz", ["design", "build"]) is None
    assert unknown_id_message("to object", "zzzzzz", ["design"]) == "Unknown to object 'zzzzzz'"


@pytest.mark.parametrize("bad", [{"start": "2027-01-04", "end": "2027-01-03"}])
def test_semantic_errors_of_a_valid_schema_are_unchanged(tmp_path, bad):
    path = _write(tmp_path, "span", lambda data: data["objects"]["build"]["schedule"].update(bad))
    (found,) = _validate(path)

    assert found.id == "E_INVALID_SPAN"
