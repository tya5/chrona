"""The CSV import guide's statement about `start` plus `predecessors` matches the product."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from chrona.app.cli import main

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
GUIDE = ROOT / "docs/guides/csv-import.md"


def _run(monkeypatch, capsys, *tokens: str) -> dict:
    monkeypatch.setattr(sys, "argv", ["chrona", *tokens])
    capsys.readouterr()
    try:
        main()
    except SystemExit:
        pass
    return json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def test_guide_says_start_with_predecessors_conflicts_at_schedule_time_and_the_product_does(tmp_path, monkeypatch, capsys):
    text = GUIDE.read_text(encoding="utf-8")
    prose = " ".join(text.split())
    assert "On a row that also has `predecessors` it is a fixed anchor" in prose
    assert "Only `chrona schedule` finds that: `chrona import` and `chrona validate` both report `ok`" in prose
    assert "`E_CONTRADICTORY_BOUNDS`" in prose
    csv = re.search(r"<!-- chrona:doc-check file: anchor.csv -->\s*```csv\n(?P<body>.*?)\n```", text, re.DOTALL)["body"]
    quoted = re.search(r"```text\n(?P<body>Authoritative start anchor.*?)\n```", text, re.DOTALL)["body"]

    monkeypatch.chdir(tmp_path)
    (tmp_path / "anchor.csv").write_text(csv + "\n", encoding="utf-8")
    imported = _run(monkeypatch, capsys, "import", "anchor.csv", "--output", "anchor.yaml", "--calendar", "standard mon-fri")
    assert imported["status"] == "ok"
    assert _run(monkeypatch, capsys, "validate", "anchor.yaml") == {"status": "ok", "diagnostics": []}
    scheduled = _run(monkeypatch, capsys, "schedule", "anchor.yaml")
    assert scheduled["status"] == "rejected"
    (diagnostic,) = scheduled["diagnostics"]
    assert diagnostic["code"] == "E_CONTRADICTORY_BOUNDS"
    assert diagnostic["message"] == quoted
    for named in ("b.start", "2027-01-04", "a-b", "2027-01-18"):
        assert named in quoted
