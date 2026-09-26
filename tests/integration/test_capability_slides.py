"""Committed evidence for capabilities no slide exercised before (#434)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

from chrona.app.cli import main

ROOT = Path(__file__).resolve().parents[2]
CZ = ROOT / "examples/controller-z"


def _surface(name: str) -> dict:
    return json.loads((CZ / f"generated/{name}.scene.json").read_text(encoding="utf-8"))["surfaces"][0]


def _primitives(surface: dict) -> dict[str, dict]:
    return {item["id"]: item for item in surface["primitives"]}


def _slot(surface: dict, slot_id: str) -> dict:
    return next(slot for slot in surface["slots"] if slot["id"] == slot_id)["bounds"]


def test_row_band_spans_table_and_timeline():
    surface = _surface("capabilities")
    table, timeline = _slot(surface, "table"), _slot(surface, "timeline")
    stripes = [item["bounds"] for key, item in _primitives(surface).items() if key.startswith("row-band:")]
    assert stripes
    for stripe in stripes:
        assert stripe["inline"] == pytest.approx(table["inline"])
        assert stripe["inline"] + stripe["inlineSize"] == pytest.approx(timeline["inline"] + timeline["inlineSize"])


def test_fill_row_distribution_fills_the_timeline():
    surface = _surface("capabilities")
    timeline = _slot(surface, "timeline")
    rows = sorted((row["bounds"] for row in surface["rows"]), key=lambda bounds: bounds["block"])
    assert rows[-1]["block"] + rows[-1]["blockSize"] == pytest.approx(timeline["block"] + timeline["blockSize"])
    assert rows[0]["blockSize"] > 60  # distributed surplus, not the packed row minimum


def test_band_grouping_draws_group_bands_without_header_rows():
    primitives = _primitives(_surface("capabilities"))
    assert any(item.get("visualRole") == "group-band" for item in primitives.values())
    assert not any(key.startswith("group-header:") for key in primitives)


def _render_with_title(tmp_path: Path, monkeypatch, title: str) -> dict:
    project = yaml.safe_load((CZ / "project.yaml").read_text(encoding="utf-8"))
    project["objects"]["firmware"]["title"] = title
    project_path = tmp_path / "project.yaml"
    project_path.write_text(yaml.safe_dump(project, sort_keys=False, allow_unicode=True), encoding="utf-8")
    scene_path = tmp_path / "scene.json"
    monkeypatch.setattr(sys, "argv", [
        "chrona", "render", str(project_path), "--actual", str(CZ / "actual.yaml"),
        "--view", str(CZ / "views/capabilities.yaml"), "--theme", str(CZ / "themes/capabilities.yaml"),
        "--scheme", str(CZ / "schemes/executive-light.yaml"), "--layout", str(CZ / "layouts/capabilities.yaml"),
        "--output", str(tmp_path / "out.svg"), "--emit-scene", str(scene_path),
    ])
    main()
    return json.loads(scene_path.read_text(encoding="utf-8"))["surfaces"][0]


def test_date_column_keeps_its_position_when_a_title_grows(tmp_path, monkeypatch):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    short = _render_with_title(tmp_path / "a", monkeypatch, "FW Feature Complete")
    longer = _render_with_title(tmp_path / "b", monkeypatch, "FW Feature Complete including the extended validation")
    finish_short = _primitives(short)["column:Finish"]["bounds"]["inline"]
    finish_long = _primitives(longer)["column:Finish"]["bounds"]["inline"]
    assert finish_long == pytest.approx(finish_short)


def test_legend_is_uppercase_and_letter_spaced_and_delta_is_monospace():
    primitives = _primitives(_surface("capabilities"))
    legend = primitives["legend:planned"]
    assert legend["text"] == "PLANNED"
    assert legend["textLayout"]["textTransform"] == "uppercase" and legend["textLayout"]["letterSpacing"] > 0
    delta = primitives["cell:firmware:Δ"]
    assert delta["textLayout"]["family"].startswith("Noto Sans Mono")


def test_a_leader_is_styled_independently_of_its_box():
    primitives = _primitives(_surface("annotations"))
    box, leader = primitives["annotation-box:architecture-callout"], primitives["annotation-leader:architecture-callout"]
    assert leader["paint"]["stroke"] != box["paint"]["stroke"]
    assert leader["paint"]["dash"] and not box["paint"]["dash"]
