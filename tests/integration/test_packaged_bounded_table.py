"""Packaged table/heading policy and fitting-copy preservation (#1295)."""
from copy import deepcopy
from datetime import date

import pytest

from chrona.resources import safe_load
from chrona.usecases import preset_library
from tests.support import synthetic_review as sr


PRESETS = tuple(entry["id"] for entry in preset_library._library())


def _parts(identifier):
    entry = next(entry for entry in preset_library._library() if entry["id"] == identifier)
    return {kind: safe_load(preset_library._read_member(preset_library._member(entry, member)))
            for kind, member in (("view", "view"), ("theme", "theme"),
                                 ("scheme", "colorScheme"), ("layout", "layout"))}


def _source(long=False):
    title = "Negotiate data-processing agreements including legal and security review " * 30 if long else "Alpha"
    source = sr.project({"a": sr.span("a", date(2027, 1, 4), 8, title=title),
                         "b": sr.span("b", date(2027, 1, 10), 70, title="Short"),
                         "c": sr.point("c", date(2027, 3, 31), title="Decision" if long else "Gate")})
    source["project"]["title"] = "An extremely long project title " * 80 if long else "Project"
    return source


def _catalogs(directory, identifier):
    copied = preset_library.copy_builtin_preset(identifier, directory / "preset")
    resources = safe_load(copied.read_bytes())["body"]["resources"]
    return tuple(copied.parent / member["path"] for member in resources.get("iconCatalogs", ()))


@pytest.mark.parametrize("identifier", PRESETS)
def test_every_packaged_preset_bounds_long_table_and_heading(tmp_path, identifier):
    presentation = _parts(identifier)
    assert sr.find_node(presentation["layout"], "table")["maxInlineShare"] == 0.4
    assert presentation["view"]["body"]["heading"]["text"]["wrap"] == "allow"
    rendered = sr.render(tmp_path, _source(long=True), presentation=presentation,
                         icon_catalogs=_catalogs(tmp_path, identifier))
    slots = {item.source: item.bounds for item in rendered.surface.slots}
    table, plot = slots["table"], slots["timeline"]
    assert table[2] <= (table[2] + plot[2]) * 0.4 + 1e-6
    cells = [item for item in rendered.surface.primitives
             if item.scene_id.startswith("cell:") and item.text_layout is not None]
    assert any(len(item.text_layout.lines) > 1 or (item.text and "…" in item.text) for item in cells)
    assert not any(item.payload["code"] == "W_LAYOUT_VISIBLE_OVERFLOW" and
                   item.payload.get("sourceRef") == "title" for item in rendered.warning_records)
    assert b"<tspan" in rendered.artifact.content


@pytest.mark.parametrize("identifier", PRESETS)
def test_fitting_packaged_copy_keeps_scene_surface_and_svg(tmp_path, identifier):
    bounded = _parts(identifier)
    original = deepcopy(bounded)
    sr.find_node(original["layout"], "table").pop("maxInlineShare")
    body = original["view"]["body"]
    body.pop("heading")
    for column in body.get("tableColumns", ()):
        column.pop("text")
    if "laneTable" in body.get("rows", {}):
        body["rows"]["laneTable"].pop("text")
    before_path, after_path = tmp_path / "before", tmp_path / "after"
    before_path.mkdir()
    after_path.mkdir()
    catalogs = _catalogs(tmp_path, identifier)
    before = sr.render(before_path, _source(), presentation=original, icon_catalogs=catalogs)
    after = sr.render(after_path, _source(), presentation=bounded, icon_catalogs=catalogs)
    assert after.surface == before.surface
    assert after.artifact.content == before.artifact.content
