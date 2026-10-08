"""Split heading sources close native graph placements, not Scene coordinates."""
from copy import deepcopy
import xml.etree.ElementTree as ET

from tests.integration.test_title_ink import ACTUAL, _network_parts, _source
from tests.support import synthetic_review as sr


def test_network_whole_source_still_ignores_unused_heading_typography(tmp_path):
    plain_parts = _network_parts()
    unused_parts = deepcopy(plain_parts)
    unused_parts["view"]["body"]["heading"]["kicker"] = "Unused kicker"
    assert "kicker" not in unused_parts["theme"]["body"]["roles"]
    (tmp_path / "plain").mkdir()
    (tmp_path / "unused").mkdir()
    plain = sr.render(tmp_path / "plain", _source(), presentation=plain_parts, actual=ACTUAL)
    unused = sr.render(tmp_path / "unused", _source(), presentation=unused_parts, actual=ACTUAL)
    assert unused.artifact.content == plain.artifact.content
    assert unused.surface.primitives == plain.surface.primitives


def test_network_parts_keep_roles_and_distinct_native_slot_owners(tmp_path):
    parts = _network_parts(fills={"heading": "accent", "subtitle": "negative"})
    whole = parts["layout"]["root"]["children"][0]
    title, subtitle = deepcopy(whole), deepcopy(whole)
    title.update(id="sign", source="heading.title")
    subtitle.update(id="deck", source="heading.subtitle")
    parts["layout"]["root"]["children"][:1] = [title, subtitle]
    rendered = sr.render(tmp_path, _source(), presentation=parts, actual=ACTUAL)
    texts = {item.scene_id: item for item in rendered.surface.primitives
             if item.scene_id in {"title", "subtitle"}}
    slots = {item.slot_id: item for item in rendered.surface.slots}
    assert texts["title"].slot_id == "sign"
    assert texts["subtitle"].slot_id == "deck"
    assert texts["title"].visual_role == "heading"
    assert texts["subtitle"].visual_role == "subtitle"
    assert texts["title"].text == "Quarterly review"
    assert texts["subtitle"].text == "Review status"
    for text in texts.values():
        x, y, width, height = slots[text.slot_id].bounds
        tx, ty, tw, th = text.bounds
        assert tx >= x - .001 and ty >= y - .001
        assert tx + tw <= x + width + .001 and ty + th <= y + height + .001
    svg = {node.attrib["data-scene-id"]: node for node in ET.fromstring(rendered.artifact.content).iter()
           if node.attrib.get("data-scene-id") in texts}
    assert set(svg) == set(texts)
    for key, text in texts.items():
        assert svg[key].attrib["fill"] == text.paint.fill
        assert float(svg[key].attrib["x"]) == text.text_layout.baseline[0]


def test_network_without_heading_host_omits_real_copy_without_a_fake_slot(tmp_path):
    parts = _network_parts()
    parts["layout"]["root"]["children"] = parts["layout"]["root"]["children"][1:]
    rendered = sr.render(tmp_path, _source(), presentation=parts, actual=ACTUAL)
    assert not any(item.scene_id in {"title", "subtitle", "kicker"}
                   for item in rendered.surface.primitives)
    assert not any(item.source == "title" for item in rendered.surface.slots)
    assert "I_LAYOUT_HEADING_PART_OMITTED:title" in rendered.surface.diagnostics
    assert "I_LAYOUT_HEADING_PART_OMITTED:subtitle" in rendered.surface.diagnostics
