from dataclasses import FrozenInstanceError

import pytest

from chrona.presentation.model.color_scale import ColorScaleError, resolve_color_scale
from chrona.presentation.model.style_fills import CompletedStyleFill, StyleFillIndex, complete_style_fills
from chrona.presentation.model.style_rules import (
    StyleFieldFact,
    StyleOccurrence,
    OccurrenceStyleIndex,
    StyleOccurrenceKey,
    evaluate_style_rules,
)
from chrona.presentation.style import (
    EncodingSource, EncodingWitness, StyleEncodingOutcome,
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


def _sources(rules, *, kind="style"):
    return {rule.rule_id: EncodingSource(
        kind, "source-resource", "/body/colorEncoding" if kind == "view"
        else rule.source_ref + "/then/encode", None if kind == "view" else rule.rule_id,
    ) for rule in rules}


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

    rule = _rule()
    fills = complete_style_fills(_index(occurrences, rule=rule), occurrences, theme=_theme(),
                                 encoding_sources=_sources((rule,)))

    assert len(fills.fills) == len(keys)
    assert tuple(fills.get(key) for key in keys) == (
        "#112233", "#445566", "#112233", "#445566", "#112233",
    )
    assert len({key for key, _ in fills.fills}) == 5
    assert all(fills.completed(key) is not None for key in keys)


def test_style_fill_index_is_frozen_detached_and_uses_exact_keys():
    key = StyleOccurrenceKey("task", "primary", "planned", "row", "item")
    witness = EncodingWitness("fill", "owners", "owner", "", (EncodingSource(
        "style", "style-resource", "/body/rules/owner-fill/then/encode", "owner-fill"),))
    source = [(key, CompletedStyleFill("#112233", witness))]
    fills = StyleFillIndex(source)
    source.clear()

    assert fills.fills == ((key, "#112233"),)
    assert fills.get(key) == "#112233"
    assert fills.completed(key) == CompletedStyleFill("#112233", witness)
    assert fills.get(StyleOccurrenceKey("task", "snapshot", "planned", "row", "item")) is None
    with pytest.raises(FrozenInstanceError):
        fills.fills = ()
    with pytest.raises(TypeError):
        fills._by_key[key] = "#ffffff"


def test_completed_style_fill_requires_atomic_colour_and_typed_witness():
    witness = EncodingWitness("fill", "owners", "owner", "A", (
        EncodingSource("view", "view-resource", "/body/colorEncoding"),))
    for color, encoding in (("", witness), (None, witness), ("#112233", None)):
        with pytest.raises(ValueError, match="colour and typed encoding witness"):
            CompletedStyleFill(color, encoding)


def test_boolean_source_uses_spec60_true_false_domain_text():
    key = StyleOccurrenceKey("task", "primary", "planned", "row", "item")
    occurrence = _occurrence(key, False, kind="boolean")
    rule = _rule(domain=("false", "true"))

    fills = complete_style_fills(_index((occurrence,), rule=rule), (occurrence,),
                                 theme=_theme(("false", "true")), encoding_sources=_sources((rule,)))

    assert fills.get(key) == "#112233"
    assert fills.scales[0].domain == ("false", "true")
    assert fills.completed(key).encoding.value == "false"


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

    fills = complete_style_fills(_index(occurrences, rule=rule), occurrences, theme=theme,
                                 encoding_sources=_sources((rule,)))

    assert fills.scales[0].domain == ("B", "A")
    assert fills.get(selected_b) == "#112233"
    assert fills.get(selected_a) == "#445566"
    assert fills.get(unmatched) is None


def test_missing_closed_domain_value_keeps_existing_scale_error():
    key = StyleOccurrenceKey("task", "primary", "planned", "row", "item")
    occurrence = _occurrence(key, None, present=False)

    with pytest.raises(ColorScaleError) as caught:
        rule = _rule(domain=("A",))
        complete_style_fills(_index((occurrence,), rule=rule), (occurrence,), theme=_theme(("A",)),
                             encoding_sources=_sources((rule,)))

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
                                 legacy_scale=legacy_scale, encoding_sources=_sources((rule,), kind="view"))

    assert fills.scales == (legacy_scale,)
    assert fills.scales[0] is legacy_scale
    assert fills.scales[0].domain == ("B", "A")
    assert fills.get(first) == "#112233"
    assert fills.get(second) == "#445566"
    assert fills.completed(first).encoding.sources == (_sources((rule,), kind="view")[rule.rule_id],)


def test_encoding_source_and_witness_use_closed_round_trip_codecs():
    view = EncodingSource("view", "quarterly-view", "/body/colorEncoding")
    style = EncodingSource("style", "review-style", "/body/rules/owner/then/encode", "owner")
    witness = EncodingWitness("fill", "owner-colors", "owner", "Planning", (view, style))
    assert EncodingSource.from_mapping(view.as_mapping()) == view
    assert EncodingSource.from_mapping(style.as_mapping()) == style
    assert EncodingWitness.from_mapping(witness.as_mapping()) == witness
    assert witness.as_mapping() == {
        "channel": "fill", "scaleId": "owner-colors", "field": "owner", "value": "Planning",
        "sources": [view.as_mapping(), style.as_mapping()],
    }


@pytest.mark.parametrize("source", [
    {"kind": "view", "id": "view", "sourceRef": "/body/colorEncoding", "ruleId": "unexpected"},
    {"kind": "style", "id": "style", "sourceRef": "/body/rules/a/then/encode"},
    {"kind": "other", "id": "x", "sourceRef": "/x"},
    {"kind": "style", "id": "", "sourceRef": "/x", "ruleId": "r"},
    {"kind": "style", "id": "s", "sourceRef": "/x", "ruleId": ""},
])
def test_encoding_source_codec_rejects_invalid_or_open_records(source):
    with pytest.raises(ValueError):
        EncodingSource.from_mapping(source)


def test_encoding_witness_requires_unique_nonempty_sources_and_string_value():
    source = EncodingSource("view", "view", "/body/colorEncoding")
    with pytest.raises(ValueError):
        EncodingWitness("stroke", "scale", "field", "x", (source,))
    with pytest.raises(ValueError):
        EncodingWitness("fill", "scale", "field", "x", ())
    with pytest.raises(ValueError):
        EncodingWitness("fill", "scale", "field", 1, (source,))
    with pytest.raises(ValueError):
        EncodingWitness.from_mapping({"channel": "fill", "scaleId": "s", "field": "f", "value": "v",
                                      "sources": [source.as_mapping(), source.as_mapping()]})
