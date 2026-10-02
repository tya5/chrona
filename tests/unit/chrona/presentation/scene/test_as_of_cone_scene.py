"""The as-of cone completes into a fading gradient polygon, follows the #478 ladder and is gated as ground (#890).

Synthetic Themes and Scenes only: nothing here reads `examples/`.
"""
from __future__ import annotations

import pytest

from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.scene.capabilities import theme_role_contract, theme_role_property_consumer
from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.paint import ScenePaintError, resolve_cone_paint
from chrona.presentation.scene.paint_analysis import blend_over, composited_contrast
from chrona.presentation.scene.visual_capabilities import BASELINE_PROFILE, SVG_PROFILE, resolve_visual_profile

BOUNDS = (200.0, 50.0, 100.0, 180.0)
INK = "#FFC800"


def _tokens(*, fidelity: str | None = None, strength=0.5, fill=True, **extra) -> ThemeTokenView:
    values = {"ink": {"type": "color", "value": INK}, "strength": {"type": "number", "value": strength},
              "over": {"type": "number", "value": 1.5},
              "must": {"type": "fidelity", "value": "required"},
              "soft": {"type": "fidelity", "value": "decorative-optional"},
              "odd": {"type": "fidelity", "value": "sometimes"}}
    role = {"opacity": "strength", **extra}
    if fill:
        role["fill"] = "ink"
    if fidelity is not None:
        role["gradientFidelity"] = fidelity
    return ThemeTokenView({"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme", "body": {
        "values": values, "roles": {"as-of-cone": role}, "metrics": {}}})


def test_the_gradient_runs_from_the_apex_to_the_foot_and_fades_to_transparent() -> None:
    result = resolve_cone_paint(_tokens(), "as-of-cone", visual_profile=None, bounds=BOUNDS)
    gradient = result.paint.gradient

    assert result.omissions == ()
    assert (gradient.start, gradient.end) == ((250.0, 50.0), (250.0, 230.0))
    assert gradient.stops == ((0.0, INK), (1.0, INK)) and gradient.stop_opacities == (1.0, 0.0)
    assert (result.paint.fill, result.paint.stroke, result.paint.opacity) == (INK, None, 0.5)


def test_the_strength_is_the_role_opacity_and_defaults_to_one() -> None:
    tokens = ThemeTokenView({"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme", "body": {
        "values": {"ink": {"type": "color", "value": INK}}, "roles": {"as-of-cone": {"fill": "ink"}}, "metrics": {}}})

    assert resolve_cone_paint(tokens, "as-of-cone", visual_profile=None, bounds=BOUNDS).paint.opacity == 1.0


def test_a_rich_profile_paints_the_cone() -> None:
    result = resolve_cone_paint(_tokens(), "as-of-cone", visual_profile=resolve_visual_profile(SVG_PROFILE, "svg"), bounds=BOUNDS)

    assert result.paint is not None and result.omissions == ()


def test_the_baseline_omits_a_decorative_optional_cone_whole_and_reports_it() -> None:
    result = resolve_cone_paint(_tokens(fidelity="soft"), "as-of-cone",
                                visual_profile=resolve_visual_profile(BASELINE_PROFILE, "svg"), bounds=BOUNDS)
    omission = result.omissions[0]

    assert result.paint is None  # never a flat ink polygon
    assert (omission.role, omission.treatment, omission.source_ref) == ("as-of-cone", "as-of-cone", "/body/roles/as-of-cone/coneSpread")
    assert (omission.visual_profile, omission.target_kind, omission.paintable_profile) == (BASELINE_PROFILE, "svg", SVG_PROFILE)
    assert omission.scene_diagnostic() == (f"I_VISUAL_TREATMENT_OMITTED:role=as-of-cone;treatment=as-of-cone;"
                                           f"profile={BASELINE_PROFILE};paintable={SVG_PROFILE}")


