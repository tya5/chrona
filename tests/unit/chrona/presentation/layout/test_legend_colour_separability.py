import pytest

from chrona.presentation.layout.legend_diagnostics import (
    _colour_pair_diagnostics,
    _figure_ink_colours,
    _palette_separation_failures,
)
from chrona.presentation.model.diagnostic_sources import DiagnosticProvenance, DiagnosticSubject
from chrona.presentation.model.color_separability import ScaleCollision
from chrona.presentation.model.surface_content import SurfaceLegendEntry
from chrona.presentation.style import StyleLegendScope


def _figure(*paints, modes=None):
    modes = modes or (None,) * len(paints)
    parts = tuple((mode, None, None, ()) for mode in modes)
    return ((parts, tuple(paints), (None,) * len(paints)),)


def _paint(fill=None, stroke=None, width=None, opacity=1.0):
    return (fill, stroke, width, (), opacity)


def test_completed_palette_prefers_fills_over_shared_border_strokes():
    left = _figure(_paint(("solid", "#336699"), "#202020", 1))
    right = _figure(_paint(("solid", "#CC6633"), "#202020", 1))

    assert _figure_ink_colours(left) == ("#336699",)
    assert _figure_ink_colours(right) == ("#CC6633",)
    assert _palette_separation_failures(left, right) == ()


def test_solid_near_and_identical_completed_palettes_use_existing_delta_floor():
    blue = _figure(_paint(("solid", "#0000FF")))
    almost_blue = _figure(_paint(("solid", "#0000FE")))
    red = _figure(_paint(("solid", "#FF0000")))

    assert _palette_separation_failures(blue, almost_blue) == (("normal", 0.127),)
    assert _palette_separation_failures(blue, blue) == (("normal", 0.0),)
    assert _palette_separation_failures(blue, red) == ()


def test_multipart_figure_uses_every_distinct_visible_fill_in_stable_order():
    glyph = _figure(
        _paint(("solid", "#121212"), "#EEEEEE", 2),
        _paint(("solid", "#DDAA33"), "#EEEEEE", 2),
        _paint(("solid", "#121212"), "#EEEEEE", 2),
    )

    assert _figure_ink_colours(glyph) == ("#121212", "#DDAA33")


def test_stroke_is_used_only_when_figure_has_no_visible_fill():
    outlined = _figure(_paint(None, "#222222", 1))
    zero_width = _figure(_paint(None, "#222222", 0))
    filled = _figure(_paint(("solid", "#AA3300"), "#222222", 1))

    assert _figure_ink_colours(outlined) == ("#222222",)
    assert _figure_ink_colours(zero_width) == ()
    assert _figure_ink_colours(filled) == ("#AA3300",)


def test_transparent_paint_does_not_contribute_ink():
    transparent = _figure(_paint(("solid", "#AA3300"), "#222222", 1, opacity=0))
    assert _figure_ink_colours(transparent) == ()


def test_gradient_is_not_sampled_and_does_not_fall_back_to_its_border():
    gradient = _figure(_paint(("gradient", "gradient:gold-to-red"), "#222222", 2))
    assert _figure_ink_colours(gradient) == ()


def test_explicit_stroke_component_does_not_contribute_its_fill_channel():
    outline = _figure(_paint(("solid", "#FF0000"), "#333333", 2), modes=("stroke",))
    assert _figure_ink_colours(outline) == ("#333333",)


def test_below_floor_is_reported_once_per_vision_in_canonical_order():
    same = _figure(_paint(("solid", "#778899")))
    assert _palette_separation_failures(
        same, same, color_vision=("tritanopia", "protanopia")
    ) == (("normal", 0.0), ("protanopia", 0.0), ("tritanopia", 0.0))


def _entry(source, label):
    return SurfaceLegendEntry(role="risk", label=label, source_ref=source)


def test_encoded_key_is_compared_with_a_distinct_semantic_legend_meaning():
    encoded = _entry("scale:risk:high", "HIGH")
    semantic = _entry("semantic:progress", "PROGRESS")
    figures = {
        encoded.source_identity: _figure(_paint(("solid", "#0000FF"))),
        semantic.source_identity: _figure(_paint(("solid", "#0000FE"))),
    }

    diagnostics, provenance = _colour_pair_diagnostics(((encoded, "risk"), (semantic, None)), figures)

    assert diagnostics == ("W_LEGEND_COLOR_NOT_SEPARABLE:normal:0.127",)
    assert provenance == (DiagnosticProvenance(diagnostics[0], (
        DiagnosticSubject("legend-key:scale:risk:high", "HIGH (risk)"),
        DiagnosticSubject("legend-key:semantic:progress", "PROGRESS (risk)"),
    )),)


def test_distinct_encoded_scales_are_compared_but_one_scale_domain_pair_is_skipped():
    high = _entry("risk:high", "HIGH")
    gate = _entry("gate:gate", "GATE")
    figures = {entry.source_identity: _figure(_paint(("solid", "#0000FF"))) for entry in (high, gate)}

    assert _colour_pair_diagnostics(((high, "risk"), (gate, "gate")), figures)[0] == (
        "W_LEGEND_COLOR_NOT_SEPARABLE:normal:0.0",
    )
    covered_high = SurfaceLegendEntry("risk:high", "HIGH", source_ref="risk:high",
        view_scale_id="risk", view_scale_domain_value="high",
        scale_collisions=(ScaleCollision("risk", "high", "gate", "normal", 0.0),))
    covered_gate = SurfaceLegendEntry("gate:gate", "GATE", source_ref="gate:gate",
        view_scale_id="risk", view_scale_domain_value="gate",
        scale_collisions=covered_high.scale_collisions)
    assert _colour_pair_diagnostics(((covered_high, "risk"), (covered_gate, "risk")), figures) == ((), ())


