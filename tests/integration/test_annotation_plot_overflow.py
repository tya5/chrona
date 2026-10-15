"""Visible-overflow completion after an annotation exhausts nearest-free plot search."""
from __future__ import annotations

from copy import deepcopy
from xml.etree import ElementTree

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


def test_exhausted_nearest_free_plot_candidate_emits_visible_overflow_scene_and_svg(tmp_path):
    rendered = _render(tmp_path, max_positions=1)
    ids = _by_id(rendered)

    assert "annotation-box:view-n1" in ids
    assert ids["annotation-text:view-n1"].text_layout is not None
    kind_text = [item for item in rendered.surface.primitives
                 if item.scene_id.startswith(("annotation-kind-text:view-n1:",
                                               "annotation-heading:view-n1:"))]
    assert kind_text

    warnings = {item.placement_id: item for item in rendered.surface.fit_warnings
                if item.code == "W_LAYOUT_LABEL_OVERFLOW"}
    assert warnings["annotation-text:view-n1"].behaviour == "visible-overflow"
    assert all(warnings[item.scene_id].behaviour == "visible-overflow" for item in kind_text)

    first_kind = next(item for item in rendered.surface.primitives
                      if item.scene_id.startswith("annotation-kind-text:view-n0:"))
    second_kind = kind_text[0]
    assert _overlaps(first_kind.bounds, second_kind.bounds)
    assert _overlaps(ids["annotation-text:view-n0"].bounds,
                     ids["annotation-text:view-n1"].bounds)

    svg_ids = {node.attrib["data-scene-id"] for node in ElementTree.fromstring(rendered.artifact.content).iter()
               if "data-scene-id" in node.attrib}
    assert "annotation-box:view-n1" in svg_ids
    assert "annotation-text:view-n1" in svg_ids
    assert any(scene_id.startswith("annotation-kind-text:view-n1:") for scene_id in svg_ids)


def test_fitting_nearest_free_plot_candidates_remain_fit(tmp_path):
    rendered = _render(tmp_path, max_positions=1024)
    ids = _by_id(rendered)

    assert ids["annotation-text:view-n0"].text_layout is not None
    assert ids["annotation-text:view-n1"].text_layout is not None
    assert not any(item.code == "W_LAYOUT_LABEL_OVERFLOW" for item in rendered.surface.fit_warnings)


def _overlaps(left, right):
    x, y, width, height = left
    ox, oy, owidth, oheight = right
    return x < ox + owidth and ox < x + width and y < oy + oheight and oy < y + height
