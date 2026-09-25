from copy import deepcopy

import pytest

from chrona.core.scenarios import ScenarioError, resolve_scenario
from chrona.scheduling.scheduler import schedule, schedule_scenario


def _project():
    return {"version": "timeline/v0.7", "project": {"id": "demo"}, "objects": {
        "tvac": {"type": "task", "schedule": {"mode": "fixed-span", "start": "2026-01-01", "end": "2026-01-05"}},
        "launch": {"type": "task", "schedule": {"mode": "scheduled", "amount": "1d"}},
    }, "relations": [{"id": "tvac-launch", "type": "dependency", "from": {"object": "tvac", "endpoint": "end"}, "to": {"object": "launch", "endpoint": "start"}}],
    "scenarios": {"slip": {"title": "TVAC slip", "objects": {"tvac": {"schedule": {"end": "2026-01-12"}}}}}}


def test_resolve_scenario_merges_recursively_is_deterministic_and_does_not_mutate_base():
    project = _project()
    original = deepcopy(project)
    first, second = resolve_scenario(project, "slip"), resolve_scenario(project, "slip")
    assert first.project["objects"]["tvac"]["schedule"]["start"] == "2026-01-01"
    assert first.project["objects"]["tvac"]["schedule"]["end"] == "2026-01-12"
    assert first.provenance == second.provenance and project == original
    assert schedule(first.project).ok
    resolved, result = schedule_scenario(project, "slip")
    assert resolved.provenance == first.provenance and result.ok


def test_resolve_scenario_rejects_unknown_or_invalid_derived_state_with_scenario_path():
    with pytest.raises(ScenarioError, match="E_SCENARIO_NOT_FOUND"):
        resolve_scenario(_project(), "missing")
    project = _project()
    project["scenarios"]["broken"] = {"objects": {"tvac": None}}
    with pytest.raises(ScenarioError, match="E_SCENARIO_INVALID") as error:
        resolve_scenario(project, "broken")
    assert error.value.diagnostic.path.startswith("/scenarios/broken")
