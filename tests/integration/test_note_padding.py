"""A rectangle or balloon note box can declare `contentInsetEm`: padding between its edge and its text (#991).

Until now only an image-backed container honoured it, so a rectangle note's text ran flush to the box edge.
Synthetic Projects through the packaged `executive-light` bundle; no `examples/` input.
"""
from __future__ import annotations

import pytest

from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr

INSET = {"top": 0.5, "right": 1.0, "bottom": 0.25, "left": 2.0}


def _render(tmp_path, *, outline: str | None, inset: dict | None = None):
    source = ak.project(("note",))
    parts = sr.bundle()
    ak.with_view_notes(parts, source)
    if outline is not None:
        container = {"outline": outline, "cornerRadius": 0.0}
        if outline == "balloon":
            container["tailBaseEm"] = 0.6
        if inset is not None:
            container["contentInsetEm"] = dict(inset)
        parts["theme"]["body"]["values"]["note-container"] = {"type": "annotationContainer", "value": container}
        parts["theme"]["body"]["roles"]["annotation-note-box"]["annotationContainer"] = "note-container"
    return sr.render(tmp_path, source, presentation=parts)


def _geometry(rendered):
    box = next(item for item in rendered.surface.primitives if item.scene_id.startswith("annotation-box:"))
    text = next(item for item in rendered.surface.primitives if item.scene_id.startswith("annotation-text:"))
    return box, text


def _sub(tmp_path, name):
    path = tmp_path / name
    path.mkdir()
    return path


def test_without_an_inset_a_rectangle_container_changes_nothing(tmp_path):
    plain = _render(_sub(tmp_path, "a"), outline=None)
    rectangle = _render(_sub(tmp_path, "b"), outline="rectangle")
    assert rectangle.artifact.content == plain.artifact.content


@pytest.mark.parametrize("outline", ["rectangle", "balloon"])
def test_the_inset_pads_the_text_inside_the_box_and_grows_the_box(tmp_path, outline):
    base_box, base_text = _geometry(_render(_sub(tmp_path, "base"), outline=outline))
    box, text = _geometry(_render(_sub(tmp_path, "padded"), outline=outline, inset=INSET))
    size = text.text_layout.font_size

    assert box.bounds[2] == pytest.approx(base_box.bounds[2] + (INSET["left"] + INSET["right"]) * size, abs=0.05)
    assert box.bounds[3] == pytest.approx(base_box.bounds[3] + (INSET["top"] + INSET["bottom"]) * size, abs=0.05)
    # The text keeps the declared left and top padding from the box edge it had before.
    left_gap = text.bounds[0] - box.bounds[0]
    top_gap = text.bounds[1] - box.bounds[1]
    base_left_gap = base_text.bounds[0] - base_box.bounds[0]
    base_top_gap = base_text.bounds[1] - base_box.bounds[1]
    assert left_gap == pytest.approx(base_left_gap + INSET["left"] * size, abs=0.05)
    assert top_gap == pytest.approx(base_top_gap + INSET["top"] * size, abs=0.05)
    assert text.text_layout.font_size == base_text.text_layout.font_size  # the text itself is not rescaled


def test_a_malformed_inset_is_rejected(tmp_path):
    with pytest.raises(Exception) as caught:
        _render(tmp_path, outline="rectangle", inset={"top": -1, "right": 0, "bottom": 0, "left": 0})
    assert "E_" in str(caught.value)
