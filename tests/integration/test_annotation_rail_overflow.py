"""Visible-overflow fallback for kind-headed notes in annotation rails (#1201).

The fixtures are synthetic Projects rendered through the packaged bundle; no example corpus inputs are read.
"""
from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
from xml.etree import ElementTree

import pytest

from chrona.usecases.render_review import RenderFailed
from chrona.presentation.layout.surface_geometry import GEOMETRY_TOLERANCE
from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr


RAIL_CANDIDATE = sr.candidate(
    "rail", region={"kind": "slot", "source": "annotations"},
    search_kind="row-aligned", connector="leader",
)
RAIL_CARD_CANDIDATE = sr.candidate(
    "rail-card", region={"kind": "slot", "source": "annotations"},
    search_kind="row-aligned", connector="none",
)
TERMINAL_LIST_CANDIDATE = sr.candidate(
    "terminal-list", region={"kind": "slot", "source": "annotations"},
    search_kind="row-aligned", connector="none",
)


def _parts(*, rail: int = 300, heading_size: int = 15, fill: bool = True,
           rail_block: int | None = None, wide_heading: bool = False,
           terminal_list: bool = True):
    source = sr.chain_project(groups=1, per_group=3)
    targets = ("g0-t0", "g0-t1", "g0-t2")
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
        annotation["candidates"] = [deepcopy(RAIL_CANDIDATE), deepcopy(RAIL_CARD_CANDIDATE)]
        if terminal_list:
            annotation["candidates"].append(deepcopy(TERMINAL_LIST_CANDIDATE))
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
    # Neighbouring completed edges can differ by one ULP before serialization.
    tolerance = float(GEOMETRY_TOLERANCE)
    return (x < ox + owidth - tolerance and ox < x + width - tolerance
            and y < oy + oheight - tolerance and oy < y + height - tolerance)


def test_overlap_oracle_accepts_roundoff_but_rejects_a_serializable_overlap():
    left = SimpleNamespace(bounds=(24.0, 626.0, 300.0, 19.6))
    touching = SimpleNamespace(bounds=(24.0, 645.5999999999999, 300.0, 28.8))
    overlapping = SimpleNamespace(bounds=(24.0, 645.599, 300.0, 28.8))
    assert not _overlap(left, touching)
    assert not _overlap(touching, left)
    assert _overlap(left, overlapping)
    assert _overlap(overlapping, left)


def _assert_boxes_do_not_overlap(rendered):
    boxes = _prims(rendered, "annotation-box")
    list_records = _prims(rendered, "annotation-list")
    assert len(boxes) + len(list_records) == 3
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
        if note_id not in boxes:
            continue
        x, y, width, height = item.bounds
        box_x, box_y, box_width, box_height = boxes[note_id].bounds
        assert x >= box_x - 0.01 and y >= box_y - 0.01
        assert x + width <= box_x + box_width + 0.01
        assert y + height <= box_y + box_height + 0.01
    occupied = [*boxes.values(), *list_records.values()]
    for index, item in enumerate(occupied):
        note_id = item.scene_id.split(":", 1)[1].split(":", 1)[0]
        for other in occupied[index + 1:]:
            other_note = other.scene_id.split(":", 1)[1].split(":", 1)[0]
            if note_id != other_note:
                assert not _overlap(item, other)


def _assert_svg_contains_notes(rendered):
    root = ElementTree.fromstring(rendered.artifact.content)
    scene_ids = {node.attrib.get("data-scene-id") for node in root.iter()}
    rendered_ids = {f"view-n{index}" for index in range(3)}
    for annotation_id in rendered_ids:
        if f"annotation-box:{annotation_id}" in scene_ids:
            assert f"annotation-heading:{annotation_id}" in scene_ids
        else:
            assert f"annotation-list:{annotation_id}" in scene_ids
    primitives = {item.scene_id: item for item in rendered.surface.primitives}
    expected = {
        "view-n0": "Synthetic risk annotation 0 with a few words.",
        "view-n1": "Synthetic note annotation 1 with a few words.",
        "view-n2": "Synthetic risk annotation 2 with a few words.",
    }
    for annotation_id, body in expected.items():
        text = primitives.get(f"annotation-text:{annotation_id}") or primitives[
            f"annotation-list:{annotation_id}"]
        assert text.text == body
        svg_text = next(node for node in root.iter()
                        if node.attrib.get("data-scene-id") == text.scene_id)
        assert "".join("".join(svg_text.itertext()).split()) == "".join(body.split())


@pytest.mark.parametrize("heading_size", [15, 17, 20, 22])
def test_fill_note_boxes_with_kind_headings_remain_complete_in_svg(tmp_path, heading_size):
    _, rendered = _render(tmp_path, heading_size=heading_size, fill=True)
    assert len(_prims(rendered, "annotation-box")) == 3
    _assert_boxes_do_not_overlap(rendered)
    _assert_svg_contains_notes(rendered)


@pytest.mark.parametrize("wide_heading", [False, True])
def test_content_sized_short_and_wide_headings_do_not_overlap_when_rail_is_narrow(tmp_path, wide_heading):
    _, rendered = _render(tmp_path, rail=180, heading_size=22, fill=False, wide_heading=wide_heading)
    _assert_boxes_do_not_overlap(rendered)
    if wide_heading:
        # An indivisible oversized header cannot be placed as a box wider than
        # its declared rail; the explicit safe destination retains the body.
        # The list record intentionally carries no kind heading; the filled
        # card controls above separately assert heading rendering.
        assert len(_prims(rendered, "annotation-list")) == 3
    _assert_svg_contains_notes(rendered)


def test_marker_none_exhausted_rail_stacks_full_records_and_reports_overflow(tmp_path):
    _, rendered = _render(tmp_path, heading_size=22, fill=True, rail_block=150,
                          terminal_list=True)
    _assert_boxes_do_not_overlap(rendered)
    _assert_svg_contains_notes(rendered)
    assert any(warning.code == "W_LAYOUT_LABEL_OVERFLOW" and warning.source_ref == "view-n2"
               for warning in rendered.surface.fit_warnings)


def test_exhausted_rail_without_declared_terminal_destination_is_rejected(tmp_path):
    source, parts = _parts(rail=1, rail_block=1, terminal_list=False)
    for annotation in parts["view"]["body"]["annotations"]:
        annotation["candidates"] = [deepcopy(RAIL_CANDIDATE)]
    with pytest.raises(RenderFailed) as caught:
        ak.render(tmp_path, source, parts)
    assert caught.value.code == "E_LAYOUT_ANNOTATION_FALLBACK_REQUIRED"
