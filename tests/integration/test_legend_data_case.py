"""Design voice transforms wording, never encoding values (#1811)."""
from datetime import date
from xml.etree import ElementTree

import pytest

from tests.integration.test_realized_legends import ACTUAL, _detail, _parts, _render, _render_with_style, _source
from tests.support import synthetic_review as sr


def _voice(parts, transform):
    body = parts["theme"]["body"]
    body["values"]["legend-voice"] = {"type": "textTransform", "value": transform}
    body["roles"]["legend"]["textTransform"] = "legend-voice"
    if transform == "small-caps":
        body["values"]["legend-caps-scale"] = {"type": "number", "value": 0.7}
        body["roles"]["legend"]["smallCapsScale"] = "legend-caps-scale"
    return parts


def _labels(rendered):
    return [node for node in rendered.surface.primitives if node.purpose == "legend-label"]


def _assert_svg_label(rendered, label):
    root = ElementTree.fromstring(rendered.artifact.content)
    node = next(node for node in root.iter() if node.attrib.get("data-scene-id") == label.scene_id)
    assert "".join(node.itertext()) == label.text


@pytest.mark.parametrize("transform", ["lowercase", "uppercase", "capitalize", "small-caps"])
@pytest.mark.parametrize("name", ["Aiko", "AiKo Research"])
def test_view_encoding_keeps_entity_title_while_design_wording_transforms(tmp_path, transform, name):
    source = _source()
    source["entities"]["a"]["title"] = name
    # Keep a real, unencoded Plan key alongside the encoded value.
    source["objects"]["behind"]["fields"].pop("owner")
    parts = _voice(_parts(), transform)
    parts["view"]["body"]["colorEncoding"] = {
        "scale": "owners", "target": "planned", "source": {"field": "owner"}, "domain": ["a"]}
    parts["theme"]["body"]["colorScales"] = {"owners": {"slots": {"a": "owner-a"}}}
    parts["scheme"]["body"]["categories"]["owner-a"] = "#3456A0"
    detail = _detail()
    detail["body"]["legend"][0]["label"] = "Authored PLAN"

    rendered = _render(tmp_path, source, actual=ACTUAL, parts=parts, detail=detail)

    labels = _labels(rendered)
    data = next(label for label in labels if label.source_ref == "scale:owners:a")
    assert data.text == name
    expected = {"lowercase": "authored plan", "uppercase": "AUTHORED PLAN",
                "capitalize": "Authored Plan", "small-caps": "AUTHORED PLAN"}[transform]
    assert expected in {label.text for label in labels}
    if transform == "lowercase":
        assert {"ahead", "on track", "behind"} <= {label.text for label in labels}
    _assert_svg_label(rendered, data)


@pytest.mark.parametrize("transform,title", [("lowercase", "owner"), ("uppercase", "OWNER"),
                                            ("small-caps", "OWNER")])
def test_style_title_uses_voice_but_domain_value_stays_literal(tmp_path, transform, title):
    source = sr.project({"one": sr.span("one", date(2026, 2, 2), 5, owner="AiKo")})
    parts = _voice(_parts(), transform)
    parts["theme"]["body"]["colorScales"] = {"owners": {"slots": {"AiKo": "owner-a"}}}
    parts["scheme"]["body"]["categories"]["owner-a"] = "#3456A0"
    style = {"version": "chrona/style/v0.2", "kind": "style", "id": "owner-voice", "body": {
        "rules": [{"id": "owner-fill", "when": {"semantic": "planned"}, "then": {"encode": {
            "channel": "fill", "source": {"field": "owner"}, "scale": "owners", "domain": ["AiKo"],
            "legend": {"title": "Owner"}}}}]}}

    rendered = _render_with_style(tmp_path, source, parts=parts, style=style)

    label = next(label for label in _labels(rendered) if label.source_ref.startswith("scale:style:"))
    assert label.text == f"{title}: AiKo"
    _assert_svg_label(rendered, label)
    if transform == "small-caps":
        layout = label.text_layout
        runs, = layout.runs
        assert "".join(run.text for run in runs) == label.text
        assert any(run.font_size < layout.font_size for run in runs)
        assert runs[-1].font_size == layout.font_size
        assert layout.bounds[2] == pytest.approx(
            sum(run.inline_size for run in runs) + layout.letter_spacing * (len(runs) - 1))


def test_a_real_other_domain_value_is_not_confused_with_folded_wording(tmp_path):
    source = sr.project({"one": sr.span("one", date(2026, 2, 2), 5, owner="Other")})
    source["entities"]["Other"]["title"] = "Other"
    parts = _voice(_parts(), "lowercase")
    parts["view"]["body"]["colorEncoding"] = {
        "scale": "owners", "target": "planned", "source": {"field": "owner"}, "domain": ["Other"]}
    parts["theme"]["body"]["colorScales"] = {"owners": {"slots": {"Other": "owner-a"}}}
    parts["scheme"]["body"]["categories"]["owner-a"] = "#3456A0"
    rendered = _render(tmp_path, source, parts=parts)
    label = next(label for label in _labels(rendered) if label.source_ref == "scale:owners:Other")
    assert label.text == "Other"
    _assert_svg_label(rendered, label)
