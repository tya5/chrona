from types import SimpleNamespace

import pytest

from chrona.core.object_references import ObjectReferenceCatalog
from chrona.presentation.model.color_scale import ColorScaleError
from chrona.presentation.model.field_roles import FieldDescriptor, FieldRoleBindings
from chrona.presentation.model.style_fills import complete_style_fills
from chrona.presentation.model.style_rules import (
    OccurrenceStyleIndex,
    StyleFieldFact,
    StyleOccurrence,
    StyleOccurrenceKey,
    evaluate_style_rules,
    field_facts_for_item,
)
from chrona.presentation.style import (
    EncodingSource,
    StyleEncodingOutcome,
    StyleFieldEquals,
    StyleFieldSource,
    StyleRule,
    StyleSelector,
)


def _rule(*, scale="owners", domain="firstAppearance"):
    return StyleRule(
        "owner-fill", StyleSelector(),
        StyleEncodingOutcome("fill", StyleFieldSource(field_name="owner"), scale, domain),
        "/body/rules/owner-fill",
    )


def _occurrence(subject, source, fact):
    return StyleOccurrence(
        StyleOccurrenceKey(subject, source, "planned"), "planned", "mark",
        fields=(fact,),
    )


def _theme():
    return {"body": {
        "colorScales": {"owners": {"palette": ["first", "second"]}},
        "categorySlots": {"first": "#112233", "second": "#445566"},
    }}


def _complete(occurrences, rule=None):
    rule = rule or _rule()
    intents = OccurrenceStyleIndex(evaluate_style_rules((rule,), occurrences))
    return complete_style_fills(
        intents, occurrences, theme=_theme(),
        encoding_sources={rule.rule_id: EncodingSource(
            "style", "style-resource", rule.source_ref + "/then/encode", rule.rule_id,
        )},
    )


def test_style_fact_keeps_reference_id_and_detaches_title_and_identity():
    project = {
        "project": {"id": "plan"},
        "entities": {"team-a": {"type": "team", "title": "Aiko"}},
        "objects": {"task": {"type": "task"}},
    }
    bindings = FieldRoleBindings.from_project(
        project,
        object_descriptors={"task": (
            FieldDescriptor("owner", "objectReference", target_profiles=("team",)),
        )},
        reference_catalog=ObjectReferenceCatalog.from_project(project),
    )
    item = SimpleNamespace(object_id="task", fields={"owner": "team-a"}, field_bindings=bindings)

    (fact,) = field_facts_for_item(item)

    assert fact.value == "team-a"
    assert fact.reference_title == "Aiko"
    assert fact.reference_identity == ("plan", "entities", "team-a")
    assert fact.non_scalar_value is False


def test_style_reference_predicate_matches_title_not_raw_target_id():
    fact = StyleFieldFact(
        "owner", "objectReference", True, "team-a", reference_title="Aiko",
        reference_identity=("plan", "entities", "team-a"),
    )
    occurrence = _occurrence("task", "primary", fact)
    by_title = StyleRule("title", StyleSelector(fields=(
        StyleFieldEquals(StyleFieldSource(field_name="owner"), "Aiko"),
    )), _rule().outcome, "/body/rules/title")
    by_id = StyleRule("id", StyleSelector(fields=(
        StyleFieldEquals(StyleFieldSource(field_name="owner"), "team-a"),
    )), _rule().outcome, "/body/rules/id")

    assert evaluate_style_rules((by_title,), (occurrence,))[0].key == occurrence.key
    assert evaluate_style_rules((by_id,), (occurrence,)) == ()


def test_same_raw_reference_value_cannot_merge_distinct_namespace_targets_in_one_scale():
    occurrences = (
        _occurrence("task-a", "primary", StyleFieldFact(
            "owner", "objectReference", True, "x", reference_title="Aiko",
            reference_identity=("plan", "entities", "x"),
        )),
        _occurrence("task-b", "snapshot", StyleFieldFact(
            "owner", "objectReference", True, "x", reference_title="Aiko",
            reference_identity=("plan", "objects", "x"),
        )),
    )

    with pytest.raises(ColorScaleError) as caught:
        _complete(occurrences)

    assert caught.value.code == "E_PRESENTATION_SCALE_VALUE"
    assert "resolves to different reference targets" in caught.value.detail
    assert caught.value.source_ref == "/body/rules/owner-fill/then/encode"


