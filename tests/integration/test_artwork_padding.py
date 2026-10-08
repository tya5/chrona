"""#1150: an artwork container's padding is measured from the artwork's inner edge.

`contentPaddingEm` replaces the absolute `contentInsetEm`: the content inset on a side is that side's widest
artwork fixed border (`sliceInsets` x `unitEm`) plus the padding. Synthetic notes through the packaged
`executive-light` bundle and `chrona-target-parts` glyphs; no `examples/` input.
"""
from __future__ import annotations

import pytest

from tests.integration.test_annotation_artwork import _render, _sub
from tests.support import annotation_artwork as aw

PADDING = {"top": 0.4, "right": 0.5, "bottom": 0.6, "left": 0.7}
SIDES = ("top", "right", "bottom", "left")
UNIT = 0.09


def _inset(insets: dict, padding: dict) -> dict:
    return {side: insets[side] * UNIT + padding[side] for side in SIDES}


def _bounds(rendered) -> dict:
    return {item.scene_id: tuple(round(float(v), 6) for v in item.bounds) for item in rendered.surface.primitives}


def _padded(tmp_path, name, insets):
    return _render(_sub(tmp_path, name), content=None, insets=insets, unit_em=UNIT, extra={"contentPaddingEm": PADDING})


def _absolute(tmp_path, name, insets):
    return _render(_sub(tmp_path, name), content=_inset(insets, PADDING), insets=insets, unit_em=UNIT)


@pytest.mark.parametrize("insets", [aw.SCROLL_INSETS, {"top": 4, "right": 2, "bottom": 6, "left": 3}])
def test_the_padding_from_the_inner_edge_is_the_slice_inset_plus_the_padding(tmp_path, insets):
    assert _bounds(_padded(tmp_path, "padded", insets)) == _bounds(_absolute(tmp_path, "absolute", insets))


def test_swapping_the_artwork_keeps_the_declared_padding_from_its_inner_edge(tmp_path):
    thin = {"top": 2, "right": 1, "bottom": 2, "left": 1}
    wide = aw.SCROLL_INSETS
    thin_render, wide_render = _padded(tmp_path, "thin", thin), _padded(tmp_path, "wide", wide)
    for rendered, insets in ((thin_render, thin), (wide_render, wide)):
        ids = {item.scene_id: item for item in rendered.surface.primitives}
        bx, by, bw, bh = ids["annotation-box:view-n0"].bounds
        tx, ty, tw, th = ids["annotation-text:view-n0"].bounds
        want = _inset(insets, PADDING)
        assert tx - bx >= want["left"] * 14 - 1e-6 and ty - by >= want["top"] * 14 - 1e-6
        assert (bx + bw) - (tx + tw) >= want["right"] * 14 - 1e-6 and (by + bh) - (ty + th) >= want["bottom"] * 14 - 1e-6
    thin_box = {item.scene_id: item for item in thin_render.surface.primitives}["annotation-box:view-n0"].bounds
    wide_box = {item.scene_id: item for item in wide_render.surface.primitives}["annotation-box:view-n0"].bounds
    assert wide_box[3] - thin_box[3] == pytest.approx(
        (_inset(wide, PADDING)["top"] + _inset(wide, PADDING)["bottom"]
         - _inset(thin, PADDING)["top"] - _inset(thin, PADDING)["bottom"]) * 14, abs=1e-6)


@pytest.mark.parametrize("kwargs", [
    {"content": aw.CONTENT_INSET},                      # both the absolute inset and the padding
    {"artwork_declared": False},                        # no artwork to measure from
    {"outline": "balloon"},                             # artwork belongs to a rectangle
])
def test_a_padding_without_its_artwork_or_beside_an_absolute_inset_is_rejected(tmp_path, kwargs):
    kwargs = {"content": None} | kwargs
    with pytest.raises(Exception) as failure:
        _render(tmp_path, extra={"contentPaddingEm": PADDING}, **kwargs)
    assert "E_THEME_TOKEN_TYPE" in str(failure.value) or "E_THEME_SCHEMA" in str(failure.value)
