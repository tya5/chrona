"""One Style scale map joins source-local aliases in View order."""
import pytest

from chrona.presentation.model.color_scale import ColorScaleError, resolve_color_scale
from chrona.presentation.model.style_fills import complete_style_fills
from chrona.presentation.model.style_rules import (
    OccurrenceStyleIndex, StyleFieldFact, StyleOccurrence, StyleOccurrenceKey,
    evaluate_style_rules,
)
from chrona.presentation.style import (
    StyleEncodingOutcome, StyleFieldSource, StyleRule, StyleSelector,
)


def _theme():
    return {"body": {
        "colorScales": {"owners": {"palette": ["first", "second", "third"]}},
        "categorySlots": {"first": "#112233", "second": "#445566", "third": "#778899"},
    }}


def _occurrence(semantic, field, value, *, kind="string", present=True):
    key = StyleOccurrenceKey(semantic, "primary", semantic, f"row-{semantic}", f"item-{semantic}")
    fact = StyleFieldFact(field, kind, present, value)
    return StyleOccurrence(key, semantic, "mark", fields=(fact,))


def _rule(rule_id, semantic, field, domain="firstAppearance"):
    return StyleRule(
        rule_id, StyleSelector(semantic=semantic),
        StyleEncodingOutcome("fill", StyleFieldSource(field_name=field), "owners", domain),
        f"/body/rules/{rule_id}",
    )


def _intents(occurrences, rules):
    return OccurrenceStyleIndex(evaluate_style_rules(tuple(rules), tuple(occurrences)))


def test_source_aliases_share_one_first_appearance_map_in_occurrence_order():
    actual = _occurrence("actual", "accountOwner", "B")
    planned = _occurrence("planned", "owner", "A")
    occurrences = (actual, planned)
    rules = (_rule("z-planned", "planned", "owner"),
             _rule("a-actual", "actual", "accountOwner"))

    fills = complete_style_fills(
        _intents(occurrences, rules), occurrences, theme=_theme(),
        source_refs={rule.rule_id: rule.source_ref for rule in rules},
    )

    assert len(fills.scales) == 1
    assert fills.scales[0].domain == ("B", "A")
    assert fills.get(actual.key) == "#112233"
    assert fills.get(planned.key) == "#445566"


def test_legacy_view_domain_is_prefix_and_exact_scale_is_reused_when_union_adds_nothing():
    theme = _theme()
    legacy = resolve_color_scale(
        {"scale": "owners", "target": "planned", "source": {"field": "owner"},
         "domain": "firstAppearance"},
        theme["body"]["colorScales"], theme["body"]["categorySlots"], observed=("A", "B"),
    )
    first = _occurrence("actual", "accountOwner", "B")
    second = _occurrence("planned", "owner", "A")
    occurrences = (first, second)
    rules = (_rule("actual", "actual", "accountOwner"), _rule("planned", "planned", "owner"))

    fills = complete_style_fills(
        _intents(occurrences, rules), occurrences, theme=theme, legacy_scale=legacy,
        source_refs={rule.rule_id: rule.source_ref for rule in rules},
    )

    assert fills.scales == (legacy,)
    assert fills.scales[0] is legacy
    assert fills.scales[0].domain == ("A", "B")


def test_new_alias_value_extends_legacy_domain_after_its_prefix():
    theme = _theme()
    legacy = resolve_color_scale(
        {"scale": "owners", "target": "planned", "source": {"field": "owner"},
         "domain": "firstAppearance"},
        theme["body"]["colorScales"], theme["body"]["categorySlots"], observed=("A", "B"),
    )
    new_value = _occurrence("actual", "accountOwner", "C")
    old_value = _occurrence("planned", "owner", "A")
    occurrences = (new_value, old_value)
    rules = (_rule("actual", "actual", "accountOwner"), _rule("planned", "planned", "owner"))

    fills = complete_style_fills(
        _intents(occurrences, rules), occurrences, theme=theme, legacy_scale=legacy,
        source_refs={rule.rule_id: rule.source_ref for rule in rules},
    )

    assert len(fills.scales) == 1
    assert fills.scales[0] is not legacy
    assert fills.scales[0].domain == ("A", "B", "C")


def test_boolean_and_string_alias_values_use_the_existing_scale_text_conversion():
    boolean = _occurrence("actual", "completion", True, kind="boolean")
    string = _occurrence("planned", "owner", "open")
    occurrences = (boolean, string)
    rules = (_rule("actual", "actual", "completion"), _rule("planned", "planned", "owner"))

    fills = complete_style_fills(
        _intents(occurrences, rules), occurrences, theme=_theme(),
        source_refs={rule.rule_id: rule.source_ref for rule in rules},
    )

    assert fills.scales[0].domain == ("true", "open")
    assert fills.get(boolean.key) == "#112233"
    assert fills.get(string.key) == "#445566"


def test_incompatible_policies_for_one_scale_id_keep_mapping_diagnostic():
    actual = _occurrence("actual", "accountOwner", "A")
    planned = _occurrence("planned", "owner", "A")
    occurrences = (actual, planned)
    rules = (_rule("actual", "actual", "accountOwner"),
             _rule("planned", "planned", "owner", domain=("A",)))

    with pytest.raises(ColorScaleError) as caught:
        complete_style_fills(
            _intents(occurrences, rules), occurrences, theme=_theme(),
            source_refs={rule.rule_id: rule.source_ref for rule in rules},
        )

    assert caught.value.code == "E_PRESENTATION_SCALE_MAPPING"
    assert caught.value.source_ref == "/body/rules/planned/then/encode"


@pytest.mark.parametrize(
    ("value", "kind", "present"),
    [("invalid", "string", True), (None, "string", False), (7, "integer", True)],
)
def test_invalid_or_missing_value_keeps_its_alias_field_and_rule_pointer(value, kind, present):
    actual = _occurrence("actual", "accountOwner", value, kind=kind, present=present)
    planned = _occurrence("planned", "owner", "A")
    occurrences = (actual, planned)
    rules = (_rule("actual", "actual", "accountOwner", domain=("A", "B")),
             _rule("planned", "planned", "owner", domain=("A", "B")))
    theme = {"body": {
        "colorScales": {"owners": {"slots": {"A": "first", "B": "second"}}},
        "categorySlots": {"first": "#112233", "second": "#445566"},
    }}

    with pytest.raises(ColorScaleError) as caught:
        complete_style_fills(
            _intents(occurrences, rules), occurrences, theme=theme,
            source_refs={rule.rule_id: rule.source_ref for rule in rules},
        )

    assert caught.value.code == "E_PRESENTATION_SCALE_VALUE"
    assert caught.value.source_ref == "/body/rules/actual/then/encode"
    assert "field='accountOwner'" in caught.value.detail
