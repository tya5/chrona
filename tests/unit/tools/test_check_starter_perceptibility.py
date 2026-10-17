from copy import deepcopy
from xml.etree import ElementTree

from tools import check_starter_perceptibility as gate
from chrona.presentation.scene.paint_analysis import composited_contrast
from chrona.presentation.scene.serialization import scene_document


def test_real_bundled_starter_has_no_perceptibility_error(capsys):
    assert gate.main() == 0
    assert "Starter perceptibility: PASS (0 errors)" in capsys.readouterr().out


def test_starter_gate_fails_a_serialized_text_intersection(monkeypatch, capsys):
    scene = deepcopy(gate.starter_scene_document())
    text = [item for item in scene["surfaces"][0]["primitives"] if item["kind"] == "Text"]
    assert len(text) >= 2
    text[1]["bounds"] = dict(text[0]["bounds"])
    monkeypatch.setattr(gate, "starter_scene_document", lambda: scene)

    assert gate.main() == 1
    output = capsys.readouterr().out
    assert "E_SCENE_TEXT_INTERSECTION" in output
    assert "Starter perceptibility: FAIL" in output


def test_closed_day_chart_and_key_paint_are_perceptible_and_match_svg():
    rendered = gate.starter_rendered_review()
    document = scene_document(rendered.scene)
    primitives = document["surfaces"][0]["primitives"]
    chart = [item for item in primitives if item["id"].startswith("calendar-closed:")]
    key = next(item for item in primitives if item["id"] == "legend-swatch:calendar-closed")
    assert chart
    assert key
    row_bands = [item for item in primitives if item.get("visualRole") == "row-band"]
    assert not row_bands  # Spec32: the bundled default declares rules, not faint bands.
    row_rules = [item for item in primitives if item.get("visualRole") == "row-rule"]
    assert row_rules

    svg_root = ElementTree.fromstring(rendered.artifact.content)
    svg_primitives = {node.attrib.get("data-scene-id"): node.attrib for node in svg_root.iter()
                      if node.attrib.get("data-scene-id")}
    for rule in row_rules:
        assert svg_primitives[rule["id"]]["stroke"].upper() == rule["paint"]["stroke"].upper()
    for primitive in (*chart, key):
        paint = primitive["paint"]
        assert "stroke" not in paint or paint["stroke"] is None
        assert 0 < paint["opacity"] < 1
        ground = (document["surfaces"][0]["canvasPaint"]["fill"] if primitive is key
                  else _closed_day_underpaint(primitive, primitives,
                                              document["surfaces"][0]["canvasPaint"]["fill"]))
        assert composited_contrast(fill=paint["fill"], opacity=paint["opacity"], ground=ground) >= 1.15
        svg = svg_primitives[primitive["id"]]
        assert svg["fill"].upper() == paint["fill"].upper()
        assert float(svg["opacity"]) == paint["opacity"]
        assert "stroke" not in svg


def _closed_day_underpaint(target, primitives, canvas):
    """Composite the completed Scene fills painted beneath one closed-day band."""
    bounds = target["bounds"]
    x = bounds["inline"] + bounds["inlineSize"] / 2
    y = bounds["block"] + bounds["blockSize"] / 2
    rgb = _rgb(canvas)
    target_order = (target["paintOrder"], primitives.index(target))
    for candidate_index, item in enumerate(primitives):
        if item["kind"] != "Rect" or item is target:
            continue
        order = (item["paintOrder"], candidate_index)
        rect = item["bounds"]
        if order >= target_order or not (rect["inline"] <= x <= rect["inline"] + rect["inlineSize"]
                                         and rect["block"] <= y <= rect["block"] + rect["blockSize"]):
            continue
        paint = item.get("paint") or {}
        if not paint.get("fill"):
            continue
        opacity = paint.get("opacity", 1.0)
        front = _rgb(paint["fill"])
        rgb = tuple(opacity * a + (1 - opacity) * b for a, b in zip(front, rgb))
    return "#" + "".join(f"{round(channel * 255):02X}" for channel in rgb)


def _rgb(color):
    return tuple(int(color[index:index + 2], 16) / 255 for index in (1, 3, 5))
