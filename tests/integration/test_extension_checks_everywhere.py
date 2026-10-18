"""#1682: profile validation and extension resolution run in every Project path, through one resolver."""
from __future__ import annotations

from hashlib import sha256

import pytest
import yaml

from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from chrona.usecases.project_checks import schedule_project_file, validate_project_file
from chrona.usecases.render_review import RenderRejected

PACKAGE = {"version": "chrona/profile/v0.3", "packageId": "atlas-delivery", "requires": {"projectFormat": "timeline/v0.7"},
           "profiles": {"work": {"extends": "task", "fields": {"risk": {"type": "enum", "enumValues": ["low", "high"], "required": True}}}}}


def _write(tmp_path, risk="low", path="extensions/atlas.yaml", identity=None, package=True):
    (tmp_path / "extensions").mkdir(exist_ok=True)
    content = yaml.safe_dump(PACKAGE).encode()
    if package:
        (tmp_path / "extensions" / "atlas.yaml").write_bytes(content)
    extension = {"packageId": "atlas-delivery", "path": path, "revision": "git:" + "0123456789abcdef" * 2 + "01234567"}
    if identity is not None:
        extension["contentIdentity"] = identity if identity != "real" else "sha256:" + sha256(content).hexdigest()
    project = {"version": "timeline/v0.7", "project": {"id": "atlas"}, "extensions": [extension],
               "objects": {"a": {"type": "work", "title": "A", "fields": {"risk": risk},
                                 "schedule": {"mode": "fixed-span", "start": "2026-03-02", "end": "2026-03-06"}}}}
    target = tmp_path / "project.yaml"
    target.write_text(yaml.safe_dump(project), encoding="utf-8")
    return target


def _codes(outcome):
    return [(d.id, d.path) for d in outcome.diagnostics]


def test_a_valid_package_passes_every_path(tmp_path):
    project = _write(tmp_path, identity="real")
    assert validate_project_file(project).ok and schedule_project_file(project).ok
    render_draft(DraftRenderRequest(project=project, target_kind="svg"))


def test_out_of_enum_value_fails_validate_schedule_and_draft_render_with_its_pointer(tmp_path):
    project = _write(tmp_path, risk="extreme")
    expected = [("E_PROFILE_FIELD_ENUM", "/objects/a/fields/risk")]
    assert _codes(validate_project_file(project)) == expected
    assert _codes(schedule_project_file(project)) == expected
    with pytest.raises(RenderRejected) as caught:
        render_draft(DraftRenderRequest(project=project, target_kind="svg"))
    assert [(d.id, d.path) for d in caught.value.diagnostics] == expected


def test_a_missing_extension_file_fails_every_path_with_its_pointer(tmp_path):
    project = _write(tmp_path, path="extensions/nope.yaml", package=False)
    expected = [("E_EXTENSION_UNRESOLVED", "/extensions/0/path")]
    assert _codes(validate_project_file(project)) == expected
    assert _codes(schedule_project_file(project)) == expected
    with pytest.raises(RenderRejected) as caught:
        render_draft(DraftRenderRequest(project=project, target_kind="svg"))
    assert [(d.id, d.path) for d in caught.value.diagnostics] == expected


def test_an_escaping_path_and_a_wrong_identity_are_pointed(tmp_path):
    escaping = _write(tmp_path, path="../outside.yaml", package=False)
    assert _codes(validate_project_file(escaping)) == [("E_SCHEMA", "/extensions/0")]  # the Project schema already refuses it
    wrong = _write(tmp_path, identity="sha256:" + "0" * 64)
    assert _codes(validate_project_file(wrong)) == [("E_CONTENT_IDENTITY", "/extensions/0/path")]
