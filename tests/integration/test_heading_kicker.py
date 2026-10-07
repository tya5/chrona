"""A declared kicker is one measured heading block, not Scene-side placement."""
from copy import deepcopy
import json
import xml.etree.ElementTree as ET

import pytest

from chrona.presentation.scene.serialization import scene_document
from chrona.presentation.model.closure import ClosureError
from chrona.usecases.render_review import RenderFailed
from tests.integration.test_heading_templates import _render


def _kicker_theme(theme, *, gap=8):
    body = theme["body"]
    role = deepcopy(body["roles"]["heading"])
    for name, value in (("fontSize", 20), ("lineHeight", 1.35), ("horizontalScale", 0.8),
                        ("opacity", 0.85), ("blockGap", gap)):
        token = "test-kicker-" + name
        body["values"][token] = {"type": "number", "value": value}
        role[name] = token
    body["roles"]["kicker"] = role
    body["colorBindings"]["kicker.fill"] = "text"
    body["colorBindings"]["heading.fill"] = "text"


def _texts(rendered):
    return {p.scene_id: p for p in rendered.surface.primitives if p.scene_id in {"kicker", "title", "subtitle"}}


def test_kicker_title_deck_are_measured_in_one_slot_and_projected_to_svg(tmp_path):
    rendered = _render(tmp_path, {"kicker": "EPISODE {project}", "title": "Board", "subtitle": "{asOf}"},
                       theme_edit=_kicker_theme)
    texts = _texts(rendered)
    assert list(texts) == ["kicker", "title", "subtitle"]
    assert [t.text for t in texts.values()] == ["EPISODE HALCYON", "Board", "Feb 20, 2026"]
    assert [t.visual_role for t in texts.values()] == ["kicker", "heading", "subtitle"]
    assert [t.purpose for t in texts.values()] == ["kicker-text", "title-text", "subtitle-text"]
    assert texts["kicker"].text_layout.font_size == 20
    assert texts["kicker"].text_layout.horizontal_scale == 0.8
    assert texts["kicker"].paint.opacity == pytest.approx(0.85)
    slot = next(s for s in rendered.surface.slots if s.source == "title")
    x, y, width, height = slot.bounds
    for text in texts.values():
        tx, ty, tw, th = text.bounds
        assert tx >= x - 0.001 and tx + tw <= x + width + 0.001
        assert ty >= y - 0.001 and ty + th <= y + height + 0.001
    assert texts["title"].bounds[1] >= texts["kicker"].bounds[1] + texts["kicker"].bounds[3] + 8 - 0.001
    assert texts["subtitle"].bounds[1] >= texts["title"].bounds[1] + texts["title"].bounds[3] - 0.001
    svg = {n.attrib["data-scene-id"]: n for n in ET.fromstring(rendered.artifact.content).iter()
           if n.attrib.get("data-scene-id") in texts}
    assert set(svg) == set(texts)
    for identifier, text in texts.items():
        node = svg[identifier]
        assert node.attrib["data-purpose"] == text.purpose
        assert node.attrib["fill"] == text.paint.fill
        assert float(node.attrib["font-size"]) == text.text_layout.font_size
        assert float(node.attrib["x"]) == pytest.approx(text.text_layout.baseline[0], abs=0.001)
        assert float(node.attrib["y"]) == pytest.approx(text.text_layout.baseline[1], abs=0.001)
    assert float(svg["kicker"].attrib["opacity"]) == pytest.approx(0.85)
    assert "matrix(0.8" in svg["kicker"].attrib["transform"]


def test_kicker_without_a_deck_uses_the_default_title_and_grows_the_slot(tmp_path):
    (tmp_path / "plain").mkdir()
    (tmp_path / "kicker").mkdir()
    plain = _render(tmp_path / "plain", None)
    headed = _render(tmp_path / "kicker", {"kicker": "Episode"}, theme_edit=_kicker_theme)
    assert list(_texts(headed)) == ["kicker", "title"]
    assert _texts(headed)["title"].text == "HALCYON"
    slot = lambda r: next(s for s in r.surface.slots if s.source == "title")
    assert slot(headed).bounds[3] > slot(plain).bounds[3]


@pytest.mark.parametrize("heading", [None, {"title": "Board"}, {"title": "Board", "subtitle": "Deck"}])
def test_unused_kicker_declarations_leave_scene_surface_and_svg_bytes_unchanged(tmp_path, heading):
    (tmp_path / "plain").mkdir()
    (tmp_path / "unused").mkdir()
    plain = _render(tmp_path / "plain", heading)
    unused = _render(tmp_path / "unused", heading, theme_edit=lambda theme: _kicker_theme_without_title_ink(theme))
    assert unused.artifact.content == plain.artifact.content
    # Resource provenance reflects the changed Theme; completed public surfaces do not.
    surfaces = lambda r: json.dumps(scene_document(r.scene)["surfaces"], sort_keys=True).encode()
    assert surfaces(unused) == surfaces(plain)


def _kicker_theme_without_title_ink(theme):
    old = deepcopy(theme["body"]["colorBindings"])
    _kicker_theme(theme)
    theme["body"]["colorBindings"] = old | {"kicker.fill": "text"}


def test_declared_kicker_requires_its_own_typography_role(tmp_path):
    with pytest.raises(RenderFailed) as caught:
        _render(tmp_path, {"kicker": "Episode"})
    assert caught.value.code == "E_THEME_ROLE_REQUIRED"


def test_negative_kicker_gap_is_a_theme_diagnostic(tmp_path):
    with pytest.raises(RenderFailed) as caught:
        _render(tmp_path, {"kicker": "Episode"}, theme_edit=lambda theme: _kicker_theme(theme, gap=-1))
    assert caught.value.code == "E_THEME_TOKEN_TYPE"


def test_block_gap_is_not_admitted_on_the_heading_role(tmp_path):
    def misplaced(theme):
        _kicker_theme(theme)
        theme["body"]["roles"]["heading"]["blockGap"] = "test-kicker-blockGap"
    with pytest.raises(ClosureError, match="E_THEME_ROLE_PROPERTY_UNSUPPORTED"):
        _render(tmp_path, {"kicker": "Episode"}, theme_edit=misplaced)
