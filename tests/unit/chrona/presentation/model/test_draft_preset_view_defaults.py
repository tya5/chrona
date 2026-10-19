"""Preset preflight validates effective Views without weakening declared inputs (#1563)."""
from datetime import date
from hashlib import sha256

import pytest
import yaml

from chrona.presentation.model.closure import ClosureError, resolve_draft_render
from chrona.resources import safe_load
from chrona.usecases.preset_library import copy_builtin_preset
from tests.support import synthetic_review as sr


def _write(path, value):
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    return path


@pytest.fixture
def inputs(tmp_path):
    project = _write(tmp_path / "project.yaml", sr.with_calendar(sr.project({
        "a": sr.span("a", date(2026, 2, 1), 40),
    })))
    preset = copy_builtin_preset("target-b", tmp_path / "preset")
    return project, preset, preset.parent / "view.yaml"


def _override(tmp_path, view):
    value = safe_load(view.read_bytes())
    value["body"]["markers"][0]["label"] = "Project voice"
    return _write(tmp_path / "override.yaml", value)


def test_declared_thin_view_uses_its_design_without_rewriting_raw_identity(inputs):
    project, preset, view = inputs
    original = view.read_bytes()
    assert "label" not in safe_load(original)["body"]["markers"][0]

    draft = resolve_draft_render(project_path=project, preset_path=preset)

    assert draft.closure.view.view.markers[0]["label"] == {"wording": "marker.asOf"}
    assert draft.closure.view.identity.content_identity == "sha256:" + sha256(original).hexdigest()
    assert view.read_bytes() == original


def test_selected_explicit_view_still_wins_after_declared_set_preflight(inputs, tmp_path):
    project, preset, view = inputs
    draft = resolve_draft_render(project_path=project, preset_path=preset,
                                 view_path=_override(tmp_path, view))
    assert draft.closure.view.view.markers[0]["label"] == "Project voice"


def test_explicit_override_does_not_hide_an_invalid_declared_view(inputs, tmp_path):
    project, preset, view = inputs
    explicit = _override(tmp_path, view)
    invalid = safe_load(view.read_bytes())
    invalid["body"]["markers"][0]["source"] = "not-actual"
    _write(view, invalid)

    with pytest.raises(ClosureError) as raised:
        resolve_draft_render(project_path=project, preset_path=preset, view_path=explicit)
    assert raised.value.diagnostic_id == "E_VIEW_SCHEMA"
    assert raised.value.source_ref.startswith("/body/markers/0/source")


def test_unsupported_declared_view_keeps_preset_provenance_even_when_overridden(inputs, tmp_path):
    project, preset, view = inputs
    explicit = _override(tmp_path, view)
    invalid = safe_load(view.read_bytes())
    invalid["version"] = "chrona/view/v9.9"
    _write(view, invalid)

    with pytest.raises(ClosureError) as raised:
        resolve_draft_render(project_path=project, preset_path=preset, view_path=explicit)
    assert raised.value.diagnostic_id == "E_RESOURCE_VERSION_UNSUPPORTED"
    assert raised.value.source_ref == "/version"
    assert raised.value.declaring_preset_id == "chrona-builtin-target-b"


@pytest.mark.parametrize("change", ["id", "path"])
def test_declared_identity_and_safe_path_checks_remain_required(inputs, change):
    project, preset, _view = inputs
    invalid = safe_load(preset.read_bytes())
    invalid["body"]["resources"]["view"][change] = "wrong-id" if change == "id" else "../outside.yaml"
    _write(preset, invalid)

    with pytest.raises(ClosureError) as raised:
        resolve_draft_render(project_path=project, preset_path=preset)
    # An unsafe path is already rejected by the preset grammar, before I/O.
    assert raised.value.diagnostic_id == ("E_DRAFT_PRESET_RESOURCE" if change == "id" else "E_PRESENTATION_PRESET_SCHEMA")
