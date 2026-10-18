from dataclasses import replace

from chrona.presentation.model.style_fills import complete_style_fills
from chrona.presentation.model.style_rules import (
    OccurrenceStyleIndex, StyleFieldFact, StyleOccurrence, StyleOccurrenceKey,
    evaluate_style_rules,
)
from chrona.presentation.review.style_intent import lower_legacy_color_encoding
from chrona.presentation.review.v05_content import _style_legend_entries, _style_match_index
from chrona.presentation.style import (
    EncodingSource, StyleEncodingOutcome, StyleFieldSource, StyleLegend, StyleRule, StyleSelector,
    bind_style_rules,
)


def _rule(rule_id, selector, title=None):
    legend = StyleLegend(title=title) if title is not None else None
    return StyleRule(
        rule_id, selector,
        StyleEncodingOutcome("fill", StyleFieldSource(field_name="owner"),
                             "owners", "firstAppearance", legend),
        f"/body/rules/{rule_id}",
    )


def _encoding_sources(rules):
    result = {}
    for rule in rules:
        if not isinstance(rule.outcome, StyleEncodingOutcome):
            continue
        if rule.style_id is None:
            result[rule.rule_id] = EncodingSource("view", "test-view", rule.source_ref)
        else:
            result[rule.rule_id] = EncodingSource(
                "style", rule.style_id, rule.source_ref + "/then/encode", rule.authored_rule_id)
    return result


def test_coalesced_authored_rules_keep_separate_scoped_legend_identity_and_matches():
    keys = (
        StyleOccurrenceKey("one", "primary", "planned", "row-1", "one"),
        StyleOccurrenceKey("two", "primary", "planned", "row-2", "two"),
    )
    occurrences = tuple(
        StyleOccurrence(key, "planned", "mark", original_roles=("critical",),
                        fields=(StyleFieldFact("owner", "string", True, value),))
        for key, value in zip(keys, ("A", "B"), strict=True)
    )
    authored = bind_style_rules("style-1", (
        _rule("scoped", StyleSelector(roles=("critical",)), "Critical"),
        _rule("global", StyleSelector(purpose="planned")),
    ))
    lowered_view = lower_legacy_color_encoding({
        "source": {"field": "owner"}, "scale": "owners",
        "domain": "firstAppearance", "target": "planned",
    })
    intents = OccurrenceStyleIndex(evaluate_style_rules(
        (*lowered_view, *authored), occurrences,
    ))
    theme = {"body": {
        "colorScales": {"owners": {"palette": ["first"]}},
        "categorySlots": {"first": "#112233"},
    }}
    fills = complete_style_fills(intents, occurrences, theme=theme, other_color="#999999",
                                 encoding_sources=_encoding_sources((*lowered_view, *authored)))

    style_matches = _style_match_index(intents, (*lowered_view, *authored))
    entries, paints = _style_legend_entries(authored, intents, occurrences, fills)

    assert style_matches.get(keys[0]).style_id == "style-1"
    assert style_matches.get(keys[0]).rule_ids == ("global", "scoped")
    assert [entry.label for entry in entries] == [
        "Critical: A", "Critical: Other", "A", "Other",
    ]
    scoped_a, scoped_other, global_a, global_other = entries
    assert scoped_a.style_scope.selector == '{"roles":["critical"]}'
    assert scoped_a.style_scope.rule_id == "scoped"
    assert scoped_other.style_value == "Other"
    assert scoped_other.style_occurrences == (keys[1],)
    assert global_a.style_scope.rule_id == "global"
    assert global_a.style_scope.title is None
    assert global_a.style_occurrences == (keys[0],)
    assert global_other.style_occurrences == (keys[1],)
    assert len({entry.source_identity for entry in entries}) == 4
    assert paints == tuple((entry.source_identity, color) for entry, color in zip(
        entries, ("#112233", "#999999", "#112233", "#999999"), strict=True))
    renamed = replace(scoped_a, style_scope=replace(scoped_a.style_scope, title="Renamed"),
                      style_occurrences=(*scoped_a.style_occurrences, keys[1]))
    assert renamed.label == "Renamed: A"
    assert renamed.source_identity == scoped_a.source_identity