def test_sharing_scale_does_not_suppress_same_value_or_uncovered_delta():
    blue = _figure(_paint(("solid", "#0000FF")))
    high = SurfaceLegendEntry("risk:high", "HIGH", view_scale_id="risk",
                              view_scale_domain_value="high")
    same_value = SurfaceLegendEntry("risk:high-alt", "HIGH (alternate)", view_scale_id="risk",
                                    view_scale_domain_value="high")
    facts = (ScaleCollision("risk", "high", "gate", "normal", 0.0),)
    gate = SurfaceLegendEntry("gate:gate", "GATE", view_scale_id="risk",
                              view_scale_domain_value="gate", scale_collisions=facts)
    figures = {entry.source_identity: blue for entry in (high, same_value, gate)}

    assert _colour_pair_diagnostics(((high, "risk"), (same_value, "risk")), figures)[0] == (
        "W_LEGEND_COLOR_NOT_SEPARABLE:normal:0.0",
    )
    assert _colour_pair_diagnostics(((high, "risk"), (gate, "risk")), figures) == ((), ())

    wrong_delta = (ScaleCollision("risk", "high", "gate", "normal", 0.001),)
    uncovered = SurfaceLegendEntry("gate:gate", "GATE", view_scale_id="risk",
                                   view_scale_domain_value="gate", scale_collisions=wrong_delta)
    assert _colour_pair_diagnostics(((high, "risk"), (uncovered, "risk")),
                                    {high.source_identity: blue, uncovered.source_identity: blue})[0] == (
        "W_LEGEND_COLOR_NOT_SEPARABLE:normal:0.0",
    )


def test_unencoded_pairs_and_missing_or_empty_figures_do_not_emit_findings():
    first = _entry("first", "First")
    second = _entry("second", "Second")
    blue = _figure(_paint(("solid", "#0000FF")))
    assert _colour_pair_diagnostics(((first, None), (second, None)),
                                    {"first": blue, "second": blue}) == ((), ())
    assert _colour_pair_diagnostics(((first, "scale"), (second, None)), {}) == ((), ())
    assert _colour_pair_diagnostics((), {"first": blue}) == ((), ())


def test_duplicate_source_identity_is_not_compared_with_itself():
    first, repeated = _entry("shared", "First"), _entry("shared", "Repeated")
    figures = {"shared": _figure(_paint(("solid", "#0000FF")))}
    assert _colour_pair_diagnostics(((first, "risk"), (repeated, "other")), figures) == ((), ())


def test_a_completed_key_without_visible_figure_ink_is_not_compared():
    first, second = _entry("first", "First"), _entry("second", "Second")
    blue = _figure(_paint(("solid", "#0000FF")))
    for absent in (None, (), _figure(_paint(("solid", "#0000FF"), opacity=0))):
        assert _colour_pair_diagnostics(((first, "risk"), (second, None)),
                                        {"first": blue, "second": absent}) == ((), ())


def test_claimed_colour_vision_is_checked_with_the_existing_minimum_palette_distance():
    gold = _entry("scale:gold", "GOLD")
    olive = _entry("semantic:olive", "OLIVE")
    figures = {
        gold.source_identity: _figure(_paint(("solid", "#B8860B"))),
        olive.source_identity: _figure(_paint(("solid", "#6B8E23"))),
    }

    diagnostics, provenance = _colour_pair_diagnostics(((gold, "risk"), (olive, None)), figures,
                                                        color_vision=("protanopia",))

    assert diagnostics == ("W_LEGEND_COLOR_NOT_SEPARABLE:protanopia:1.487",)
    assert len(provenance) == 1 and provenance[0].diagnostic == diagnostics[0]
    assert provenance[0].subjects == (
        DiagnosticSubject("legend-key:scale:gold", "GOLD (risk)"),
        DiagnosticSubject("legend-key:semantic:olive", "OLIVE (risk)"),
    )


def test_view_and_style_entries_expose_their_typed_encoding_scale_identity():
    view = SurfaceLegendEntry("scale:risk:high", "HIGH", view_scale_id="risk",
                              view_scale_domain_value="high")
    style = SurfaceLegendEntry("style:key", "High", style_scope=StyleLegendScope(
        "severity", "high-risk", "severity-scale", "field:risk", None, False),
        style_value="high")

    assert view.encoding_scale_id == "risk"
    assert view.encoding_domain_value == "high"
    assert style.view_scale_id is None
    assert style.encoding_scale_id == "severity-scale"


@pytest.mark.parametrize("scale_id", ["", 3])
def test_invalid_view_scale_identity_is_rejected(scale_id):
    with pytest.raises(ValueError, match="non-empty string"):
        SurfaceLegendEntry("scale:risk:high", "HIGH", view_scale_id=scale_id,
                           view_scale_domain_value="high")


def test_view_and_style_scale_identities_cannot_be_ambiguous():
    scope = StyleLegendScope("severity", "high-risk", "severity-scale", "field:risk", None, False)
    with pytest.raises(ValueError, match="both View and Style"):
        SurfaceLegendEntry("style:key", "High", style_scope=scope, style_value="high",
                           view_scale_id="risk", view_scale_domain_value="high")

