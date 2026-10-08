from copy import deepcopy

import pytest

from chrona.presentation.scene.ink_touch import InkTouchError
from chrona.presentation.scene.paint_analysis import blend_over, composited_contrast
from chrona.presentation.scene.surface_overprint import (
    ordered_overprint_pairs,
    sample_radial_gradient,
)


def _bounds(x=1, y=1, width=1, height=1):
    return {"inline": x, "block": y, "inlineSize": width, "blockSize": height}


def _subject():
    return {"id": "label", "paintOrder": 10, "bounds": _bounds()}


def _radial(*, opacity=0.5, order=20):
    return {"id": "vignette", "paintOrder": order, "visualRole": "canvas-overlay-gradient",
            "bounds": _bounds(0, 0, 20, 20), "paint": {"fill": "#000000", "opacity": opacity,
            "radialGradient": {"center": [10, 10], "radii": [5, 5], "fidelity": "required", "stops": [
                {"offset": 0, "color": "#000000", "opacity": 0},
                {"offset": 0.5, "color": "#000000", "opacity": 0},
                {"offset": 1, "color": "#000000", "opacity": 1}]}}}


def _sparse(*, opacity=0.5, order=30):
    return {"id": "grain", "paintOrder": order, "visualRole": "canvas-overlay",
            "kind": "Rect", "bounds": _bounds(0, 0, 20, 20),
            "paint": {"fill": None, "stroke": "#ff0000", "opacity": opacity},
            "pattern": {"tileInlineSize": 10, "tileBlockSize": 10, "angleDegrees": 0,
                "origin": [0, 0], "regionBounds": _bounds(0, 0, 20, 20), "clipBounds": _bounds(0, 0, 20, 20),
                "primitives": [{"kind": "circle", "cx": 2, "cy": 2, "radius": 1}]}}


def _pairs(overlays, *, subject=None, foreground="#000000", opacity=1, sample=(2, 2)):
    subject = subject or _subject()
    return ordered_overprint_pairs(subject, [subject, *overlays], 0, foreground=foreground, opacity=opacity,
                                     grounds=[("#ffffff", "canvas", "canvas")], sample=sample)


def test_radial_samples_declared_inner_plateau_outer_fade_and_clip():
    gradient = _radial()["paint"]["radialGradient"]
    assert sample_radial_gradient(gradient, (10, 10)) == ("#000000", 0)
    assert sample_radial_gradient(gradient, (12.5, 10)) == ("#000000", 0)
    assert sample_radial_gradient(gradient, (13.75, 10)) == ("#000000", 0.5)
    assert sample_radial_gradient(gradient, (20, 10)) == ("#000000", 1)
    assert _pairs([_radial()], sample=(21, 10)) == _pairs([])


def test_radial_overprint_tints_foreground_and_backdrop_not_just_ground():
    pair, = _pairs([_radial()], foreground="#112233")
    assert pair.foreground == blend_over(ink="#000000", opacity=0.5, ground="#112233")
    assert pair.backdrop == blend_over(ink="#000000", opacity=0.5, ground="#ffffff")
    assert (pair.ground_kind, pair.ground_id) == ("overlay-blend", "vignette")


def test_opaque_overlay_erases_contrast_instead_of_creating_fake_contrast():
    pair, = _pairs([_radial(opacity=1)], foreground="#ffffff")
    assert pair.foreground == pair.backdrop == "#000000"
    assert composited_contrast(fill=pair.foreground, opacity=1, ground=pair.backdrop) == 1


def test_sparse_overlay_keeps_covered_and_uncovered_pairs_in_scene_order():
    pairs = _pairs([_sparse(), _radial(order=40)])
    assert len(pairs) == 2
    base, covered = pairs
    assert base.foreground == "#000000" and base.backdrop == "#808080"
    red_foreground = blend_over(ink="#ff0000", opacity=0.5, ground="#000000")
    red_backdrop = blend_over(ink="#ff0000", opacity=0.5, ground="#ffffff")
    assert covered.foreground == blend_over(ink="#000000", opacity=0.5, ground=red_foreground)
    assert covered.backdrop == blend_over(ink="#000000", opacity=0.5, ground=red_backdrop)
    assert all(pair.ground_id == "vignette" for pair in pairs)
    assert _pairs([_radial(), _sparse()]) != pairs


def test_overlapping_same_color_tile_parts_apply_layer_opacity_only_once():
    overlay = _sparse()
    overlay["pattern"]["primitives"] *= 2
    assert _pairs([overlay]) == _pairs([_sparse()])


def test_holes_and_before_content_overlay_are_not_later_ink():
    subject = _subject()
    subject["bounds"] = _bounds(4, 4, 1, 1)
    assert _pairs([_sparse()], subject=subject) == _pairs([], subject=subject)
    assert _pairs([_radial(order=5)]) == _pairs([])


@pytest.mark.parametrize("mutation", ["opacity", "stop", "geometry"])
def test_invalid_overprint_fails_closed(mutation):
    overlay = deepcopy(_radial())
    if mutation == "opacity":
        overlay["paint"]["opacity"] = 2
    elif mutation == "stop":
        overlay["paint"]["radialGradient"]["stops"][1]["color"] = "#ffffff"
    else:
        overlay["paint"]["radialGradient"]["radii"][0] = 0
    with pytest.raises(InkTouchError):
        _pairs([overlay])


def test_oversized_serialized_radial_integer_fails_with_the_quality_error_boundary():
    overlay = _radial()
    overlay["paint"]["radialGradient"]["center"][0] = 10 ** 1000
    with pytest.raises(InkTouchError):
        _pairs([overlay])
