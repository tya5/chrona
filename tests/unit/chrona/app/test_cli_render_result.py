"""The successful-render machine channel is a single stdout envelope."""
from __future__ import annotations

import json

import pytest

from chrona.app import cli


@pytest.mark.parametrize("warnings", [[], [
    {"code": "W_LAYOUT_LABEL_SUPPRESSED", "severity": "warning", "message": "label left out: 設計"},
    {"code": "I_LAYOUT_PLOT_LABELS_SUPPRESSED", "severity": "info", "count": 2, "message": "two labels"},
]])
def test_render_result_has_one_stdout_envelope_and_no_stderr(monkeypatch, capsys, warnings):
    sentinel = object()

    def payloads(rendered):
        assert rendered is sentinel
        return warnings

    monkeypatch.setattr(cli, "warning_payloads", payloads)
    cli._emit_render_result(sentinel)
    captured = capsys.readouterr()
    assert captured.err == ""
    assert len(captured.out.splitlines()) == 1
    assert json.loads(captured.out) == {"status": "ok", "diagnostics": [], "warnings": warnings}
    if warnings:
        assert "設計" in captured.out
