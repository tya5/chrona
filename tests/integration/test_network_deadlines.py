"""Network deadlines are measured node content, never timeline overlays (#1397)."""
from copy import deepcopy
from xml.etree import ElementTree

import pytest

from chrona.presentation.scene.serialization import scene_document, validate_scene_document
from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from tests.integration.test_deadline_mark import MIXED, _parts, _render, _source
from tests.support import synthetic_review as sr


def _network_parts(*, show="all", caption=None, outline=None, width=2, flow="horizontal"):
    parts = _parts(show, outline=outline, width=width)
    layout = parts["layout"]
    layout["requiredThemeTokens"] = ["spacing.l", "spacing.m"]
    layout["dependencyNetworkFlowDirection"] = flow
    layout["root"]["children"] = [sr.find_node(layout, "title"), {
        "id": "network", "kind": "slot", "source": "network", "inlineSize": "fill", "blockSize": "fill",
        "place": {"inline": "stretch", "block": "stretch", "safety": "strict"},
        "priority": "required", "overflow": "visible-overflow",
    }]
    body = parts["view"]["body"]
    body["surface"] = "dependency-network"
    for key in ("tableColumns", "hierarchyColumn", "backgroundDecoration", "axis", "markers", "periods",
                "shading", "timePresentation", "annotations", "annotationPresentation"):
        body.pop(key, None)
    body["rows"] = {"mode": "automatic"}
    body["grouping"] = {"by": "none", "missing": "ungrouped"}
    body["visibility"] = {"labels": False, "relations": "semantic", "annotations": "none"}
    if caption is not None:
        body["deadlines"]["caption"] = caption
    return parts


def _footers(rendered):
    return {item.source_ref: item for item in rendered.surface.primitives
            if item.scene_id.startswith("deadline-network-label:")}


@pytest.mark.parametrize("flow", ["horizontal", "vertical-rl", "vertical-lr"])
def test_network_deadlines_close_dates_state_and_caption_inside_node_before_svg(tmp_path, flow):
    parts = _network_parts(flow=flow, caption={"template": "{daysLate} days late", "format": {"form": "english-words"}})
    source = _source(**MIXED)
    source["relations"] = [{"id": "a-g", "type": "dependency", "lag": "0d",
                            "from": {"object": "a", "endpoint": "end"},
                            "to": {"object": "g", "endpoint": "at"}}]
    rendered = _render(tmp_path, source=source, parts=parts)
    footers = _footers(rendered)
    assert {key: item.text for key, item in footers.items()} == {
        "a": "2026-02-05 nine days late", "b": "2026-03-25",
        "g": "2026-03-10 ten days late", "h": "2026-03-05"}
    primitives = {item.scene_id: item for item in rendered.surface.primitives}
    assert {key.removeprefix("deadline-network-tick:") for key in primitives
            if key.startswith("deadline-network-tick:")} == set(MIXED)
    assert {key.removeprefix("deadline-network-slip:") for key in primitives
            if key.startswith("deadline-network-slip:")} == {"a", "g"}
    assert not any(key.startswith(("deadline-tick:", "deadline-run:")) for key in primitives)
    edge, = [item for key, item in primitives.items() if key.startswith("network-edge:")]
    host = primitives["network-node:a"]
    target = primitives["network-node:g"]
    assert edge.points[0] == pytest.approx(
        (host.bounds[0] + host.bounds[2], host.bounds[1] + host.bounds[3] / 2)
        if flow == "horizontal" else (host.bounds[0] + host.bounds[2] / 2, host.bounds[1] + host.bounds[3]))
    assert edge.points[-1] == pytest.approx(
        (target.bounds[0], target.bounds[1] + target.bounds[3] / 2)
        if flow == "horizontal" else (target.bounds[0] + target.bounds[2] / 2, target.bounds[1]))
    for object_id, footer in footers.items():
        node = primitives[f"network-node:{object_id}"]
        x, y, w, h = node.bounds
        tx, ty, tw, th = footer.bounds
        assert x <= tx and y <= ty and tx + tw <= x + w + 1e-6 and ty + th <= y + h + 1e-6
        assert footer.slot_id == node.slot_id == "network"
        assert footer.purpose == "deadline-caption"
    provenance = {item.primitive_id: item.subjects for item in rendered.surface.primitive_provenance}
    assert all(provenance[item.scene_id][0].source_ref == "/objects/" + item.source_ref for item in footers.values())
    validate_scene_document(scene_document(rendered.scene))
    root = ElementTree.fromstring(rendered.artifact.content)
    svg_text = ["".join(item.itertext()) for item in root.iter() if item.tag.endswith("text")]
    assert all(item.text in svg_text for item in footers.values())


def test_network_deadline_is_not_hidden_by_timeline_window_and_overrides_replace_global_show(tmp_path):
    parts = _network_parts(show="slipped")
    parts["view"]["body"]["deadlines"]["overrides"] = {"a": {"show": "hidden"}, "b": {"show": "all"}}
    rendered = _render(tmp_path, source=_source(a="2025-01-01", b="2027-01-01", **{"g": MIXED["g"]}), parts=parts)
    assert {key: item.text for key, item in _footers(rendered).items()} == {"b": "2027-01-01", "g": "2026-03-10"}
    assert not any("DEADLINE_OUTSIDE_WINDOW" in str(item) for item in rendered.surface.diagnostics)


def test_network_hidden_footers_preserve_omitted_deadlines_exactly(tmp_path):
    parts = _network_parts(show=None)
    before = _render(tmp_path, parts=parts, name="omitted")
    hidden = deepcopy(parts)
    hidden["view"]["body"]["deadlines"] = {"show": "all", "overrides": {key: {"show": "hidden"} for key in MIXED}}
    after = _render(tmp_path, parts=hidden, name="hidden")
    assert after.surface == before.surface
    assert after.artifact.content == before.artifact.content


def test_network_zero_ink_retains_dates_without_ghost_outlines(tmp_path):
    rendered = _render(tmp_path, parts=_network_parts(width=0, outline=3))
    assert set(_footers(rendered)) == set(MIXED)
    assert not any(item.scene_id.startswith(("deadline-network-tick:", "deadline-network-slip:", "deadline-outline:"))
                   for item in rendered.surface.primitives)


def test_network_outline_is_per_stroke_above_host_and_uses_existing_contrast_classes(tmp_path):
    rendered = _render(tmp_path, parts=_network_parts(outline=2))
    primitives = {item.scene_id: item for item in rendered.surface.primitives}
    strokes = [item for item in primitives.values() if item.purpose == "deadline-mark"]
    assert len(strokes) == 6
    for stroke in strokes:
        outline = primitives[f"deadline-outline:{stroke.scene_id}"]
        assert outline.kind == "Rect" and len(stroke.points) == 2
        assert primitives[f"network-node:{stroke.source_ref}"].paint_order < outline.paint_order < stroke.paint_order
        assert outline.bounds[2] <= 6 or outline.bounds[3] <= 6  # straight-segment ground, not an L-square
    findings = evaluate_scene_contrast(scene_document(rendered.scene))
    deadline_findings = [item for item in findings if item.visual_role == "deadline-mark"]
    assert deadline_findings
    assert all(item.contrast_ratio >= 3 and item.ground_id.startswith("deadline-outline:")
               for item in deadline_findings)
