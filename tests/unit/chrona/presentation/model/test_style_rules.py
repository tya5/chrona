from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from chrona.presentation.model.style_rules import (
    OccurrenceStyleIntent,
    StyleEvaluationError,
    StyleFieldFact,
    StyleOccurrence,
    StyleOccurrenceKey,
    evaluate_style_rules,
)
from chrona.presentation.style import (
    StyleEncodingOutcome,
    StyleFieldEquals,
    StyleFieldSource,
    StyleLegend,
    StyleRoleOutcome,
    StyleRule,
    StyleSelector,
)


def _rule(rule_id: str, selector: StyleSelector, outcome, ref: str | None = None) -> StyleRule:
    return StyleRule(rule_id, selector, outcome, ref or f"/body/rules/{rule_id}")


def _occurrence(*, subject="task-1", source="primary", semantic="planned", purpose="planned",
                family="mark", roles=("planned", "critical"), comparison=None, column=None,
                fields=(), row="row-1", member="member-1", column_id="") -> StyleOccurrence:
    return StyleOccurrence(
        StyleOccurrenceKey(subject, source, semantic, row, member, column_id),
        purpose, family, roles, comparison, column, tuple(fields),
    )


def _field(name="risk", kind="enum", value="high", *, present=True, cardinality="one",
           enum_values=("low", "high"), aliases=()):
    return StyleFieldFact(name, kind, present, value, cardinality, enum_values, aliases)


def _fill(source: StyleFieldSource, *, scale="risk", domain=("low", "high"), legend=None, channel="fill"):
    return StyleEncodingOutcome(channel, source, scale, domain, legend)


def test_six_selector_intersection_matches_unseen_combination_and_uses_original_roles():
    occurrence = _occurrence(
        semantic="tableCell", purpose="table-cell", family="label", roles=("critical",),
        comparison="behind", column=(("comparisonFacet", "finishDelta"),),
        fields=(_field(aliases=("responsible",)),),
    )
    rule = _rule("unseen", StyleSelector(
        semantic="tableCell", purpose="table-cell", comparison_category="behind",
        column_source=(("comparisonFacet", "finishDelta"),), roles=("critical",),
        fields=(StyleFieldEquals(StyleFieldSource(field_role="responsible"), "high"),),
    ), StyleRoleOutcome("forecast-focus"))

    result = evaluate_style_rules((rule,), (occurrence,))

    assert result == (OccurrenceStyleIntent(
        occurrence.key, "forecast-focus", None, ("unseen",), ("unseen",), ()),)
    assert occurrence.original_roles == ("critical",)
    with pytest.raises(FrozenInstanceError):
        occurrence.purpose = "actual"


def test_source_specific_field_role_alias_and_repeated_subject_are_distinct_occurrences():
    first = _occurrence(source="primary", fields=(
        _field("risk", value="low", aliases=("responsible",)),
    ))
    second = _occurrence(source="scenario", fields=(
        _field("payload", value="high", aliases=("responsible",)),
    ))
    rule = _rule("risk-fill", StyleSelector(fields=(
        StyleFieldEquals(StyleFieldSource(field_role="responsible"), "high"),
    )), _fill(StyleFieldSource(field_role="responsible")))

    results = evaluate_style_rules((rule,), (first, second))

    assert tuple(item.key for item in results) == (second.key,)
    assert results[0].key.subject_id == first.key.subject_id == second.key.subject_id
    assert results[0].key.source_kind == "scenario"
    assert results[0].fill.source == StyleFieldSource(field_name="payload")


@pytest.mark.parametrize("value", [True, False])
def test_boolean_fact_does_not_match_numeric_literal(value):
    # A malformed upstream value must not make bool equal numeric 1 even when
    # the declared field type admitted the numeric literal.
    occurrence = _occurrence(fields=(StyleFieldFact("flag", "number", True, value),))
    rule = _rule("bool-number", StyleSelector(fields=(
        StyleFieldEquals(StyleFieldSource(field_name="flag"), 1),
    )), StyleRoleOutcome("flagged"))
    assert evaluate_style_rules((rule,), (occurrence,)) == ()


@pytest.mark.parametrize("fact", [
    StyleFieldFact("risk", "enum", True, None, enum_values=("low", "high")),
    StyleFieldFact("risk", "enum", False, "high", enum_values=("low", "high")),
])
def test_absent_and_null_facts_are_nonmatches_without_project_validation(fact):
    occurrence = _occurrence(fields=(fact,))
    rule = _rule("high", StyleSelector(fields=(
        StyleFieldEquals(StyleFieldSource(field_name="risk"), "high"),
    )), StyleRoleOutcome("high-risk"))
    assert evaluate_style_rules((rule,), (occurrence,)) == ()