@pytest.mark.parametrize("domain", ["firstAppearance", ("x",)])
def test_same_raw_reference_value_from_distinct_logical_projects_cannot_merge(domain):
    occurrences = (
        _occurrence("task-a", "primary", StyleFieldFact(
            "owner", "objectReference", True, "x", reference_title="Aiko",
            reference_identity=("plan-a", "entities", "x"),
        )),
        _occurrence("task-b", "snapshot", StyleFieldFact(
            "owner", "objectReference", True, "x", reference_title="Aiko",
            reference_identity=("plan-b", "entities", "x"),
        )),
    )

    with pytest.raises(ColorScaleError, match="different reference targets"):
        _complete(occurrences, _rule(domain=domain))


def test_same_namespace_reference_identity_with_title_change_keeps_one_scale_value():
    occurrences = (
        _occurrence("task-a", "primary", StyleFieldFact(
            "owner", "objectReference", True, "x", reference_title="Aiko",
            reference_identity=("plan", "entities", "x"),
        )),
        _occurrence("task-b", "snapshot", StyleFieldFact(
            "owner", "objectReference", True, "x", reference_title="Aiko Tanaka",
            reference_identity=("plan", "entities", "x"),
        )),
    )

    fills = _complete(occurrences)

    assert fills.scales[0].domain == ("x",)
    assert fills.get(occurrences[0].key) == fills.get(occurrences[1].key) == "#112233"


def test_present_non_scalar_is_not_treated_as_absent_or_null_for_encoding():
    occurrence = _occurrence("task", "primary", StyleFieldFact(
        "owner", "objectReference", True, None, cardinality="many",
        non_scalar_value=True, non_scalar_type="list",
    ))

    with pytest.raises(ColorScaleError) as caught:
        _complete((occurrence,))

    assert caught.value.code == "E_PRESENTATION_SCALE_VALUE"
    assert "valueType=list" in caught.value.detail


@pytest.mark.parametrize("value,value_type", [(["x"], "list"), ({"id": "x"}, "dict")])
@pytest.mark.parametrize("domain", ["firstAppearance", ("x",)])
def test_present_non_scalar_rejects_for_first_appearance_and_explicit_domains(value, value_type, domain):
    occurrence = _occurrence("task", "primary", StyleFieldFact(
        "owner", "string", True, None, non_scalar_value=True, non_scalar_type=value_type,
    ))
    rule = _rule(domain=domain)

    with pytest.raises(ColorScaleError) as caught:
        _complete((occurrence,), rule)

    assert caught.value.code == "E_PRESENTATION_SCALE_VALUE"
    assert f"valueType={value_type}" in caught.value.detail


@pytest.mark.parametrize("value,value_type", [(["x"], "list"), ({"id": "x"}, "dict")])
def test_field_fact_captures_present_nonscalar_shape_for_encoding_validation(value, value_type):
    bindings = FieldRoleBindings.from_project(
        {"project": {"id": "plan"}},
        object_descriptors={"task": (FieldDescriptor("owner", "string"),)},
    )
    item = SimpleNamespace(object_id="task", fields={"owner": value}, field_bindings=bindings)

    (fact,) = field_facts_for_item(item)

    assert fact.present is True
    assert fact.value is None
    assert fact.non_scalar_value is True
    assert fact.non_scalar_type == value_type


@pytest.mark.parametrize("present,value", [(False, None), (True, None)])
def test_missing_and_null_values_remain_unencoded_not_non_scalar_errors(present, value):
    occurrence = _occurrence("task", "primary", StyleFieldFact(
        "owner", "objectReference", present, value,
    ))

    fills = _complete((occurrence,))

    assert fills.get(occurrence.key) is None
