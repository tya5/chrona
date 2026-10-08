"""View heading parts can be claimed by independent Layout slots (#1239)."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image
import pytest
import yaml

from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.scene.serialization import scene_document
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderRequest, render_review
from tests.integration.test_frame_glyph_render import CATALOGUE, PNG, SVG, _parts as _frame_parts
from tests.integration.test_heading_templates import ACTUAL, _source
from tests.support import synthetic_review as sr


ROOT = Path(__file__).resolve().parents[2]


def _slot(identifier: str, source: str, *, caption: str | None = None) -> dict:
    node = {
        "id": identifier, "kind": "slot", "source": source,
        "inlineSize": "fill", "blockSize": "content",
        "place": {"inline": "start", "block": "start", "safety": "safe"},
        "priority": "required", "overflow": "visible-overflow",
    }
    if caption is not None:
        node["heading"] = {"text": caption}
    return node


def _parts(*, heading: dict, split: tuple[str, ...] = ("kicker", "title", "subtitle"),
           caption_empty_kicker: bool = False) -> dict:
    parts = sr.bundle("control-room-dark")
    parts["view"]["body"]["heading"] = deepcopy(heading)
    root = parts["layout"]["root"]
    root["children"][0:1] = [
        _slot(f"{part}-part-slot", f"heading.{part}",
              caption="Empty kicker caption" if caption_empty_kicker and part == "kicker" else None)
        for part in split
    ]
    return parts


def _render_parts(directory, parts: dict, *, source=None, target: str = "svg", profile: str = SVG,
                  catalogues: tuple = ()):
    directory.mkdir(parents=True, exist_ok=True)
    paths = {kind: sr._write(directory / f"{kind}.yaml", value) for kind, value in parts.items()}
    project_path = sr._write(directory / "project.yaml", source or _source())
    actual_path = sr._write(directory / "actual.yaml", ACTUAL)
    draft = resolve_draft_render(
        project_path=project_path, view_path=paths["view"], theme_path=paths["theme"],
        scheme_path=paths["scheme"], layout_path=paths["layout"], actual_path=actual_path,
        icon_catalog_paths=catalogues, viewport=(900, 560), target_kind=target, visual_profile=profile)
    return render_review(RenderRequest(
        closure=draft.closure, snapshot_root=draft.asset_root, asset_root=draft.asset_root,
        scheduler=ReferenceScheduler(), renderer=None, draft_auto_block=draft.auto_block))


def _primitive_by_id(rendered):
    return {item.scene_id: item for item in rendered.surface.primitives}


def _slot_by_source(rendered):
    return {item.source: item for item in rendered.surface.slots}


def _theme_for_split(parts: dict) -> None:
    body = parts["theme"]["body"]
    heading = deepcopy(body["roles"]["heading"])
    body["roles"]["kicker"] = deepcopy(heading)
    body["roles"]["subtitle"] = deepcopy(heading)
    body["colorBindings"]["heading.fill"] = "text"
    body["colorBindings"]["kicker.fill"] = "text"
    body["colorBindings"]["subtitle.fill"] = "text"


def test_split_heading_parts_keep_roles_slots_and_actual_svg_geometry(tmp_path):
    parts = _parts(heading={"kicker": "EPISODE", "title": "Programme", "subtitle": "Subtitle"})
    _theme_for_split(parts)
    rendered = _render_parts(tmp_path, parts)
    primitives, slots = _primitive_by_id(rendered), _slot_by_source(rendered)

    assert {name: primitives[name].visual_role for name in ("kicker", "title", "subtitle")} == {
        "kicker": "kicker", "title": "heading", "subtitle": "subtitle"}
    for part in ("kicker", "title", "subtitle"):
        assert primitives[part].slot_id == slots[f"heading.{part}"].slot_id
        sx, sy, sw, sh = slots[f"heading.{part}"].bounds
        x, y, width, height = primitives[part].bounds
        assert x >= sx - 0.01 and x + width <= sx + sw + 0.01
        assert y >= sy - 0.01 and y + height <= sy + sh + 0.01, (part, (x, y, width, height),
                                                                   (sx, sy, sw, sh))

    svg = {node.attrib.get("data-scene-id"): node for node in ET.fromstring(rendered.artifact.content).iter()
           if node.attrib.get("data-scene-id") in {"kicker", "title", "subtitle"}}
    assert set(svg) == {"kicker", "title", "subtitle"}
    assert [svg[part].attrib["data-purpose"] for part in ("kicker", "title", "subtitle")] == [
        "kicker-text", "title-text", "subtitle-text"]
    assert all(svg[part].attrib["x"] and svg[part].attrib["y"] for part in svg)


def test_empty_allocated_part_has_no_text_or_slot_caption(tmp_path):
    parts = _parts(heading={"title": "Programme"}, split=("title", "kicker"), caption_empty_kicker=True)
    _theme_for_split(parts)
    rendered = _render_parts(tmp_path, parts)

    assert "title" in _primitive_by_id(rendered)
    assert "kicker" not in _primitive_by_id(rendered)
    assert "slot-heading:kicker-part-slot" not in _primitive_by_id(rendered)
    assert not any(item.purpose == "slot-heading-text" for item in rendered.surface.primitives)
    assert "I_LAYOUT_SLOT_HEADING_OMITTED:kicker-part-slot:no-content" in rendered.surface.diagnostics


def test_nonempty_unclaimed_part_is_reported_without_synthesizing_a_slot(tmp_path):
    parts = _parts(heading={"kicker": "EPISODE", "title": "Programme", "subtitle": "Subtitle"},
                   split=("title", "subtitle"))
    _theme_for_split(parts)
    rendered = _render_parts(tmp_path, parts)

    assert "kicker" not in _primitive_by_id(rendered)
    assert "I_LAYOUT_HEADING_PART_OMITTED:kicker" in rendered.surface.diagnostics


def test_heading_is_a_whole_block_alias_for_title_in_svg_and_scene_surfaces(tmp_path):
    heading = {"kicker": "EPISODE", "title": "Programme", "subtitle": "Subtitle"}
    title_parts = _parts(heading=heading, split=("title",))
    title_parts["layout"]["root"]["children"][0]["source"] = "title"
    alias_parts = deepcopy(title_parts)
    alias_parts["layout"]["root"]["children"][0]["source"] = "heading"
    _theme_for_split(title_parts)
    _theme_for_split(alias_parts)
    legacy = _render_parts(tmp_path / "title", title_parts)
    alias = _render_parts(tmp_path / "heading", alias_parts)

    assert alias.artifact.content == legacy.artifact.content
    surfaces = lambda rendered: json.dumps(scene_document(rendered.scene)["surfaces"], sort_keys=True).encode()
    assert surfaces(alias) == surfaces(legacy)


def _bulb_theme(parts: dict) -> None:
    body = parts["theme"]["body"]
    heading = deepcopy(body["roles"]["heading"])
    body["roles"]["kicker"] = deepcopy(heading)
    body["roles"]["subtitle"] = deepcopy(heading)
    body["colorBindings"]["kicker.fill"] = "category:marquee-text"
    body["colorBindings"]["subtitle.fill"] = "category:marquee-text"


@pytest.mark.parametrize(("target", "profile"), [("svg", SVG), ("png", PNG)])
def test_bulb_sign_keeps_only_title_inside_frame_and_renders_both_targets(tmp_path, target, profile):
    parts = _frame_parts()
    parts["view"]["body"]["heading"] = {
        "kicker": "NOW SHOWING", "title": "Marquee bulbs", "subtitle": "A programme board"}
    _bulb_theme(parts)
    root = parts["layout"]["root"]
    sign = root["children"][0]
    sign["children"][0]["source"] = "heading.title"
    outside = [
        _slot("kicker-outside-sign", "heading.kicker"),
        _slot("subtitle-outside-sign", "heading.subtitle"),
    ]
    root["children"][1:1] = outside
    rendered = _render_parts(tmp_path / target, parts, target=target, profile=profile, catalogues=(CATALOGUE,))
    primitives, slots = _primitive_by_id(rendered), _slot_by_source(rendered)

    title = primitives["title"]
    kicker, subtitle = primitives["kicker"], primitives["subtitle"]
    frame_slot = next(slot for slot in rendered.surface.slots
                      if slot.slot_id == "frame-glyph-slot:marquee-title-panel")
    fx, fy, fw, fh = frame_slot.bounds
    tx, ty, tw, th = title.bounds
    assert tx >= fx and ty >= fy and tx + tw <= fx + fw and ty + th <= fy + fh
    assert kicker.slot_id == slots["heading.kicker"].slot_id
    assert subtitle.slot_id == slots["heading.subtitle"].slot_id
    for item in (kicker, subtitle):
        x, y, width, height = item.bounds
        assert y >= fy + fh or y + height <= fy
    glyphs = [item for item in rendered.surface.primitives if item.visual_role == "frame-glyph-marquee"]
    assert len(glyphs) > 8

    if target == "svg":
        nodes = {node.attrib.get("data-scene-id"): node for node in ET.fromstring(rendered.artifact.content).iter()
                 if node.attrib.get("data-scene-id")}
        assert all(part in nodes for part in ("title", "kicker", "subtitle"))
        assert nodes["title"].attrib["data-purpose"] == "title-text"
        png = __import__("resvg_py").svg_to_bytes(
            svg_string=rendered.artifact.content.decode("utf-8"), dpi=96,
            font_files=[str(ROOT / "src/chrona/resources/fonts" / name) for name in (
                "noto-sans-regular-v1.ttf", "noto-sans-bold-v1.ttf", "noto-sans-mono-regular-v1.ttf")],
            skip_system_fonts=True)
    else:
        png = rendered.artifact.content
    (tmp_path / f"heading-parts-{target}.png").write_bytes(bytes(png))
    if target == "svg":
        (tmp_path / "heading-parts.svg").write_bytes(rendered.artifact.content)
    image = Image.open(io.BytesIO(bytes(png))).convert("RGB")
    assert image.width > 0 and image.height > 0
    colors = set(image.get_flattened_data())
    assert (255, 218, 99) in colors  # bulb ink
    assert (246, 236, 203) in colors  # title ink
