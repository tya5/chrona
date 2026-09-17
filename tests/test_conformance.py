from datetime import date
from pathlib import Path

import yaml

from chrona.temporal import Calendar, advance, retreat, is_scheduled_amount
from chrona.validation import validate_project
from chrona.scheduler import schedule


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


def test_dependency_bound_cases_execute_through_scheduler():
    fixture = yaml.safe_load(FIXTURE.read_text())
    for case in fixture["scheduling"]["dependency_bounds"]:
        source_endpoint = case["source"]["endpoint"]
        source_value = _date(case["source"]["value"])
        if source_endpoint == "at":
            source_schedule = {"mode": "fixed", "at": source_value}
        elif source_endpoint == "start":
            source_schedule = {"mode": "fixed", "start": source_value, "end": advance(source_value, "1d")}
        else:
            source_schedule = {"mode": "fixed", "start": retreat(source_value, "1d"), "end": source_value}
        target_endpoint = case["target"]["endpoint"]
        project = {
            "version": "timeline/v0.1",
            "project": {"id": case["name"]},
            "objects": {
                "source": {"type": "task", "schedule": source_schedule},
                "target": {"type": "task", "schedule": {"mode": "scheduled", "amount": "1d"}},
            },
            "relations": [{
                "type": "dependency",
                "from": {"object": "source", "endpoint": source_endpoint},
                "to": {"object": "target", "endpoint": target_endpoint},
                "lag": case["lag"],
            }],
        }
        result = schedule(project)
        assert result.ok, case["name"]
        assert result.placements["target"][target_endpoint] == _date(case["expected_lower_bound"]), case["name"]


def test_multiple_bound_cases_execute_through_scheduler():
    fixture = yaml.safe_load(FIXTURE.read_text())
    for case in fixture["scheduling"]["multiple_bounds"]:
        if case.get("expected") == "schedule_error":
            project = {
                "version": "timeline/v0.1",
                "project": {"id": case["name"]},
                "objects": {"target": {"type": "task", "schedule": {"mode": "scheduled", "amount": "1d", "anchor": {"start": "2026-10-20"}, "constraints": {"start": {"min": "2026-10-20", "max": "2026-10-15"}}}}},
            }
            assert not schedule(project).ok
            continue
        bounds = case["bounds"]
        objects = {"target": {"type": "task", "schedule": {"mode": "scheduled", "amount": "1d"}}}
        relations = []
        for index, bound in enumerate(bounds):
            source_id = f"source-{index}"
            value = _date(bound["min"])
            objects[source_id] = {"type": "task", "schedule": {"mode": "fixed", "start": retreat(value, "1d"), "end": value}}
            relations.append({"type": "dependency", "from": {"object": source_id, "endpoint": "end"}, "to": {"object": "target", "endpoint": bound["endpoint"]}, "lag": "0d"})
        result = schedule({"version": "timeline/v0.1", "project": {"id": case["name"]}, "objects": objects, "relations": relations})
        assert result.ok, case["name"]
        assert result.placements["target"]["start"] == _date(case["expected_min"]), case["name"]


def test_calendar_placement_cases_execute_through_scheduler():
    calendar = {"working_days": ["mon", "tue", "wed", "thu", "fri"], "exceptions": [{"date": "2026-10-12", "working": False}]}
    project = {
        "version": "timeline/v0.1",
        "project": {"id": "calendar-placement", "calendar": "standard"},
        "calendars": {"standard": calendar},
        "objects": {
            "source": {"type": "task", "schedule": {"mode": "fixed", "start": "2026-10-09", "end": "2026-10-10"}},
            "target": {"type": "task", "schedule": {"mode": "scheduled", "amount": "1wd"}},
        },
        "relations": [{"type": "dependency", "from": {"object": "source", "endpoint": "end"}, "to": {"object": "target", "endpoint": "start"}, "lag": "0d"}],
    }
    result = schedule(project)
    assert result.ok
    assert result.placements["target"] == {"start": date(2026, 10, 13), "end": date(2026, 10, 14)}
