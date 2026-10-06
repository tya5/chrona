"""Declared summary flow is closed in Layout and preserved in actual SVG."""
from copy import deepcopy
import json
import xml.etree.ElementTree as ET

import pytest
import yaml

from chrona.presentation.scene.serialization import scene_document
from chrona.presentation.model.closure import ClosureError
from chrona.usecases.render_review import RenderFailed
from tests.integration.test_derived_figures import ACTUAL, COUNTDOWN, _metric, _parts, _render, _source, _summary
from tests.support import synthetic_review as sr, text_treatments as tt


def _theme(parts, *, gap=7):
    body = parts["theme"]["body"]
    for role, template, size, scale, separation, ink in (
        ("summary-caption", "summary", 16, 0.8, gap, "textMuted"),
        ("metric", "metric", 48, 0.7, 11, "text"),
        ("summary-unit", "summary", 12, 1, 5, "positive"),
    ):
        binding = deepcopy(body["roles"][template])
        if role == "summary-caption":
            binding["fontFamily"] = "editorial"
        for name, value in (("fontSize", size), ("lineHeight", 1.25),
                            ("horizontalScale", scale), ("inlineGap", separation)):
            token = f"test-{role}-{name}"
            body["values"][token] = {"type": "number", "value": value}
            binding[name] = token
        body["roles"][role] = binding
        body["colorBindings"][role + ".fill"] = ink


def _texts(rendered):
    return {p.scene_id: p for p in rendered.surface.primitives if p.scene_id.startswith("summary:")}


def _inline(*metrics):
    summary = _summary(*(metrics or (_metric(),)))
    panel = summary["body"]["panels"][0]
    panel.update(title="Until launch", arrangement="inline")
    return summary


def test_inline_closes_common_baseline_role_widths_gaps_and_actual_svg(tmp_path):
    parts = _parts(COUNTDOWN)
    _theme(parts)
    rendered = _render(tmp_path, parts, _inline())
    texts = _texts(rendered)
    caption, value, unit = texts.values()
    assert [t.text for t in texts.values()] == ["Until launch", "28", "DAYS"]
    assert [t.visual_role for t in texts.values()] == ["summary-caption", "metric", "summary-unit"]
    assert [t.text_layout.font_size for t in texts.values()] == [16, 48, 12]
    assert caption.text_layout.family != unit.text_layout.family
    assert len({t.paint.fill for t in texts.values()}) == 3
    assert caption.text_layout.baseline[1] == value.text_layout.baseline[1] == unit.text_layout.baseline[1]
    assert value.bounds[0] == pytest.approx(caption.bounds[0] + caption.bounds[2] + 7, abs=0.001)
    assert unit.bounds[0] == pytest.approx(value.bounds[0] + value.bounds[2] + 11, abs=0.001)
    slot = next(s for s in rendered.surface.slots if s.source == "summary")
    x, y, width, height = slot.bounds
    assert x + width == pytest.approx(unit.bounds[0] + unit.bounds[2], abs=0.001)  # No last-run gap.
    for t in texts.values():
        assert t.bounds[1] >= y - 0.001
        assert t.bounds[1] + t.bounds[3] <= y + height + 0.001
    svg = {n.attrib["data-scene-id"]: n for n in ET.fromstring(rendered.artifact.content).iter()
           if n.attrib.get("data-scene-id") in texts}
    assert set(svg) == set(texts)
    for identifier, text in texts.items():
        node = svg[identifier]
        assert node.attrib["fill"] == text.paint.fill
        assert node.attrib["data-purpose"] == text.purpose
        assert float(node.attrib["font-size"]) == text.text_layout.font_size
        assert float(node.attrib["x"]) == pytest.approx(text.text_layout.baseline[0], abs=0.001)
        assert float(node.attrib["y"]) == pytest.approx(text.text_layout.baseline[1], abs=0.001)
    assert "matrix(0.7" in svg[value.scene_id].attrib["transform"]


def test_multiple_metrics_and_mixed_panels_preserve_order_and_stack_pitch(tmp_path):
    parts = _parts(COUNTDOWN)
    _theme(parts)
    summary = _inline(_metric(metric_id="one"), _metric(metric_id="two", label="LEFT"))
    stack = deepcopy(summary["body"]["panels"][0])
    stack.update(id="stack", arrangement="stack")
    summary["body"]["panels"].append(stack)
    rendered = _render(tmp_path, parts, summary)
    texts = _texts(rendered)
    inline = [t for name, t in texts.items() if name.startswith("summary:key")]
    stacked = [t for name, t in texts.items() if name.startswith("summary:stack")]
    assert [t.text for t in inline] == ["Until launch", "28", "DAYS", "28", "LEFT"]
    assert len({t.text_layout.baseline[1] for t in inline}) == 1
    assert stacked[0].bounds[1] >= max(t.bounds[1] + t.bounds[3] for t in inline) - 0.001
    for first, second in zip(stacked, stacked[1:]):
        assert second.bounds[1] == pytest.approx(first.bounds[1] + first.bounds[3], abs=0.001)
    assert [t.visual_role for t in stacked] == ["text", "metric", "subtitle", "metric", "subtitle"]


