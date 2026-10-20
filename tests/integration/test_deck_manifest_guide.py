"""The deck-manifest guide's files run, and the errors it quotes are the product's (#1842 row 2)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

from chrona.app.cli import main
from tools.check_documented_commands import discover

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
GUIDE = Path("docs/guides/deck-manifest.md")


def _file(name: str) -> str:
    text = (ROOT / GUIDE).read_text(encoding="utf-8")
    match = re.search(rf"<!-- chrona:doc-check file: {re.escape(name)} -->\s*```[^\n]*\n(?P<body>.*?)\n```", text, re.DOTALL)
    assert match is not None, name
    return match["body"] + "\n"


def _run(monkeypatch, capsys, *tokens: str) -> dict:
    monkeypatch.setattr(sys, "argv", ["chrona", *tokens])
    capsys.readouterr()
    try:
        main()
    except SystemExit:
        pass
    lines = capsys.readouterr().out.strip().splitlines()
    return json.loads(lines[-1]) if lines else {"status": "ok"}  # materialize prints nothing on success on this base


def _deck(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    for name in ("deck-project.yaml", "deck-baseline-project.yaml", "deck-baseline-ref.yaml", "deck-view-compare.yaml", "deck-manifest.yaml"):
        (tmp_path / name).write_text(_file(name), encoding="utf-8")
    assert _run(monkeypatch, capsys, "preset", "copy", "mission-light", "--output", "deck-look")["status"] == "ok"


def _manifest(tmp_path: Path) -> dict:
    return yaml.safe_load((tmp_path / "deck-manifest.yaml").read_text(encoding="utf-8"))


def _save(tmp_path: Path, manifest: dict, name: str = "deck-manifest.yaml") -> None:
    (tmp_path / name).write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")


def test_guide_deck_writes_then_checks_both_slides(tmp_path, monkeypatch, capsys):
    _deck(tmp_path, monkeypatch, capsys)
    for slide in ("overview", "compare"):
        written = _run(monkeypatch, capsys, "materialize", "deck-manifest.yaml", "--slide", slide, "--output", f"deck-write-{slide}", "--write")
        assert written["status"] == "ok"
        assert (tmp_path / "deck-generated" / f"{slide}.svg").is_file()
        assert _run(monkeypatch, capsys, "materialize", "deck-manifest.yaml", "--slide", slide, "--output", f"deck-check-{slide}")["status"] == "ok"
    # the compare slide draws one baseline ghost per task; the overview slide, whose View does not compare, draws none
    assert (tmp_path / "deck-generated/compare.svg").read_text(encoding="utf-8").count('data-purpose="snapshot"') == 4
    assert 'data-purpose="snapshot"' not in (tmp_path / "deck-generated/overview.svg").read_text(encoding="utf-8")
    documented = {item.tokens[4] for item in discover(ROOT)
                  if item.path == GUIDE and item.tokens[1:2] == ("materialize",)}
    assert documented == {"overview", "compare"}


def test_guide_rules_hold(tmp_path, monkeypatch, capsys):
    _deck(tmp_path, monkeypatch, capsys)
    base = _manifest(tmp_path)

    missing = yaml.safe_load(yaml.safe_dump(base))
    del missing["slides"][0]["expectedSvg"]
    _save(tmp_path, missing)
    rejected = _run(monkeypatch, capsys, "materialize", "deck-manifest.yaml", "--slide", "overview", "--output", "o1", "--write")
    assert rejected["diagnostics"][0]["code"] == "E_MATERIALIZER_MANIFEST_SCHEMA"
    assert "missing required property 'expectedSvg'" in rejected["diagnostics"][0]["message"]

    renamed = yaml.safe_load(yaml.safe_dump(base))
    renamed["contextDefaults"]["view"]["id"] = "plan-view"
    _save(tmp_path, renamed)
    rejected = _run(monkeypatch, capsys, "materialize", "deck-manifest.yaml", "--slide", "overview", "--output", "o2", "--write")
    assert rejected["diagnostics"][0]["code"] == "E_CLOSURE_ID"

    direct = yaml.safe_load(yaml.safe_dump(base))
    direct["contextDefaults"]["inputs"]["snapshot"].update(kind="project", address="deck-baseline-project.yaml")
    _save(tmp_path, direct)
    rejected = _run(monkeypatch, capsys, "materialize", "deck-manifest.yaml", "--slide", "overview", "--output", "o3", "--write")
    assert rejected["diagnostics"][0]["code"] == "E_MATERIALIZER_MANIFEST_SCHEMA"
    assert "expected exactly 'snapshot-ref'" in rejected["diagnostics"][0]["message"]

    none = yaml.safe_load(yaml.safe_dump(base))
    none["slides"][0]["contextOverrides"]["body"] = {"inputs": {"snapshot": None}}
    _save(tmp_path, none)
    # `inputs: {snapshot: null}` removes the baseline for that slide ...
    assert _run(monkeypatch, capsys, "materialize", "deck-manifest.yaml", "--slide", "overview", "--output", "o4", "--write")["status"] == "ok"
    # ... and a slide whose View compares with it is then refused
    none["slides"][1]["contextOverrides"]["body"]["inputs"] = {"snapshot": None}
    _save(tmp_path, none)
    assert _run(monkeypatch, capsys, "materialize", "deck-manifest.yaml", "--slide", "compare", "--output", "o5", "--write")["status"] == "rejected"


def test_snapshot_ref_without_a_project_names_what_is_missing(tmp_path, monkeypatch, capsys):
    _deck(tmp_path, monkeypatch, capsys)
    (tmp_path / "deck-broken-ref.yaml").write_text(
        "version: chrona/snapshot-ref/v0.3\nkind: snapshot-ref\nid: plan-baseline\n", encoding="utf-8")
    manifest = _manifest(tmp_path)
    manifest["contextDefaults"]["inputs"]["snapshot"]["address"] = "deck-broken-ref.yaml"
    _save(tmp_path, manifest, "deck-broken-manifest.yaml")
    rejected = _run(monkeypatch, capsys, "materialize", "deck-broken-manifest.yaml", "--slide", "compare", "--output", "broken-out", "--write")
    (diagnostic,) = rejected["diagnostics"]
    assert diagnostic["code"] == "E_MATERIALIZER_CONTEXT"
    quoted = re.search(r"```text\n(?P<body>snapshot reference.*?)\n```", (ROOT / GUIDE).read_text(encoding="utf-8"), re.DOTALL)["body"]
    assert diagnostic["message"] == f"E_MATERIALIZER_CONTEXT: {quoted}"
    assert "plan-baseline" in quoted and "deck-broken-ref.yaml" in quoted and "/body/project" in quoted
