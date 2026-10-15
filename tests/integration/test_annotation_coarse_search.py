"""Whole-region retry follows every ordinary annotation candidate (#1568)."""
from __future__ import annotations

from copy import deepcopy

from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr


def test_later_fine_candidate_precedes_first_candidate_coarse_retry(tmp_path):
    source = ak.project(kinds=("risk", "risk"))
    parts = sr.bundle()
    ak.with_view_notes(parts, source)
    ak.with_kind_theme(parts)
    annotations = parts["view"]["body"]["annotations"]
    shared_anchor = deepcopy(annotations[0]["anchor"])
    candidates = [
        sr.candidate("plot-near", connector="none", max_positions=1),
        sr.candidate("plot-wide", connector="none", max_positions=1024),
    ]
    for annotation in annotations:
        annotation["anchor"] = deepcopy(shared_anchor)
        annotation["candidates"] = deepcopy(candidates)

    rendered = ak.render(tmp_path, source, parts)
    diagnostics = rendered.scene.diagnostics
    assert any(item.startswith("W_LAYOUT_ANNOTATION_CANDIDATE_FALLBACK:view-n1:plot-wide")
               for item in diagnostics)
    assert not any(item.startswith("W_LAYOUT_LABEL_OVERFLOW:annotation-text:view-n1")
                   for item in diagnostics)
    by_id = {item.scene_id: item for item in rendered.surface.primitives}
    first, second = by_id["annotation-box:view-n0"], by_id["annotation-box:view-n1"]
    assert not _overlaps(first.bounds, second.bounds)


def test_crowded_neighborhood_retries_across_plot_and_keeps_boxes_separate(tmp_path):
    source = ak.project(kinds=("risk", "risk"))
    parts = sr.bundle()
    ak.with_view_notes(parts, source)
    ak.with_kind_theme(parts)
    annotations = parts["view"]["body"]["annotations"]
    shared_anchor = deepcopy(annotations[0]["anchor"])
    candidate = sr.candidate("plot-near", connector="none", max_positions=1)
    for annotation in annotations:
        annotation["anchor"] = deepcopy(shared_anchor)
        annotation["candidates"] = [deepcopy(candidate)]

    rendered = ak.render(tmp_path, source, parts)
    by_id = {item.scene_id: item for item in rendered.surface.primitives}
    first, second = by_id["annotation-box:view-n0"], by_id["annotation-box:view-n1"]
    assert not _overlaps(first.bounds, second.bounds)
    assert not any(item.startswith("W_LAYOUT_LABEL_OVERFLOW:")
                   for item in rendered.scene.diagnostics)


def _overlaps(left, right):
    x, y, width, height = left
    ox, oy, owidth, oheight = right
    return x < ox + owidth and ox < x + width and y < oy + oheight and oy < y + height
