"""`annotationContainer.inlineSize: fill` sizes a note box to its annotations slot (#1051).

Synthetic Projects through the packaged `executive-light` bundle with a 300 px note rail; no `examples/` input.
The rules checked on the published Scene: every filled box has the slot's inline extent on both edges and shares
one right edge, no body line is wider than the box inner width, the default is byte-identical, `maxInlineEm`
makes a narrower start-aligned column, a tilted note's rotated bounds fill the slot, and a note that does not sit
in the slot keeps its content size and warns.
"""
from __future__ import annotations

from copy import deepcopy

import pytest

from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr

from pathlib import Path

MATERIAL = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file()
                ) / "src/chrona/resources/icons/material-symbols-outline-rounded-v2026-09-22.yaml"
RAIL = 300
TARGETS = ["g0-t1", "g1-t2", "g2-t1"]


def _rail_candidate():
    return sr.candidate("rail", region={"kind": "slot", "source": "annotations"}, search_kind="row-aligned",
                        connector="leader")


def _render(tmp_path, *, container=None, texts=None, words=3, candidates=None, rail=RAIL, name="r"):
    directory = tmp_path / name
    directory.mkdir()
    parts = sr.bundle()
    sr.with_note_rail(parts, rail)
    if container is not None:
        parts["theme"]["body"]["values"]["note-container"] = {"type": "annotationContainer", "value": dict(container)}
        parts["theme"]["body"]["roles"]["annotation-note-box"]["annotationContainer"] = "note-container"
    source = sr.chain_project()
    ids = sr.add_notes(source, parts["view"], TARGETS, candidates or [_rail_candidate()], words=words)
    for note_id, text in zip(ids, texts or (), strict=False):
        source["annotations"][note_id]["text"] = text
    return sr.render(directory, source, presentation=parts)


def _prims(rendered, prefix):
    return {item.scene_id.split(":", 1)[1]: item for item in rendered.surface.primitives
            if item.scene_id.startswith(prefix + ":")}


def _boxes(rendered):
    return _prims(rendered, "annotation-box")


FILL = {"outline": "rectangle", "cornerRadius": 0, "inlineSize": "fill"}


def test_a_theme_without_the_property_is_byte_identical(tmp_path):
    plain = _render(tmp_path, name="a")
    bare = _render(tmp_path, container={"outline": "rectangle", "cornerRadius": 0}, name="b")
    explicit = _render(tmp_path, container={"outline": "rectangle", "cornerRadius": 0, "inlineSize": "content"}, name="c")
    assert bare.artifact.content == plain.artifact.content
    assert explicit.artifact.content == plain.artifact.content


def test_a_filled_box_has_the_slot_extent_on_both_edges_and_shares_one_right_edge(tmp_path):
    content = _boxes(_render(tmp_path, container={"outline": "rectangle", "cornerRadius": 0}, name="c"))
    assert len({round(box.bounds[2], 1) for box in content.values()}) > 1  # today: ragged
    boxes = _boxes(_render(tmp_path, container=FILL, name="f"))
    assert set(boxes) == set(content) and len(boxes) == 3
    starts = {round(box.bounds[0], 3) for box in boxes.values()}
    ends = {round(box.bounds[0] + box.bounds[2], 3) for box in boxes.values()}
    assert len(starts) == 1 and len(ends) == 1
    assert all(box.bounds[2] == pytest.approx(RAIL, abs=0.01) for box in boxes.values())


def test_a_short_body_keeps_the_full_width_and_start_alignment(tmp_path):
    rendered = _render(tmp_path, container=FILL, texts=("Short.", "Short too.", "Also short."))
    boxes, texts = _boxes(rendered), _prims(rendered, "annotation-text")
    for note, box in boxes.items():
        assert box.bounds[2] == pytest.approx(RAIL, abs=0.01)
        assert texts[note].bounds[0] == pytest.approx(box.bounds[0], abs=0.01)  # start-aligned, not centred
        assert texts[note].bounds[2] < RAIL / 2


def test_a_long_body_wraps_and_only_the_block_size_grows(tmp_path):
    short = _render(tmp_path, container=FILL, texts=("Short.",) * 3, name="s")
    long = _render(tmp_path, container=FILL, words=12, name="l")
    for note, box in _boxes(long).items():
        assert box.bounds[2] == pytest.approx(RAIL, abs=0.01)
        assert box.bounds[3] > _boxes(short)[note].bounds[3] * 2
        assert len(_prims(long, "annotation-text")[note].text_layout.lines) >= 3


