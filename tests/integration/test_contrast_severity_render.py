"""#995: a decoration below its floor is reported by a real render and fails nothing.

A synthetic Project is rendered through a packaged preset bundle with a named-period band whose colour the test
chooses, so no corpus slide can change what these tests prove.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document, validate_scene_document
from chrona.usecases.draft_render import warning_payloads
from tests.support import synthetic_review as sr

WINDOW = {"mode": "explicit", "start": "2026-01-01", "end": "2026-04-01"}
FEBRUARY = {"start": "2026-02-01", "end": "2026-03-01"}


def _source() -> dict:
    source = sr.project({
        "a": sr.span("a", date(2026, 1, 5), 40),
        "b": sr.span("b", date(2026, 2, 10), 30, owner="b"),
    })
    source["periods"] = {"window": FEBRUARY}
    return source


def _parts(color: str) -> dict:
    parts = sr.bundle("executive-light")
    body = parts["theme"]["body"]
    for key in ("period-band.fill", "period-band.stroke"):
        body["colorBindings"].pop(key, None)
    body["roles"]["period-band"] = {"backgroundTreatment": "fill", "backgroundPaintOrder": 11,
                                    "opacity": "opacity.axis-band"}
    body["colorBindings"]["period-band.fill"] = color
    parts["view"]["body"]["window"] = dict(WINDOW)
    parts["view"]["body"]["periods"] = [{"id": "window"}]
    return parts


def _render(tmp_path: Path, color: str):
    return sr.render(tmp_path, _source(), presentation=_parts(color))


def _contrast_records(rendered) -> list:
    return [item for item in rendered.warning_records if item.payload["code"].startswith("W_SCENE_DECORATION")]


def test_a_band_the_canvas_swallows_renders_and_is_reported_as_a_warning(tmp_path):
    rendered = _render(tmp_path, "surface")  # the band takes the canvas colour: invisible, a decoration miss

    (record,) = _contrast_records(rendered)
    payload = record.payload
    assert (payload["code"], payload["severity"], payload["findingCode"]) == (
        "W_SCENE_DECORATION_CONTRAST", "warning", "E_SCENE_DECORATION_CONTRAST")
    assert payload["primitiveIds"] == [item.scene_id for item in rendered.surface.primitives
                                       if item.purpose == "period-band"]
    facts = payload["measuredFacts"]
    assert facts["floor"] == 1.10 and facts["contrastRatio"] < 1.10
    assert (facts["groundId"], facts["groundKind"], facts["paintChannel"]) == ("canvas", "canvas", "fill")
    assert record.identity in rendered.scene.diagnostics
    assert rendered.contrast_warnings and rendered.contrast_warnings[0].code == "W_SCENE_DECORATION_CONTRAST"
    assert rendered.artifact.content  # the picture is written: nothing failed


def test_the_warning_reaches_the_transport_payloads_with_a_message(tmp_path):
    rendered = _render(tmp_path, "surface")

    rows = [row for row in warning_payloads(rendered) if row["code"] == "W_SCENE_DECORATION_CONTRAST"]
    assert len(rows) == 1 and rows[0]["severity"] == "warning"
    assert "background decoration" in rows[0]["message"]
    validate_scene_document(scene_document(rendered.scene))


def test_a_legible_band_carries_no_contrast_warning(tmp_path):
    rendered = _render(tmp_path, "accent")

    assert _contrast_records(rendered) == []
    assert rendered.contrast_warnings == ()
    assert not [item for item in evaluate_scene_contrast(scene_document(rendered.scene)) if item.severity != "info"]


@pytest.mark.parametrize("color", ["surface", "accent"])
def test_two_renders_are_byte_identical_with_identical_diagnostics(tmp_path, color):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    first = _render(tmp_path / "a", color)
    second = _render(tmp_path / "b", color)

    assert first.artifact.content == second.artifact.content
    assert first.scene.diagnostics == second.scene.diagnostics
