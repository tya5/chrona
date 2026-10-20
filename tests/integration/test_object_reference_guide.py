"""The objectReference guide's files run and show what the guide says (#1842 row 2)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

from chrona.app.cli import main

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
GUIDE = ROOT / "docs/guides/object-reference.md"
FILES = ("ref-profile.yaml", "ref-plan.yaml", "ref-view.yaml")


def _run(monkeypatch, capsys, *tokens: str) -> dict:
    monkeypatch.setattr(sys, "argv", ["chrona", *tokens])
    capsys.readouterr()
    try:
        main()
    except SystemExit:
        pass
    out = capsys.readouterr().out.strip()
    try:
        return json.loads(out)  # `schedule` prints indented JSON
    except json.JSONDecodeError:
        return json.loads(out.splitlines()[-1])


def _write_files(tmp_path: Path) -> None:
    text = GUIDE.read_text(encoding="utf-8")
    for name in FILES:
        match = re.search(rf"<!-- chrona:doc-check file: {re.escape(name)} -->\s*```[^\n]*\n(?P<body>.*?)\n```", text, re.DOTALL)
        assert match is not None, name
        (tmp_path / name).write_text(match["body"] + "\n", encoding="utf-8")


def test_guide_plan_validates_and_the_view_shows_target_titles(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_files(tmp_path)
    assert _run(monkeypatch, capsys, "validate", "ref-plan.yaml") == {"status": "ok", "diagnostics": []}
    assert _run(monkeypatch, capsys, "schedule", "ref-plan.yaml")["status"] == "ok"
    assert _run(monkeypatch, capsys, "render", "ref-plan.yaml", "--preset", "mission-light", "--view", "ref-view.yaml",
                "--output", "ref.svg")["status"] == "ok"
    svg = (tmp_path / "ref.svg").read_text(encoding="utf-8")
    for shown in (">Public API v2<", ">Partner portal<", ">Aiko, Ben<", ">Ben<"):
        assert shown in svg
    assert "del-api" not in svg  # the stored id is not drawn when the target has a title


def test_guide_error_pointers_hold(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_files(tmp_path)
    plan = yaml.safe_load((tmp_path / "ref-plan.yaml").read_text(encoding="utf-8"))
    plan["objects"]["api"]["fields"] = {"deliverable": "del-portl", "reviewers": ["aiko", "del-api"]}
    (tmp_path / "bad.yaml").write_text(yaml.safe_dump(plan, sort_keys=False), encoding="utf-8")
    report = _run(monkeypatch, capsys, "validate", "bad.yaml")
    assert report["status"] == "rejected"
    assert {item["code"] for item in report["diagnostics"]} == {"E_PROFILE_FIELD_TYPE"}
    assert {item["sourceRef"] for item in report["diagnostics"]} >= {
        "/objects/api/fields/deliverable", "/objects/api/fields/reviewers/1"}
