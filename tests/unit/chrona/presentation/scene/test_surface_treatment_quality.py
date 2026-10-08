from copy import deepcopy

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.paint_analysis import blend_over, sample_linear_gradient
from chrona.presentation.scene.perceptibility import evaluate_scene_perceptibility
from tests.unit.chrona.presentation.scene.test_surface_overprint import (
    _bounds,
    _radial,
    _sparse,
)


def _mark(*, bounds=None, kind="Rect"):
    return {"id": "subject", "kind": kind, "visualRole": "planned", "purpose": "planned",
            "slotId": "content", "paintOrder": 10, "bounds": bounds or _bounds(),
            "paint": {"fill": "#000000", "opacity": 1}}


def _scene(*primitives, canvas=None):
    primitives = deepcopy(primitives)
    for item in primitives:
        item.setdefault("kind", "Rect")
        item.setdefault("slotId", "content")
        if "pattern" in item:
            item["pattern"].update(densityBasisPoints=100, cornerRadius=0)
    return {"version": "chrona/scene/v0.7", "kind": "scene", "surfaces": [{
        "id": "synthetic", "slots": [{"id": "content", "bounds": _bounds(0, 0, 20, 20), "overflow": "fit"}],
        "canvasPaint": canvas or {"fill": "#ffffff", "opacity": 1}, "primitives": list(primitives)}]}


def _contrast(scene):
    return next(item for item in evaluate_scene_contrast(scene) if item.primitive_id == "subject")


def _perceptibility_ratio(scene):
    finding = next(item for item in evaluate_scene_perceptibility(scene)
                   if item.code == "I_SCENE_PAINT_CONTRAST" and item.primitive_ids == ("subject",))
    return dict(finding.measured_facts)["contrastRatio"]


def _underlay():
    value = _sparse(opacity=1, order=0)
    value.update(id="rain", visualRole="canvas-texture")
    return value


def test_both_gates_observe_opaque_overprint_erasure_not_flat_canvas_contrast():
    scene = _scene(_mark(kind="Text"), _radial(opacity=1))
    finding = _contrast(scene)
    assert finding.contrast_ratio == _perceptibility_ratio(scene) == 1
    assert finding.code == "E_SCENE_MARK_CONTRAST"
    assert (finding.ground_kind, finding.ground_id) == ("overlay-blend", "vignette")
    assert "E_SCENE_TEXT_OCCLUDED" not in {item.code for item in evaluate_scene_perceptibility(scene)}


def test_sparse_overprint_conservative_pairs_are_shared_by_both_gates():
    scene = _scene(_mark(), _sparse(opacity=0.5))
    finding = _contrast(scene)
    assert finding.contrast_ratio == _perceptibility_ratio(scene)
    assert finding.ground_color == blend_over(ink="#ff0000", opacity=0.5, ground="#ffffff")
    assert finding.ground_kind == "overlay-blend"


def test_transparent_underlay_uses_actual_ink_and_preserves_holes():
    touched = _scene(_underlay(), _mark())
    hole = _scene(_underlay(), _mark(bounds=_bounds(4, 4, 1, 1)))
    assert (_contrast(touched).ground_kind, _contrast(touched).ground_color) == ("pattern-ink", "#ff0000")
    assert (_contrast(hole).ground_kind, _contrast(hole).ground_color) == ("canvas", "#ffffff")
    assert _contrast(touched).contrast_ratio == _perceptibility_ratio(touched)


def test_later_opaque_host_hides_underlay_but_translucent_host_composes_over_ink():
    host = {"id": "host", "kind": "Rect", "visualRole": "unclassified", "purpose": "panel",
            "slotId": "content", "paintOrder": 5, "bounds": _bounds(0, 0, 20, 20),
            "paint": {"fill": "#ffffff", "opacity": 1}}
    opaque = _scene(_underlay(), host, _mark())
    assert _contrast(opaque).ground_color == "#ffffff"
    translucent_host = deepcopy(host)
    translucent_host["paint"] = {"fill": "#000000", "opacity": 0.5}
    translucent = _scene(_underlay(), translucent_host, _mark())
    assert _contrast(translucent).ground_color == "#800000"
    assert _contrast(translucent).ground_kind == "translucent-over-pattern-ink"
    assert _contrast(translucent).contrast_ratio == _perceptibility_ratio(translucent)


def test_canvas_gradient_is_the_real_backdrop_visible_through_underlay_holes():
    gradient = {"start": [0, 0], "end": [20, 0], "stops": [
        {"offset": 0, "color": "#000000"}, {"offset": 1, "color": "#ffffff"}], "fidelity": "required"}
    scene = _scene(_underlay(), _mark(bounds=_bounds(4, 4, 1, 1)),
                   canvas={"fill": "#ffffff", "opacity": 1, "gradient": gradient})
    assert _contrast(scene).ground_color == sample_linear_gradient(gradient, (4.5, 4.5))
    assert _contrast(scene).contrast_ratio == _perceptibility_ratio(scene)


def test_pattern_candidate_overflow_is_fail_closed_in_both_gates():
    overlay = _sparse()
    overlay["pattern"].update(tileInlineSize=0.001, tileBlockSize=0.001)
    scene = _scene(_mark(), overlay)
    assert _contrast(scene).code == "E_SCENE_CONTRAST_GROUND_UNSUPPORTED"
    assert any(item.code == "E_SCENE_CONTRAST_GROUND_UNSUPPORTED"
               for item in evaluate_scene_perceptibility(scene))


def test_decoration_dominant_substrate_policy_is_unchanged_by_surface_overprint():
    decoration = _mark()
    decoration.update(visualRole="row-band", purpose="row-decoration")
    before = _contrast(_scene(decoration))
    after = _contrast(_scene(decoration, _radial(opacity=1)))
    assert before == after
