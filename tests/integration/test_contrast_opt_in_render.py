"""#1126: contrast constraints are an opt-in design option, proven through real renders.

A synthetic Project is rendered through a packaged preset bundle whose period band is the accent colour, so a
member label lies on a ground it misses the ground-text floor on (4.44 against 4.5): a text finding that no
render reported before. No corpus slide can change what these tests prove.
"""
from __future__ import annotations

import pytest

from chrona.presentation.scene.contrast_policy import POLICY_MEMBERS, STRICT_SEVERITIES, evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document
from chrona.usecases.render_review import RenderFailed
from tests.integration.test_contrast_severity_render import _parts, _source
from pathlib import Path
from tests.support import synthetic_review as sr

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
STARTER_CATALOG = ROOT / "src/chrona/resources/icons/chrona-theme-starter-v2026-10-09.yaml"


def _render(tmp_path, policy=None, *, name="r"):
    directory = tmp_path / name
    directory.mkdir()
    parts = _parts("accent")
    if policy is not None:
        parts["theme"]["body"]["contrastPolicy"] = policy
    return sr.render(directory, _source(), presentation=parts)


def _text_records(rendered):
    return [item for item in rendered.warning_records if item.payload["code"] == "W_SCENE_STATE_TEXT_CONTRAST"]


def test_a_theme_that_declares_nothing_is_not_blocked_and_the_miss_is_a_typed_warning(tmp_path):
    rendered = _render(tmp_path)

    (record,) = _text_records(rendered)
    payload = record.payload
    assert (payload["severity"], payload["findingCode"]) == ("warning", "E_SCENE_STATE_TEXT_CONTRAST")
    assert payload["measuredFacts"]["floor"] == 4.5 and payload["measuredFacts"]["contrastRatio"] < 4.5
    assert record.identity in rendered.scene.diagnostics
    assert rendered.artifact.content


def test_the_same_miss_is_an_error_of_the_gate_without_the_theme_default(tmp_path):
    # Evidence that the default, not the evaluator, is what unblocks the Theme: the corpus tool's strict gate sees it.
    rendered = _render(tmp_path)

    findings = evaluate_scene_contrast(scene_document(rendered.scene))
    assert [item for item in findings if item.severity == "error" and item.code == "E_SCENE_STATE_TEXT_CONTRAST"]


@pytest.mark.parametrize("severity", ["warning", "none", "error"])
def test_an_unrelated_member_never_changes_the_outcome(tmp_path, severity):
    rendered = _render(tmp_path, {"mark": severity, "decoration": severity})

    assert len(_text_records(rendered)) == 1


def test_a_theme_that_opts_ground_text_into_error_fails_the_render(tmp_path):
    with pytest.raises(RenderFailed) as raised:
        _render(tmp_path, {"groundText": "error"})

    assert (raised.value.code, raised.value.source_ref) == (
        "E_SCENE_STATE_TEXT_CONTRAST", "/body/contrastPolicy/groundText")
    assert "contrastPolicy.groundText: error" in raised.value.message and "member-label" in raised.value.message


def test_ground_text_set_to_none_reports_nothing_and_renders(tmp_path):
    rendered = _render(tmp_path, {"groundText": "none"})

    assert _text_records(rendered) == [] and rendered.artifact.content


def test_ground_text_set_to_warning_equals_the_default_byte_for_byte(tmp_path):
    declared = _render(tmp_path, {"groundText": "warning"}, name="a")
    default = _render(tmp_path, name="b")

    assert declared.artifact.content == default.artifact.content
    assert declared.scene.diagnostics == default.scene.diagnostics


def test_the_policy_changes_only_diagnostics_never_the_picture(tmp_path):
    pictures = {severity: _render(tmp_path, {"groundText": severity}, name=severity).artifact.content
                for severity in ("none", "warning")}

    assert pictures["none"] == pictures["warning"]


def test_the_error_class_follows_the_finding_not_the_neighbour(tmp_path):
    # `stateText` and `mark` at error do not fail a render whose only miss is ground text.
    rendered = _render(tmp_path, {"stateText": "error", "mark": "error", "unsupportedGround": "error"})

    assert len(_text_records(rendered)) == 1


# --- the packaged presets are held to the floors by explicit opt-in --------------------------------------------

# `editorial-readable-default` carries only a Theme (it reuses the editorial scheme, layout and view).
BUNDLES = ("control-room-dark", "editorial", "elevated-light", "executive-light",
           "mission-light", "print-mono", "technical-print")


@pytest.mark.parametrize("bundle", BUNDLES)
def test_an_opted_in_bundled_preset_renders_a_standard_project_with_no_floor_miss(tmp_path, bundle):
    parts = sr.bundle(bundle)
    parts["theme"]["body"]["contrastPolicy"] = {member: "error" for member in POLICY_MEMBERS}
    directory = tmp_path / bundle
    directory.mkdir()

    rendered = sr.render(directory, _source(), presentation=parts, icon_catalogs=(STARTER_CATALOG,))

    assert rendered.artifact.content
    assert not [item for item in rendered.warning_records if item.payload["code"].startswith("W_SCENE_")
                and "CONTRAST" in item.payload["code"]]


def test_an_opted_in_preset_that_regresses_is_blocked(tmp_path):
    parts = sr.bundle("executive-light")
    parts["theme"]["body"]["contrastPolicy"] = {member: "error" for member in POLICY_MEMBERS}
    parts["theme"]["body"]["colorBindings"]["variance-behind.fill"] = "surface"  # then Theme resolution refuses it
    (tmp_path / "x").mkdir()
    from chrona.presentation.model.closure import ClosureError

    with pytest.raises((ClosureError, RenderFailed)):
        sr.render(tmp_path / "x", _source(), presentation=parts)


def test_the_repository_gate_default_is_the_strict_severities():
    assert STRICT_SEVERITIES == {"mark": "error", "stateText": "error", "groundText": "error",
                                 "unsupportedGround": "error", "decoration": "warning"}