@pytest.mark.parametrize("fidelity", ["must", None])
def test_the_baseline_fails_a_required_cone_before_serialization(fidelity) -> None:
    with pytest.raises(ScenePaintError) as caught:
        resolve_cone_paint(_tokens(fidelity=fidelity), "as-of-cone",
                           visual_profile=resolve_visual_profile(BASELINE_PROFILE, "svg"), bounds=BOUNDS)

    assert caught.value.diagnostic_id == "E_VISUAL_CAPABILITY_UNSUPPORTED"
    assert caught.value.path == "/body/roles/as-of-cone/coneSpread"


def test_an_unknown_fidelity_a_missing_ink_and_an_overstrong_opacity_fail_at_their_pointers() -> None:
    with pytest.raises(ScenePaintError) as fidelity:
        resolve_cone_paint(_tokens(fidelity="odd"), "as-of-cone", visual_profile=None, bounds=BOUNDS)
    with pytest.raises(ScenePaintError) as ink:
        resolve_cone_paint(_tokens(fill=False), "as-of-cone", visual_profile=None, bounds=BOUNDS)
    with pytest.raises(ScenePaintError) as strong:
        resolve_cone_paint(_tokens(strength=1.5), "as-of-cone", visual_profile=None, bounds=BOUNDS)

    assert (fidelity.value.diagnostic_id, fidelity.value.path) == ("E_VISUAL_CAPABILITY_FIDELITY", "/body/roles/as-of-cone/gradientFidelity")
    assert (ink.value.diagnostic_id, ink.value.path) == ("E_THEME_ROLE_REQUIRED", "/body/roles/as-of-cone/fill")
    assert (strong.value.diagnostic_id, strong.value.path) == ("E_PRESENTATION_PAINT_INVALID", "/body/roles/as-of-cone/opacity")


def test_the_role_is_admitted_for_ink_strength_spread_extent_and_fidelity_only() -> None:
    for name in ("fill", "opacity", "coneSpread", "coneExtent", "gradientFidelity"):
        assert theme_role_property_consumer("as-of-cone", name) is not None
    for name in ("stroke", "strokeWidth", "dash", "pattern", "backgroundPaintOrder", "glowBlur", "shadowBlur",
                 "gradientStart", "gradientAngle", "markPaintOrder"):
        assert theme_role_property_consumer("as-of-cone", name) is None
    assert theme_role_contract("as-of-cone").scene_kinds == frozenset(("Symbol",))


# --- the contrast ground -------------------------------------------------------------------------------------

CANVAS = "#FFFFFF"


def _scene(*primitives):
    return {"version": "chrona/scene/v0.7", "kind": "scene", "surfaces": [{
        "id": "review", "canvasPaint": {"fill": CANVAS, "opacity": 1}, "primitives": list(primitives),
        "decorationDispositions": []}]}


def _cone(*, strength=0.6, order=50, ink=INK):
    # A cone from the apex (250, 50) widening to half-width 50 at the foot (y 250): spread 0.25, extent 1.
    outline = [("move", (250.0, 50.0)), ("line", (300.0, 250.0)), ("line", (200.0, 250.0)), ("line", (250.0, 50.0))]
    return {"id": "as-of-cone", "visualRole": "as-of-cone", "purpose": "as-of-cone", "kind": "Symbol", "paintOrder": order,
            "bounds": {"inline": 200.0, "block": 50.0, "inlineSize": 100.0, "blockSize": 200.0},
            "symbol": {"outline": [{"kind": kind, "points": [list(point)]} for kind, point in outline]},
            "paint": {"fill": ink, "opacity": strength, "gradient": {
                "start": [250.0, 50.0], "end": [250.0, 250.0], "fidelity": "required",
                "stops": [{"offset": 0, "color": ink, "opacity": 1}, {"offset": 1, "color": ink, "opacity": 0}]}}}


def _mark(identifier="bar", *, block, height=10.0, inline=240.0, width=20.0, fill="#F4C000", order=100, role="planned",
          purpose="planned", stroke=None):
    value = {"id": identifier, "visualRole": role, "purpose": purpose, "kind": "Rect", "paintOrder": order,
             "bounds": {"inline": inline, "block": block, "inlineSize": width, "blockSize": height},
             "paint": {"fill": fill, "opacity": 1}}
    if stroke:
        value["paint"].update({"stroke": stroke, "strokeWidth": 1})
    return value


