"""#980: no packaged preset renders a free label the gate rejects.

Each packaged preset renders a synthetic Project (two spans) through the draft path, as `chrona render --preset`; the completed Scene is judged by the contrast policy and no legibility finding (a mark or a label below
its floor) may be an error. A preset cannot draw project notes (it declares no annotation roles), so the ink its
Theme binds to the note index, which an author inherits when adding them, is checked against the scheme grounds
directly. Synthetic input only; nothing here reads `examples/`.
"""
from __future__ import annotations

from datetime import date

import pytest
import yaml

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.paint_analysis import composited_contrast
from chrona.presentation.scene.serialization import scene_document
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from tests.support import synthetic_review as sr

PRESETS = ("control-room-dark", "editorial", "elevated-light", "executive-light",
           "mission-light", "print-mono", "technical-print")


def _project() -> dict:
    return sr.project({
        "a": sr.span("a", date(2026, 1, 5), 40),
        "b": sr.span("b", date(2026, 2, 16), 30, owner="b"),
    })


@pytest.mark.parametrize("preset", PRESETS)
def test_a_packaged_preset_renders_no_label_or_mark_the_gate_rejects(tmp_path, preset):
    project = tmp_path / "project.yaml"
    project.write_text(yaml.safe_dump(_project(), sort_keys=False), encoding="utf-8")
    rendered = render_draft(DraftRenderRequest(project=project, target_kind="svg", preset=preset)).rendered
    findings = evaluate_scene_contrast(scene_document(rendered.scene))

    errors = [(item.purpose, item.visual_role, item.primitive_id, round(item.contrast_ratio or 0, 2), item.ground_color)
              for item in findings if item.severity == "error"]
    assert not errors, errors
    # The sweep looked at the labels it is about: free ink at the required floor, not only marks.
    assert any(item.visual_role == "text" and item.floor == 4.5 for item in findings)


@pytest.mark.parametrize("preset", PRESETS)
def test_the_note_index_ink_a_preset_binds_is_legible_on_its_scheme_grounds(preset):
    parts = sr.bundle(preset)
    colors = parts["scheme"]["body"]["colors"]
    ink = colors[parts["theme"]["body"]["colorBindings"]["note-index.fill"]]
    for ground in ("surface", "surfaceRaised"):
        assert composited_contrast(fill=ink, opacity=1.0, ground=colors[ground]) >= 4.5, (preset, ground)
