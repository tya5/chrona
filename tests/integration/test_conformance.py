from datetime import date
from pathlib import Path

import yaml

from chrona.core.temporal import Calendar, advance, retreat, is_scheduled_amount
from chrona.core.validation import validate_project
from chrona.scheduling.scheduler import schedule


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
FIXTURE = ROOT / "conformance" / "conformance-v0.1.yaml"


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
        "version": "timeline/v0.3",
        "project": {"id": "dates"},
        "objects": {
            "task": {
                "type": "task",
                "schedule": {"mode": "fixed", "start": date(2026, 10, 1), "end": date(2026, 10, 2)},
            }
        },
    }
    assert validate_project(project) == []


def test_m26_operational_release_acceptance_manifest_has_complete_evidence():
    manifest = yaml.safe_load((ROOT / "conformance" / "operational-workflows-release-acceptance-v0.1.yaml").read_text())
    assert manifest["immutableInputsOnly"] is True
    assert manifest["useCases"] == ["UC-10", "UC-11", "UC-12"]
    assert [item["id"] for item in manifest["acceptance"]] == [f"A26-{index:02d}" for index in range(1, 11)]
    assert all((ROOT / item["evidence"]).is_file() for item in manifest["acceptance"])


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
            "version": "timeline/v0.3",
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
                "version": "timeline/v0.3",
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
        result = schedule({"version": "timeline/v0.3", "project": {"id": case["name"]}, "objects": objects, "relations": relations})
        assert result.ok, case["name"]
        assert result.placements["target"]["start"] == _date(case["expected_min"]), case["name"]


def test_calendar_placement_cases_execute_through_scheduler():
    calendar = {"working_days": ["mon", "tue", "wed", "thu", "fri"], "exceptions": [{"date": "2026-10-12", "working": False}]}
    project = {
        "version": "timeline/v0.3",
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


def test_cycle_fixture_cases_report_the_required_distinction():
    def cycle(lag):
        return {
            "version": "timeline/v0.3",
            "project": {"id": f"cycle-{lag}"},
            "objects": {
                "A": {"type": "task", "schedule": {"mode": "scheduled", "amount": "1d"}},
                "B": {"type": "task", "schedule": {"mode": "scheduled", "amount": "1d"}},
            },
            "relations": [
                {"type": "dependency", "from": {"object": "A", "endpoint": "start"}, "to": {"object": "B", "endpoint": "start"}, "lag": lag},
                {"type": "dependency", "from": {"object": "B", "endpoint": "start"}, "to": {"object": "A", "endpoint": "start"}, "lag": "0d"},
            ],
        }

    assert {item.id for item in schedule(cycle("0d")).diagnostics} == {"E_UNSUPPORTED_CYCLE"}
    assert {item.id for item in schedule(cycle("1d")).diagnostics} == {"E_UNSATISFIABLE_DEPENDENCIES"}


def test_diagnostic_fixture_cases_have_stable_ids():
    missing_calendar = {
        "version": "timeline/v0.3",
        "project": {"id": "missing-calendar"},
        "objects": {"task": {"type": "task", "schedule": {"mode": "scheduled", "amount": "1wd", "anchor": {"start": "2026-10-01"}}}},
    }
    unknown_reference = {
        "version": "timeline/v0.3",
        "project": {"id": "unknown-reference"},
        "objects": {"task": {"type": "task", "schedule": {"mode": "fixed", "start": "2026-10-01", "end": "2026-10-02"}}},
        "relations": [{"type": "dependency", "from": {"object": "missing", "endpoint": "end"}, "to": {"object": "task", "endpoint": "start"}}],
    }
    empty_span = {
        "version": "timeline/v0.3",
        "project": {"id": "empty-span"},
        "objects": {"task": {"type": "task", "schedule": {"mode": "fixed", "start": "2026-10-01", "end": "2026-10-01"}}},
    }
    assert {item.id for item in validate_project(missing_calendar)} == {"E_CALENDAR_REQUIRED"}
    assert {item.id for item in validate_project(unknown_reference)} == {"E_REFERENCE"}
    assert {item.id for item in validate_project(empty_span)} == {"E_INVALID_SPAN"}


def test_authority_fixture_cases_execute_through_scheduler():
    fixed_target = {
        "version": "timeline/v0.3",
        "project": {"id": "fixed-target"},
        "objects": {
            "source": {"type": "task", "schedule": {"mode": "fixed", "start": "2026-10-01", "end": "2026-10-10"}},
            "target": {"type": "task", "schedule": {"mode": "fixed", "start": "2026-10-10", "end": "2026-10-11"}},
        },
        "relations": [{"type": "dependency", "from": {"object": "source", "endpoint": "end"}, "to": {"object": "target", "endpoint": "start"}, "lag": "2d"}],
    }
    anchored_target = {
        "version": "timeline/v0.3",
        "project": {"id": "anchored-target"},
        "objects": {
            "source": {"type": "task", "schedule": {"mode": "fixed", "start": "2026-10-01", "end": "2026-10-12"}},
            "target": {"type": "task", "schedule": {"mode": "scheduled", "amount": "5d", "anchor": {"start": "2026-10-10"}}},
        },
        "relations": [{"type": "dependency", "from": {"object": "source", "endpoint": "end"}, "to": {"object": "target", "endpoint": "start"}, "lag": "0d"}],
    }
    assert {item.id for item in schedule(fixed_target).diagnostics} == {"E_FIXED_TARGET_VIOLATION"}
    assert {item.id for item in schedule(anchored_target).diagnostics} == {"E_CONTRADICTORY_BOUNDS"}
