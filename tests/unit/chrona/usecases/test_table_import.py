"""`chrona import`: a CSV or TSV table becomes the Project the terse compiler writes, with cell-level errors (#1307)."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import yaml

from chrona.core.validation import validate_project
from chrona.scheduling.scheduler import schedule
from chrona.usecases.table_import import import_table
from chrona.usecases.terse_compile import compile_plan

PLAN = """terse 0.1
project my-plan "My plan" calendar standard
calendar standard mon-fri except 2027-04-02
kickoff "Kickoff" gate 2027-03-01
design "Design" task 10wd from 2027-03-02
build "Build" task 20wd after design +1wd deadline 2027-05-14
review "Design review" gate after design.start
phase-2 "Phase 2" group
  tests "Tests" task 5wd after build
  launch "Launch" gate 2027-06-30 after tests +2d, review
"""
TABLE = """id,title,type,start,end,duration,parent,predecessors,deadline
kickoff,Kickoff,gate,2027-03-01,,,,,
design,Design,task,2027-03-02,,10wd,,,
build,Build,task,,,20wd,,design +1wd,2027-05-14
review,Design review,gate,,,,,design.start,
phase-2,Phase 2,group,,,,,,
tests,Tests,task,,,5wd,phase-2,build,
launch,Launch,gate,2027-06-30,,,phase-2,"tests +2d, review",
"""
CALENDAR = ["standard mon-fri except 2027-04-02"]


def _import(text, **options):
    options.setdefault("project_id", "my-plan")
    options.setdefault("title", "My plan")
    options.setdefault("calendars", CALENDAR)
    return import_table(text, **options)


def test_the_table_equivalent_of_a_terse_plan_gives_the_same_project_yaml_as_compile():
    expected = compile_plan(PLAN.encode("utf-8"))
    result = _import(TABLE)

    assert expected.ok and result.ok, result.diagnostics
    assert result.project_yaml == expected.yaml


def _table(headers, *rows):
    import csv
    import io
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow([row.get(header, "") for header in headers])
    return out.getvalue()


def test_a_table_using_every_column_validates_schedules_and_writes_an_actual_set():
    headers = ["ID", "Title", "Type", "Start", "Finish", "Duration", "Parent", "Predecessors", "Deadline", "Calendar", "Progress",
               "Actual Start", "Actual Finish", "Owner"]
    table = _table(
        headers,
        {"ID": "g", "Title": "Gate", "Type": "gate", "Start": "2027-03-01", "Actual Start": "2027-03-01", "Owner": "pm"},
        {"ID": "a", "Title": "Alpha", "Start": "2027-03-02", "Finish": "2027-03-05", "Calendar": "standard", "Progress": "60%",
         "Actual Start": "2027-03-02", "Owner": "ana"},
        {"ID": "p", "Title": "Phase", "Type": "group"},
        {"ID": "b", "Title": "Beta", "Duration": "3wd", "Parent": "p", "Predecessors": "a", "Deadline": "2027-06-01",
         "Calendar": "standard", "Progress": "0.25"},
        {"ID": "c", "Title": "Gamma", "Start": "2027-03-15", "Finish": "2027-03-19", "Parent": "p", "Predecessors": "a, b.start +1d",
         "Progress": "40", "Actual Finish": "2027-03-19", "Owner": "bo"})

    result = import_table(table, project_id="all-columns", calendars=["standard mon-fri"], as_of="2027-04-01")

    assert result.ok, [item.as_dict() for item in result.diagnostics]
    project = yaml.safe_load(result.project_yaml)
    assert validate_project(project) == [] and schedule(project).ok
    assert project["objects"]["a"]["schedule"] == {"mode": "fixed-span", "start": "2027-03-02", "end": "2027-03-06"}  # finish is inclusive
    assert project["objects"]["b"]["parent"] == "p" and project["objects"]["a"]["fields"] == {"Owner": "ana"}
    actual = yaml.safe_load(result.actual_yaml)
    assert actual["body"]["asOf"] == "2027-04-01"
    observed = {item["projectObjectId"]: item["actual"] for item in actual["body"]["observations"]}
    assert observed["a"] == {"start": "2027-03-02", "progress": 0.6} and observed["b"] == {"progress": 0.25}
    assert observed["g"] == {"at": "2027-03-01"} and observed["c"] == {"finish": "2027-03-19", "progress": 0.4}


def test_three_mistakes_are_three_diagnostics_with_row_and_column_in_one_run():
    table = ("id,title,type,start,end,predecessors\n"
             "a,A,task,2027-3-05,2027-03-09,\n"
             "b,B,task,2027-03-01,2027-03-05,zzz\n"
             "a,Again,task,2027-03-01,2027-03-05,\n")
    result = import_table(table, project_id="p")

    assert not result.ok
    found = {(item.code, item.row, item.column, item.header) for item in result.diagnostics}
    assert found == {("E_TERSE_DATE_INVALID", 2, 4, "start"), ("E_TERSE_REFERENCE_UNKNOWN", 3, 6, "predecessors"),
                     ("E_IMPORT_ID_DUPLICATE", 4, 1, "id")}
    assert all("row" in item.as_dict()["message"] for item in result.diagnostics)


def test_parent_mistakes_and_column_mistakes_are_named():
    unknown = import_table("id,type,parent,start,end\nx,task,grop,2027-03-01,2027-03-05\n", project_id="p")
    assert [(item.code, item.header) for item in unknown.diagnostics] == [("E_IMPORT_PARENT_UNKNOWN", "parent")]

    cycle = import_table("id,type,parent\na,group,b\nb,group,a\n", project_id="p")
    assert "E_IMPORT_PARENT_CYCLE" in {item.code for item in cycle.diagnostics}

    no_id = import_table("title,start\nA,2027-03-01\n", project_id="p")
    assert [item.code for item in no_id.diagnostics] == ["E_IMPORT_COLUMN_MISSING"]

    both = import_table("id,start,end,finish\na,2027-03-01,2027-03-02,2027-03-02\n", project_id="p")
    assert "E_IMPORT_COLUMN_CONFLICT" in {item.code for item in both.diagnostics}


def test_a_header_mapping_renames_the_users_columns_and_a_tsv_is_read_with_tabs():
    table = "Task id\tName\tFrom\tTo\nt1\tOne\t2027-03-01\t2027-03-05\n"
    result = import_table(table, delimiter="\t", project_id="p",
                          mapping={"Task id": "id", "Name": "title", "From": "start", "To": "end"})

    assert result.ok, [item.as_dict() for item in result.diagnostics]
    assert yaml.safe_load(result.project_yaml)["objects"]["t1"]["title"] == "One"


def test_the_command_writes_files_reports_cells_and_never_overwrites(tmp_path):
    def chrona(*args):
        return subprocess.run([sys.executable, "-c", "from chrona.app.cli import main; main()", *args], cwd=tmp_path,
                              capture_output=True, text=True, timeout=120)

    (tmp_path / "plan.csv").write_text(TABLE, encoding="utf-8")
    (tmp_path / "bad.csv").write_text("id,start,end\na,2027-13-01,2027-03-05\n", encoding="utf-8")
    first = chrona("import", "plan.csv", "-o", "project.yaml", "--calendar", CALENDAR[0], "--project-id", "my-plan", "--title", "My plan")
    assert first.returncode == 0 and json.loads(first.stdout) == {"status": "ok", "project": "project.yaml", "actual": None, "created": ["project.yaml"]}
    assert (tmp_path / "project.yaml").read_bytes() == compile_plan(PLAN.encode("utf-8")).yaml

    again = chrona("import", "plan.csv", "-o", "project.yaml", "--calendar", CALENDAR[0])
    assert again.returncode == 2 and json.loads(again.stdout)["diagnostics"][0]["code"] == "E_IMPORT_OUTPUT_EXISTS"

    rejected = chrona("import", "bad.csv", "-o", "bad.yaml")
    report = json.loads(rejected.stdout)
    assert rejected.returncode == 1 and report["status"] == "rejected" and not (tmp_path / "bad.yaml").exists()
    assert report["diagnostics"][0]["cell"] == {"row": 2, "column": 2, "header": "start"}

    missing = chrona("import", "nope.csv", "-o", "x.yaml")
    assert missing.returncode == 2 and json.loads(missing.stdout)["diagnostics"][0]["code"] == "E_IMPORT_INPUT_IO"
