"""#950: note ink is judged on the note box, so a dark-first Theme can draw paper-light notes.

The packaged `executive-light` bundle takes the dark `control-room-dark` Scheme, and its notes are given a light
box and a dark ink: before the fix Theme resolution compared the dark ink with the dark canvas and refused the
Theme, though the prose lies on the box. Synthetic Project; no `examples/` input.
"""
from __future__ import annotations

import pytest

from chrona.presentation.model.closure import ClosureError
from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document
from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr

LIGHT_BOX, DARK_CANVAS = "#EAF0FA", "#0B1220"


def _parts(box="text", ink="surface"):
    source = ak.project(("note", "note"))
    parts = sr.bundle()
    parts["scheme"] = sr.bundle("control-room-dark")["scheme"]
    ak.with_view_notes(parts, source)
    bindings = parts["theme"]["body"]["colorBindings"]
    bindings["annotation-note-box.fill"] = box
    bindings["annotation-note-text.fill"] = ink
    return source, parts


def _findings(rendered, role):
    return [item for item in evaluate_scene_contrast(scene_document(rendered.scene)) if item.visual_role == role]


def test_a_dark_canvas_theme_with_light_notes_renders_and_passes_the_gates(tmp_path):
    source, parts = _parts()
    rendered = sr.render(tmp_path, source, presentation=parts)
    canvas = rendered.scene.surfaces[0].canvas_paint.fill
    assert canvas == DARK_CANVAS
    document = scene_document(rendered.scene)
    assert not [item for item in evaluate_scene_contrast(document) if item.severity == "error"]
    texts = _findings(rendered, "annotation-note-text")
    assert len(texts) == 2
    for finding in texts:
        # The prose is judged on its own note box, never on the dark canvas it floats above.
        assert finding.ground_id.startswith("annotation-box:")
        assert finding.ground_color == LIGHT_BOX
        assert finding.contrast_ratio > 14 and finding.severity == "info" and finding.floor == 4.5


def test_the_note_box_is_the_light_ground_in_the_completed_scene(tmp_path):
    source, parts = _parts()
    rendered = sr.render(tmp_path, source, presentation=parts)
    boxes = [item for item in rendered.surface.primitives if item.visual_role == "annotation-note-box"]
    assert boxes and all(item.paint.fill == LIGHT_BOX for item in boxes)


def test_ink_too_close_to_its_box_is_refused_at_theme_resolution_naming_role_and_box(tmp_path):
    source, parts = _parts(ink="textMuted")
    with pytest.raises(ClosureError) as error:
        sr.render(tmp_path, source, presentation=parts)
    assert error.value.diagnostic_id == "E_SCHEME_STATE_TEXT_CONTRAST"
    assert error.value.source_ref == "/body/roles/annotation-note-text/fill"
    assert error.value.detail.startswith("'annotation-note-text':'annotation-note-box':")


def test_a_light_ink_on_a_dark_box_still_renders_as_before(tmp_path):
    source, parts = _parts(box="surfaceRaised", ink="text")
    rendered = sr.render(tmp_path, source, presentation=parts)
    assert not [item for item in evaluate_scene_contrast(scene_document(rendered.scene)) if item.severity == "error"]
    assert all(item.ground_color == "#16213A" for item in _findings(rendered, "annotation-note-text"))
