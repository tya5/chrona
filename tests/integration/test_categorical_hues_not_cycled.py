"""Owner colours beyond the palette fold into one neutral Other, never a repeated hue (#1628)."""
from __future__ import annotations

import json
import sys

from chrona.app.cli import main
from chrona.presentation.model.color_separability import MINIMUM_CATEGORY_DELTA_E, delta_e_2000

OWNERS = ["pm", "鈴木", "佐藤", "Lena", "Raj", "QT", "田中", "Maria", "Ken"]


def _run(monkeypatch, capsys, *argv):
    monkeypatch.setattr(sys, "argv", ["chrona", *argv])
    capsys.readouterr()
    main()
    return json.loads(capsys.readouterr().out)


def _plan(tmp_path, monkeypatch, capsys):
    rows = ["id,title,type,start,duration,parent,owner",
            "ga,Group A,group,,,,", "gb,Group B,group,,,,", "gc,Group C,group,,,,"]
    for index in range(len(OWNERS)):
        rows.append(f"task-{index},Task {index},task,2026-10-05,3wd,g{'abc'[index % 3]},{OWNERS[index]}")
    table = tmp_path / "plan.csv"
    table.write_text("\n".join(rows) + "\n", encoding="utf-8")
    project = tmp_path / "plan.yaml"
    result = _run(monkeypatch, capsys, "import", str(table), "--calendar", "standard mon-fri",
                  "--role", "responsible=owner", "-o", str(project))
    assert result["status"] == "ok"
    return project


def test_wallboard_dark_legend_has_no_two_entries_with_one_colour(tmp_path, monkeypatch, capsys):
    project = _plan(tmp_path, monkeypatch, capsys)
    scene_path = tmp_path / "scene.json"
    result = _run(monkeypatch, capsys, "render", "--preset", "wallboard-dark", str(project),
                  "-o", str(tmp_path / "out.svg"), "--emit-scene", str(scene_path))
    assert result["status"] == "ok"
    primitives = json.loads(scene_path.read_text(encoding="utf-8"))["surfaces"][0]["primitives"]
    legend = {item["sourceRef"]: item["paint"]["fill"] for item in primitives
              if item.get("sourceKind") == "legend" and item.get("purpose") == "legend-swatch"}
    assert "scale:series#other" in legend
    # Only painted scale values and the calendar key remain; no unused base Planned/Milestone key is synthesized.
    assert "planned" not in legend and "milestone" not in legend
    colors = list(legend.values())
    assert len(set(colors)) == len(colors), legend
    scale_colors = [color for ref, color in legend.items() if ref.startswith("scale:") and ref != "scale:series#other"]
    for index, color in enumerate(scale_colors):
        for other in scale_colors[index + 1:]:
            assert delta_e_2000(color, other) >= MINIMUM_CATEGORY_DELTA_E, legend
    folded = [item for item in result["warnings"] if item["code"] == "I_PRESENTATION_SCALE_FOLDED"]
    assert len(folded) == 1 and folded[0]["severity"] == "info"
    assert folded[0]["foldedCount"] == len(OWNERS) - folded[0]["distinctColors"]
    assert not any(item["code"] == "W_PRESENTATION_SCALE_NOT_SEPARABLE" for item in result["warnings"])