INSET = {"top": 0.5, "right": 1.0, "bottom": 0.5, "left": 2.0}


@pytest.mark.parametrize("inset", [None, INSET])
def test_no_body_line_is_wider_than_the_box_inner_width(tmp_path, inset):
    container = dict(FILL, **({"contentInsetEm": inset} if inset else {}))
    rendered = _render(tmp_path, container=container, words=8)
    for note, box in _boxes(rendered).items():
        text = _prims(rendered, "annotation-text")[note]
        size = text.text_layout.font_size
        inner = box.bounds[2] - ((inset["left"] + inset["right"]) * size if inset else 0)
        assert text.bounds[2] <= inner + 0.01
        assert len(text.text_layout.lines) >= 2
        assert box.bounds[2] == pytest.approx(RAIL, abs=0.01)


def test_the_kind_border_is_part_of_the_chrome_the_body_wraps_inside(tmp_path):
    source = ak.project(("note",), text="i " * 160)
    parts = sr.bundle()
    ak.with_view_notes(parts, source)
    sr.with_note_rail(parts, RAIL)
    ak.with_kind_theme(parts, border_side="start", border_width=20, bar=False, label_fill="text")
    for annotation in parts["view"]["body"]["annotations"]:
        annotation["candidates"] = [_rail_candidate()]
    parts["theme"]["body"]["values"]["note-container"] = {
        "type": "annotationContainer", "value": dict(FILL, border={"start": {"width": 20, "paint": "kind"}})}
    parts["theme"]["body"]["roles"]["annotation-note-box"]["annotationContainer"] = "note-container"
    directory = tmp_path / "k"
    directory.mkdir()
    rendered = ak.render(directory, source, parts)
    box = next(iter(_boxes(rendered).values()))
    text = next(iter(_prims(rendered, "annotation-text").values()))
    assert box.bounds[2] == pytest.approx(RAIL, abs=0.01)
    assert text.bounds[2] <= RAIL - 20 + 0.01
    assert text.bounds[0] >= box.bounds[0] + 20 - 0.01


def test_a_maximum_makes_a_narrower_column_aligned_to_the_slot_start(tmp_path):
    rendered = _render(tmp_path, container=dict(FILL, maxInlineEm=15))
    boxes = _boxes(rendered)
    size = next(iter(_prims(rendered, "annotation-text").values())).text_layout.font_size
    wide = _boxes(_render(tmp_path, container=FILL, name="w"))
    assert all(box.bounds[2] == pytest.approx(15 * size, abs=0.01) for box in boxes.values())
    assert {round(box.bounds[0], 3) for box in boxes.values()} == {round(box.bounds[0], 3) for box in wide.values()}
    assert len({round(box.bounds[0] + box.bounds[2], 3) for box in boxes.values()}) == 1


def test_a_maximum_wider_than_the_slot_is_the_slot(tmp_path):
    boxes = _boxes(_render(tmp_path, container=dict(FILL, maxInlineEm=500)))
    assert all(box.bounds[2] == pytest.approx(RAIL, abs=0.01) for box in boxes.values())


@pytest.mark.parametrize("angle", [-3.0, 4.0])
def test_a_tilted_note_has_rotated_bounds_that_fill_the_slot(tmp_path, angle):
    rendered = _render(tmp_path, container=dict(FILL, tiltDegrees=[angle]), words=6)
    plain = _boxes(_render(tmp_path, container=FILL, words=6, name="p"))
    boxes = _boxes(rendered)
    assert len(boxes) == 3
    for note, box in boxes.items():
        assert box.bounds[2] == pytest.approx(RAIL, abs=0.01)
        assert box.bounds[0] == pytest.approx(plain[note].bounds[0], abs=0.01)
    for box in boxes.values():  # a rotated polygon whose own extent is the slot width, not an axis-aligned Rect
        assert box.kind.value == "Symbol" and len(box.symbol.outline) == 5
        xs = [command.points[0][0] for command in box.symbol.outline[:4]]
        assert max(xs) - min(xs) == pytest.approx(RAIL, abs=0.01)


