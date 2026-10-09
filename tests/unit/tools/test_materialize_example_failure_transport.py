from __future__ import annotations

import json
import sys

import pytest

import tools.materialize_example as materializer
from chrona.core.diagnostics import Diagnostic
from chrona.usecases.failure_report import report_failure
from chrona.usecases.render_review import RenderFailed, RenderRejected


def _argv(monkeypatch, tmp_path):
    manifest = tmp_path / "manifest.yaml"
    output = tmp_path / "materialized"
    monkeypatch.setattr(sys, "argv", [
        "materialize-example", str(manifest), "--slide", "synthetic-slide", "--output", str(output),
    ])
    return manifest, output


def test_main_transports_every_rejected_diagnostic_row_and_details(tmp_path, monkeypatch, capsys):
    manifest, output = _argv(monkeypatch, tmp_path)
    error = RenderRejected([
        Diagnostic("E_PROJECT_UNKNOWN_FIELD", "unexpected property 'wireless'", "/wireless",
                   details={"property": "wireless", "expected": "declared project field"}),
        Diagnostic("E_ACTUAL_UNKNOWN_OBJECT", "object 'board-rev-c' is not declared", "/objects/board-rev-c",
                   details={"objectId": "board-rev-c", "expected": "a project object id"}),
    ], component="core")
    monkeypatch.setattr(materializer, "materialize", lambda *args, **kwargs: (_ for _ in ()).throw(error))

    with pytest.raises(SystemExit) as exited:
        materializer.main()

    captured = capsys.readouterr()
    assert exited.value.code == report_failure(error).exit_code == 1
    payload = json.loads(captured.out)
    assert payload == report_failure(error).payload()
    assert payload["status"] == "rejected"
    assert [row["code"] for row in payload["diagnostics"]] == [
        "E_PROJECT_UNKNOWN_FIELD", "E_ACTUAL_UNKNOWN_OBJECT",
    ]
    assert payload["diagnostics"][0]["sourceRef"] == "/wireless"
    assert payload["diagnostics"][0]["details"]["property"] == "wireless"
    assert payload["diagnostics"][1]["sourceRef"] == "/objects/board-rev-c"
    assert payload["diagnostics"][1]["details"]["objectId"] == "board-rev-c"
    assert captured.err == ""


def test_main_transports_render_failure_through_shared_report_mapper(tmp_path, monkeypatch, capsys):
    _argv(monkeypatch, tmp_path)
    error = RenderFailed("E_LAYOUT_MARK_OVERFLOW", "target needs a completed mark", "layout",
                         "/layoutManifest/sources/titlecard")
    monkeypatch.setattr(materializer, "materialize", lambda *args, **kwargs: (_ for _ in ()).throw(error))

    with pytest.raises(SystemExit) as exited:
        materializer.main()

    captured = capsys.readouterr()
    assert exited.value.code == report_failure(error).exit_code == 1
    payload = json.loads(captured.out)
    assert payload == report_failure(error).payload()
    (row,) = payload["diagnostics"]
    assert row["code"] == "E_LAYOUT_MARK_OVERFLOW"
    assert row["component"] == "layout"
    assert row["sourceRef"] == "/layoutManifest/sources/titlecard"
    assert "target needs a completed mark" in row["message"]
    assert captured.err == ""


def test_main_uses_existing_unknown_exception_mapping_without_traceback(tmp_path, monkeypatch, capsys):
    _argv(monkeypatch, tmp_path)
    error = RuntimeError("synthetic materializer operand marker")
    monkeypatch.setattr(materializer, "materialize", lambda *args, **kwargs: (_ for _ in ()).throw(error))

    with pytest.raises(SystemExit) as exited:
        materializer.main()

    captured = capsys.readouterr()
    assert exited.value.code == report_failure(error).exit_code == 2
    payload = json.loads(captured.out)
    assert payload == report_failure(error).payload()
    assert payload["status"] == "failed"
    assert payload["diagnostics"][0]["code"] == "E_TOOL_FAILURE"
    assert "synthetic materializer operand marker" in payload["diagnostics"][0]["message"]
    assert captured.err == ""


def test_main_keeps_success_silent_and_passes_materializer_arguments(tmp_path, monkeypatch, capsys):
    manifest, output = _argv(monkeypatch, tmp_path)
    calls = []
    monkeypatch.setattr(materializer, "materialize", lambda *args, **kwargs: calls.append((args, kwargs)))

    materializer.main()

    assert calls == [((manifest, "synthetic-slide", output), {"write": False})]
    assert capsys.readouterr().out == ""
    assert capsys.readouterr().err == ""


def test_library_materialize_preserves_typed_failure_and_never_prints(tmp_path, monkeypatch, capsys):
    error = RenderFailed("E_THEME_TOKEN_MISSING", "token spacing.s is absent", "theme", "/body/values")
    monkeypatch.setattr(materializer, "_materialize", lambda *args, **kwargs: (_ for _ in ()).throw(error))

    with pytest.raises(RenderFailed) as raised:
        materializer.materialize(tmp_path / "manifest.yaml", "synthetic-slide", tmp_path / "output", write=False)

    assert raised.value is error
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""
