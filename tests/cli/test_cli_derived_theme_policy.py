"""A derived Theme (v0.16) declares `contrastPolicy` and the render applies it (#1854 row 2)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

from chrona.app.cli import main

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "skills" / "chrona" / "examples" / "launch.yaml"


def _run(monkeypatch, capsys, *argv):
    monkeypatch.setattr(sys, "argv", ["chrona", *argv])
    try:
        main()
    except SystemExit as raised:
        code = raised.code
    else:
        code = 0
    return code, json.loads(capsys.readouterr().out)


@pytest.fixture
def look(tmp_path, monkeypatch, capsys):
    """A copy of the packaged target-b preset (its Theme declares `contrastPolicy: {decoration: none}`)."""
    directory = tmp_path / "tb"
    assert _run(monkeypatch, capsys, "preset", "copy", "target-b", "--output", str(directory))[0] == 0
    return directory


def _derive(look: Path, policy: dict) -> Path:
    path = look / "derived.yaml"
    path.write_text(yaml.safe_dump({
        "version": "chrona/theme/v0.16", "kind": "theme", "id": "derived-target-b",
        "body": {"extends": {"id": "target-b", "path": "theme.yaml"}, "contrastPolicy": policy}}), encoding="utf-8")
    return path


def _render(look, theme, monkeypatch, capsys, tmp_path):
    return _run(monkeypatch, capsys, "render", str(PROJECT), "--preset", str(look / "preset.yaml"),
                "--theme", str(theme), "--output", str(tmp_path / "out.svg"))


def test_a_derived_theme_without_the_policy_keeps_the_bases_policy(look, monkeypatch, capsys, tmp_path):
    code, payload = _render(look, _derive(look, {"mark": "warning"}), monkeypatch, capsys, tmp_path)
    assert (code, payload["status"]) == (0, "ok")  # the base's decoration: none still holds


def test_a_derived_theme_policy_is_applied_by_the_render(look, monkeypatch, capsys, tmp_path):
    code, payload = _render(look, _derive(look, {"decoration": "error"}), monkeypatch, capsys, tmp_path)
    assert code == 1 and payload["status"] == "rejected"
    assert payload["diagnostics"][0]["code"] == "E_SCENE_DECORATION_CONTRAST"
    assert payload["diagnostics"][0]["sourceRef"] == "/body/contrastPolicy/decoration"
