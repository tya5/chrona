"""#995: a decoration below its floor is reported by a real render and fails nothing.

A synthetic Project is rendered through a packaged preset bundle with a named-period band whose colour the test
chooses, so no corpus slide can change what these tests prove.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from chrona.presentation.model.closure import ClosureError
from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document, validate_scene_document
from chrona.usecases.draft_render import warning_payloads
from chrona.usecases.render_review import RenderFailed
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
    # The subject is the decoration class: a legibility finding (a label on an accent band, #980) is not a warning.
    assert not [item for item in evaluate_scene_contrast(scene_document(rendered.scene))
                if item.severity_class == "decoration" and item.severity != "info"]


# --- (c) the Theme's knob restores blocking ---------------------------------------------------------------


def _with_policy(color: str, policy) -> dict:
    parts = _parts(color)
    parts["theme"]["body"]["contrastPolicy"] = policy
    return parts


def test_a_theme_that_declares_decoration_blocking_fails_the_render_on_a_faint_band(tmp_path):
    with pytest.raises(RenderFailed) as raised:
        sr.render(tmp_path, _source(), presentation=_with_policy("surface", {"decoration": "error"}))

    assert (raised.value.code, raised.value.source_ref) == (
        "E_SCENE_DECORATION_CONTRAST", "/body/contrastPolicy/decoration")
    assert "period-band" in raised.value.message and "contrastPolicy.decoration: error" in raised.value.message


def test_the_same_theme_renders_a_legible_band(tmp_path):
    rendered = sr.render(tmp_path, _source(), presentation=_with_policy("accent", {"decoration": "error"}))

    assert _contrast_records(rendered) == [] and rendered.artifact.content


def test_a_theme_that_declares_decoration_warning_is_the_default(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    declared = sr.render(tmp_path / "a", _source(), presentation=_with_policy("surface", {"decoration": "warning"}))
    default = _render(tmp_path / "b", "surface")

    assert [item.identity for item in _contrast_records(declared)] == [item.identity for item in _contrast_records(default)]
    assert declared.artifact.content == default.artifact.content


@pytest.mark.parametrize("policy", [None, {"decoration": "warning"}, {"decoration": "error"}])
def test_a_mark_on_a_translucent_ground_never_fails_a_render_whatever_the_knob(tmp_path, policy):
    # A mark on a translucent host has the code the decoration knob restores, but it is a legibility finding:
    # the corpus gate keeps it, and the render does not start failing on it.
    parts = _parts("accent")
    # Translucent, but strong enough that every decoration still clears its own floor.
    parts["theme"]["body"]["values"]["opacity.axis-band"] = {"type": "number", "value": 0.9}
    if policy is not None:
        parts["theme"]["body"]["contrastPolicy"] = policy
    rendered = sr.render(tmp_path, _source(), presentation=parts)

    findings = evaluate_scene_contrast(scene_document(rendered.scene))
    marks = [item for item in findings if item.severity == "error"]
    assert marks and {(item.code, item.severity_class) for item in marks} == {
        ("E_SCENE_CONTRAST_GROUND_UNSUPPORTED", "legibility")}
    assert rendered.artifact.content


def test_the_knob_changes_nothing_about_text_legibility_at_theme_resolution(tmp_path):
    for policy in (None, {"decoration": "warning"}, {"decoration": "error"}):
        parts = _parts("accent")
        parts["theme"]["body"]["colorBindings"]["variance-behind.fill"] = "surface"  # state text as faint as the canvas
        if policy is not None:
            parts["theme"]["body"]["contrastPolicy"] = policy
        directory = tmp_path / f"p{len(list(tmp_path.iterdir()))}"
        directory.mkdir()
        with pytest.raises(ClosureError) as raised:
            sr.render(directory, _source(), presentation=parts)
        assert (raised.value.diagnostic_id, raised.value.source_ref) == (
            "E_SCHEME_STATE_TEXT_CONTRAST", "/body/roles/variance-behind/fill")


@pytest.mark.parametrize("policy,pointer", [
    ({"decoration": "info"}, "/body/contrastPolicy/decoration"), ({"marks": "warning"}, "/body/contrastPolicy"),
    ({"decoration": None}, "/body/contrastPolicy/decoration"), ("error", "/body/contrastPolicy")])
def test_an_unknown_policy_is_refused_by_the_schema_before_any_render(tmp_path, policy, pointer):
    with pytest.raises(ClosureError) as raised:
        sr.render(tmp_path, _source(), presentation=_with_policy("accent", policy))

    assert (raised.value.diagnostic_id, raised.value.source_ref) == ("E_THEME_SCHEMA", pointer)


@pytest.mark.parametrize("color", ["surface", "accent"])
def test_two_renders_are_byte_identical_with_identical_diagnostics(tmp_path, color):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    first = _render(tmp_path / "a", color)
    second = _render(tmp_path / "b", color)

    assert first.artifact.content == second.artifact.content
    assert first.scene.diagnostics == second.scene.diagnostics
