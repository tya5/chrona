from dataclasses import FrozenInstanceError

import pytest

from chrona.presentation.model.color_scale import ColorScaleError, resolve_color_scale
from chrona.presentation.model.style_fills import StyleFillIndex, complete_style_fills
from chrona.presentation.model.style_rules import (
    StyleFieldFact,
    StyleOccurrence,
    OccurrenceStyleIndex,
    StyleOccurrenceKey,
    evaluate_style_rules,
)
from chrona.presentation.style import (
    StyleEncodingOutcome,
    StyleFieldSource,
    StyleRule,
    StyleSelector,
)


def _occurrence(key, value, *, kind="string", present=True):
    table_cell = key.semantic_id == "tableCell"
    return StyleOccurrence(
        key,
        "table-cell" if table_cell else key.semantic_id,
        "label" if table_cell else "mark",
        fields=(StyleFieldFact("owner", kind, present, value),),
    )


def _rule(domain=("A", "B"), *, field="owner", scale="owners", selector=None):
    return StyleRule(
        "owner-fill",
        selector or StyleSelector(),
        StyleEncodingOutcome("fill", StyleFieldSource(field_name=field), scale, domain),
        "/body/rules/owner-fill",
    )


def _theme(domain=("A", "B")):
    colors = {value: color for value, color in zip(domain, ("#112233", "#445566"), strict=False)}
    return {"body": {
        "colorScales": {"owners": {"slots": {value: value for value in domain}}},
        "categorySlots": colors,
    }}


def _index(occurrences, *, rule=None):
    selected = evaluate_style_rules((rule or _rule(),), tuple(occurrences))
    return OccurrenceStyleIndex(selected)


def test_full_occurrence_key_keeps_rows_sources_and_columns_independent():
    keys = (
        StyleOccurrenceKey("same", "primary", "planned", "row-a", "item-a"),
        StyleOccurrenceKey("same", "primary", "planned", "row-b", "item-a"),
        StyleOccurrenceKey("same", "snapshot", "planned", "row-a", "item-a"),
        StyleOccurrenceKey("same", "primary", "tableCell", "row-a", "item-a", "owner-a"),
        StyleOccurrenceKey("same", "primary", "tableCell", "row-a", "item-a", "owner-b"),
    )
    occurrences = tuple(_occurrence(key, "A" if index % 2 == 0 else "B")
                        for index, key in enumerate(keys))

    fills = complete_style_fills(_index(occurrences), occurrences, theme=_theme())

    assert len(fills.fills) == len(keys)
    assert tuple(fills.get(key) for key in keys) == (
        "#112233", "#445566", "#112233", "#445566", "#112233",
    )
    assert len({key for key, _ in fills.fills}) == 5


def test_style_fill_index_is_frozen_detached_and_uses_exact_keys():
    key = StyleOccurrenceKey("task", "primary", "planned", "row", "item")
    source = [(key, "#112233")]
    fills = StyleFillIndex(source)
    source.clear()

    assert fills.fills == ((key, "#112233"),)
    assert fills.get(key) == "#112233"
    assert fills.get(StyleOccurrenceKey("task", "snapshot", "planned", "row", "item")) is None
    with pytest.raises(FrozenInstanceError):
        fills.fills = ()
    with pytest.raises(TypeError):
        fills._by_key[key] = "#ffffff"


def test_boolean_source_uses_spec60_true_false_domain_text():
    key = StyleOccurrenceKey("task", "primary", "planned", "row", "item")
    occurrence = _occurrence(key, False, kind="boolean")
    rule = _rule(domain=("false", "true"))

    fills = complete_style_fills(_index((occurrence,), rule=rule), (occurrence,),
                                 theme=_theme(("false", "true")))

    assert fills.get(key) == "#112233"
    assert fills.scales[0].domain == ("false", "true")


def test_first_appearance_domain_uses_only_matched_intents_in_input_order():
    selected_a = StyleOccurrenceKey("a", "primary", "planned", "r1", "a")
    selected_b = StyleOccurrenceKey("b", "primary", "planned", "r2", "b")
    unmatched = StyleOccurrenceKey("c", "primary", "actual", "r3", "c")
    occurrences = (
        _occurrence(selected_b, "B"),
        _occurrence(selected_a, "A"),
        _occurrence(unmatched, "UNUSED"),
    )
    rule = _rule(domain="firstAppearance", selector=StyleSelector(semantic="planned"))
    theme = {"body": {
        "colorScales": {"owners": {"palette": ["first", "second"]}},
        "categorySlots": {"first": "#112233", "second": "#445566"},
    }}

    fills = complete_style_fills(_index(occurrences, rule=rule), occurrences, theme=theme)

    assert fills.scales[0].domain == ("B", "A")
    assert fills.get(selected_b) == "#112233"
    assert fills.get(selected_a) == "#445566"
    assert fills.get(unmatched) is None


def test_missing_closed_domain_value_keeps_existing_scale_error():
    key = StyleOccurrenceKey("task", "primary", "planned", "row", "item")
    occurrence = _occurrence(key, None, present=False)

    with pytest.raises(ColorScaleError) as caught:
        complete_style_fills(_index((occurrence,), rule=_rule(domain=("A",))),
                             (occurrence,), theme=_theme(("A",)),
                             source_refs={"owner-fill": "/body/rules/owner-fill"})

    assert caught.value.code == "E_PRESENTATION_SCALE_VALUE"
    assert caught.value.source_ref == "/body/rules/owner-fill/then/encode"
    assert "object='task'" in caught.value.detail


def test_legacy_view_scale_reuses_its_preclosed_first_appearance_domain():
    first = StyleOccurrenceKey("b", "primary", "planned", "r1", "b")
    second = StyleOccurrenceKey("a", "primary", "planned", "r2", "a")
    occurrences = (_occurrence(first, "B"), _occurrence(second, "A"))
    legacy_scale = resolve_color_scale(
        {"scale": "owners", "target": "planned", "source": {"field": "owner"},
         "domain": "firstAppearance"},
        {"owners": {"palette": ["first", "second"]}},
        {"first": "#112233", "second": "#445566"},
        observed=("B", "A"),
    )
    rule = _rule(domain="firstAppearance")

    fills = complete_style_fills(_index(occurrences, rule=rule), occurrences,
                                 legacy_scale=legacy_scale)

    assert fills.scales == (legacy_scale,)
    assert fills.scales[0] is legacy_scale
    assert fills.scales[0].domain == ("B", "A")
    assert fills.get(first) == "#112233"
    assert fills.get(second) == "#445566"
