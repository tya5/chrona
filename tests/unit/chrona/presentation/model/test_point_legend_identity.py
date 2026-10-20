from dataclasses import replace

from chrona.presentation.layout.legend_candidates import coalesce_actual_keys
from chrona.presentation.model.legend_paint import RealizedGlyphInk, RealizedLegendKey
from chrona.presentation.model.theme_paint import PaintFamily, resolve_theme_paint_witness
from chrona.presentation.model.theme_tokens import ThemeTokenView


def _paint_tokens():
    tokens = ThemeTokenView({"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
        "body": {"values": {"ink": {"type": "color", "value": "#345678"},
                              "other": {"type": "color", "value": "#112233"}},
                 "roles": {"actual": {"fill": "ink"}, "other": {"fill": "other"}}}})
    return tokens


def _key(state, *, geometry=(("circle",),), paints=None, paint=None):
    tokens = _paint_tokens()
    paint = paint or resolve_theme_paint_witness(tokens, "actual", PaintFamily.SOLID)
    paints = paints or (paint,)
    glyph = RealizedGlyphInk("point", geometry, tuple(paints), (10.0, 10.0))
    return RealizedLegendKey("actual", "actual", paint, glyph=glyph, point_state=state)


def test_same_point_ink_keeps_semantic_state_in_identity_and_coalescing():
    planned, actual, forecast = (_key(state) for state in ("planned", "actual", "forecast"))

    assert planned.ink_identity == actual.ink_identity == forecast.ink_identity
    assert planned.identity != actual.identity != forecast.identity
    assert len(coalesce_actual_keys((planned, actual, forecast))) == 3


def test_point_coalescing_requires_same_canonical_glyph_and_ordered_paints():
    tokens = _paint_tokens()
    first_paint = resolve_theme_paint_witness(tokens, "actual", PaintFamily.SOLID)
    second_paint = resolve_theme_paint_witness(tokens, "other", PaintFamily.SOLID)
    base = _key("actual", paint=first_paint)
    different_shape = _key("actual", geometry=(("diamond",),), paint=first_paint)
    different_order = _key("actual", paints=(first_paint, second_paint), paint=first_paint)
    reverse_order = _key("actual", paints=(second_paint, first_paint), paint=second_paint)
    same = _key("actual", paint=first_paint)

    assert base.grouping_identity != different_shape.grouping_identity
    assert different_order.grouping_identity != reverse_order.grouping_identity
    assert len(coalesce_actual_keys((base, same))) == 1


def test_legacy_nonpoint_identity_and_grouping_remain_unchanged():
    actual = _key("actual")
    legacy = replace(actual, point_state=None)
    another_legacy = replace(legacy, glyph=replace(legacy.glyph, footprint=(20.0, 12.0)))

    assert legacy.identity == another_legacy.identity
    assert legacy.grouping_identity == another_legacy.grouping_identity
