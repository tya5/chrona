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


_DATE_SCHEMA = {"type": "object", "properties": {"on": {"type": "string", "format": "date"}}}


def _format_violation(value, schema=_DATE_SCHEMA):
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker(["date"]))
    return explain_errors(validator.iter_errors(value))


def test_format_violation_names_the_format_and_never_echoes_the_value():
    secret = "2026-02-30-SECRET-VALUE"
    violation = _format_violation({"on": secret})

    assert violation.pointer == "/on"
    assert violation.rule == "format"
    assert violation.expected == ("YYYY-MM-DD calendar date",)
    assert violation.actual_kind == "string"
    assert violation.message == "expected a YYYY-MM-DD calendar date"
    assert secret not in violation.message
    assert "SECRET" not in repr(violation)


def test_format_violation_on_an_impossible_calendar_date():
    violation = _format_violation({"on": "2026-02-30"})

    assert (violation.rule, violation.pointer) == ("format", "/on")
    assert "2026-02-30" not in violation.message


def test_unknown_format_falls_back_to_the_declared_name_without_the_value():
    checker = jsonschema.FormatChecker()
    checker.checks("shouty")(lambda value: not isinstance(value, str) or value.isupper())
    schema = {"type": "string", "format": "shouty"}
    validator = jsonschema.Draft202012Validator(schema, format_checker=checker)

    violation = explain_errors(validator.iter_errors("quiet-value"))

    assert violation.rule == "format"
    assert violation.expected == ("value in format 'shouty'",)
    assert violation.message == "expected a value in format 'shouty'"
    assert "quiet-value" not in violation.message


