"""Global finish, zero-float driving paths and explicit calendar basis."""

from datetime import date
from pathlib import Path

import yaml

from chrona.scheduling.scheduler import schedule
from chrona.usecases.project_checks import schedule_project_mapping


def _project(objects, relations=(), **context):
    return {"version": "timeline/v0.7", "project": {"id": "analysis", **context},
            "objects": objects, "relations": list(relations)}


def _span(start, end):
    return {"type": "task", "schedule": {"mode": "fixed-span", "start": start, "end": end}}


def _edge(source, target, target_endpoint="start"):
    return {"type": "dependency", "from": {"object": source, "endpoint": "end"},
            "to": {"object": target, "endpoint": target_endpoint}, "lag": "0d"}


def test_issue_cpm_keeps_launch_slack_and_uses_one_global_finish():
    project = _project({
        "design": _span("2027-01-04", "2027-01-15"),
        "build": {"type": "task", "schedule": {"mode": "scheduled", "amount": "10wd"}},
        "launch": {"type": "gate", "schedule": {"mode": "fixed-point", "at": "2027-03-01"}},
        "docs": {"type": "task", "schedule": {"mode": "scheduled", "amount": "5wd"}},
        "campaign": _span("2027-02-01", "2027-02-05"),
        "survey": {"type": "task", "schedule": {"mode": "scheduled", "amount": "3wd"}},
    }, [_edge("design", "build"), _edge("build", "launch", "at"),
        _edge("design", "docs"), _edge("campaign", "survey")], calendar="office")
    project["calendars"] = {"office": {"working_days": ["mon", "tue", "wed", "thu", "fri"]}}
    result = schedule(project)
    assert result.ok
    analysis = result.analysis
    assert analysis.project_finish == date(2027, 3, 1)
    assert analysis.total_float["build"].value == 21
    # Weekdays strictly after Feb10 through Mar1, independently of latest-start arithmetic.
    early = result.placements["survey"]["end"]
    days = sum(date.fromordinal(n).weekday() < 5
               for n in range(early.toordinal() + 1, analysis.project_finish.toordinal() + 1))
    assert analysis.total_float["survey"].value == days == 13
    assert analysis.critical == frozenset()
    assert all(value.unit == "working-days" and value.calendar == "office"
               for value in analysis.total_float.values())


def test_zero_driving_chain_to_finish_remains_critical():
    project = _project({"root": _span("2027-01-01", "2027-01-02"),
                        "finish": {"type": "task", "schedule": {"mode": "scheduled", "amount": "2d"}},
                        "earlier": _span("2026-01-01", "2026-01-02")}, [_edge("root", "finish")])
    result = schedule(project)
    assert result.ok
    assert result.analysis.critical == frozenset({"root", "finish"})
    assert result.analysis.total_float["earlier"].value == 0


def test_isolated_fixed_finish_is_not_a_critical_path_but_movable_finish_is():
    fixed = _project({"root": _span("2027-01-01", "2027-01-02")})
    assert schedule(fixed).analysis.critical == frozenset()
    fixed["objects"]["root"]["schedule"] = {
        "mode": "scheduled", "amount": "1d", "constraints": {"start": {"min": "2027-01-01"}}}
    assert schedule(fixed).analysis.critical == frozenset({"root"})
    fixed["objects"]["root"]["schedule"] = {
        "mode": "scheduled", "amount": "1d", "anchor": {"start": "2027-01-01"}}
    assert schedule(fixed).analysis.critical == frozenset()


def test_serialized_units_follow_effective_calendar_not_amount_spelling():
    project = _project({"day": _span("2027-01-01", "2027-01-02"),
                        "work": {**_span("2027-01-01", "2027-01-02"), "calendar": "office"}})
    project["calendars"] = {"office": {"working_days": ["mon", "tue", "wed", "thu", "fri"]}}
    output = schedule_project_mapping(project).analysis["totalFloat"]
    assert output == {"day": {"value": 0, "unit": "calendar-days", "calendar": None},
                      "work": {"value": 0, "unit": "working-days", "calendar": "office"}}
    project["project"]["calendar"] = "office"
    assert schedule_project_mapping(project).analysis["totalFloat"]["day"]["calendar"] == "office"
    project["calendars"]["other"] = {"working_days": ["sat"]}
    project["project"]["calendar"] = "other"
    units = schedule_project_mapping(project).analysis["totalFloat"]
    assert units["day"]["calendar"] == "other"
    assert units["work"]["calendar"] == "office"


def test_critical_zero_and_path_invariant_over_every_conformance_project():
    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    checked = []
    for path in sorted((root / "conformance").rglob("*.yaml")):
        project = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(project, dict) or not str(project.get("version", "")).startswith("timeline/"):
            continue
        # This delivery fixture embeds its oracle beside the authored Project.
        if path.name == "implementation-delivery-roadmap-v0.1.yaml":
            project = {key: value for key, value in project.items() if key != "expectedPlacements"}
        result = schedule(project)
        assert result.ok, (path, result.diagnostics)
        analysis = result.analysis
        successors = {}
        for relation in project.get("relations", ()):
            successors.setdefault(relation["from"]["object"], []).append(relation["to"]["object"])
        for object_id in analysis.critical:
            assert analysis.total_float[object_id].value == 0
            visited, pending = set(), [object_id]
            while pending:
                current = pending.pop()
                if current not in visited:
                    visited.add(current)
                    pending.extend(successors.get(current, ()))
            assert any((result.placements[item].get("end") or result.placements[item].get("at"))
                       == analysis.project_finish for item in visited)
        checked.append(path.name)
    assert set(checked) == {"calendar.yaml", "semiconductor.yaml", "dependencies.yaml",
                            "implementation-delivery-roadmap-v0.1.yaml", "controller-x.yaml", "minimal.yaml"}
