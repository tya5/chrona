"""The ``inverse`` command in apply_project_command results: apply, then apply the inverse, restores the file (#1892 row 2, item 4)."""
from __future__ import annotations

import copy
import json

import pytest

from chrona.resources import schema_validator

from tests.unit.chrona.app.test_agent_project_structure_commands import _call, _created, _relation

FIXED = {"type": "task", "schedule": {"mode": "fixed-span", "start": "2026-11-02", "end": "2026-11-06"}}
SCHEDULED = {"type": "task", "schedule": {"mode": "scheduled", "amount": "5wd"}}
NOTE = {"kind": "risk", "text": "Vendor slip", "anchor": {"object": "build"}}
PERIOD = {"start": "2026-11-02", "end": "2026-11-13", "title": "Launch window"}
SCENARIO = {"title": "Slip", "objects": {"build": {"title": "Build slipped"}}}
EXTENSION = {"packageId": "team.delivery", "resource": {"profiles": {}}}

RICH = {
    "version": "timeline/v0.7",
    "project": {"id": "launch", "title": "Launch", "calendar": "team"},
    "calendars": {"team": {"working_days": ["mon", "tue", "wed", "thu", "fri"]},
                  "spare": {"working_days": ["mon", "tue"]},
                  "ops": {"working_days": ["mon", "tue", "wed", "thu", "fri", "sat"]}},
    "entities": {"ana": {"type": "person"}, "bo": {"type": "person"}, "cy": {"type": "person"}},
    "objects": {"design": copy.deepcopy(FIXED), "spare-task": copy.deepcopy(SCHEDULED),
                "build": copy.deepcopy(SCHEDULED), "audit": {**copy.deepcopy(SCHEDULED), "calendar": "ops"}},
    "relations": [_relation(id="r1"), {**_relation(), "to": {"object": "audit", "endpoint": "start"}},
                  {**_relation(id="r3"), "to": {"object": "spare-task", "endpoint": "start"}}],
    "fieldRoles": {"responsible": "owner", "phase": "stage"},
    "annotations": {"n1": NOTE, "n2": {**NOTE, "text": "Second"}},
    "periods": {"p1": copy.deepcopy(PERIOD), "p2": {**PERIOD, "title": "Second"}},
    "extensions": [copy.deepcopy(EXTENSION), {**copy.deepcopy(EXTENSION), "packageId": "team.other"}],
    "scenarios": {"s1": copy.deepcopy(SCENARIO), "s2": {"title": "Second"}},
}
SOLE = {  # every optional member holds one entry, so removing it deletes the member from the middle of the file
    "version": "timeline/v0.7",
    "project": {"id": "launch"},
    "calendars": {"only": {"working_days": ["mon", "tue"]}},
    "entities": {"solo": {"type": "person"}},
    "objects": {"design": copy.deepcopy(FIXED), "build": copy.deepcopy(FIXED)},
    "relations": [_relation()],
    "fieldRoles": {"responsible": "owner"},
    "annotations": {"only": NOTE},
    "periods": {"only": copy.deepcopy(PERIOD)},
    "extensions": [copy.deepcopy(EXTENSION)],
    "scenarios": {"only": copy.deepcopy(SCENARIO)},
}
MINIMAL = {"version": "timeline/v0.7", "project": {"id": "launch"}, "objects": {"design": copy.deepcopy(FIXED), "build": copy.deepcopy(FIXED)}}

