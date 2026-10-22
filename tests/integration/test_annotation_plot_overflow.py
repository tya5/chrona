"""Visible-overflow completion after an annotation exhausts nearest-free plot search."""
from __future__ import annotations

from copy import deepcopy

import pytest

from chrona.usecases.render_review import RenderFailed
from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr


def _render(tmp_path, *, max_positions: int):
    source = ak.project(kinds=("risk", "risk"), text="Required synthetic plot annotation text.")
    parts = sr.bundle()
    if max_positions == 1:
        # This is the explicit exhausted-search fixture: the legal plot cannot
        # contain the measured callout at all, so neither coarse nor fine
        # search has a box to accept and the existing visible fallback applies.
        sr.fix_inline(parts, "timeline", 20, token="tiny-timeline-inline")
        sr.fix_block(parts, "timeline", 20, token="tiny-timeline-block")
    ak.with_view_notes(parts, source)
    ak.with_kind_theme(parts)
    view_annotations = parts["view"]["body"]["annotations"]
    shared_anchor = deepcopy(view_annotations[0]["anchor"])
    candidate = sr.candidate("plot-near", connector="none", max_positions=max_positions)
    for annotation in view_annotations:
        annotation["anchor"] = deepcopy(shared_anchor)
        annotation["candidates"] = [deepcopy(candidate)]
    return ak.render(tmp_path, source, parts)


def _by_id(rendered):
    return {item.scene_id: item for item in rendered.surface.primitives}


def test_exhausted_nearest_free_plot_candidate_requires_an_explicit_safe_fallback(tmp_path):
    with pytest.raises(RenderFailed) as failure:
        _render(tmp_path, max_positions=1)

    assert failure.value.code == "E_LAYOUT_ANNOTATION_FALLBACK_REQUIRED"
    assert failure.value.source_ref.startswith("/body/")


def test_fitting_nearest_free_plot_candidates_remain_fit(tmp_path):
    rendered = _render(tmp_path, max_positions=1024)
    ids = _by_id(rendered)

    assert ids["annotation-text:view-n0"].text_layout is not None
    assert ids["annotation-text:view-n1"].text_layout is not None
    assert not any(item.code == "W_LAYOUT_LABEL_OVERFLOW" for item in rendered.surface.fit_warnings)

def test_exhausted_nearest_free_tail_requires_an_explicit_safe_fallback(tmp_path):
    source = ak.project(kinds=("risk",), text="Required synthetic plot annotation text.")
    parts = sr.bundle()
    sr.fix_inline(parts, "timeline", 20, token="tiny-tail-timeline-inline")
    sr.fix_block(parts, "timeline", 20, token="tiny-tail-timeline-block")
    sr.with_balloon_notes(parts)
    ak.with_view_notes(parts, source)
    annotation = parts["view"]["body"]["annotations"][0]
    annotation["candidates"] = [sr.candidate("plot-tail", connector="tail", max_positions=1)]
    with pytest.raises(RenderFailed) as failure:
        ak.render(tmp_path, source, parts)

    assert failure.value.code == "E_LAYOUT_ANNOTATION_FALLBACK_REQUIRED"
    assert failure.value.source_ref.startswith("/body/")


def test_fitting_nearest_free_tail_candidates_remain_fit(tmp_path):
    source = ak.project(kinds=("risk",), text="Required synthetic plot annotation text.")
    parts = sr.bundle()
    sr.with_balloon_notes(parts)
    ak.with_view_notes(parts, source)
    parts["view"]["body"]["annotations"][0]["candidates"] = [
        sr.candidate("plot-tail", connector="tail", max_positions=1024)]

    rendered = ak.render(tmp_path, source, parts)
    ids = _by_id(rendered)
    assert ids["annotation-box:view-n0"].kind.value == "Symbol"
    assert ids["annotation-text:view-n0"].text_layout is not None
    assert not any(item.code == "W_LAYOUT_LABEL_OVERFLOW" for item in rendered.surface.fit_warnings)
