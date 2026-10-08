"""Native slot captions are admitted, owned and serialized by their real surfaces."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from importlib import import_module
import xml.etree.ElementTree as ET

import pytest

from tests.support import synthetic_review as sr
from chrona.presentation.scene.serialization import serialize_scene


def _heading_role(parts):
    body = parts["theme"]["body"]
    body["values"].update({
        "slot-heading-size": {"type": "number", "value": 11},
        "slot-heading-weight": {"type": "fontWeight", "value": 700},
        "slot-heading-spacing": {"type": "number", "value": 0.1},
        "slot-heading-transform": {"type": "textTransform", "value": "uppercase"},
    })
    body["roles"]["slot-heading"] = {
        **body["roles"]["text"], "fontWeight": "slot-heading-weight", "fontSize": "slot-heading-size",
        "letterSpacing": "slot-heading-spacing", "textTransform": "slot-heading-transform",
    }
    body["colorBindings"]["slot-heading.fill"] = "textMuted"


def _svg_texts(rendered):
    root = ET.fromstring(rendered.artifact.content)
    return {node.attrib["data-scene-id"]: "".join(node.itertext())
            for node in root.iter() if node.attrib.get("data-scene-id")}


def _assert_heading_sources(rendered, labels):
    slots = {slot.slot_id: slot.bounds for slot in rendered.surface.slots}
    primitives = {item.scene_id: item for item in rendered.surface.primitives}
    svg = _svg_texts(rendered)
    for source, label in labels.items():
        scene_id = f"slot-heading:{source}"
        caption = primitives[scene_id]
        assert caption.kind == "Text" and caption.slot_id == source
        assert caption.text == label.upper()
        assert scene_id in svg and label.upper() in svg[scene_id]
        slot = slots[source]
        left, top, width, height = caption.bounds
        assert left >= slot[0] - 0.5 and top >= slot[1] - 0.5
        assert left + width <= slot[0] + slot[2] + 0.5
        assert top + height <= slot[1] + slot[3] + 0.5
        content = [item for item in rendered.surface.primitives
                   if item.slot_id == source and item.scene_id != scene_id and item.kind == "Text"]
        assert content, f"expected native text content in {source}: {[item.scene_id for item in rendered.surface.primitives]}"
        assert all(item.bounds[1] >= top + height - 0.5 for item in content), source


def _timeline_parts():
    parts = sr.bundle("executive-light")
    _heading_role(parts)
    labels = {
        "title": "Project", "table": "Table", "timeline": "Schedule",
        "timeline-axis": "Calendar", "group-details": "Group detail",
        "milestones": "Milestones", "observations": "Observations",
    }
    for source, label in labels.items():
        sr.find_node(parts["layout"], source)["heading"] = {"text": label, "block": "top"}
    return parts, labels


@pytest.mark.parametrize(("emphasis", "paint_role"), [
    ("normal", "text"), ("attention", "variance-ahead"), ("critical", "variance-behind"),
])
def test_all_timeline_and_detail_native_slots_emit_owned_captions_in_scene_and_svg(
        tmp_path, monkeypatch, emphasis, paint_role):
    usecase = import_module("chrona.usecases.render_review")
    detail_layout = import_module("chrona.presentation.layout.surface_content")
    natural_calls = []
    completed_calls = []
    observation_batches = []
    native_natural = usecase.prepare_surface_natural_candidate
    native_complete = usecase.prepare_surface_content

    def record_natural(request):
        result = native_natural(request)
        natural_calls.append((request, result))
        return result

    def record_completed(request, *, natural=None):
        result = native_complete(request, natural=natural)
        completed_calls.append((request, natural, result))
        return result

    native_observations = detail_layout.compose_observations

    def record_observations(**kwargs):
        result = native_observations(**kwargs)
        observation_batches.append(result)
        return result

    monkeypatch.setattr(usecase, "prepare_surface_natural_candidate", record_natural)
    monkeypatch.setattr(usecase, "prepare_surface_content", record_completed)
    monkeypatch.setattr(detail_layout, "compose_observations", record_observations)

    directory = tmp_path / "timeline-details"
    directory.mkdir()
    parts, labels = _timeline_parts()
    if emphasis == "attention":
        body = parts["theme"]["body"]
        body["roles"]["tableColumnLabel"] = dict(body["roles"]["text"])
        body["colorBindings"]["tableColumnLabel.fill"] = "textMuted"
    source = sr.project({
        "task": sr.span("task", date(2026, 1, 5), 20, owner="a"),
        "release": sr.point("release", date(2026, 3, 2), owner="a"),
    })
    detail = {
        "version": "chrona/review-detail-profile/v0.1", "id": "native-headings",
        "body": {
            "groupDetails": [{"groupId": "a", "label": "Team A", "description": "A synthetic group detail."}],
            "milestones": ["release"],
            "observations": {
                "columns": [{"id": "status:x/y", "label": "Status"}],
                "rows": [{"id": "reviewed/a%2Fb", "source": "synthetic review", "emphasis": emphasis,
                          "cells": {"status:x/y": "Ready"}}],
            },
        },
    }
    rendered = sr.render(directory, source, presentation=parts, detail=detail, viewport=(1600, None))

    assert len(completed_calls) == 1 and natural_calls
    final_request, final_natural = natural_calls[-1]
    completed_request, completed_natural, completed = completed_calls[-1]
    assert completed_request is final_natural.inline.request
    assert completed_natural is final_natural
    assert final_request.layout_manifest is completed_request.layout_manifest
    assert final_natural.required_timeline_block() == completed.required_timeline_block()
    assert completed_request.surface_content.observation_rows
    assert observation_batches and observation_batches[-1].text
    observation_caption = next(item for item in rendered.surface.primitives
                               if item.scene_id == "slot-heading:observations")
    assert all(item.slot_id == "observations" for item in observation_batches[-1].text)
    assert all(item.bounds.block >= observation_caption.bounds[1] + observation_caption.bounds[3] - 0.5
               for item in observation_batches[-1].text)
    _assert_heading_sources(rendered, labels)
    primitives = {item.scene_id: item for item in rendered.surface.primitives}
    svg = _svg_texts(rendered)
    for placed in observation_batches[-1].text:
        projected = primitives[placed.placement_id]
        assert projected.text == placed.content
        assert projected.source_ref == placed.source_ref
        assert projected.slot_id == placed.slot_id
        assert projected.bounds == tuple(float(value) for value in (
            placed.bounds.inline, placed.bounds.block, placed.bounds.inline_size, placed.bounds.block_size))
        assert projected.baseline == placed.baseline
        assert projected.text_layout.lines == placed.lines
        assert projected.text_layout.asset_identity == placed.font_asset_identity
        assert projected.table_row_id is None and projected.table_column_id is None
        assert placed.content in svg[placed.placement_id]
    cell = primitives["observations:row:reviewed%2Fa%252Fb:cell:status%3Ax%2Fy"]
    assert cell.visual_role == paint_role
    assert cell.purpose == "observation-cell" and cell.source_ref == "reviewed/a%2Fb"
    assert primitives["observations:header:status%3Ax%2Fy"].source_ref == "status:x/y"
    assert primitives["observations:header:status%3Ax%2Fy"].visual_role == (
        "tableColumnLabel" if emphasis == "attention" else "text")
    attribution = primitives["observations:row:reviewed%2Fa%252Fb:source"]
    assert attribution.visual_role == "text" and attribution.purpose == "observation-source"
    assert attribution.table_row_id is None and attribution.table_column_id is None
    assert b'"purpose":"observation-source"' in serialize_scene(rendered.scene)


def _network_parts(labels):
    from tests.integration.test_title_ink import _network_parts as native_network_parts

    parts = native_network_parts()
    _heading_role(parts)
    sr.find_node(parts["layout"], "title")["heading"] = {"text": labels["title"], "block": "top"}
    network = next(node for node in parts["layout"]["root"]["children"] if node.get("source") == "network")
    network["heading"] = {"text": labels["network"], "block": "top"}
    return parts


def test_dependency_network_and_title_captions_are_admitted_and_serialized(tmp_path):
    labels = {"title": "Project", "network": "Dependency network"}
    parts = _network_parts(labels)
    source = sr.project({
        "a": sr.span("a", date(2026, 1, 5), 10, owner="a"),
        "b": sr.span("b", date(2026, 1, 20), 10, owner="b"),
    }, relations=[{
        "id": "depends", "type": "dependency", "lag": "0d",
        "from": {"object": "a", "endpoint": "end"},
        "to": {"object": "b", "endpoint": "start"},
    }])
    directory = tmp_path / "network"
    directory.mkdir()
    rendered = sr.render(directory, source, presentation=parts)
    serialize_scene(rendered.scene)
    captions = {"title": labels["title"], "network": labels["network"]}
    slots = {slot.slot_id: slot.bounds for slot in rendered.surface.slots}
    primitives = {item.scene_id: item for item in rendered.surface.primitives}
    svg = _svg_texts(rendered)
    for source_ref, label in captions.items():
        scene_id = f"slot-heading:{source_ref}"
        caption = primitives[scene_id]
        assert caption.kind == "Text" and caption.slot_id == source_ref
        assert caption.text == label.upper()
        assert scene_id in svg and label.upper() in svg[scene_id]
        slot = slots[source_ref]
        assert caption.bounds[0] >= slot[0] - 0.5
        assert caption.bounds[1] >= slot[1] - 0.5
        assert caption.bounds[0] + caption.bounds[2] <= slot[0] + slot[2] + 0.5
        assert caption.bounds[1] + caption.bounds[3] <= slot[1] + slot[3] + 0.5
    assert any(item.slot_id == "network" and item.scene_id != "slot-heading:network"
               for item in rendered.surface.primitives)
