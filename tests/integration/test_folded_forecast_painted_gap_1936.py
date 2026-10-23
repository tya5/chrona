"""Folded forecast deltas reserve the title and measure authored gaps from painted mark ink."""
from dataclasses import replace
from xml.etree import ElementTree

import pytest

from chrona.resources import builtin_preset_source_root, safe_load
from chrona.usecases.draft_render import render_draft
from tests.integration.test_forecast_occurrence_coverage import _request, _write


def _render(tmp_path, *, stroke_width, authored_gap=None, monkeypatch=None, capture=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    request = _request(tmp_path, placement="plot", folded=True, viewport="2400xauto")
    theme_root = builtin_preset_source_root("presets/bundles/technical-print")
    theme = safe_load(theme_root.joinpath("theme.yaml").read_bytes())
    body = theme["body"]
    body["values"]["painted-gap-stroke"] = {"type": "number", "value": stroke_width}
    if authored_gap is not None:
        body["values"]["painted-label-gap"] = {"type": "number", "value": authored_gap}
        body["metrics"]["timeline.mark.labelGap"] = "painted-label-gap"
    body["roles"]["planned"]["strokeWidth"] = "painted-gap-stroke"
    if monkeypatch is not None:
        from chrona.presentation.layout import surface_composer
        prepare = surface_composer.prepare_member_labels

        def capture_allocations(context, requests, obstacles):
            session = prepare(context, requests, obstacles)
            if capture is not None:
                capture.extend(item for item in session._allocations
                               if item.request.placement_id == "variance:group-header:team:gate")
            return session

        with monkeypatch.context() as local_patch:
            local_patch.setattr(surface_composer, "prepare_member_labels", capture_allocations)
            return render_draft(replace(request, theme=_write(tmp_path / "theme.yaml", theme))).rendered
    return render_draft(replace(request, theme=_write(tmp_path / "theme.yaml", theme))).rendered


def _primitive(rendered, scene_id):
    return next(item for item in rendered.surface.primitives if item.scene_id == scene_id)


def test_folded_forecast_side_gap_uses_painted_envelope_and_keeps_title_reservation(tmp_path, monkeypatch):
    narrow_captures, wide_captures = [], []
    narrow_ink = _render(tmp_path / "narrow", stroke_width=4, authored_gap=20,
                         monkeypatch=monkeypatch, capture=narrow_captures)
    wide_ink = _render(tmp_path / "wide", stroke_width=12, authored_gap=20,
                       monkeypatch=monkeypatch, capture=wide_captures)
    mark_id = "planned:group-header:team:gate:part0"
    delta_id = "variance:group-header:team:gate"
    title_id = "member-label:group-header:team:gate"
    narrow_mark, wide_mark = _primitive(narrow_ink, mark_id), _primitive(wide_ink, mark_id)
    narrow_delta, wide_delta = _primitive(narrow_ink, delta_id), _primitive(wide_ink, delta_id)
    narrow_title, wide_title = _primitive(narrow_ink, title_id), _primitive(wide_ink, title_id)

    # Correcting completed mark ink can legitimately shift allocated lane positions.
    assert narrow_mark.bounds[2:] == wide_mark.bounds[2:]
    assert narrow_title.bounds[2:] == wide_title.bounds[2:]
    # Source closure may prepare more than once. Every attempt must carry the
    # same completed painted/composite anchor, with the semantic title
    # reservation preserved and its vertical envelope coming from mark ink.
    by_ink = (narrow_captures, wide_captures)
    assert all(by_ink)
    observed_anchors = []
    for allocations in by_ink:
        anchors = []
        for allocation in allocations:
            anchor = allocation.request.painted_anchor
            assert anchor is not None
            assert allocation.candidate is not None and allocation.candidate.side == "end"
            assert allocation.candidate.bounds.x == pytest.approx(
                anchor.right + allocation.selected_preparation().geometry.gap)
            # The painted anchor symmetrically reserves the full title reach
            # about the folded point (the semantic anchor is slightly larger
            # vertically because the mark facet is inset inside its host).
            assert anchor.x + anchor.width / 2 == pytest.approx(
                allocation.request.anchor.x + allocation.request.anchor.width / 2)
            assert anchor.width > 2 * narrow_title.bounds[2]
            anchors.append(anchor)
        assert all(anchor == anchors[0] for anchor in anchors)
        observed_anchors.append(anchors[0])
    narrow_anchor, wide_anchor = observed_anchors
    assert wide_anchor.y < narrow_anchor.y
    assert wide_anchor.bottom > narrow_anchor.bottom
    for rendered, stroke_width in ((narrow_ink, 4), (wide_ink, 12)):
        svg_text = ElementTree.fromstring(rendered.artifact.content)
        svg_mark = next(node for node in svg_text.iter()
                        if node.attrib.get("data-scene-id") == mark_id)
        assert svg_mark.attrib["fill"] == "none"
        assert svg_mark.attrib["stroke"] != "none"
        assert float(svg_mark.attrib["stroke-width"]) == stroke_width
        svg_delta = next(node for node in svg_text.iter()
                         if node.attrib.get("data-scene-id") == delta_id)
        mark, delta = _primitive(rendered, mark_id), _primitive(rendered, delta_id)
        assert delta.text in "".join(svg_delta.itertext())
        # Independent adapter evidence: the emitted delta lies beyond even
        # the mark's full command hull plus its painted stroke and the gap.
        # The composite reservation additionally keeps the folded title clear.
        assert delta.bounds[0] - (mark.bounds[0] + mark.bounds[2] + stroke_width / 2) >= 20
        assert any(node.attrib.get("data-scene-id") == title_id for node in svg_text.iter())


def test_folded_forecast_default_gap_keeps_semantic_anchor_spacing(tmp_path, monkeypatch):
    # Without an authored binding, the request stays on the legacy semantic
    # anchor path; corrected completed mark ink may still affect lane allocation.
    narrow_captures, wide_captures = [], []
    narrow_ink = _render(tmp_path / "narrow", stroke_width=4,
                         monkeypatch=monkeypatch, capture=narrow_captures)
    wide_ink = _render(tmp_path / "wide", stroke_width=12,
                       monkeypatch=monkeypatch, capture=wide_captures)
    delta_id = "variance:group-header:team:gate"

    assert _primitive(narrow_ink, delta_id)
    assert _primitive(wide_ink, delta_id)
    for allocation in (*narrow_captures, *wide_captures):
        assert allocation.request.painted_anchor is None
        assert allocation.candidate is not None and allocation.candidate.side == "end"
        assert allocation.candidate.bounds.x == pytest.approx(
            allocation.request.anchor.right + allocation.selected_preparation().geometry.gap)
