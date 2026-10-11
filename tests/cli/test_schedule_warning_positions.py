"""`chrona schedule` positions W_DEADLINE on the line or key it is about (#946)."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

PLAN = """terse 0.1
project p "P"
a "A" task 2027-03-01..2027-03-20 deadline 2027-03-10
b "B" task 2027-03-01..2027-03-05 deadline 2027-03-31
"""
YAML = """version: timeline/v0.7
project: {id: p, title: P}
objects:
  a:
    type: task
    title: A
    schedule: {mode: fixed-span, start: '2027-03-01', end: '2027-03-20'}
    deadline: '2027-03-10'
"""


def _schedule(tmp_path: Path, name: str, text: str) -> dict:
    (tmp_path / name).write_text(text, encoding="utf-8")
    result = subprocess.run([sys.executable, "-c", "from chrona.app.cli import main; main()", "schedule", name], cwd=tmp_path,
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout
    return json.loads(result.stdout)


def test_a_terse_plans_deadline_warning_carries_the_plan_line(tmp_path):
    (warning,) = _schedule(tmp_path, "plan.chrona", PLAN)["warnings"]

    assert warning["code"] == "W_DEADLINE" and warning["source"] == "plan.chrona"
    where = warning["sourceRange"]
    assert where["line"] == 3 and where["endLine"] == 3
    line = PLAN.splitlines()[2]
    assert line[where["column"] - 1:where["endColumn"] - 1] == "deadline 2027-03-10"


def test_a_yaml_projects_deadline_warning_carries_the_key_range(tmp_path):
    (warning,) = _schedule(tmp_path, "project.yaml", YAML)["warnings"]

    where = warning["sourceRange"]
    assert "source" not in warning and where["line"] == 8
    assert YAML.splitlines()[7][where["column"] - 1:where["endColumn"] - 1] == "deadline"


def test_a_schedule_without_warnings_has_none_to_position(tmp_path):
    payload = _schedule(tmp_path, "ok.chrona", 'terse 0.1\nproject p "P"\na "A" task 2027-03-01..2027-03-05 deadline 2027-03-31\n')

    assert payload["warnings"] == []
