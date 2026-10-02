"""A relation label is label text: its ink is the text role's, whatever the Theme binds `annotation.fill` to (#880 item 2).

Every packaged and example Theme binds `annotation.fill` to a ground colour (the role paints annotation boxes), and the
relation label used to take its ink from that role, so it was drawn in about the colour of the plot behind it. Proven on a
synthetic Project through a packaged bundle, so no corpus edit can change what these tests prove.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from chrona.presentation.scene.paint_analysis import composited_contrast
from tests.support import synthetic_review as sr

PRESETS = ("executive-light", "control-room-dark")


def _source() -> dict:
    return sr.project(
        {"a": sr.span("a", date(2026, 1, 5), 30), "b": sr.span("b", date(2026, 3, 2), 30, owner="b")},
        [{"id": "a-to-b", "type": "dependency", "lag": "5d",
          "from": {"object": "a", "endpoint": "end"}, "to": {"object": "b", "endpoint": "start"}}])


def _render(tmp_path: Path, preset: str, annotation_fill: str | None = None):
    """The one relation label of a synthetic Project, and the Scheme colours it may be painted from."""
    parts = sr.bundle(preset)
    parts["view"]["body"]["window"] = {"mode": "explicit", "start": "2026-01-01", "end": "2026-05-01"}
    parts["view"]["body"]["visibility"]["relations"] = {
        "mode": "semantic", "overflow": "suppress", "content": ["lag", "endpointPair"]}
    if annotation_fill is not None:
        parts["theme"]["body"]["colorBindings"]["annotation.fill"] = annotation_fill
    directory = tmp_path / "render"
    directory.mkdir()
    rendered = sr.render(directory, _source(), presentation=parts)
    (label,) = [item for item in rendered.surface.primitives if item.purpose == "relation-label"]
    return label, parts["scheme"]["body"]["colors"]


@pytest.mark.parametrize("preset", PRESETS)
def test_a_relation_label_is_drawn_in_the_text_ink(tmp_path, preset):
    label, colors = _render(tmp_path, preset)

    assert label.text and "start" in label.text
    assert label.paint.fill == colors["text"]
    assert label.visual_role == "text"


@pytest.mark.parametrize("preset", PRESETS)
@pytest.mark.parametrize("ground", ["surface", "surfaceRaised"])
def test_the_ink_does_not_follow_a_theme_that_binds_annotation_fill_to_the_ground(tmp_path, preset, ground):
    label, colors = _render(tmp_path, preset, annotation_fill=ground)

    assert label.paint.fill == colors["text"]
    assert label.paint.fill != colors[ground]


@pytest.mark.parametrize("preset", PRESETS)
def test_a_relation_label_is_legible_against_the_canvas(tmp_path, preset):
    label, colors = _render(tmp_path, preset)

    assert composited_contrast(fill=label.paint.fill, opacity=1.0, ground=colors["surface"]) >= 4.5
