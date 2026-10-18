from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from chrona.presentation.style import (
    StyleEncodingOutcome,
    StyleFieldEquals,
    StyleFieldSource,
    StyleRuleError,
    StyleSelector,
    canonical_style_selector,
    parse_style_rules,
)


def _rule(*, rule_id="risk", when=None, then=None):
    return {
        "id": rule_id,
        "when": when or {"semantic": "planned"},
        "then": then or {"role": "planned"},
    }


def _encoding(*, legend=None):
    value = {
        "channel": "fill",
        "source": {"field": "risk"},
        "scale": "risk-scale",
        "domain": ["low", "high"],
    }
    if legend is not None:
        value["legend"] = legend
    return {"encode": value}


def test_parse_detaches_values_and_retains_exact_rule_source_and_column_mapping():
    column_source = {"comparisonFacet": "finishDelta"}
    roles = ["critical", "late"]
    fields = [{"source": {"fieldRole": "responsible"}, "equals": "payload"}]
    domain = ["low", "high"]
    body = {"rules": [
        _rule(when={"semantic": "planned", "columnSource": column_source,
                    "roles": roles, "fields": fields},
              then=_encoding(legend={"title": "Risk — payload team", "showScope": True})),
    ]}
    body["rules"][0]["then"]["encode"]["domain"] = domain

    (rule,) = parse_style_rules(body)

    assert rule.source_ref == "/body/rules/0"
    assert rule.selector.column_source == (("comparisonFacet", "finishDelta"),)
    assert rule.selector.fields == (StyleFieldEquals(StyleFieldSource(field_role="responsible"), "payload"),)
    assert isinstance(rule.outcome, StyleEncodingOutcome)
    assert rule.outcome.domain == ("low", "high")
    column_source["comparisonFacet"] = "changed"
    roles.append("changed")
    fields[0]["equals"] = "changed"
    domain.append("changed")
    assert rule.selector.column_source == (("comparisonFacet", "finishDelta"),)
    assert rule.selector.roles == ("critical", "late")
    assert rule.selector.fields[0].equals == "payload"
    assert rule.outcome.domain == ("low", "high")
    with pytest.raises(FrozenInstanceError):
        rule.rule_id = "changed"


def test_duplicate_rule_id_reports_later_original_pointer():
    with pytest.raises(StyleRuleError) as caught:
        parse_style_rules({"rules": [_rule(), _rule()]})

    assert caught.value.diagnostic_id == "E_STYLE_RULE_ID_DUPLICATE"
    assert caught.value.source_ref == "/body/rules/1/id"


@pytest.mark.parametrize("legend", [None, {}, {"title": "   "}])
def test_scoped_encoding_requires_nonblank_authored_legend_title(legend):
    then = _encoding(legend=legend) if legend is not None else _encoding()
    with pytest.raises(StyleRuleError) as caught:
        parse_style_rules({"rules": [_rule(when={"purpose": "planned", "roles": ["critical"]},
                                            then=then)]})

    assert caught.value.diagnostic_id == "E_STYLE_LEGEND_TITLE_REQUIRED"
    assert caught.value.source_ref == "/body/rules/0/then/encode/legend/title"


def test_global_encoding_does_not_require_legend_title():
    (rule,) = parse_style_rules({"rules": [_rule(when={"semantic": "planned", "purpose": "planned"},
                                                  then=_encoding())]})
    assert isinstance(rule.outcome, StyleEncodingOutcome)
    assert rule.outcome.legend is None


def test_canonical_selector_sorts_roles_predicates_and_mapping_keys():
    left = StyleSelector(
        semantic="planned",
        column_source=(("comparisonFacet", "finishDelta"), ("sourceType", "table")),
        roles=("late", "critical"),
        fields=(
            StyleFieldEquals(StyleFieldSource(field_name="risk"), "high"),
            StyleFieldEquals(StyleFieldSource(field_role="responsible"), "payload"),
        ),
    )
    right = StyleSelector(
        semantic="planned",
        column_source=(("sourceType", "table"), ("comparisonFacet", "finishDelta")),
        roles=("critical", "late"),
        fields=tuple(reversed(left.fields)),
    )

    assert canonical_style_selector(left) == canonical_style_selector(right)


def test_canonical_selector_preserves_boolean_vs_numeric_equality():
    boolean = StyleSelector(fields=(StyleFieldEquals(StyleFieldSource(field_name="enabled"), True),))
    integer = StyleSelector(fields=(StyleFieldEquals(StyleFieldSource(field_name="enabled"), 1),))
    floating = StyleSelector(fields=(StyleFieldEquals(StyleFieldSource(field_name="enabled"), 1.0),))

    assert canonical_style_selector(boolean) != canonical_style_selector(integer)
    assert canonical_style_selector(integer) != canonical_style_selector(floating)


def test_nonfinite_field_equality_is_rejected_with_fact_type_diagnostic():
    for value in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(StyleRuleError) as caught:
            parse_style_rules({"rules": [_rule(when={"fields": [
                {"source": {"field": "score"}, "equals": value},
            ]})]})
        assert caught.value.diagnostic_id == "E_STYLE_FACT_TYPE"
        assert caught.value.source_ref == "/body/rules/0/when/fields/0/equals"
