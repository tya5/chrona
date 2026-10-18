from __future__ import annotations

import pytest

from chrona.presentation.model.style_fills import CompletedStyleFill, StyleFillIndex
from chrona.presentation.model.style_mark_paint import validate_style_mark_paint
from chrona.presentation.model.style_rules import (
    OccurrenceStyleIndex, OccurrenceStyleIntent, StyleOccurrence, StyleOccurrenceKey,
)
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.style import EncodingSource, EncodingWitness


def _tokens(role, values=None, *, glyphs=None, patterns=None):
    return ThemeTokenView({
        "version": "chrona/resolved-theme/v0.2",
        "kind": "resolved-theme",
        "body": {
            "values": values or {},
            "roles": {"selected": role},
            "metrics": {},
        },
    }, catalog_glyphs=glyphs or {}, catalog_patterns=patterns or {})


def _inputs(shape, role="selected", *, fill=None, values=None, glyphs=None):
    key = StyleOccurrenceKey("subject", "primary", "planned", "row", "member")
    occurrence = StyleOccurrence(
        key, "planned", "mark", mark_shape=shape,
    )
    intent = OccurrenceStyleIntent(
        key, role, None, ("paint-rule",), ("paint-rule",), (),
    )
    witness = EncodingWitness(
        "fill", "fixture-scale", "owner", "A",
        (EncodingSource("style", "fixture-style", "/body/rules/paint/then/encode", "paint"),),
    )
    fills = (StyleFillIndex(((key, CompletedStyleFill(fill, witness)),))
             if fill is not None else StyleFillIndex())
    return OccurrenceStyleIndex((intent,)), (occurrence,), fills, values, glyphs


def test_selected_span_role_can_use_its_exact_completed_fill_to_satisfy_host():
    values = {"stroke": {"type": "color", "value": "#123456"},
              "width": {"type": "number", "value": 1}}
    intents, occurrences, fills, _, _ = _inputs(
        "span", fill="#abcdef", values=values,
    )
    tokens = _tokens({"stroke": "stroke", "strokeWidth": "width"}, values)

    validate_style_mark_paint(intents, occurrences, fills, tokens)


def test_selected_span_without_required_fill_reports_style_role_incompatibility():
    intents, occurrences, fills, _, _ = _inputs("span")

    with pytest.raises(ValueError) as caught:
        validate_style_mark_paint(
            intents, occurrences, fills, _tokens({}),
            source_refs={"paint-rule": "/body/rules/0"},
        )

    error = caught.value
    assert error.diagnostic_id == "E_STYLE_ROLE_INCOMPATIBLE"
    assert error.subject == occurrences[0].key
    assert error.rule_ids == ("paint-rule",)
    assert error.source_ref == "/body/rules/0/then/role"
    assert "themePath=/body/roles/selected/fill" in error.detail


def test_selected_point_requires_symbol_binding_before_measurement():
    intents, occurrences, fills, _, _ = _inputs("point")

    with pytest.raises(ValueError) as caught:
        validate_style_mark_paint(intents, occurrences, fills, _tokens({"fill": "missing"}))

    assert caught.value.diagnostic_id == "E_STYLE_ROLE_INCOMPATIBLE"
    assert "themePath=/body/roles/selected/symbol" in caught.value.detail


def test_catalogue_point_checks_each_authored_fill_and_stroke_part_channel():
    values = {
        "symbol": {"type": "symbol", "value": {"shape": {"catalog": "fixture:split"}}},
        "fill": {"type": "color", "value": "#112233"},
        "stroke": {"type": "color", "value": "#445566"},
        "width": {"type": "number", "value": 1.5},
    }
    glyphs = {"fixture:split": {
        "viewport": {"inlineSize": 10, "blockSize": 10},
        "parts": [
            {"paint": "fill", "data": "M 0 0 L 10 0 L 5 10 Z"},
            {"paint": "stroke", "strokeWidth": 1, "lineCap": "round",
             "lineJoin": "round", "data": "M 0 0 L 10 10"},
        ],
    }}
    role = {"symbol": "symbol", "fill": "fill", "stroke": "stroke", "strokeWidth": "width"}
    intents, occurrences, fills, _, _ = _inputs(
        "point", values=values, glyphs=glyphs,
    )

    validate_style_mark_paint(intents, occurrences, fills, _tokens(role, values, glyphs=glyphs))

    broken = _tokens({"symbol": "symbol", "fill": "fill"}, values, glyphs=glyphs)
    with pytest.raises(ValueError) as caught:
        validate_style_mark_paint(intents, occurrences, fills, broken)
    assert caught.value.diagnostic_id == "E_STYLE_ROLE_INCOMPATIBLE"
    assert "themePath=/body/roles/selected/stroke" in caught.value.detail


def test_catalogue_pattern_role_uses_solid_host_and_requires_its_stroke():
    values = {
        "pattern": {"type": "pattern", "value": {"kind": "catalog", "ref": "fixture:hatch"}},
        "fill": {"type": "color", "value": "#112233"},
        "stroke": {"type": "color", "value": "#445566"},
        "width": {"type": "number", "value": 1},
    }
    patterns = {"fixture:hatch": {"tile": {"inlineSize": 4, "blockSize": 4},
                                  "angle": 45, "densityBasisPoints": 10000,
                                  "primitives": [{"kind": "line", "points": [[0, 0], [4, 4]]}]}}
    intents, occurrences, fills, _, _ = _inputs("span")

    validate_style_mark_paint(
        intents, occurrences, fills,
        _tokens({"pattern": "pattern", "fill": "fill", "stroke": "stroke",
                 "strokeWidth": "width"}, values, patterns=patterns),
    )

    with pytest.raises(ValueError) as caught:
        validate_style_mark_paint(
            intents, occurrences, fills,
            _tokens({"pattern": "pattern", "fill": "fill"}, values, patterns=patterns),
        )
    assert caught.value.diagnostic_id == "E_STYLE_ROLE_INCOMPATIBLE"
    assert "themePath=/body/roles/selected/stroke" in caught.value.detail