def test_default_explicit_stack_and_unused_new_role_declarations_are_byte_identical(tmp_path):
    parts = _parts(COUNTDOWN)
    summary = _summary(_metric())
    (tmp_path / "default").mkdir()
    default = _render(tmp_path / "default", parts, summary)
    for name, add_roles in (("stack", False), ("unused", True)):
        (tmp_path / name).mkdir()
        changed = deepcopy(parts)
        explicit = deepcopy(summary)
        explicit["body"]["panels"][0]["arrangement"] = "stack"
        if add_roles:
            # Only new bindings are unused; do not modify existing metric typography/ink.
            original_metric = deepcopy(changed["theme"]["body"]["roles"]["metric"])
            _theme(changed)
            changed["theme"]["body"]["roles"]["metric"] = original_metric | {"inlineGap": "test-metric-inlineGap"}
        result = _render(tmp_path / name, changed, explicit)
        assert result.artifact.content == default.artifact.content
        surfaces = lambda r: json.dumps(scene_document(r.scene)["surfaces"], sort_keys=True).encode()
        assert surfaces(result) == surfaces(default)


def test_inline_lines_and_shorthand_keep_combined_text_without_unit_inference(tmp_path):
    parts = _parts(COUNTDOWN)
    _theme(parts)
    summary = _inline()
    panel = summary["body"]["panels"][0]
    panel["presentation"] = "lines"
    panel["metrics"] = {"countdown": {"source": {"figure": "countdown"}, "label": "DAYS", "format": "count"},
                        "literal": "63 DAYS"}
    texts = list(_texts(_render(tmp_path, parts, summary)).values())
    assert [t.text for t in texts] == ["Until launch", "DAYS: 28", "literal: 63 DAYS"]
    assert {t.visual_role for t in texts} == {"summary-caption"}
    assert len({t.text_layout.baseline[1] for t in texts}) == 1


@pytest.mark.parametrize("role", ["summary-caption", "summary-unit"])
def test_inline_requires_its_own_role(tmp_path, role):
    parts = _parts(COUNTDOWN)
    _theme(parts)
    del parts["theme"]["body"]["roles"][role]
    with pytest.raises(RenderFailed) as caught:
        _render(tmp_path, parts, _inline())
    assert caught.value.code == "E_THEME_ROLE_REQUIRED"


@pytest.mark.parametrize("gap", [-1, "bad"])
def test_invalid_inline_gap_uses_existing_theme_diagnostic(tmp_path, gap):
    parts = _parts(COUNTDOWN)
    _theme(parts, gap=gap)
    with pytest.raises(RenderFailed) as caught:
        _render(tmp_path, parts, _inline())
    assert caught.value.code == "E_THEME_TOKEN_TYPE"


@pytest.mark.skipif(not tt.cjk_available(), reason="requires the optional Noto Sans JP package")
def test_declared_cjk_face_can_render_the_title_card_wording_without_project_rules(tmp_path):
    parts = _parts(COUNTDOWN)
    _theme(parts)
    body = parts["theme"]["body"]
    body["values"]["caption-cjk"] = {"type": "fontFamily", "value": tt.JP}
    body["roles"]["summary-caption"]["fontFamily"] = "caption-cjk"
    descriptor = yaml.safe_load((tt.ROOT / "src/chrona/resources/fonts/default-font-metrics.yaml").read_bytes())
    descriptor["assets"].extend(yaml.safe_load(tt.CJK_DESCRIPTOR.read_bytes())["assets"])
    descriptor_path = sr._write(tmp_path / "metrics.yaml", descriptor)
    source = _source()
    source["periods"]["window"].update(start="2026-04-24", end="2026-04-30")
    summary = _inline()
    summary["body"]["panels"][0]["title"] = "発射まで"
    result = sr.render(tmp_path, source, presentation=parts, actual=ACTUAL,
                       summary=summary, font_metrics_path=descriptor_path)
    texts = list(_texts(result).values())
    assert [t.text for t in texts] == ["発射まで", "63", "DAYS"]
    assert texts[0].text_layout.family == tt.JP
    assert len({t.text_layout.baseline[1] for t in texts}) == 1
    assert "発射まで" in result.artifact.content.decode()


def test_inline_semantics_do_not_depend_on_panel_or_metric_id_spelling(tmp_path):
    parts = _parts(COUNTDOWN)
    _theme(parts)
    summary = _inline(_metric(metric_id="caption:value"))
    summary["body"]["panels"][0]["id"] = "value:caption"
    texts = list(_texts(_render(tmp_path, parts, summary)).values())
    assert [t.purpose for t in texts] == ["summary-caption", "summary-figure-value", "summary-unit"]
    assert [t.visual_role for t in texts] == ["summary-caption", "metric", "summary-unit"]


def test_inline_gap_is_not_admitted_on_other_roles(tmp_path):
    parts = _parts(COUNTDOWN)
    _theme(parts)
    parts["theme"]["body"]["roles"]["summary"]["inlineGap"] = "test-metric-inlineGap"
    with pytest.raises(ClosureError, match="E_THEME_ROLE_PROPERTY_UNSUPPORTED"):
        _render(tmp_path, parts, _inline())
