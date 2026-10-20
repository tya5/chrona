from dataclasses import replace

from chrona.presentation.layout.legend_candidates import (
    _point_label_variants, coalesce_actual_keys, coalesce_point_keys, point_key_label,
)
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


def test_identical_completed_point_figure_has_one_key_covering_all_states():
    planned, actual, forecast = (replace(_key(state), family="milestone")
                                 for state in ("planned", "actual", "forecast"))

    assert planned.ink_identity == actual.ink_identity == forecast.ink_identity
    assert planned.identity == actual.identity == forecast.identity
    (combined,) = coalesce_point_keys((actual, forecast, planned))
    assert combined.point_states == ("planned", "actual", "forecast")
    assert combined.key_id == planned.key_id
    assert point_key_label("Gate", combined, multiple=False, wording={}) == "Gate"
    assert point_key_label("Gate", combined, multiple=True, wording={
        "planned-plain": "Plan", "actual": "Observed", "forecast": "Estimate"
    }) == "Gate · Plan / Observed / Estimate"


def test_point_visual_identity_keeps_different_owners_separate_and_ignores_coverage_subset():
    key = _key("planned")
    other_owner = replace(key, family="custom")
    assert len(coalesce_point_keys((key, other_owner))) == 2
    subset = replace(key, covered_point_states=("actual",))
    assert subset.grouping_identity == key.grouping_identity
    assert subset.key_id == key.key_id


def test_mixed_coverage_reserves_every_final_localized_subset_label():
    planned, actual = (replace(_key(state), family="milestone") for state in ("planned", "actual"))
    forecast = replace(_key("forecast", geometry=(("diamond",),)), family="milestone")
    combined, distinct = coalesce_point_keys((actual, forecast, planned))
    assert combined.point_states == ("planned", "actual")
    assert distinct.point_states == ("forecast",)
    wording = {"planned-plain": "予定", "actual": "実績", "forecast": "見込"}
    assert set(_point_label_variants("Gate", combined, multiple=True, wording=wording)) == {
        "Gate", "Gate · 予定", "Gate · 実績", "Gate · 予定 / 実績"}
    assert point_key_label("Gate", combined, multiple=True, wording=wording) == "Gate · 予定 / 実績"


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
    assert len(coalesce_point_keys((base, different_shape, different_order, reverse_order))) == 4


def test_legacy_nonpoint_identity_and_grouping_remain_unchanged():
    actual = _key("actual")
    legacy = replace(actual, point_state=None)
    another_legacy = replace(legacy, glyph=replace(legacy.glyph, footprint=(20.0, 12.0)))

    assert legacy.identity == another_legacy.identity
    assert legacy.grouping_identity == another_legacy.grouping_identity