def test_selector_field_is_admitted_even_when_no_occurrence_matches():
    rule = _rule("unknown", StyleSelector(fields=(
        StyleFieldEquals(StyleFieldSource(field_name="unknown"), "x"),
    )), StyleRoleOutcome("role"))
    with pytest.raises(StyleEvaluationError) as caught:
        evaluate_style_rules((rule,), ())
    assert caught.value.diagnostic_id == "E_STYLE_FACT_UNKNOWN"
    assert caught.value.source_ref.endswith("/when/fields/0")


@pytest.mark.parametrize("descriptor,literal", [
    (StyleFieldFact("n", "integer", False, None), "1"),
    (StyleFieldFact("n", "enum", False, None, enum_values=("a",)), "b"),
    (StyleFieldFact("n", "string", False, None, cardinality="many"), "a"),
])
def test_typed_predicate_rejects_incompatible_declared_type(descriptor, literal):
    rule = _rule("wrong", StyleSelector(fields=(
        StyleFieldEquals(StyleFieldSource(field_name="n"), literal),
    )), StyleRoleOutcome("role"))
    with pytest.raises(StyleEvaluationError) as caught:
        evaluate_style_rules((rule,), (), field_catalogue=(descriptor,))
    assert caught.value.diagnostic_id == "E_STYLE_FACT_TYPE"


def test_opaque_undeclared_field_is_not_admitted_as_a_when_predicate():
    opaque = StyleFieldFact("legacy-risk", None, False, None)
    rule = _rule("opaque", StyleSelector(fields=(
        StyleFieldEquals(StyleFieldSource(field_name="legacy-risk"), "high"),
    )), StyleRoleOutcome("risk"))
    with pytest.raises(StyleEvaluationError) as caught:
        evaluate_style_rules((rule,), (), field_catalogue=(opaque,))
    assert caught.value.diagnostic_id == "E_STYLE_FACT_UNKNOWN"


def test_resource_reference_is_not_an_admitted_scalar_predicate():
    descriptor = StyleFieldFact("resource", "resourceReference", False, None)
    rule = _rule("resource-ref", StyleSelector(fields=(
        StyleFieldEquals(StyleFieldSource(field_name="resource"), "theme:base"),
    )), StyleRoleOutcome("role"))
    with pytest.raises(StyleEvaluationError) as caught:
        evaluate_style_rules((rule,), (), field_catalogue=(descriptor,))
    assert caught.value.diagnostic_id == "E_STYLE_FACT_TYPE"


def test_equal_assignments_coalesce_ignore_legend_copy_and_sort_rule_ids():
    occurrence = _occurrence(fields=(_field(aliases=("responsible",)),))
    source = StyleFieldSource(field_role="responsible")
    rules = (
        _rule("z", StyleSelector(semantic="planned"),
              _fill(source, legend=StyleLegend("Risk by team"))),
        _rule("a", StyleSelector(purpose="planned"),
              _fill(StyleFieldSource(field_name="risk"), legend=StyleLegend("Other title"))),
        _rule("role", StyleSelector(roles=("critical",)), StyleRoleOutcome("review")),
    )

    result = evaluate_style_rules(rules, (occurrence,))[0]

    assert result.role == "review"
    assert result.fill == _fill(StyleFieldSource(field_name="risk"))
    assert result.matched_rule_ids == ("a", "role", "z")
    assert result.role_rule_ids == ("role",)
    assert result.fill_rule_ids == ("a", "z")


def test_conflicting_role_and_same_channel_encoding_fail_with_all_rule_ids():
    occurrence = _occurrence(fields=(
        _field("risk", aliases=("responsible",)),
        _field("severity", aliases=("responsible",)),
    ))
    rules = (
        _rule("role-a", StyleSelector(purpose="planned"), StyleRoleOutcome("red")),
        _rule("role-b", StyleSelector(semantic="planned"), StyleRoleOutcome("blue")),
    )
    with pytest.raises(StyleEvaluationError) as caught:
        evaluate_style_rules(rules, (occurrence,))
    assert caught.value.diagnostic_id == "E_STYLE_RULE_CONFLICT"
    assert caught.value.rule_ids == ("role-a", "role-b")
    assert caught.value.subject == occurrence.key
    with pytest.raises(StyleEvaluationError) as reversed_error:
        evaluate_style_rules(tuple(reversed(rules)), (occurrence,))
    assert reversed_error.value.source_ref == caught.value.source_ref
    assert reversed_error.value.rule_ids == caught.value.rule_ids

    conflict = (
        _rule("fill-a", StyleSelector(purpose="planned"), _fill(StyleFieldSource(field_name="risk"))),
        _rule("fill-b", StyleSelector(semantic="planned"), _fill(StyleFieldSource(field_name="severity"))),
    )
    with pytest.raises(StyleEvaluationError) as caught:
        evaluate_style_rules(conflict, (occurrence,))
    assert caught.value.diagnostic_id == "E_STYLE_RULE_CONFLICT"
    assert caught.value.rule_ids == ("fill-a", "fill-b")


