"""Owner colours beyond the palette fold into one neutral Other, never a repeated hue (#1628)."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import yaml

from chrona.app.cli import main
from chrona.presentation.model.color_separability import MINIMUM_CATEGORY_DELTA_E, delta_e_2000


ROOT = Path(__file__).resolve().parents[2]

OWNERS = ["pm", "鈴木", "佐藤", "Lena", "Raj", "QT", "田中", "Maria", "Ken"]


def _run(monkeypatch, capsys, *argv):
    monkeypatch.setattr(sys, "argv", ["chrona", *argv])
    capsys.readouterr()
    main()
    return json.loads(capsys.readouterr().out)


def _plan(tmp_path, monkeypatch, capsys, owners=OWNERS):
    rows = ["id,title,type,start,duration,parent,owner",
            "ga,Group A,group,,,,", "gb,Group B,group,,,,", "gc,Group C,group,,,,"]
    for index, owner in enumerate(owners):
        rows.append(f"task-{index},Task {index},task,2026-10-05,3wd,g{'abc'[index % 3]},{owner}")
    table = tmp_path / "plan.csv"
    table.write_text("\n".join(rows) + "\n", encoding="utf-8")
    project = tmp_path / "plan.yaml"
    result = _run(monkeypatch, capsys, "import", str(table), "--calendar", "standard mon-fri",
                  "--role", "responsible=owner", "-o", str(project))
    assert result["status"] == "ok"
    return project


def _mission_light_layout_with_legend(tmp_path):
    source = ROOT / "src/chrona/resources/presets/bundles/mission-light/layout.yaml"
    layout = yaml.safe_load(source.read_bytes())
    layout["id"] = "mission-light-encoding-legend-test"
    layout["root"]["children"].append({
        "id": "encoding-legend", "kind": "slot", "source": "legend",
        "inlineSize": "fill", "blockSize": "content",
        "place": {"inline": "stretch", "block": "end", "safety": "safe"},
        "priority": "preferred", "overflow": "visible-overflow",
    })
    path = tmp_path / "mission-light-encoding-legend.yaml"
    path.write_text(yaml.safe_dump(layout, sort_keys=False), encoding="utf-8")
    return path


def _mission_light_scheme_without_print_claim(tmp_path):
    source = ROOT / "src/chrona/resources/presets/bundles/mission-light/scheme.yaml"
    scheme = yaml.safe_load(source.read_bytes())
    scheme["body"]["suitability"]["print"] = "not-claimed"
    path = tmp_path / "mission-light-unclaimed-print.yaml"
    path.write_text(yaml.safe_dump(scheme, sort_keys=False), encoding="utf-8")
    return path


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
    assert not any(item["code"] == "W_PRESENTATION_SCALE_NOT_SEPARABLE" and item["vision"] == "normal"
                   for item in result["warnings"])


def test_mission_light_eight_owners_get_a_keyed_folded_other_with_distinct_screened_inks(
        tmp_path, monkeypatch, capsys):
    owners = ["Ada", "Benoit", "Chika", "Diego", "Eleni", "Farah", "Gabe", "Hana"]
    project = _plan(tmp_path, monkeypatch, capsys, owners)
    scene_path = tmp_path / "mission-light.json"
    layout = _mission_light_layout_with_legend(tmp_path)
    scheme = _mission_light_scheme_without_print_claim(tmp_path)
    result = _run(monkeypatch, capsys, "render", "--preset", "mission-light", str(project),
                  "--layout", str(layout), "--scheme", str(scheme),
                  "-o", str(tmp_path / "mission-light.svg"), "--emit-scene", str(scene_path))
    assert result["status"] == "ok"

    primitives = json.loads(scene_path.read_text(encoding="utf-8"))["surfaces"][0]["primitives"]
    legend = {item["sourceRef"]: item["paint"]["fill"] for item in primitives
              if item.get("sourceKind") == "legend" and item.get("purpose") == "legend-swatch"
              and item.get("paint", {}).get("fill")}
    assert "scale:series#other" in legend
    non_other_key_inks = [color for source_ref, color in legend.items()
                          if source_ref.startswith("scale:series:") and source_ref != "scale:series#other"]
    assert len(non_other_key_inks) <= 6
    assert len(set(non_other_key_inks)) == len(non_other_key_inks), legend
    folded = [item for item in result["warnings"] if item["code"] == "I_PRESENTATION_SCALE_FOLDED"]
    assert len(folded) == 1 and folded[0]["severity"] == "info"
    assert folded[0]["distinctColors"] <= 6
    assert folded[0]["foldedCount"] == 8 - folded[0]["distinctColors"]
    assert not any(item["code"] == "W_PRESENTATION_SCALE_NOT_SEPARABLE" and item["vision"] == "normal"
                   for item in result["warnings"])
    # The project-local Layout adds a legend slot without changing the
    # packaged mission-light resources. Folded source values share Other ink.
    encoded_marks = {item["encoding"]["value"]: item["paint"]["fill"] for item in primitives
                     if item.get("encoding", {}).get("scaleId") == "series"
                     and item.get("paint", {}).get("fill")}
    assert set(encoded_marks) == set(owners)
    folded_values = set(folded[0]["folded"])
    assert len(folded_values) == folded[0]["foldedCount"]
    other_inks = {encoded_marks[value] for value in folded_values}
    non_other_inks = [encoded_marks[value] for value in owners if value not in folded_values]
    assert len(other_inks) == 1
    assert len(non_other_inks) == folded[0]["distinctColors"]
    assert len(set(non_other_inks)) == len(non_other_inks)
    assert other_inks.isdisjoint(non_other_inks)
