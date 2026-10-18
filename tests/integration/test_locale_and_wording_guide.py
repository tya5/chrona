"""The locale-and-wording guide's runnable example renders the localized and overridden texts it describes (#1724)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree

from chrona.app.cli import main
from tools.check_documented_commands import discover


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
GUIDE = Path("docs/guides/locale-and-wording.md")
FILES = ("locale-plan.yaml", "locale-actual.yaml", "locale-view.yaml", "locale-detail.yaml")


def _documented_file(name: str) -> str:
    text = (ROOT / GUIDE).read_text(encoding="utf-8")
    match = re.search(rf"<!-- chrona:doc-check file: {re.escape(name)} -->\s*```[^\n]*\n(?P<body>.*?)\n```",
                      text, re.DOTALL)
    assert match is not None, name
    return match["body"] + "\n"


def _write_files(tmp_path: Path) -> None:
    for name in FILES:
        (tmp_path / name).write_text(_documented_file(name), encoding="utf-8")


def _render(monkeypatch, capsys, tokens: list[str]) -> dict:
    monkeypatch.setattr(sys, "argv", tokens)
    capsys.readouterr()
    try:
        main()
    except SystemExit:
        pass
    return json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def _texts(svg: Path) -> list[str]:
    root = ElementTree.parse(svg).getroot()
    return ["".join(node.itertext()).strip() for node in root.iter("{http://www.w3.org/2000/svg}text")]


def _guide_renders() -> list[list[str]]:
    commands = [list(item.tokens) for item in discover(ROOT) if item.path == GUIDE and item.tokens[1:2] == ("render",)]
    assert len(commands) == 2
    return commands


def test_guide_renders_japanese_headers_marker_legend_override_and_years(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_files(tmp_path)
    ja, en = _guide_renders()
    assert _render(monkeypatch, capsys, ja)["status"] == "ok"
    assert _render(monkeypatch, capsys, en)["status"] == "ok"
    japanese, english = _texts(tmp_path / "locale-ja.svg"), _texts(tmp_path / "locale-en.svg")

    # table headers: the table entry (column.task) and the View wording.keys override (column.plan)
    assert {"タスク", "予定"} <= set(japanese) and "計画" not in japanese
    assert {"Task", "予定"} <= set(english)
    # marker and legend: table entries; the closed-day legend is the View override, never Weekend
    assert {"本日", "計画期間", "実績", "マイルストーン", "依存関係", "休日"} <= set(japanese)
    assert {"TODAY", "TASK DURATION", "ACTUAL", "MILESTONE", "DEPENDENCY", "休日"} <= set(english)
    assert "WEEKEND" not in english and "休業日" not in japanese
    # honest limits: the default Progress label is still English under ja-JP
    assert "PROGRESS" in japanese
    # years in multi-year table dates, and the axis
    assert "2026年12月14日 – 2026年12月24日" in japanese and "2026年12月25日 – 2027年1月14日" in japanese
    assert "2027年1月15日" in japanese and "2026年12月" in japanese and "2027年1月" in japanese
    assert "25 Dec 2026 – 14 Jan 2027" in english


def test_guide_table_entry_is_used_without_the_override_and_wording_keys_reach_a_string_legend(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_files(tmp_path)
    view = (tmp_path / "locale-view.yaml").read_text(encoding="utf-8")
    (tmp_path / "locale-view.yaml").write_text(view.replace("      column.plan: 予定\n", ""), encoding="utf-8")
    detail = (tmp_path / "locale-detail.yaml").read_text(encoding="utf-8")
    (tmp_path / "locale-detail.yaml").write_text(detail.replace("{wording: legend.calendar-closed}", "Weekend"),
                                                 encoding="utf-8")
    ja, _ = _guide_renders()
    assert _render(monkeypatch, capsys, ja)["status"] == "ok"
    japanese = _texts(tmp_path / "locale-ja.svg")
    assert "計画" in japanese  # level 1: the table entry once the override is gone
    assert "休日" in japanese and "WEEKEND" not in japanese  # level 3 replaces an authored string


def test_guide_unknown_wording_key_is_rejected_with_the_documented_code(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_files(tmp_path)
    view = (tmp_path / "locale-view.yaml").read_text(encoding="utf-8")
    (tmp_path / "locale-view.yaml").write_text(view.replace("column.plan: 予定", "column.nope: x"), encoding="utf-8")
    ja, _ = _guide_renders()
    result = _render(monkeypatch, capsys, ja)
    assert result["status"] == "rejected"
    assert [(d["code"], d["sourceRef"]) for d in result["diagnostics"]] == [
        ("E_VIEW_WORDING_UNKNOWN", "/body/wording/keys/column.nope")]
    assert "E_VIEW_WORDING_UNKNOWN" in (ROOT / GUIDE).read_text(encoding="utf-8")
    assert "/body/wording/keys/column.nope" in (ROOT / GUIDE).read_text(encoding="utf-8")


def test_guide_key_table_matches_the_bundled_wording_table():
    from chrona.presentation.model.wording_tables import wording_catalog
    text = (ROOT / GUIDE).read_text(encoding="utf-8")
    catalog = wording_catalog()
    for key in catalog["en-US"]:
        assert f"`{key}`" in text, key
    for table in catalog.values():
        for key in ("column.task", "legend.calendar-closed", "missing.inProgress"):
            assert table[key] in text
