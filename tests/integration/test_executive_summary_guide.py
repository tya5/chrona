"""Run the literal executive-summary guide recipe and inspect native output."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree

import yaml

from chrona.app.cli import main
from tools.check_documented_commands import discover


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
GUIDE = Path("docs/guides/executive-summary.md")


def _documented_file(name: str) -> str:
    text = (ROOT / GUIDE).read_text(encoding="utf-8")
    pattern = re.compile(
        rf"<!-- chrona:doc-check file: {re.escape(name)} -->\s*```[^\n]*\n(?P<body>.*?)\n```",
        re.DOTALL,
    )
    match = pattern.search(text)
    assert match is not None, name
    return match["body"] + "\n"


def _commands(*, command: str) -> tuple[tuple[str, ...], ...]:
    return tuple(item.tokens for item in discover(ROOT)
                 if item.path == GUIDE and len(item.tokens) > 1 and item.tokens[1] == command)


def _run(monkeypatch, capsys, tokens: tuple[str, ...]) -> dict:
    monkeypatch.setattr(sys, "argv", list(tokens))
    capsys.readouterr()
    main()
    return json.loads(capsys.readouterr().out.strip().splitlines()[-1])


def test_guide_imports_and_renders_the_same_recipe_with_all_three_presets(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "executive-plan.csv").write_text(_documented_file("executive-plan.csv"), encoding="utf-8")
    (tmp_path / "executive-view.yaml").write_text(_documented_file("executive-view.yaml"), encoding="utf-8")

    imports = _commands(command="import")
    assert len(imports) == 1, imports
    assert _run(monkeypatch, capsys, imports[0])["status"] == "ok"

    copies = tuple(item.tokens for item in discover(ROOT)
                   if item.path == GUIDE and item.tokens[1:2] == ("preset",))
    assert len(copies) == 1, copies
    assert _run(monkeypatch, capsys, copies[0])["status"] == "ok"
    copied_layout = tmp_path / "executive-layout" / "layout.yaml"
    layout = yaml.safe_load(copied_layout.read_text(encoding="utf-8"))
    layout["reviewSurface"]["rowDistribution"] = "fill"
    copied_layout.write_text(yaml.safe_dump(layout, sort_keys=False), encoding="utf-8")

    renders = _commands(command="render")
    assert len(renders) == 3, renders
    assert "--preset" not in renders[0]
    assert "executive-light" in renders[1]
    assert renders[2][renders[2].index("--preset") + 1] == "mission-light"

    for tokens in renders:
        result = _run(monkeypatch, capsys, tokens)
        assert result["status"] == "ok", result
        output = Path(tokens[tokens.index("--output") + 1])
        scene = Path(tokens[tokens.index("--emit-scene") + 1])
        svg = output.read_bytes()
        assert svg.startswith(b"<svg")
        visible_text = " ".join(ElementTree.fromstring(svg).itertext())
        assert "Design sign-off" in visible_text
        assert "Public launch" in visible_text
        primitives = json.loads(scene.read_text(encoding="utf-8"))["surfaces"][0]["primitives"]
        planned = [item for item in primitives if item.get("purpose") == "planned" and item.get("sourceKind") == "object"]
        gates = {item.get("sourceRef") for item in planned
                 if item.get("sourceRef") in {"design-signoff", "launch"} and item.get("kind") == "Symbol"}
        summaries = [item for item in planned
                     if item.get("sourceRef") in {"programme", "design", "delivery"} and item.get("kind") == "Rect"]
        assert gates == {"design-signoff", "launch"}, gates
        assert {item.get("sourceRef") for item in summaries} == {"programme", "design", "delivery"}
        assert len(summaries) == 3, summaries


def _render_planned(monkeypatch, capsys, tmp_path, csv: str, view: str, *extra: str) -> tuple[str, set[str]]:
    for stale in ("project.yaml", "out.svg", "out.scene.json"):
        (tmp_path / stale).unlink(missing_ok=True)
    (tmp_path / "plan.csv").write_text(csv, encoding="utf-8")
    (tmp_path / "view.yaml").write_text(view, encoding="utf-8")
    assert _run(monkeypatch, capsys, ("chrona", "import", "plan.csv", "--output", "project.yaml",
                                      "--calendar", "standard mon-fri", "--project-id", "p", "--title", "P"))["status"] == "ok"
    result = _run(monkeypatch, capsys, ("chrona", "render", "project.yaml", "--view", "view.yaml", *extra,
                                        "--output", "out.svg", "--emit-scene", "out.scene.json"))
    assert result["status"] == "ok", result
    text = " ".join(ElementTree.fromstring((tmp_path / "out.svg").read_bytes()).itertext())
    primitives = json.loads((tmp_path / "out.scene.json").read_text(encoding="utf-8"))["surfaces"][0]["primitives"]
    rects = {item["sourceRef"] for item in primitives
             if item.get("purpose") == "planned" and item.get("sourceKind") == "object" and item.get("kind") == "Rect"}
    return text, rects


def test_guide_depth_counts_from_the_top_level_rows_on_nested_and_grouped_only_plans(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    nested_csv, view = _documented_file("executive-plan.csv"), _documented_file("executive-view.yaml")
    assert "depth: 1" in view
    # Nested plan: the single programme row is the top; depth 1 adds the two phases.
    text, rects = _render_planned(monkeypatch, capsys, tmp_path, nested_csv, view)
    assert rects == {"programme", "design", "delivery"}
    assert "Design sign-off" in text and "Public launch" in text

    # Grouped-only plan: phases are the top-level rows, so the same page is depth 0 ...
    lines = [line for line in nested_csv.splitlines() if not line.startswith("programme,")]
    grouped_csv = "\n".join(line.removesuffix("programme") if line.endswith(",programme") else line
                            for line in lines) + "\n"
    text, rects = _render_planned(monkeypatch, capsys, tmp_path, grouped_csv, view.replace("depth: 1", "depth: 0"))
    assert rects == {"design", "delivery"}
    assert "Design sign-off" in text and "Public launch" in text

    # ... and depth 1 on that plan reaches the tasks, as the guide warns.
    _text, rects = _render_planned(monkeypatch, capsys, tmp_path, grouped_csv, view)
    assert {"research", "build"} <= rects


def test_guide_table_header_follows_the_render_locale(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    view = _documented_file("executive-view.yaml")
    assert "header: {wording: column.task}" in view
    for locale, header in (("en-US", "Task"), ("ja-JP", "タスク")):
        text, _rects = _render_planned(monkeypatch, capsys, tmp_path, _documented_file("executive-plan.csv"), view,
                                       "--locale", locale)
        assert header in text and "Work item" not in text
