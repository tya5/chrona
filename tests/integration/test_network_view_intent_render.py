"""Declared network content and order survive Layout, Scene and actual SVG."""
from datetime import date
from xml.etree import ElementTree

import pytest

from chrona.usecases.failure_report import report_failure
from chrona.usecases.draft_render import warning_payloads
from chrona.usecases.render_review import RenderFailed
from tests.integration.test_title_ink import _network_parts
from tests.support import synthetic_review as sr


def _fixture():
    parts = _network_parts()
    body = parts["view"]["body"]
    body["selection"] = {"include": {"ids": ["a", "b"]}}
    body["ordering"] = {"by": "title", "direction": "descending", "tieBreak": "id"}
    body["network"] = {"nodeLabel": {"source": {"field": "caption"}}}
    parts["theme"]["body"]["values"]["member-space"] = {"type": "number", "value": 48}
    parts["theme"]["body"]["metrics"]["network.member.gap"] = "member-space"
    source = sr.project({
        "a": sr.span("a", date(2026, 2, 2), 5, title="Alpha title"),
        "b": sr.span("b", date(2026, 2, 2), 5, title="Beta title"),
        "excluded": sr.span("excluded", date(2026, 2, 2), 5, title="Not selected"),
    })
    source["objects"]["a"]["fields"]["caption"] = "Alpha node"
    source["objects"]["b"]["fields"]["caption"] = "Beta node"
    return parts, source


def test_network_subset_labels_order_and_member_gap_reach_real_svg(tmp_path):
    parts, source = _fixture()
    rendered = sr.render(tmp_path, source, presentation=parts)
    primitives = {item.scene_id: item for item in rendered.surface.primitives}
    nodes = {key.removeprefix("network-node:"): item for key, item in primitives.items()
             if key.startswith("network-node:")}
    assert set(nodes) == {"a", "b"}
    assert nodes["b"].bounds[1] < nodes["a"].bounds[1]
    assert nodes["a"].bounds[1] - (nodes["b"].bounds[1] + nodes["b"].bounds[3]) == 48
    svg = ElementTree.fromstring(rendered.artifact.content)
    svg_by_id = {item.attrib["data-scene-id"]: item for item in svg.iter()
                 if "data-scene-id" in item.attrib}
    for object_id, expected in (("a", "Alpha node"), ("b", "Beta node")):
        scene_id = f"network-label:{object_id}"
        assert primitives[scene_id].text == expected
        assert "".join(svg_by_id[scene_id].itertext()) == expected
    assert "Not selected" not in rendered.artifact.content.decode()


def test_empty_network_label_keeps_the_measured_node_without_title_fallback(tmp_path):
    parts, source = _fixture()
    source["objects"]["a"]["fields"]["caption"] = ""
    rendered = sr.render(tmp_path, source, presentation=parts)
    node = next(item for item in rendered.surface.primitives if item.scene_id == "network-node:a")
    assert node.bounds[2] > 0 and node.bounds[3] > 0
    assert not any(item.scene_id == "network-label:a" and item.text
                   for item in rendered.surface.primitives)
    assert "Alpha title" not in rendered.artifact.content.decode()


def test_unbound_network_label_role_uses_title_and_existing_declaration_info(tmp_path):
    parts, source = _fixture()
    parts["view"]["body"]["network"]["nodeLabel"]["source"] = {"fieldRole": "phase"}
    rendered = sr.render(tmp_path, source, presentation=parts)
    labels = {item.source_ref: item.text for item in rendered.surface.primitives
              if item.scene_id.startswith("network-label:")}
    assert labels == {"a": "Alpha title", "b": "Beta title"}
    records = [item for item in warning_payloads(rendered)
               if item["code"] == "I_VIEW_FIELD_ROLE_UNBOUND"]
    assert len(records) == 1
    assert records[0]["fieldRole"] == "phase" and records[0]["count"] == 1
    assert records[0]["sourceRefs"] == ["/body/network/nodeLabel/source/fieldRole"]


@pytest.mark.parametrize("value", (False, 123, ["not", "text"], {"not": "text"}))
def test_nontext_network_field_is_a_pointed_view_failure_not_a_tool_error(tmp_path, value):
    parts, source = _fixture()
    source["objects"]["a"]["fields"]["caption"] = value
    with pytest.raises(RenderFailed) as caught:
        sr.render(tmp_path, source, presentation=parts)
    error = caught.value
    assert error.code == "E_VIEW_NETWORK_LABEL_SOURCE"
    assert error.component == "view" and error.source_ref == "/body/network/nodeLabel/source"
    assert error.details["objectId"] == "a"
    assert error.details["sourceSubjects"] == [{"sourceRef": "/objects/a", "title": "Alpha title"}]
    report = report_failure(error)
    assert report.status == "rejected"