def _band(identifier="band", *, fill="#FFE9B0", order=10):
    return {"id": identifier, "visualRole": "row-band", "purpose": "row-decoration", "kind": "Rect", "paintOrder": order,
            "bounds": {"inline": 0.0, "block": 0.0, "inlineSize": 600.0, "blockSize": 300.0},
            "paint": {"fill": fill, "opacity": 1}}


def _finding(scene, identifier="bar"):
    return next(item for item in evaluate_scene_contrast(scene) if item.primitive_id == identifier)


def _ratio(mark_fill, ground):
    return composited_contrast(fill=mark_fill, opacity=1.0, ground=ground)


def test_a_mark_in_the_cone_is_judged_on_the_ink_composited_at_the_strength_the_gradient_has_there() -> None:
    # The mark spans y 140..150 inside the cone; the gradient has faded to 0.6 * (1 - (140 - 50) / 200) at its top.
    finding = _finding(_scene(_cone(), _mark(block=140.0)))
    top = blend_over(ink=INK, opacity=0.6 * (1 - 90 / 200), ground=CANVAS)
    bottom = blend_over(ink=INK, opacity=0.6 * (1 - 100 / 200), ground=CANVAS)

    assert finding.ground_kind == "cone-blend" and finding.ground_id == "as-of-cone"
    assert finding.contrast_ratio == pytest.approx(min(_ratio("#F4C000", top), _ratio("#F4C000", bottom)))
    assert finding.contrast_ratio < _ratio("#F4C000", CANVAS)  # the cone made the ground harder, and the gate saw it


def test_the_worst_of_the_stops_a_mark_spans_decides_not_its_centre() -> None:
    mark = _mark(block=60.0, height=180.0, inline=245.0, width=10.0, fill="#C89600")  # a tall mark across most of the gradient
    finding = _finding(_scene(_cone(strength=1.0), mark))
    centre = blend_over(ink=INK, opacity=1.0 * (1 - (150 - 50) / 200), ground=CANVAS)
    ends = [blend_over(ink=INK, opacity=1.0 * (1 - (block - 50) / 200), ground=CANVAS) for block in (60.0, 240.0)]

    assert finding.contrast_ratio == pytest.approx(min(_ratio("#C89600", ground) for ground in ends))
    assert finding.contrast_ratio <= _ratio("#C89600", centre) + 1e-9


def test_a_mark_the_cone_does_not_reach_keeps_its_own_ground() -> None:
    outside = _finding(_scene(_cone(), _mark(block=140.0, inline=40.0)))
    below = _finding(_scene(_cone(), _mark(block=252.0)))
    without = _finding(_scene(_mark(block=140.0)))

    assert outside.ground_kind == below.ground_kind == without.ground_kind == "canvas"
    assert outside.contrast_ratio == below.contrast_ratio == without.contrast_ratio


def test_a_mark_straddling_the_edge_is_judged_on_the_cone_and_on_the_host() -> None:
    # The cone's half-width at y 145 is 0.25 * 95 = 23.75, so the edge is at x 273.75 and this mark crosses it.
    straddling = _finding(_scene(_cone(strength=1.0), _mark(block=140.0, inline=268.0, fill="#F4C000")))
    blended = blend_over(ink=INK, opacity=1.0 * (1 - 90 / 200), ground=CANVAS)

    assert straddling.contrast_ratio == pytest.approx(min(_ratio("#F4C000", blended), _ratio("#F4C000", CANVAS)))


def test_the_cone_tints_the_band_it_lies_over_not_the_canvas() -> None:
    finding = _finding(_scene(_band(), _cone(), _mark(block=140.0)))
    band = "#FFE9B0"
    expected = min(_ratio("#F4C000", blend_over(ink=INK, opacity=0.6 * (1 - block_offset / 200), ground=band))
                   for block_offset in (90, 100))

    assert finding.contrast_ratio == pytest.approx(expected)
    assert finding.ground_id == "as-of-cone"


