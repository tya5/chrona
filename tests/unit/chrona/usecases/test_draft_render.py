import os
import pathlib
import sys
import tempfile
import xml.etree.ElementTree as ET

import pytest

from chrona.app.cli import main
from chrona.usecases.draft_render import (
    DraftRenderRequest, looks_like_preset_path, parse_viewport, render_draft, resolve_preset_argument,
    typesetter_identity, warning_payloads,
)
from chrona.usecases.failure_report import StableFailure, report_failure

PROJECT = """\
version: timeline/v0.7
project: {id: draft-unit, title: Draft unit}
objects:
  design: {type: task, title: Design, schedule: {mode: fixed-span, start: '2026-10-01', end: '2026-10-31'}}
  release: {type: gate, title: Release, schedule: {mode: fixed-point, at: '2026-12-18'}}
relations: []
"""


@pytest.fixture
def project(tmp_path):
    path = tmp_path / "project.yaml"
    path.write_text(PROJECT, encoding="utf-8")
    return path


def test_viewport_parsing_and_its_failures():
    assert parse_viewport("1600xauto") == (1600, None)
    assert parse_viewport("800X600") == (800, 600)
    for value, message in [("900", "viewport must be WIDTHxHEIGHT"), ("wide x tall", "viewport must be WIDTHxHEIGHT"),
                           ("0x10", "viewport dimensions must be positive or block size may be auto")]:
        with pytest.raises(StableFailure) as raised:
            parse_viewport(value)
        report = report_failure(raised.value)
        assert (report.status, report.exit_code, report.diagnostics[0]["code"], report.diagnostics[0]["sourceRef"]) == (
            "failed", 2, "E_COMMAND_VIEWPORT", "/viewport")
        assert report.diagnostics[0]["message"] == message


def test_typesetter_descriptor_rules():
    assert typesetter_identity(None, None, None, "svg") is None
    identity = typesetter_identity("typst", "0.13.1", "grammar", "typst")
    assert (identity.engine, identity.version) == ("typst", "0.13.1")
    with pytest.raises(StableFailure) as raised:
        typesetter_identity("typst", None, None, "svg")
    assert raised.value.code == "E_RENDER_TYPESETTER_DESCRIPTOR" and raised.value.exit_code == 2


def test_typesetter_identity_defaults_from_the_target():
    typst = typesetter_identity(None, None, None, "typst")
    assert (typst.engine, typst.version, typst.adapter_grammar) == ("typst", None, "chrona-typst/v0.1")
    tikz = typesetter_identity(None, None, None, "tikz")
    assert (tikz.engine, tikz.version, tikz.adapter_grammar) == ("tectonic", None, "chrona-tikz/v0.1")
    assert typesetter_identity(None, "0.13.1", None, "typst").version == "0.13.1"


def test_a_preset_value_is_a_path_only_with_a_separator_or_yaml_suffix():
    assert looks_like_preset_path("dir/preset.yaml") and looks_like_preset_path("p.yml")
    assert not looks_like_preset_path("editorial")
    assert resolve_preset_argument(None) == (None, None)
    path, owned = resolve_preset_argument(os.path.join("some", "preset.yaml").replace(os.sep, "/"))
    assert str(path) == os.path.join("some", "preset.yaml") and owned is None


def test_a_builtin_preset_name_is_copied_into_a_temporary_directory_that_the_caller_owns():
    path, owned = resolve_preset_argument("editorial")
    try:
        assert path.is_file() and str(path).startswith(owned.name)
    finally:
        owned.cleanup()
    assert not path.exists()


def test_an_unknown_builtin_preset_leaves_no_temporary_directory(monkeypatch):
    created = []
    real = tempfile.TemporaryDirectory

    def tracking(*args, **kwargs):
        directory = real(*args, **kwargs)
        created.append(directory.name)
        return directory

    monkeypatch.setattr(tempfile, "TemporaryDirectory", tracking)
    with pytest.raises(StableFailure):
        resolve_preset_argument("no-such-preset")
    assert created and not any(pathlib.Path(name).exists() for name in created)