CASES = [
    ("setObject replace", RICH, "setObject", {"id": "spare-task", "object": {**SCHEDULED, "title": "Renamed"}}),
    ("setObject new", RICH, "setObject", {"id": "ship", "object": copy.deepcopy(FIXED)}),
    ("setObject new before", RICH, "setObject", {"id": "ship", "object": copy.deepcopy(FIXED), "before": "build"}),
    ("removeObject middle", {**RICH, "relations": RICH["relations"][:2]}, "removeObject", {"id": "spare-task"}),
    ("removeObject last", {**RICH, "relations": [RICH["relations"][0], RICH["relations"][2]]}, "removeObject", {"id": "audit"}),
    ("setRelation replace by id", RICH, "setRelation", {"relation": {**_relation(id="r1"), "lag": "2d"}}),
    ("setRelation new with id", RICH, "setRelation", {"relation": _relation(id="r4", type="dependency") | {"to": {"object": "audit", "endpoint": "end"}}}),
    ("setRelation new without id", RICH, "setRelation", {"relation": {**_relation(), "to": {"object": "build", "endpoint": "end"}}}),
    ("setRelation new at index", RICH, "setRelation", {"relation": _relation(id="r0"), "index": 1}),
    ("setRelation identical (no change)", RICH, "setRelation", {"relation": RICH["relations"][1]}),
    ("removeRelation by id", RICH, "removeRelation", {"id": "r1"}),
    ("removeRelation by relation", RICH, "removeRelation", {"relation": RICH["relations"][1]}),
    ("removeRelation sole", SOLE, "removeRelation", {"relation": SOLE["relations"][0]}),
    ("setCalendar replace", RICH, "setCalendar", {"id": "spare", "calendar": {"working_days": ["fri"]}}),
    ("setCalendar new", RICH, "setCalendar", {"id": "night", "calendar": {"working_days": ["sat"]}}),
    ("setCalendar new in a new member", MINIMAL, "setCalendar", {"id": "night", "calendar": {"working_days": ["sat"]}}),
    ("removeCalendar middle", RICH, "removeCalendar", {"id": "spare"}),
    ("removeCalendar sole", SOLE, "removeCalendar", {"id": "only"}),
    ("setEntity replace", RICH, "setEntity", {"id": "bo", "entity": {"type": "person", "title": "Bo"}}),
    ("setEntity new", RICH, "setEntity", {"id": "di", "entity": {"type": "person"}}),
    ("setEntity new in a new member", MINIMAL, "setEntity", {"id": "di", "entity": {"type": "person"}}),
    ("removeEntity middle", RICH, "removeEntity", {"id": "bo"}),
    ("removeEntity sole", SOLE, "removeEntity", {"id": "solo"}),
    ("setFieldRole replace", RICH, "setFieldRole", {"role": "responsible", "binding": "lead"}),
    ("setFieldRole new", {**RICH, "fieldRoles": {"phase": "stage"}}, "setFieldRole", {"role": "responsible", "binding": "owner"}),
    ("setFieldRole new in a new member", MINIMAL, "setFieldRole", {"role": "phase", "binding": "stage"}),
    ("removeFieldRole first", RICH, "removeFieldRole", {"role": "responsible"}),
    ("removeFieldRole sole", SOLE, "removeFieldRole", {"role": "responsible"}),
    ("setAnnotation replace", RICH, "setAnnotation", {"id": "n1", "annotation": {**NOTE, "text": "Changed"}}),
    ("setAnnotation new", RICH, "setAnnotation", {"id": "n3", "annotation": NOTE}),
    ("setAnnotation new in a new member", MINIMAL, "setAnnotation", {"id": "n3", "annotation": {**NOTE, "anchor": {"object": "design"}}}),
    ("removeAnnotation first", RICH, "removeAnnotation", {"id": "n1"}),
    ("removeAnnotation sole", SOLE, "removeAnnotation", {"id": "only"}),
    ("setPeriod replace", RICH, "setPeriod", {"id": "p1", "period": {**PERIOD, "title": "Changed"}}),
    ("setPeriod new", RICH, "setPeriod", {"id": "p3", "period": copy.deepcopy(PERIOD)}),
    ("setPeriod new before", RICH, "setPeriod", {"id": "p3", "period": copy.deepcopy(PERIOD), "before": "p2"}),
    ("setPeriod new in a new member", MINIMAL, "setPeriod", {"id": "p3", "period": copy.deepcopy(PERIOD)}),
    ("removePeriod first", RICH, "removePeriod", {"id": "p1"}),
    ("removePeriod sole", SOLE, "removePeriod", {"id": "only"}),
    ("setScenario replace", RICH, "setScenario", {"id": "s1", "scenario": {"title": "Changed"}}),
    ("setScenario new", RICH, "setScenario", {"id": "s3", "scenario": copy.deepcopy(SCENARIO)}),
    ("setScenario new in a new member", MINIMAL, "setScenario", {"id": "s3", "scenario": copy.deepcopy(SCENARIO)}),
    ("removeScenario first", RICH, "removeScenario", {"id": "s1"}),
    ("removeScenario sole", SOLE, "removeScenario", {"id": "only"}),
    ("setExtension replace", RICH, "setExtension", {"packageId": "team.other", "extension": {**EXTENSION, "packageId": "team.other", "resource": {"profiles": {"x": {}}}}}),
    ("setExtension new", RICH, "setExtension", {"packageId": "team.third", "extension": {**EXTENSION, "packageId": "team.third"}}),
    ("setExtension new at index", RICH, "setExtension", {"packageId": "team.third", "extension": {**EXTENSION, "packageId": "team.third"}, "index": 1}),
    ("setExtension new in a new member", MINIMAL, "setExtension", {"packageId": "team.third", "extension": {**EXTENSION, "packageId": "team.third"}}),
    ("removeExtension first", RICH, "removeExtension", {"packageId": "team.delivery"}),
    ("removeExtension sole", SOLE, "removeExtension", {"packageId": "team.delivery"}),
    ("setProjectMeta replace title", RICH, "setProjectMeta", {"title": "Launch 2"}),
    ("setProjectMeta add title", SOLE, "setProjectMeta", {"title": "Launch"}),
    ("setProjectMeta remove title", RICH, "setProjectMeta", {"title": None}),
    ("setProjectMeta remove title and change calendar", RICH, "setProjectMeta", {"title": None, "calendar": "ops"}),
    ("setProjectMeta remove an absent title", SOLE, "setProjectMeta", {"title": None}),
]


