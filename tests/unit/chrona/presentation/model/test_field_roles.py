from dataclasses import FrozenInstanceError

import pytest

from chrona.presentation.model.field_roles import FieldRead, FieldRoleBindings


def test_bindings_resolve_each_source_projects_role_without_rewriting_fields():
    raw_fields = {"owner": "team-a", "phase": "design"}
    primary = FieldRoleBindings.from_project({
        "fieldRoles": {"responsible": "owner", "phase": "phase"},
    })
    snapshot = FieldRoleBindings.from_project({
        "fieldRoles": {"responsible": "team", "phase": "stage"},
    })

    assert primary.read(raw_fields, {"fieldRole": "responsible"}) == "team-a"
    assert snapshot.read(raw_fields, {"fieldRole": "responsible"}) is None
    assert snapshot.read({"team": "team-old", "stage": "review"},
                         {"fieldRole": "responsible"}) == "team-old"
    assert primary.read_result(raw_fields, {"fieldRole": "responsible"}) == FieldRead("owner", True, "team-a")
    assert snapshot.read_result({"team": "team-old"}, {"fieldRole": "responsible"}) == FieldRead(
        "team", True, "team-old")
    assert raw_fields == {"owner": "team-a", "phase": "design"}


def test_undeclared_role_is_distinguishable_from_declared_role_with_missing_value():
    bindings = FieldRoleBindings.from_project({"fieldRoles": {"phase": "phase"}})

    assert bindings.field_for("responsible") is None
    assert bindings.read({"owner": "team-a"}, {"fieldRole": "responsible"}) is None
    assert bindings.field_for("phase") == "phase"
    assert bindings.read({}, {"fieldRole": "phase"}) is None
    assert bindings.read_result({}, {"fieldRole": "responsible"}) == FieldRead(None, False, None)
    assert bindings.read_result({}, {"fieldRole": "phase"}) == FieldRead("phase", False, None)


def test_presence_result_distinguishes_missing_from_explicit_null_and_is_frozen():
    bindings = FieldRoleBindings()

    missing = bindings.read_result({}, {"field": "risk"})
    explicit_null = bindings.read_result({"risk": None}, {"field": "risk"})

    assert missing == FieldRead("risk", False, None)
    assert explicit_null == FieldRead("risk", True, None)
    assert bindings.read({}, {"field": "risk"}) is None
    assert bindings.read({"risk": None}, {"field": "risk"}) is None
    with pytest.raises(FrozenInstanceError):
        explicit_null.present = False


def test_direct_field_reference_is_unchanged_and_does_not_read_entity_fields():
    bindings = FieldRoleBindings.from_project({
        "fieldRoles": {"responsible": "owner"},
    })

    assert bindings.read({"owner": "team-id", "team": "object-team"},
                         {"field": "team"}) == "object-team"
    assert bindings.read({"owner": "team-id"}, {"field": "owner"}) == "team-id"
    # Entity records are intentionally outside this API's Project object-field
    # lookup path; callers pass only the selected object's fields here.
    assert bindings.read({}, {"fieldRole": "responsible"}) is None


def test_presence_result_preserves_false_and_zero_values():
    bindings = FieldRoleBindings()
    fields = {"enabled": False, "count": 0}

    assert bindings.read_result(fields, {"field": "enabled"}) == FieldRead("enabled", True, False)
    assert bindings.read_result(fields, {"field": "count"}) == FieldRead("count", True, 0)
    assert bindings.read(fields, {"field": "enabled"}) is False
    assert bindings.read(fields, {"field": "count"}) == 0


def test_bindings_are_frozen_and_ignore_absent_project_declarations():
    raw_roles = {"responsible": "owner"}
    bindings = FieldRoleBindings.from_project({"fieldRoles": raw_roles})
    raw_roles["responsible"] = "changed"

    assert bindings.bindings == (("responsible", "owner"),)
    assert FieldRoleBindings.from_project({}).field_for("responsible") is None
