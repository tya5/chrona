"""Annotation, project-meta, entity and field-role removal commands of apply_project_command (#1892 row 1, item 3)."""
from __future__ import annotations

import copy

from chrona.resources import schema_validator

from tests.unit.chrona.app.test_agent_project_structure_commands import PROJECT, _apply, _call, _created, _saved

NOTE = {"kind": "risk", "text": "Vendor slip", "anchor": {"object": "build"}}


def _codes(result: dict) -> list[str]:
    return [row["code"] for row in result["projectResult"]["diagnostics"]] if "projectResult" in result else [row["code"] for row in result["diagnostics"]]


def _ok(result: dict) -> str:
    assert result["projectResult"]["status"] == "accepted", result
    return result["projectResult"]["resultRevision"]


def test_annotation_is_added_replaced_removed_and_must_anchor_on_an_object(tmp_path):
    revision = _created(tmp_path)
    missing = _apply(tmp_path, "a0", "setAnnotation", {"id": "n1", "annotation": {**NOTE, "anchor": {"object": "ghost"}}}, revision)
    assert missing["projectResult"]["status"] == "rejected"
    assert missing["projectResult"]["diagnostics"][0]["code"] == "E_PROJECT_OBJECT_MISSING"
    assert "/payload/annotation/anchor/object" in missing["projectResult"]["diagnostics"][0]["detail"]
    assert "annotations" not in _saved(tmp_path)
    revision = _ok(_apply(tmp_path, "a1", "setAnnotation", {"id": "n1", "annotation": NOTE}, revision))
    assert _saved(tmp_path)["annotations"] == {"n1": NOTE}
    revision = _ok(_apply(tmp_path, "a2", "setAnnotation", {"id": "n1", "annotation": {**NOTE, "text": "Slip confirmed"}}, revision))
    assert _saved(tmp_path)["annotations"]["n1"]["text"] == "Slip confirmed"
    bad = _apply(tmp_path, "a3", "setAnnotation", {"id": "n2", "annotation": {"kind": "risk"}}, revision)["projectResult"]
    assert bad["status"] == "rejected" and "/payload/annotation" in bad["diagnostics"][0]["detail"]
    # an anchored object cannot be removed from under its annotation
    blocked = _apply(tmp_path, "a4", "removeObject", {"id": "build"}, revision)["projectResult"]
    assert blocked["diagnostics"][0]["code"] == "E_PROJECT_OBJECT_REFERENCED" and "annotation 'n1'" in blocked["diagnostics"][0]["detail"]
    unknown = _apply(tmp_path, "a5", "removeAnnotation", {"id": "zz"}, revision)["projectResult"]
    assert unknown["diagnostics"][0]["code"] == "E_PROJECT_ANNOTATION_MISSING" and "n1" in unknown["diagnostics"][0]["detail"]
    revision = _ok(_apply(tmp_path, "a6", "removeAnnotation", {"id": "n1"}, revision))
    assert "annotations" not in _saved(tmp_path)
    assert _call(tmp_path, "validate_project", {"project": "project.yaml"}).structured["status"] == "ok"


def test_project_meta_sets_and_clears_the_header_but_never_the_id_or_an_unknown_calendar(tmp_path):
    revision = _created(tmp_path)
    revision = _ok(_apply(tmp_path, "m1", "setProjectMeta", {"title": "Launch plan", "calendar": "ops"}, revision))
    assert _saved(tmp_path)["project"] == {"id": "launch", "calendar": "ops", "title": "Launch plan"}
    before = (tmp_path / "project.yaml").read_bytes()
    for index, payload in enumerate(({"id": "other"}, {}, {"title": 3})):
        rejected = _apply(tmp_path, f"m2{index}", "setProjectMeta", payload, revision)
        assert rejected["status"] == "rejected" or rejected["projectResult"]["status"] == "rejected", rejected
    ghost = _apply(tmp_path, "m3", "setProjectMeta", {"calendar": "nope"}, revision)["projectResult"]
    assert ghost["status"] == "rejected" and "/payload/calendar" in ghost["diagnostics"][0]["detail"]
    assert (tmp_path / "project.yaml").read_bytes() == before
    no_default = _apply(tmp_path, "m4", "setProjectMeta", {"calendar": None}, revision)["projectResult"]
    assert no_default["status"] == "rejected" and no_default["diagnostics"][0]["code"] == "E_CALENDAR_REQUIRED"
    _ok(_apply(tmp_path, "m5", "setProjectMeta", {"title": None}, revision))
    assert _saved(tmp_path)["project"] == {"id": "launch", "calendar": "ops"}


def test_remove_entity_is_refused_while_a_field_names_it_and_remove_field_role_unbinds(tmp_path):
    project = copy.deepcopy(PROJECT)
    project["entities"] = {"ana": {"type": "person"}, "unused": {"type": "person"}}
    project["objects"]["build"]["fields"] = {"owner": "ana", "helpers": [{"who": "ana"}]}
    project["fieldRoles"] = {"responsible": "owner"}
    revision = _created(tmp_path, project)
    blocked = _apply(tmp_path, "e1", "removeEntity", {"id": "ana"}, revision)["projectResult"]
    assert blocked["diagnostics"][0]["code"] == "E_PROJECT_ENTITY_REFERENCED"
    assert "object 'build' (fields.owner)" in blocked["diagnostics"][0]["detail"] and "fields.helpers" in blocked["diagnostics"][0]["detail"]
    unknown = _apply(tmp_path, "e2", "removeEntity", {"id": "zz"}, revision)["projectResult"]
    assert unknown["diagnostics"][0]["code"] == "E_PROJECT_ENTITY_MISSING"
    revision = _ok(_apply(tmp_path, "e3", "removeEntity", {"id": "unused"}, revision))
    assert list(_saved(tmp_path)["entities"]) == ["ana"]
    gone = _apply(tmp_path, "r0", "removeFieldRole", {"role": "phase"}, revision)["projectResult"]
    assert gone["diagnostics"][0]["code"] == "E_PROJECT_FIELD_ROLE_MISSING" and "responsible" in gone["diagnostics"][0]["detail"]
    revision = _ok(_apply(tmp_path, "r1", "removeFieldRole", {"role": "responsible"}, revision))
    saved = _saved(tmp_path)
    assert "fieldRoles" not in saved and saved["objects"]["build"]["fields"]["owner"] == "ana"
    assert _call(tmp_path, "validate_project", {"project": "project.yaml"}).structured["status"] == "ok"


def test_results_replay_and_validate_against_the_result_schema(tmp_path):
    revision = _created(tmp_path)
    first = _apply(tmp_path, "z1", "setAnnotation", {"id": "n1", "annotation": NOTE}, revision)
    again = _apply(tmp_path, "z1", "setAnnotation", {"id": "n1", "annotation": NOTE}, revision)
    assert again["projectResult"]["replayed"] is True
    validator = schema_validator("project-command-result-v0.1.schema.yaml")
    rejected = _apply(tmp_path, "z2", "removeEntity", {"id": "none"}, first["projectResult"]["resultRevision"])
    assert not list(validator.iter_errors(rejected["projectResult"]))
