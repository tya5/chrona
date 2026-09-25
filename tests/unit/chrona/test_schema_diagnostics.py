import jsonschema

from chrona.core.validation import validate_project
from chrona.schema_diagnostics import explain_all_errors, explain_errors


def _violation(schema, value):
    return explain_errors(jsonschema.Draft202012Validator(schema).iter_errors(value))


def test_enum_explanation_has_a_pointer_and_ordered_allowed_values():
    violation = _violation({"type": "object", "properties": {"side": {"enum": ["above", "below"]}}}, {"side": "inside"})

    assert violation.pointer == "/side"
    assert violation.rule == "enum"
    assert violation.expected == ("'above'", "'below'")
    assert violation.message == "expected one of 'above', 'below'"


def test_unknown_property_explanation_suggests_one_close_declared_name():
    violation = _violation(
        {"type": "object", "additionalProperties": False, "properties": {"visibility": {"type": "boolean"}}},
        {"visiblity": True},
    )

    assert violation.pointer == "/"
    assert violation.rule == "additionalProperties"
    assert violation.message == "unexpected property 'visiblity'; did you mean 'visibility'?"


def test_explain_all_errors_keeps_every_leaf_in_stable_pointer_order():
    schema = {"type": "object", "properties": {
        "alpha": {"enum": ["a"]}, "beta": {"type": "integer"},
    }}
    errors = tuple(jsonschema.Draft202012Validator(schema).iter_errors({"alpha": "wrong", "beta": "wrong"}))

    all_errors = explain_all_errors(errors, resource_kind="view", resource_identity="demo")

    assert [(item.pointer, item.rule, item.resource_kind, item.resource_identity) for item in all_errors] == [
        ("/alpha", "enum", "view", "demo"), ("/beta", "type", "view", "demo"),
    ]


def test_explain_all_errors_flattens_union_wrappers_without_changing_legacy_explanation():
    schema = {"oneOf": [
        {"type": "object", "required": ["mode"], "properties": {"mode": {"const": "fixed-point"}}},
        {"type": "object", "required": ["amount"], "properties": {"amount": {"type": "integer"}}},
    ]}
    errors = tuple(jsonschema.Draft202012Validator(schema).iter_errors({"mode": "wrong"}))

    all_errors = explain_all_errors(errors)

    assert all(item.rule != "union" for item in all_errors)
    assert {item.rule for item in all_errors} == {"const", "required"}
    assert explain_errors(errors).rule == "union"


def test_tagged_union_explanation_names_the_available_tags_once():
    violation = _violation(
        {"oneOf": [
            {"type": "object", "required": ["mode", "at"], "properties": {"mode": {"const": "fixed-point"}}},
            {"type": "object", "required": ["mode", "amount"], "properties": {"mode": {"const": "scheduled"}}},
        ]},
        {"mode": "fixed"},
    )

    assert violation.pointer == "/"
    assert violation.rule == "union"
    assert violation.expected == ("mode='fixed-point'", "mode='scheduled'")
    assert violation.message == "expected one permitted form: mode='fixed-point'; mode='scheduled'"


def test_key_shape_union_explanation_names_legal_required_property_forms():
    violation = _violation(
        {"oneOf": [
            {"type": "object", "required": ["field"], "properties": {"field": {"type": "string"}}},
            {"type": "object", "required": ["facet"], "properties": {"facet": {"type": "string"}}},
        ]},
        {"unknown": "x"},
    )

    assert violation.pointer == "/"
    assert violation.rule == "union"
    assert violation.expected == ("properties field", "properties facet")


def test_core_validation_uses_the_shared_explanation_and_pointer():
    diagnostics = validate_project({"version": "timeline/v0.4", "project": {"id": "demo"}})

    assert len(diagnostics) == 1
    assert diagnostics[0].id == "E_SCHEMA"
    assert diagnostics[0].path == "/version"
    assert diagnostics[0].message == "expected exactly 'timeline/v0.7'"


def test_violation_retains_explicit_ingress_context():
    violation = _violation({"type": "string"}, 1)
    assert violation.resource_kind is None
    assert violation.resource_identity is None
    contextual = explain_errors(
        jsonschema.Draft202012Validator({"type": "string"}).iter_errors(1),
        resource_kind="project", resource_identity="demo",
    )
    assert (contextual.resource_kind, contextual.resource_identity) == ("project", "demo")


def test_project_v06_rejects_removed_fixed_mode_without_a_compatibility_path():
    project = {
        "version": "timeline/v0.7",
        "project": {"id": "demo"},
        "objects": {"task": {"type": "task", "schedule": {"mode": "fixed", "at": "2026-09-23"}}},
    }

    diagnostics = validate_project(project)

    assert len(diagnostics) == 1
    assert diagnostics[0].id == "E_SCHEMA"
    assert diagnostics[0].path == "/objects/task/schedule"
    assert "fixed-point" in diagnostics[0].message
    assert "fixed-span" in diagnostics[0].message