def test_format_is_reported_before_a_pattern_failure_at_the_same_pointer():
    schema = {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$", "format": "date"}

    assert _format_violation("2026-13-45", schema).rule == "format"
    assert _format_violation("not a date", schema).rule == "format"


def test_format_violation_is_kept_by_explain_all_errors_in_pointer_order():
    validator = jsonschema.Draft202012Validator(
        {"type": "object", "properties": {"a": {"type": "integer"}, "on": {"format": "date"}}},
        format_checker=jsonschema.FormatChecker(["date"]),
    )

    violations = explain_all_errors(validator.iter_errors({"a": "x", "on": "2026-02-30"}))

    assert [(item.pointer, item.rule) for item in violations] == [("/a", "type"), ("/on", "format")]


def test_no_format_checker_means_no_format_violation():
    # The schema factory installs no format checker yet, so a format annotation asserts nothing.
    validator = jsonschema.Draft202012Validator(_DATE_SCHEMA)
    assert list(validator.iter_errors({"on": "2026-02-30"})) == []


# --------------------------------------------------------------------------------------------
# A union branch that only references a shared schema part explains like the inline branch (I662-S2f)
# --------------------------------------------------------------------------------------------

_INLINE_FR = {"type": "object", "required": ["fr"], "additionalProperties": False,
              "properties": {"fr": {"type": "number", "exclusiveMinimum": 0, "maximum": 1000000}}}
_PART_FR = {"description": "Positive fractional track size.", "$ref": "urn:chrona:common-v0.1#/$defs/fractionalTrack"}


def _union_schema(branch):
    return {"type": "object", "properties": {"width": {"oneOf": [
        {"enum": ["content", "fill"]}, branch,
        {"type": "object", "required": ["minmax"], "additionalProperties": False, "properties": {"minmax": {"type": "object"}}}]}}}


def _violation_with_parts(schema, value):
    from chrona.resources import validator_for_schema

    return explain_errors(validator_for_schema(schema).iter_errors(value))


def test_union_forms_follow_a_shared_part_reference_to_its_required_members():
    inline = _violation_with_parts(_union_schema(_INLINE_FR), {"width": {"zz": 1}})
    referenced = _violation_with_parts(_union_schema(_PART_FR), {"width": {"zz": 1}})

    assert inline.message == "expected one permitted form: properties fr; properties minmax"
    assert referenced == inline


def test_a_referenced_branch_without_the_part_lookup_would_lose_its_form(monkeypatch):
    # The mutation that proves the parity above is not vacuous: without the lookup the `$ref` branch has no `required`.
    import chrona.schema_diagnostics as diagnostics

    monkeypatch.setattr(diagnostics, "_shared_part_branch", lambda branch: branch)
    message = _violation_with_parts(_union_schema(_PART_FR), {"width": {"zz": 1}}).message

    assert message == "expected one permitted form: properties minmax"


def test_a_local_reference_branch_is_left_as_written():
    # Only a `urn:` part reference can be followed: the error carries no root document to resolve `#/...` against.
    schema = _union_schema({"$ref": "#/$defs/fr"})
    schema["$defs"] = {"fr": _INLINE_FR}

    assert _violation_with_parts(schema, {"width": {"zz": 1}}).message == "expected one permitted form: properties minmax"


def test_the_view_table_width_unions_explain_as_their_inlined_twin_did():
    # Both `fr` branches of View's table-column width now reference `fractionalTrack`; the union messages must not move.
    from jsonschema import Draft202012Validator
    from referencing import Resource

    from chrona.resources import dereferenced_schema, schema_document, schema_registry

    def site(schema, pointer):
        registry = schema_registry().with_resource(schema["$id"], Resource.from_contents(schema))
        return Draft202012Validator({"$ref": f"{schema['$id']}#{pointer}"}, registry=registry)

    adopted, twin = schema_document("view-v0.28.schema.yaml"), dereferenced_schema("view-v0.28.schema.yaml")
    base = "/allOf/1/properties/body/properties/tableColumns/items/properties/width"
    cases = (
        (base, [{"zz": 1}, {}, 5, "bad", None, [], {"fr": 0}, {"fr": "x"}, {"fr": 2000000}, {"minmax": 1}, {"minmax": {"min": "content"}},
                {"fr": 1, "extra": 1}, "content", {"fr": 2}]),
        (base + "/oneOf/2/properties/minmax/properties/max", [{"zz": 1}, {}, 5, "bad", None, {"fr": 0}, {"fr": "x"}, {"fr": 1, "extra": 1}, "fill", {"fr": 3}]),
    )
    messages = set()
    for pointer, values in cases:
        for value in values:
            results = []
            for schema in (adopted, twin):
                errors = list(site(schema, pointer).iter_errors(value))
                results.append(("valid",) if not errors else (explain_errors(errors), explain_all_errors(errors)))
            assert results[0] == results[1], (pointer, value)
            if results[0] != ("valid",):
                messages.add(results[0][0].message)
    assert "expected one permitted form: properties fr; properties minmax" in messages


def test_view_axis_fill_scale_is_closed_and_band_only():
    from jsonschema import Draft202012Validator
    from referencing import Resource

    from chrona.resources import schema_document, schema_registry

    schema = schema_document("view-v0.28.schema.yaml")
    registry = schema_registry().with_resource(schema["$id"], Resource.from_contents(schema))
    pointer = "/allOf/1/properties/body/properties/axis/properties/tiers/items"
    validator = Draft202012Validator({"$ref": f"{schema['$id']}#{pointer}"}, registry=registry)

    assert validator.is_valid({"unit": "quarter", "every": 1, "role": "band",
                               "fillScale": {"scale": "phase", "key": "interval", "containingTier": 0}})
    assert not validator.is_valid({"unit": "month", "every": 1, "role": "labels",
                                   "fillScale": {"scale": "phase", "key": "alternating"}})
    assert not validator.is_valid({"unit": "auto", "every": 1, "role": "band",
                                   "fillScale": {"scale": "phase", "key": "alternating"}})
    assert not validator.is_valid({"unit": "month", "every": 1, "role": "band",
                                   "fillScale": {"scale": "phase", "key": "alternating", "extra": True}})
    assert not validator.is_valid({"unit": "month", "every": 1, "role": "band",
                                   "fillScale": {"scale": "phase", "key": "other"}})
    assert not validator.is_valid({"unit": "month", "every": 1, "role": "band",
                                   "fillScale": {"scale": "phase", "key": "interval", "containingTier": -1}})