def test_encoding_admits_known_opaque_and_unresolved_sources():
    opaque = StyleFieldFact("legacy-risk", None, False, None)
    occurrence = _occurrence(fields=(opaque,))
    accepted = _rule("legacy", StyleSelector(), _fill(StyleFieldSource(field_name="legacy-risk")))
    assert evaluate_style_rules((accepted,), (occurrence,))[0].fill.source == StyleFieldSource(field_name="legacy-risk")

    unknown = _rule("unknown-source", StyleSelector(), _fill(StyleFieldSource(field_name="absent")))
    assert evaluate_style_rules((unknown,), (occurrence,))[0].fill.source == StyleFieldSource(field_name="absent")


def test_legacy_encoding_keeps_missing_raw_source_as_occurrence_intent():
    occurrence = _occurrence(fields=())
    matched = _rule("missing-value", StyleSelector(semantic="planned"),
                    _fill(StyleFieldSource(field_name="legacy-risk")))
    unmatched = _rule("unmatched", StyleSelector(roles=("actual",)),
                      _fill(StyleFieldSource(field_name="not-declared")))

    intents = evaluate_style_rules((matched, unmatched), (occurrence,))

    assert len(intents) == 1
    assert intents[0].matched_rule_ids == ("missing-value",)
    assert intents[0].fill.source == StyleFieldSource(field_name="legacy-risk")


def test_occurrence_semantic_requires_its_bound_purpose_and_family():
    occurrence = _occurrence(semantic="forecast", purpose="planned", family="mark")
    with pytest.raises(StyleEvaluationError) as caught:
        evaluate_style_rules((), (occurrence,))
    assert caught.value.diagnostic_id == "E_STYLE_FACT_TYPE"

    forecast = _occurrence(semantic="forecast", purpose="forecast", family="mark")
    rule = _rule("forecast", StyleSelector(semantic="forecast", purpose="forecast"),
                 StyleRoleOutcome("forecast-focus"))
    assert evaluate_style_rules((rule,), (forecast,))[0].role == "forecast-focus"


def test_duplicate_occurrence_identity_is_rejected():
    occurrence = _occurrence()
    with pytest.raises(StyleEvaluationError) as caught:
        evaluate_style_rules((), (occurrence, occurrence))
    assert caught.value.diagnostic_id == "E_STYLE_RULE_CONFLICT"
    assert caught.value.subject == occurrence.key


@pytest.mark.parametrize("semantic,purpose,family,channel", [
    ("asOf", "as-of", "line", "fill"),
    ("planned", "planned", "mark", "stroke"),
])
def test_encoding_rejects_nonfill_or_nonfillable_target(semantic, purpose, family, channel):
    occurrence = _occurrence(semantic=semantic, purpose=purpose)
    occurrence = StyleOccurrence(occurrence.key, purpose, family, occurrence.original_roles)
    rule = _rule("not-fillable", StyleSelector(semantic=semantic),
                 _fill(StyleFieldSource(field_name="risk"), channel=channel))
    with pytest.raises(StyleEvaluationError) as caught:
        evaluate_style_rules((rule,), (occurrence,))
    assert caught.value.diagnostic_id == "E_STYLE_TARGET"
    with pytest.raises(StyleEvaluationError) as caught:
        evaluate_style_rules((rule,), ())
    assert caught.value.diagnostic_id == "E_STYLE_TARGET"


def test_invalid_semantic_and_purpose_fail_as_closed_vocabulary_facts():
    rule = _rule("bad", StyleSelector(semantic="invented"), StyleRoleOutcome("role"))
    with pytest.raises(StyleEvaluationError) as caught:
        evaluate_style_rules((rule,), ())
    assert caught.value.diagnostic_id == "E_STYLE_FACT_UNKNOWN"

    invalid_occurrence = _occurrence(purpose="invented")
    with pytest.raises(StyleEvaluationError) as caught:
        evaluate_style_rules((), (invalid_occurrence,))
    assert caught.value.diagnostic_id == "E_STYLE_FACT_UNKNOWN"
