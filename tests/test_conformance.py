from datetime import date
from pathlib import Path

import yaml

from chrona.temporal import Calendar, advance, retreat, is_scheduled_amount
from chrona.validation import validate_project


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "timeline-design" / "docs" / "examples" / "conformance-v0.1.yaml"


def _date(value):
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def _assert_temporal_case(case, calendar=None):
    steps = [case["input"] | {"expected": case["expected"]}] if "input" in case else case["steps"]
    for step in steps:
        value = _date(step["date"])
        actual = advance(value, step["amount"], calendar) if step["op"] == "advance" else retreat(value, step["amount"], calendar)
        assert actual == _date(step["expected"]), case["name"]


def test_temporal_reference_fixture():
    fixture = yaml.safe_load(FIXTURE.read_text())
    for case in fixture["temporal"]["calendar_period"]:
        _assert_temporal_case(case)

    work = fixture["temporal"]["work_period"]
    calendar = Calendar.from_mapping(work["calendar"])
    for case in work["cases"]:
        _assert_temporal_case(case, calendar)


def test_scheduled_amount_fixture():
    fixture = yaml.safe_load(FIXTURE.read_text())
    checks = fixture["validation"]
    assert all(is_scheduled_amount(value) for value in checks["valid_scheduled_amounts"])
    assert not any(is_scheduled_amount(value) for value in checks["invalid_scheduled_amounts"])


def test_yaml_date_scalars_validate_against_json_compatible_schema():
    project = {
        "version": "timeline/v0.1",
        "project": {"id": "dates"},
        "objects": {
            "task": {
                "type": "task",
                "schedule": {"mode": "fixed", "start": date(2026, 10, 1), "end": date(2026, 10, 2)},
            }
        },
    }
    assert validate_project(project) == []