def test_a_note_that_is_not_in_a_slot_keeps_its_content_size_and_warns(tmp_path):
    plot = [sr.candidate("plot-near", connector="none")]
    filled = _render(tmp_path, container=FILL, candidates=plot, name="f")
    content = _render(tmp_path, container={"outline": "rectangle", "cornerRadius": 0}, candidates=plot, name="c")
    assert {note: box.bounds for note, box in _boxes(filled).items()} == {note: box.bounds for note, box in _boxes(content).items()}
    warned = [item for item in filled.scene.diagnostics if item.startswith("W_LAYOUT_ANNOTATION_FILL_NOT_SLOT:")]
    assert sorted(warned) == [f"W_LAYOUT_ANNOTATION_FILL_NOT_SLOT:note-{index}:plot-near" for index in range(3)]
    assert not [item for item in content.scene.diagnostics if "FILL_NOT_SLOT" in item]


def test_a_filled_note_in_the_slot_does_not_warn(tmp_path):
    assert not [item for item in _render(tmp_path, container=FILL).scene.diagnostics if "FILL_NOT_SLOT" in item]


def test_a_word_wider_than_the_slot_makes_the_box_wider_and_is_never_clipped(tmp_path):
    word = "W" * 60
    rendered = _render(tmp_path, container=FILL, texts=(word, word, word))
    for note, box in _boxes(rendered).items():
        text = _prims(rendered, "annotation-text")[note]
        assert text.bounds[2] > RAIL
        assert box.bounds[2] >= text.bounds[2] - 0.01
        assert word in text.text_layout.lines  # the word is one unbroken line


@pytest.mark.parametrize("value", [
    {"inlineSize": "wide"},
    {"inlineSize": "content", "maxInlineEm": 10},
    {"maxInlineEm": 10},
    {"inlineSize": "fill", "maxInlineEm": 0},
    {"inlineSize": "fill", "maxInlineEm": -4},
])
def test_a_malformed_declaration_is_rejected(tmp_path, value):
    with pytest.raises(Exception) as caught:
        _render(tmp_path, container={"outline": "rectangle", "cornerRadius": 0, **value})
    assert "E_" in str(caught.value)


def test_the_balloon_and_the_content_inset_compose_with_fill(tmp_path):
    container = {"outline": "balloon", "cornerRadius": 0.2, "tailBaseEm": 0.6, "inlineSize": "fill",
                 "contentInsetEm": deepcopy(INSET)}
    rendered = _render(tmp_path, container=container, words=6)
    for box in _boxes(rendered).values():
        assert box.bounds[2] == pytest.approx(RAIL, abs=0.01)


@pytest.mark.parametrize("side", ["leading", "trailing"])
def test_a_label_visual_is_part_of_the_chrome_the_body_wraps_inside(tmp_path, side):
    source = ak.project(("note",), text="i " * 160)
    parts = sr.bundle()
    ak.with_view_notes(parts, source)
    sr.with_note_rail(parts, RAIL)
    parts["view"]["body"]["visuals"] = [{"target": {"kind": "annotation", "id": "view-n0"},
                                         "ref": "material:10k-outline-rounded", "decorative": True, "side": side}]
    for annotation in parts["view"]["body"]["annotations"]:
        annotation["candidates"] = [_rail_candidate()]
    parts["theme"]["body"]["values"]["note-container"] = {"type": "annotationContainer", "value": dict(FILL)}
    parts["theme"]["body"]["roles"]["annotation-note-box"]["annotationContainer"] = "note-container"
    directory = tmp_path / side
    directory.mkdir()
    rendered = ak.render(directory, source, parts, catalogs=(MATERIAL,), visual_profile="chrona-output/visual/v0.7-svg")
    box = next(iter(_boxes(rendered).values()))
    text = next(iter(_prims(rendered, "annotation-text").values()))
    icon = next(item for item in rendered.surface.primitives if item.scene_id.startswith("visual:annotation-text:"))
    assert box.bounds[2] == pytest.approx(RAIL, abs=0.01)
    assert icon.bounds[0] >= box.bounds[0] - 0.01 and icon.bounds[0] + icon.bounds[2] <= box.bounds[0] + RAIL + 0.01
    assert text.bounds[2] <= RAIL - icon.bounds[2] + 0.01  # the body wraps in what the icon leaves
    if side == "trailing":  # a trailing visual stands at the box's end edge
        assert icon.bounds[0] + icon.bounds[2] == pytest.approx(box.bounds[0] + RAIL, abs=4)
