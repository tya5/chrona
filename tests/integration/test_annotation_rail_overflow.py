"""Visible-overflow fallback for kind-headed notes in annotation rails (#1201).

The fixtures are synthetic Projects rendered through the packaged bundle; no example corpus inputs are read.
"""
from __future__ import annotations

from copy import deepcopy
from xml.etree import ElementTree

import pytest

from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr


RAIL_CANDIDATE = sr.candidate(
    "rail", region={"kind": "slot", "source": "annotations"},
    search_kind="row-aligned", connector="leader",
)


def _parts(*, rail: int = 300, heading_size: int = 15, fill: bool = True,
           rail_block: int | None = None, wide_heading: bool = False):
    source = sr.chain_project(groups=5)
    targets = ("g0-t1", "g2-t2", "g4-t1")
    source["annotations"] = {
        f"n{index}": {"kind": kind, "text": f"Synthetic {kind} annotation {index} with a few words.",
                      "anchor": {"object": target}}
        for index, (kind, target) in enumerate(zip(("risk", "note", "risk"), targets, strict=True))
    }
    parts = sr.bundle()
    ak.with_view_notes(parts, source)
    ak.with_kind_theme(parts)
    sr.with_note_rail(parts, rail)

    view = parts["view"]["body"]
    view["visibility"]["annotations"]["marker"] = "none"
    for annotation in view["annotations"]:
        annotation["candidates"] = [deepcopy(RAIL_CANDIDATE)]
    theme = parts["theme"]["body"]
    for kind in theme["annotationKinds"].values():
        kind["title"] = "{label} {secondary}"
        kind["heading"] = ("A deliberately long separate annotation heading for {subject} "
                            "to test natural-width overflow" if wide_heading else "{subject}")
    theme["roles"]["annotation-heading"] = {
        **deepcopy(theme["roles"]["annotation-kind-label"]),
        "fontSize": "rail-heading-size", "lineHeight": "rail-heading-line",
    }
    theme["values"].update({
        "rail-heading-size": {"type": "number", "value": heading_size},
        "rail-heading-line": {"type": "number", "value": 1.15},
    })
    theme["colorBindings"]["annotation-heading.fill"] = "text"
    theme["values"]["rail-note-container"] = {
        "type": "annotationContainer",
        "value": {"outline": "rectangle", "cornerRadius": 0,
                  **({"inlineSize": "fill"} if fill else {})},
    }
    theme["roles"]["annotation-note-box"]["annotationContainer"] = "rail-note-container"

    if rail_block is not None:
        sr.fix_block(parts, "annotations", rail_block, token="rail-block-size")
    return source, parts


def _render(tmp_path, **options):
    tmp_path.mkdir(parents=True, exist_ok=True)
    source, parts = _parts(**options)
    rendered = ak.render(tmp_path, source, parts)
    return source, rendered


def _prims(rendered, prefix: str):
    return {item.scene_id.split(":", 1)[1]: item for item in rendered.surface.primitives
            if item.scene_id.startswith(prefix + ":")}


def _overlap(left, right) -> bool:
    x, y, width, height = left.bounds
    ox, oy, owidth, oheight = right.bounds
    return x < ox + owidth and ox < x + width and y < oy + oheight and oy < y + height


def _assert_boxes_do_not_overlap(rendered):
    boxes = _prims(rendered, "annotation-box")
    assert len(boxes) == 3
    values = list(boxes.values())
    for index, box in enumerate(values):
        assert all(not _overlap(box, other) for other in values[index + 1:])

    text_prefixes = ("annotation-kind-text:", "annotation-heading:", "annotation-text:")
    texts = [item for item in rendered.surface.primitives
             if item.scene_id.startswith(text_prefixes)]
    bars = [item for item in rendered.surface.primitives
            if item.scene_id.startswith("annotation-kind-bar:")]
    for item in (*texts, *bars):
        note_id = item.scene_id.split(":", 1)[1].split(":", 1)[0]
        x, y, width, height = item.bounds
        box_x, box_y, box_width, box_height = boxes[note_id].bounds
        assert x >= box_x - 0.01 and y >= box_y - 0.01
        assert x + width <= box_x + box_width + 0.01
        assert y + height <= box_y + box_height + 0.01
    children = (*texts, *bars)
    for index, item in enumerate(children):
        note_id = item.scene_id.split(":", 1)[1].split(":", 1)[0]
        for other in children[index + 1:]:
            other_note = other.scene_id.split(":", 1)[1].split(":", 1)[0]
            if note_id != other_note:
                assert not _overlap(item, other)


def _assert_svg_contains_notes(rendered):
    root = ElementTree.fromstring(rendered.artifact.content)
    scene_ids = {node.attrib.get("data-scene-id") for node in root.iter()}
    assert {f"annotation-box:view-n{index}" for index in range(3)} <= scene_ids
    assert {f"annotation-heading:view-n{index}" for index in range(3)} <= scene_ids


@pytest.mark.parametrize("heading_size", [15, 17, 20, 22])
def test_fill_note_boxes_with_kind_headings_remain_complete_in_svg(tmp_path, heading_size):
    _, rendered = _render(tmp_path, heading_size=heading_size, fill=True)
    _assert_boxes_do_not_overlap(rendered)
    _assert_svg_contains_notes(rendered)


@pytest.mark.parametrize("wide_heading", [False, True])
def test_content_sized_short_and_wide_headings_do_not_overlap_when_rail_is_narrow(tmp_path, wide_heading):
    _, rendered = _render(tmp_path, rail=180, heading_size=22, fill=False, wide_heading=wide_heading)
    boxes = _prims(rendered, "annotation-box")
    assert len(boxes) == 3
    _assert_boxes_do_not_overlap(rendered)
    if wide_heading:
        assert any(box.bounds[2] > 180 for box in boxes.values())
    _assert_svg_contains_notes(rendered)


def test_marker_none_exhausted_rail_stacks_full_boxes_and_reports_overflow(tmp_path):
    _, rendered = _render(tmp_path, heading_size=22, fill=True, rail_block=150)
    _assert_boxes_do_not_overlap(rendered)
    _assert_svg_contains_notes(rendered)
    assert any(warning.code == "W_LAYOUT_LABEL_OVERFLOW" for warning in rendered.surface.fit_warnings)

