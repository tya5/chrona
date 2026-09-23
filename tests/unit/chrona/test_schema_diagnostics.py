import jsonschema

from chrona.core.validation import validate_project
from chrona.schema_diagnostics import explain_errors


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
    assert diagnostics[0].message == "expected exactly 'timeline/v0.5'"
