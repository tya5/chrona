"""Visible-overflow completion after an annotation exhausts nearest-free plot search."""
from __future__ import annotations

from copy import deepcopy
from xml.etree import ElementTree

from chrona.presentation.layout.labels import LabelRect
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


def test_exhausted_nearest_free_tail_keeps_visible_integrated_balloon_and_anchor_tip(tmp_path):
    source = ak.project(kinds=("risk",), text="Required synthetic plot annotation text.")
    parts = sr.bundle()
    sr.fix_inline(parts, "timeline", 20, token="tiny-tail-timeline-inline")
    sr.fix_block(parts, "timeline", 20, token="tiny-tail-timeline-block")
    sr.with_balloon_notes(parts)
    ak.with_view_notes(parts, source)
    annotation = parts["view"]["body"]["annotations"][0]
    annotation["candidates"] = [sr.candidate("plot-tail", connector="tail", max_positions=1)]
    rendered = ak.render(tmp_path, source, parts)
    ids = _by_id(rendered)

    balloon = ids["annotation-box:view-n0"]
    # Scene's native path-backed symbol is how the completed Balloon geometry
    # is represented and serialized by this adapter.
    assert balloon.kind.value == "Symbol" and balloon.symbol is not None
    assert ids["annotation-text:view-n0"].text_layout is not None
    assert "annotation-leader:view-n0" not in ids
    assert any(item.placement_id == "annotation-text:view-n0" and item.behaviour == "visible-overflow"
               for item in rendered.surface.fit_warnings if item.code == "W_LAYOUT_LABEL_OVERFLOW")
    anchor = next(item for item in rendered.surface.primitives
                  if item.source_ref == "t0" and item.visual_role == "planned" and item.kind == "Rect")
    anchor_bounds = LabelRect(*anchor.bounds)
    outline_points = tuple(point for command in balloon.symbol.outline for point in command.points)
    tip = next(point for point in outline_points
               if point[0] < balloon.bounds[0] or point[0] > balloon.bounds[0] + balloon.bounds[2]
               or point[1] < balloon.bounds[1] or point[1] > balloon.bounds[1] + balloon.bounds[3])
    # The integrated tail tip reaches the selected temporal body anchor inside
    # its completed mark; it is not a detached box or substituted leader.
    assert anchor_bounds.x <= tip[0] <= anchor_bounds.right
    assert anchor_bounds.y <= tip[1] <= anchor_bounds.bottom
    svg = {node.attrib.get("data-scene-id"): node for node in ElementTree.fromstring(rendered.artifact.content).iter()
           if node.attrib.get("data-scene-id")}
    assert svg[balloon.scene_id].tag.endswith("path")
    data = svg[balloon.scene_id].attrib["d"]
    point_text = tuple(f"{value:.3f}".rstrip("0").rstrip(".") for value in tip)
    assert f"{point_text[0]} {point_text[1]}" in data


def _overlaps(left, right):
    x, y, width, height = left
    ox, oy, owidth, oheight = right
    return x < ox + owidth and ox < x + width and y < oy + oheight and oy < y + height