def test_view_lowered_rule_does_not_create_style_match_metadata_or_legend():
    key = StyleOccurrenceKey("one", "primary", "planned", "row-1", "one")
    occurrence = StyleOccurrence(
        key, "planned", "mark", fields=(StyleFieldFact("owner", "string", True, "A"),),
    )
    lowered = lower_legacy_color_encoding({
        "source": {"field": "owner"}, "scale": "owners",
        "domain": "firstAppearance", "target": "planned",
    })
    intents = OccurrenceStyleIndex(evaluate_style_rules(lowered, (occurrence,)))
    fills = complete_style_fills(
        intents, (occurrence,),
        theme={"body": {"colorScales": {"owners": {"palette": ["first"]}},
                         "categorySlots": {"first": "#112233"}}},
        encoding_sources=_encoding_sources(lowered),
    )

    assert _style_match_index(intents, lowered).get(key) is None
    assert _style_legend_entries(lowered, intents, (occurrence,), object()) == ((), ())
    assert fills.completed(key).encoding.sources == (
        EncodingSource("view", "test-view", "/body/colorEncoding"),)


def test_folded_other_identity_does_not_alias_literal_domain_value_other():
    keys = (
        StyleOccurrenceKey("literal", "primary", "planned", "row-1", "literal"),
        StyleOccurrenceKey("folded", "primary", "planned", "row-2", "folded"),
    )
    occurrences = tuple(
        StyleOccurrence(key, "planned", "mark", fields=(StyleFieldFact("owner", "string", True, value),))
        for key, value in zip(keys, ("Other", "B"), strict=True)
    )
    authored = bind_style_rules("style-1", (_rule("global", StyleSelector(purpose="planned")),))
    intents = OccurrenceStyleIndex(evaluate_style_rules(authored, occurrences))
    theme = {"body": {
        "colorScales": {"owners": {"palette": ["first"]}},
        "categorySlots": {"first": "#112233"},
    }}
    fills = complete_style_fills(intents, occurrences, theme=theme, other_color="#999999",
                                 encoding_sources=_encoding_sources(authored))
    assert fills.completed(keys[0]).encoding.sources == (
        EncodingSource("style", "style-1", "/body/rules/global/then/encode", "global"),)

    entries, _paints = _style_legend_entries(authored, intents, occurrences, fills)

    assert [entry.style_value for entry in entries] == ["Other", "Other"]
    assert [entry.style_occurrences for entry in entries] == [(keys[0],), (keys[1],)]
    assert entries[0].source_identity != entries[1].source_identity


def test_literal_scale_ref_ending_in_other_suffix_is_not_folded_other():
    values = ("x#other", "A", "B")
    keys = tuple(StyleOccurrenceKey(value, "primary", "planned", f"row-{index}", value)
                 for index, value in enumerate(values, start=1))
    occurrences = tuple(
        StyleOccurrence(key, "planned", "mark", fields=(StyleFieldFact("owner", "string", True, value),))
        for key, value in zip(keys, values, strict=True)
    )
    authored = bind_style_rules("style-1", (_rule("global", StyleSelector(purpose="planned")),))
    intents = OccurrenceStyleIndex(evaluate_style_rules(authored, occurrences))
    theme = {"body": {
        "colorScales": {"owners": {"palette": ["first", "second"]}},
        "categorySlots": {"first": "#112233", "second": "#445566"},
    }}
    fills = complete_style_fills(intents, occurrences, theme=theme, other_color="#999999",
                                 encoding_sources=_encoding_sources(authored))

    entries, _paints = _style_legend_entries(authored, intents, occurrences, fills)

    assert [entry.style_value for entry in entries] == ["x#other", "A", "Other"]
    assert [entry.style_occurrences for entry in entries] == [(keys[0],), (keys[1],), (keys[2],)]