def test_a_host_painted_after_the_cone_hides_it() -> None:
    covering = {"id": "panel", "visualRole": "unclassified", "purpose": "panel", "kind": "Rect", "paintOrder": 60,
                "bounds": {"inline": 230.0, "block": 120.0, "inlineSize": 60.0, "blockSize": 60.0},
                "paint": {"fill": "#222222", "opacity": 1}}

    finding = _finding(_scene(_cone(), covering, _mark(block=140.0, fill="#FFFFFF")))

    assert (finding.ground_id, finding.ground_kind, finding.ground_color) == ("panel", "flat", "#222222")


def test_a_mark_painted_below_the_cone_is_not_on_it() -> None:
    finding = _finding(_scene(_cone(), _mark(block=140.0, order=40)))

    assert finding.ground_kind == "canvas"


def test_a_state_text_is_gated_on_the_cone_too() -> None:
    label = _mark("variance", block=140.0, fill="#7A5A00", role="variance-behind", purpose="table-cell")
    label["contrastTreatment"] = "required"

    finding = _finding(_scene(_cone(strength=1.0), label), "variance")

    assert finding.code == "E_SCENE_STATE_TEXT_CONTRAST" and finding.ground_kind == "cone-blend"


def test_a_decoration_is_not_judged_against_the_cone() -> None:
    tint = _mark("tint", block=140.0, fill="#FFFFFF", role="row-band", purpose="row-decoration")

    assert _finding(_scene(_cone(strength=1.0), tint), "tint").ground_kind == "canvas"


def test_the_cone_has_no_contrast_floor_of_its_own() -> None:
    assert all(item.primitive_id != "as-of-cone" for item in evaluate_scene_contrast(_scene(_cone(strength=1.0))))


def test_a_cone_is_never_the_host_of_an_unrelated_ordinary_ground_lookup() -> None:
    """The cone's bounding box covers rows it does not tint: a mark off the polygon but inside the box keeps its host."""
    inside_box_outside_polygon = _mark(block=60.0, inline=205.0, width=10.0)  # the polygon is a few px wide at y 60

    assert _finding(_scene(_cone(), inside_box_outside_polygon)).ground_kind == "canvas"


def test_an_unreadable_cone_is_a_malformed_document_not_a_silent_skip() -> None:
    broken = _cone()
    broken["paint"]["gradient"]["stops"] = [{"offset": 0, "color": INK}, {"offset": 1, "color": INK}]  # no stop opacity

    with pytest.raises(Exception, match="E_SCENE_CONTRAST_DOCUMENT"):
        evaluate_scene_contrast(_scene(broken, _mark(block=140.0)))


DARK = "#101010"  # a dark ink makes the cone's top the better ground for a pale mark and the canvas the worse one


def test_a_mark_straddling_the_edge_keeps_the_unblended_host_when_it_is_the_worse_ground() -> None:
    pale = _mark(block=140.0, inline=268.0, fill="#FFFFFF")
    finding = _finding(_scene(_cone(strength=1.0, ink=DARK), pale))

    assert finding.contrast_ratio == pytest.approx(1.0) and finding.ground_kind == "canvas"


def test_a_mark_wholly_inside_is_judged_on_the_blended_grounds_only() -> None:
    pale = _mark(block=140.0, inline=245.0, width=10.0, fill="#FFFFFF")
    finding = _finding(_scene(_cone(strength=1.0, ink=DARK), pale))

    assert finding.ground_kind == "cone-blend" and finding.contrast_ratio > 1.5


def test_a_tall_mark_is_judged_where_the_gradient_is_worst_for_it_not_at_its_top() -> None:
    # Dark ink fades to the canvas: for a white mark the foot end of the mark is the worse ground.
    tall = _mark(block=60.0, height=180.0, inline=249.0, width=2.0, fill="#FFFFFF")
    finding = _finding(_scene(_cone(strength=1.0, ink=DARK), tall))
    foot = blend_over(ink=DARK, opacity=1.0 * (1 - (240.0 - 50.0) / 200.0), ground=CANVAS)

    assert finding.contrast_ratio == pytest.approx(_ratio("#FFFFFF", foot))
