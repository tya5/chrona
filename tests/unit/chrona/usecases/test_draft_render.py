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
    for values, kind in [((None, None, None), "typst"), (("typst", None, None), "svg")]:
        with pytest.raises(StableFailure) as raised:
            typesetter_identity(*values, kind)
        assert raised.value.code == "E_RENDER_TYPESETTER_DESCRIPTOR" and raised.value.exit_code == 2


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
    with pytest.raises(ValueError):
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


def test_render_draft_bytes_equal_the_cli_output_file(project, tmp_path, monkeypatch):
    request = DraftRenderRequest(project=project, target_kind="svg", preset="editorial")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["chrona", "render", str(project), "--preset", "editorial", "-o", "cli.svg"])
    main()
    assert (tmp_path / "cli.svg").read_bytes() == render_draft(request).artifact.content


def test_render_draft_failures_are_typed_for_the_failure_report(project, tmp_path):
    with pytest.raises(StableFailure) as raised:
        render_draft(DraftRenderRequest(project=project, target_kind="svg", viewport="0x0"))
    assert raised.value.code == "E_COMMAND_VIEWPORT"
    with pytest.raises(OSError):
        render_draft(DraftRenderRequest(project=tmp_path / "missing.yaml", target_kind="svg"))
    with pytest.raises(ValueError) as unknown:
        render_draft(DraftRenderRequest(project=project, target_kind="svg", preset="no-such-preset"))
    assert report_failure(unknown.value).diagnostics[0]["code"] == "E_BUILTIN_PRESET_UNKNOWN"