def test_render_draft_returns_the_artifact_and_does_no_io_of_its_own(project, tmp_path, capsys):
    before = sorted(path.name for path in tmp_path.iterdir())
    result = render_draft(DraftRenderRequest(project=project, target_kind="svg"))
    assert result.artifact.target_kind == "svg" and result.artifact.media_type.startswith("image/svg")
    assert ET.fromstring(result.artifact.content).tag.endswith("svg")
    assert sorted(path.name for path in tmp_path.iterdir()) == before
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""
    assert all(isinstance(payload, dict) for payload in warning_payloads(result.rendered))


@pytest.mark.parametrize("with_relations", [False, True])
def test_render_progress_preserves_artifact_scene_and_request_identity(project, with_relations):
    from dataclasses import replace
    from chrona.presentation.model.render_progress import RenderProgress, RenderProgressEvent

    if with_relations:
        project.write_text(PROJECT.replace("relations: []", """relations:
  - id: design-release
    type: dependency
    lag: 0d
    from: {object: design, endpoint: end}
    to: {object: release, endpoint: at}
"""), encoding="utf-8")
    request = DraftRenderRequest(project=project, target_kind="svg")
    events = []
    observed = replace(request, progress=RenderProgress(events.append))
    assert observed == request
    quiet = render_draft(request)
    verbose = render_draft(observed)
    assert verbose.artifact == quiet.artifact
    assert verbose.rendered.scene == quiet.rendered.scene
    assert verbose.rendered.warning_records == quiet.rendered.warning_records
    assert [event for event in events if event.phase != "routing"] == [
        RenderProgressEvent("schedule"), RenderProgressEvent("layout"), RenderProgressEvent("output")]
    routing = [event for event in events if event.phase == "routing"]
    assert routing == [RenderProgressEvent("routing", k, int(with_relations), "route-label-reserved")
                       for k in range(int(with_relations) + 1)]


def test_render_draft_bytes_equal_the_cli_output_file(project, tmp_path, monkeypatch):
    request = DraftRenderRequest(project=project, target_kind="svg", preset="editorial")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["chrona", "render", str(project), "--preset", "editorial", "-o", "cli.svg"])
    main()
    assert (tmp_path / "cli.svg").read_bytes() == render_draft(request).artifact.content


@pytest.mark.parametrize("preset", ["technical-print", "elevated-light"])
def test_png_draft_uses_a_target_peer_and_reports_it_outside_scene(project, preset):
    rendered = render_draft(DraftRenderRequest(project=project, preset=preset, target_kind="png")).rendered
    assert rendered.artifact.content.startswith(b"\x89PNG\r\n\x1a\n")
    fallback = rendered.preset_visual_profile_fallback
    assert fallback is not None
    assert fallback.preset_id == f"chrona-builtin-{preset}"
    assert fallback.preferred_profile == "chrona-output/visual/v0.7-svg"
    assert fallback.selected_profile == "chrona-output/visual/v0.7-png"
    assert fallback.target_kind == "png"
    (payload,) = [item for item in warning_payloads(rendered) if item["code"] == fallback.code]
    assert payload["severity"] == "info"
    assert payload["selectedProfile"] == fallback.selected_profile
    assert payload["preferredProfile"] == fallback.preferred_profile
    assert payload["targetKind"] == "png"
    assert not any(fallback.code in diagnostic for diagnostic in rendered.scene.diagnostics)
    assert not any(fallback.code in diagnostic for diagnostic in rendered.surface.diagnostics)


def test_render_draft_failures_are_typed_for_the_failure_report(project, tmp_path):
    with pytest.raises(StableFailure) as raised:
        render_draft(DraftRenderRequest(project=project, target_kind="svg", viewport="0x0"))
    assert raised.value.code == "E_COMMAND_VIEWPORT"
    with pytest.raises(OSError):
        render_draft(DraftRenderRequest(project=tmp_path / "missing.yaml", target_kind="svg"))
    with pytest.raises(StableFailure) as unknown:
        render_draft(DraftRenderRequest(project=project, target_kind="svg", preset="no-such-preset"))
    assert report_failure(unknown.value).diagnostics[0]["code"] == "E_BUILTIN_PRESET_UNKNOWN"
