from copy import deepcopy
from datetime import date

import pytest

from tests.support import synthetic_review as sr


def parts():
    result = sr.bundle("executive-light")
    result["view"]["body"]["rows"] = {"mode": "automatic"}
    result["view"]["body"]["tableColumns"] = [
        {"id": "Task", "source": "title", "missing": "em-dash", "align": "start",
         "width": {"minmax": {"min": "content", "max": {"fr": 1}}}, "headerOrientation": "horizontal"}]
    sr.find_node(result["layout"], "table")["maxInlineShare"] = 0.4
    return result


def source(title):
    return sr.project({"a": sr.span("a", date(2027, 1, 4), 8, title=title),
                       "b": sr.span("b", date(2027, 1, 10), 70, title="Short")})


@pytest.mark.parametrize("caption", [False, True])
def test_standard_render_enforces_declared_table_bound_with_source_linked_ellipsis(tmp_path, caption):
    title = "X" * 800
    presentation = parts()
    if caption:
        sr.find_node(presentation["layout"], "table")["heading"] = {"text": "Work plan"}
    rendered = sr.render(tmp_path, source(title), presentation=presentation)
    slots = {item.source: item.bounds for item in rendered.surface.slots}
    table, plot = slots["table"], slots["timeline"]
    assert table[2] / (table[2] + plot[2]) <= 0.4
    cell = next(item for item in rendered.surface.primitives if item.scene_id == "cell:a:Task")
    assert cell.text.endswith("…")
    assert cell.text_layout.bounds[0] + cell.text_layout.bounds[2] <= table[0] + table[2]
    assert any(item.payload["code"] == "W_LAYOUT_TEXT_ELLIPSIZED" for item in rendered.warning_records)
    assert not any(item.payload["code"] == "W_LAYOUT_VISIBLE_OVERFLOW" and item.payload.get("sourceRef") == "title"
                   for item in rendered.warning_records)
    assert "…" in rendered.artifact.content.decode()


def test_authored_heading_ellipsis_reaches_public_warning_with_full_source(tmp_path):
    presentation = parts()
    presentation["view"]["body"]["heading"] = {"text": {"wrap": "allow"}}
    project = source("Alpha")
    project["project"]["title"] = "X" * 800
    rendered = sr.render(tmp_path, project, presentation=presentation)
    warning = next(item.payload for item in rendered.warning_records
                   if item.payload["code"] == "W_LAYOUT_TEXT_ELLIPSIZED" and item.payload.get("placementId") == "title")
    assert warning["sourceTitle"] == "X" * 800
    assert warning["requiredInline"] > warning["availableInline"]


def test_short_table_keeps_actual_scene_geometry_and_paint_unchanged(tmp_path):
    bounded_parts = parts()
    ordinary_parts = deepcopy(bounded_parts)
    sr.find_node(ordinary_parts["layout"], "table").pop("maxInlineShare")
    ordinary_path, bounded_path = tmp_path / "ordinary", tmp_path / "bounded"
    ordinary_path.mkdir()
    bounded_path.mkdir()
    ordinary = sr.render(ordinary_path, source("Alpha"), presentation=ordinary_parts)
    bounded = sr.render(bounded_path, source("Alpha"), presentation=bounded_parts)
    assert bounded.surface == ordinary.surface
    assert bounded.artifact.content == ordinary.artifact.content


def test_render_pipeline_projects_authored_heading_and_table_wrap_intent(tmp_path):
    presentation = parts()
    presentation["view"]["body"]["heading"] = {"text": {"wrap": "allow"}}
    presentation["view"]["body"]["tableColumns"][0]["text"] = {"wrap": "allow"}
    project = source("task words " * 100)
    project["project"]["title"] = "project title " * 80
    rendered = sr.render(tmp_path, project, presentation=presentation)
    texts = {item.scene_id: item for item in rendered.surface.primitives if getattr(item, "text_layout", None)}
    assert len(texts["title"].text_layout.lines) > 1
    assert len(texts["cell:a:Task"].text_layout.lines) > 1
    row = next(item for item in rendered.surface.rows if item.object_id == "a")
    cell = texts["cell:a:Task"].text_layout.bounds
    assert cell[1] >= row.bounds[1]
    assert cell[1] + cell[3] <= row.bounds[1] + row.bounds[3]
    assert not any(item.payload["code"] == "W_LAYOUT_VISIBLE_OVERFLOW" and item.payload.get("sourceRef") == "title"
                   for item in rendered.warning_records)
    import xml.etree.ElementTree as ET
    tree = ET.fromstring(rendered.artifact.content)
    assert any(len(node.findall("{http://www.w3.org/2000/svg}tspan")) > 1
               for node in tree.iter("{http://www.w3.org/2000/svg}text"))
