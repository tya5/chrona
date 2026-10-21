"""The update guide's weekly example renders its Project members in the five approved designs (#1870 row 6)."""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree

import pytest

from chrona.app.cli import main

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
GUIDE = ROOT / "docs/guides/update-a-plan.md"
README = ROOT / "README.md"
DESIGNS = ("target-b", "yuya", "titlecard", "marquee", "sunday")


def _documented_file(name: str) -> str:
    match = re.search(rf"<!-- chrona:doc-check file: {re.escape(name)} -->\s*```[^\n]*\n(?P<body>.*?)\n```",
                      GUIDE.read_text(encoding="utf-8"), re.DOTALL)
    assert match is not None, name
    return match["body"] + "\n"


def _render(monkeypatch, capsys, tokens: list[str]) -> dict:
    monkeypatch.setattr(sys, "argv", tokens)
    capsys.readouterr()
    main()
    return json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def _write_files(tmp_path: Path) -> None:
    for name in ("update-baseline.yaml", "update-plan.yaml", "update-actual.yaml"):
        (tmp_path / name).write_text(_documented_file(name), encoding="utf-8")


def _texts(path: Path) -> str:
    return " ".join(ElementTree.fromstring(path.read_bytes()).itertext())


@pytest.mark.parametrize("design", DESIGNS)
def test_the_guide_plan_draws_its_note_and_risk_in_each_approved_design(tmp_path, monkeypatch, capsys, design):
    prose = " ".join(GUIDE.read_text(encoding="utf-8").split())
    assert "**Notes and risks** are the top-level `annotations` map of the plan" in prose
    assert "skills/chrona/references/notes-risks-and-lanes.md" in prose
    assert "`W_PRESENTATION_ANNOTATION_NOT_DRAWN`" in prose
    monkeypatch.chdir(tmp_path)
    _write_files(tmp_path)

    result = _render(monkeypatch, capsys, [
        "chrona", "render", "update-plan.yaml", "--actual", "update-actual.yaml",
        "--snapshot", "update-baseline.yaml", "--preset", design, "--output", f"{design}.svg"])

    assert result["status"] == "ok", result
    assert not [item for item in result["warnings"] if item["code"] == "W_PRESENTATION_ANNOTATION_NOT_DRAWN"]
    text = _texts(tmp_path / f"{design}.svg")
    assert "Copy arrived two days late" in text
    assert "Vendor review may move the launch gate" in text


@pytest.mark.parametrize("design", DESIGNS)
def test_an_open_task_has_a_blank_delta_cell_and_one_started_today_has_no_bar(tmp_path, monkeypatch, capsys, design):
    prose = " ".join(GUIDE.read_text(encoding="utf-8").split())
    assert "Build's cell is **blank**" in prose
    assert "`missingBy: {inProgress: blank}`" in prose
    assert "**A task that started on `asOf` has no actual bar yet.**" in prose
    monkeypatch.chdir(tmp_path)
    _write_files(tmp_path)
    (tmp_path / "today.yaml").write_text(
        _documented_file("update-actual.yaml").replace(
            "start: '2026-11-12', openUntil: asOf", "start: '2026-11-16', openUntil: asOf"), encoding="utf-8")
    def delta_cell(actual: str) -> tuple[dict, str]:
        name = f"{design}-{actual.removesuffix('.yaml')}"
        result = _render(monkeypatch, capsys, [
            "chrona", "render", "update-plan.yaml", "--snapshot", "update-baseline.yaml", "--preset", design,
            "--actual", actual, "--output", f"{name}.svg", "--emit-scene", f"{name}.scene.json"])
        scene = json.loads((tmp_path / f"{name}.scene.json").read_text(encoding="utf-8"))
        cells: list[str] = []

        def walk(node):
            if isinstance(node, dict):
                if node.get("purpose") == "table-cell" and str(node.get("id", "")).startswith("cell:build:Δ"):
                    cells.append(node.get("text", ""))
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(scene)
        assert len(cells) == 1, cells
        return result, cells[0]

    open_result, open_cell = delta_cell("update-actual.yaml")
    assert open_cell == "" and open_result["status"] == "ok"
    today_result, today_cell = delta_cell("today.yaml")
    assert today_cell == "" and today_result["status"] == "ok"
    assert [item["code"] for item in today_result["warnings"] if item["code"] == "W_LAYOUT_OPEN_ACTUAL_INVALID"]


@pytest.mark.skipif(importlib.util.find_spec("chrona_fonts_noto_cjk") is None,
                    reason="the unpublished Noto Sans JP provider package is not installed")
def test_the_readme_png_route_passes_font_dirs_and_runs(tmp_path, monkeypatch, capsys):
    text = README.read_text(encoding="utf-8")
    assert "font_dirs" in text
    command = re.search(r'python -c "(?P<code>import pathlib, resvg_py, chrona_fonts_noto_cjk[^\n]*?)"\n', text)
    assert command is not None
    monkeypatch.chdir(tmp_path)
    _write_files(tmp_path)
    (tmp_path / "my-chrona-project").mkdir()
    result = _render(monkeypatch, capsys, ["chrona", "render", "update-plan.yaml", "--locale", "ja-JP",
                                           "--output", "my-chrona-project/plan.svg"])
    assert result["status"] == "ok", result

    exec(compile(command["code"], "<readme>", "exec"), {})

    assert (tmp_path / "my-chrona-project/plan@2x.png").read_bytes().startswith(b"\x89PNG")
