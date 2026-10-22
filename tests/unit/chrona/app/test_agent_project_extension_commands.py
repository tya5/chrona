"""Extension, period and scenario commands of apply_project_command (#1920, #1892 row 1)."""
from __future__ import annotations

from tests.unit.chrona.app.test_agent_project_structure_commands import _apply, _call, _created, _saved

PROFILE = """version: chrona/profile/v0.3
packageId: team-delivery
contentIdentity: sha256:0000000000000000000000000000000000000000000000000000000000000000
requires: {projectFormat: timeline/v0.7}
profiles:
  work:
    extends: task
    fields:
      team: {type: enum, enumValues: [x, y], required: true}
"""
DECLARATION = {"packageId": "team-delivery", "path": "team.yaml", "revision": "git:0123456789abcdef0123456789abcdef01234567"}


def _ok(result: dict) -> str:
    assert result["projectResult"]["status"] == "accepted", result
    return result["projectResult"]["resultRevision"]


def _rejected(result: dict) -> dict:
    assert result["projectResult"]["status"] == "rejected", result
    return result["projectResult"]["diagnostics"][0]


def test_extension_period_and_scenario_commands_round_trip(tmp_path):
    (tmp_path / "team.yaml").write_text(PROFILE, encoding="utf-8")
    revision = _created(tmp_path)
    mismatch = _rejected(_apply(tmp_path, "e0", "setExtension", {"packageId": "other", "extension": DECLARATION}, revision))
    assert mismatch["code"] == "E_PROJECT_COMMAND" and "/payload/extension/packageId" in mismatch["detail"]
    missing_file = _rejected(_apply(tmp_path, "e1", "setExtension", {"packageId": "team-delivery", "extension": {**DECLARATION, "path": "nope.yaml"}}, revision))
    assert missing_file["code"] == "E_EXTENSION_UNRESOLVED" and "/payload/extension/path" in missing_file["detail"]
    assert "extensions" not in _saved(tmp_path)
    revision = _ok(_apply(tmp_path, "e2", "setExtension", {"packageId": "team-delivery", "extension": DECLARATION}, revision))
    assert _saved(tmp_path)["extensions"] == [DECLARATION]
    revision = _ok(_apply(tmp_path, "e3", "setObject", {"id": "typed", "object": {
        "type": "work", "fields": {"team": "x"}, "schedule": {"mode": "scheduled", "amount": "2wd"}}}, revision))
    blocked = _rejected(_apply(tmp_path, "e4", "removeExtension", {"packageId": "team-delivery"}, revision))
    assert blocked["code"] == "E_PROJECT_EXTENSION_REFERENCED" and "object 'typed'" in blocked["detail"]
    unknown = _rejected(_apply(tmp_path, "e5", "removeExtension", {"packageId": "zz"}, revision))
    assert unknown["code"] == "E_PROJECT_EXTENSION_MISSING" and "team-delivery" in unknown["detail"]
    revision = _ok(_apply(tmp_path, "e6", "setObject", {"id": "typed", "object": {
        "type": "task", "schedule": {"mode": "scheduled", "amount": "2wd"}}}, revision))
    revision = _ok(_apply(tmp_path, "e7", "removeExtension", {"packageId": "team-delivery"}, revision))
    assert "extensions" not in _saved(tmp_path)

    period = {"start": "2026-11-02", "end": {"object": "build", "endpoint": "end"}, "title": "Window"}
    ghost = _rejected(_apply(tmp_path, "p0", "setPeriod", {"id": "w", "period": {**period, "end": {"object": "ghost", "endpoint": "end"}}}, revision))
    assert "/payload/period/end/object" in ghost["detail"]
    revision = _ok(_apply(tmp_path, "p1", "setPeriod", {"id": "w", "period": period}, revision))
    blocked = _rejected(_apply(tmp_path, "p2", "removeObject", {"id": "build"}, revision))
    assert blocked["code"] == "E_PROJECT_OBJECT_REFERENCED" and "period 'w' (end)" in blocked["detail"]
    assert _rejected(_apply(tmp_path, "p3", "removePeriod", {"id": "zz"}, revision))["code"] == "E_PROJECT_PERIOD_MISSING"

    bad = _rejected(_apply(tmp_path, "s0", "setScenario", {"id": "x", "scenario": {"objects": {"ghost": None}}}, revision))
    assert bad["code"] == "E_SCENARIO_OBJECT_NOT_FOUND" and "/payload/scenario/objects/ghost" in bad["detail"]
    gone = _rejected(_apply(tmp_path, "s1", "setScenario", {"id": "x", "scenario": {"relations": {"remove": ["nope"]}}}, revision))
    assert gone["code"] == "E_SCENARIO_RELATION_NOT_FOUND" and "/payload/scenario/relations/remove" in gone["detail"]
    assert "scenarios" not in _saved(tmp_path)
    revision = _ok(_apply(tmp_path, "s2", "setRelation", {"relation": {
        "type": "dependency", "id": "d-b", "from": {"object": "design", "endpoint": "end"}, "to": {"object": "build", "endpoint": "start"}}}, revision))
    revision = _ok(_apply(tmp_path, "s3", "setScenario", {"id": "x", "scenario": {
        "title": "Drop", "objects": {"audit": None}, "relations": {"remove": ["d-b"]}}}, revision))
    assert _rejected(_apply(tmp_path, "s4", "removeRelation", {"id": "d-b"}, revision))["code"] == "E_PROJECT_RELATION_REFERENCED"
    assert _rejected(_apply(tmp_path, "s5", "removeObject", {"id": "audit"}, revision))["code"] == "E_PROJECT_OBJECT_REFERENCED"
    assert _rejected(_apply(tmp_path, "s6", "removeScenario", {"id": "zz"}, revision))["code"] == "E_PROJECT_SCENARIO_MISSING"
    revision = _ok(_apply(tmp_path, "s7", "removeScenario", {"id": "x"}, revision))
    assert "scenarios" not in _saved(tmp_path)
    assert _call(tmp_path, "validate_project", {"project": "project.yaml"}).structured["status"] == "ok"