def _command(command_id: str, command_type: str, payload: dict, base: str) -> dict:
    return {"version": "chrona/project-command/v0.1", "commandId": command_id, "type": command_type,
            "target": {"kind": "project", "path": "project.yaml"}, "baseRevision": base, "payload": payload}


def _run(root, command: dict) -> dict:
    result = _call(root, "apply_project_command", {"project": "project.yaml", "command": command}).structured
    return result["projectResult"]


@pytest.mark.parametrize(("label", "project", "command_type", "payload"), CASES, ids=[case[0] for case in CASES])
def test_apply_then_inverse_restores_the_exact_file_bytes(tmp_path, label, project, command_type, payload):
    start_revision = _created(tmp_path, json.loads(json.dumps(project)))
    path = tmp_path / "project.yaml"
    start = path.read_bytes()
    first = _run(tmp_path, _command("edit-1", command_type, copy.deepcopy(payload), start_revision))
    assert first["status"] == "accepted", first
    assert list(schema_validator("project-command-result-v0.1.schema.yaml").iter_errors(first)) == []
    after = path.read_bytes()
    inverse = first["inverse"]
    assert inverse["baseRevision"] == first["resultRevision"] and inverse["target"] == {"kind": "project", "path": "project.yaml"}
    assert list(schema_validator("project-command-v0.1.schema.yaml").iter_errors(inverse)) == []
    undone = _run(tmp_path, inverse)  # the returned object is a complete request: no field is added or changed
    assert undone["status"] == "accepted", undone
    assert path.read_bytes() == start
    assert undone["resultRevision"] == start_revision
    # the inverse of the inverse is the original edit again (redo), byte for byte
    redone = _run(tmp_path, undone["inverse"])
    assert redone["status"] == "accepted" and path.read_bytes() == after
    assert redone["resultRevision"] == first["resultRevision"]


def test_the_inverse_is_bound_to_the_result_revision_and_stale_once_the_file_moves_on(tmp_path):
    revision = _created(tmp_path, json.loads(json.dumps(RICH)))
    first = _run(tmp_path, _command("a", "setProjectMeta", {"title": "One"}, revision))
    _run(tmp_path, _command("b", "setProjectMeta", {"title": "Two"}, first["resultRevision"]))
    stale = _run(tmp_path, first["inverse"])
    assert stale["status"] == "rejected" and stale["diagnostics"][0]["code"] == "E_AUTHORING_BASE_REVISION"


def test_a_replayed_result_keeps_the_same_inverse_and_a_rejection_has_none(tmp_path):
    revision = _created(tmp_path, json.loads(json.dumps(RICH)))
    command = _command("a", "setEntity", {"id": "di", "entity": {"type": "person"}}, revision)
    first = _run(tmp_path, command)
    replay = _run(tmp_path, copy.deepcopy(command))
    assert replay["replayed"] is True and replay["inverse"] == first["inverse"]
    rejected = _run(tmp_path, _command("b", "removeObject", {"id": "ghost"}, first["resultRevision"]))
    assert rejected["status"] == "rejected" and "inverse" not in rejected


def test_placement_members_are_checked_against_the_file(tmp_path):
    revision = _created(tmp_path, json.loads(json.dumps(MINIMAL)))
    path = tmp_path / "project.yaml"
    start = path.read_bytes()
    for command_type, payload, pointer in (
        ("setObject", {"id": "ship", "object": FIXED, "before": "ghost"}, "/payload/before"),
        ("setRelation", {"relation": _relation(id="r1"), "index": 5}, "/payload/index"),
        ("setEntity", {"id": "ana", "entity": {"type": "person"}, "memberBefore": "ghost"}, "/payload/memberBefore"),
        ("setProjectMeta", {"title": "T", "order": ["id", "ghost"]}, "/payload/order"),
    ):
        rejected = _run(tmp_path, _command("p-" + command_type, command_type, payload, revision))
        assert rejected["status"] == "rejected", (command_type, rejected)
        assert rejected["diagnostics"][0]["detail"].startswith(pointer)
    assert path.read_bytes() == start


def test_an_explicit_placement_puts_a_new_key_where_asked(tmp_path):
    revision = _created(tmp_path, json.loads(json.dumps(MINIMAL)))
    moved = _run(tmp_path, _command("p1", "setObject", {"id": "ship", "object": FIXED, "before": "build"}, revision))
    assert moved["status"] == "accepted"
    import yaml
    assert list(yaml.safe_load((tmp_path / "project.yaml").read_text(encoding="utf-8"))["objects"]) == ["design", "ship", "build"]
    placed = _run(tmp_path, _command("p2", "setEntity", {"id": "ana", "entity": {"type": "person"}, "memberBefore": "objects"}, moved["resultRevision"]))
    assert placed["status"] == "accepted"
    assert list(yaml.safe_load((tmp_path / "project.yaml").read_text(encoding="utf-8"))) == ["version", "project", "entities", "objects"]
