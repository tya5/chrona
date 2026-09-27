"""Attached points are drawn on their host's row with their facts visible (#486 A486-2)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from xml.etree import ElementTree

import yaml

from chrona.app.cli import main

ROOT = Path(__file__).resolve().parents[2]
HALCYON = ROOT / "examples/halcyon-1"
GATES = {"campaign-readiness": ("Campaign readiness review", "2027-09-24"),
         "range-safety": ("Range safety review", "2027-10-01")}


def _render(tmp_path: Path, monkeypatch, points: str | None = None, *,
            lanes: bool = False, packing: list[str] | None = None,
            with_delta: bool = False) -> tuple[dict, str]:
    project = yaml.safe_load((HALCYON / "project.yaml").read_text(encoding="utf-8"))
    for object_id, (title, at) in GATES.items():
        project["objects"][object_id] = {"type": "gate", "title": title, "attachesTo": "campaign",
                                         "schedule": {"mode": "fixed-point", "at": at}}
    project_path = tmp_path / "project.yaml"
    project_path.write_text(yaml.safe_dump(project, sort_keys=False), encoding="utf-8")
    preset = tmp_path / "preset"
    monkeypatch.setattr(sys, "argv", ["chrona", "preset", "copy", "mission-light", "--output", str(preset)])
    main()
    view_path = preset / "view.yaml"
    view = yaml.safe_load(view_path.read_text(encoding="utf-8"))
    if lanes:
        if packing is not None:
            view["body"]["rows"]["packing"] = packing
    else:
        view["body"]["rows"]["mode"] = "automatic"
        for key in ("packing", "laneTable", "laneKeys"):
            view["body"]["rows"].pop(key, None)
    view_path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")
    if points is not None:
        view = yaml.safe_load(view_path.read_text(encoding="utf-8"))
        view["body"]["rows"]["points"] = points
        view_path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")
    actual_path = HALCYON / "actual.yaml"
    if with_delta:
        actual = yaml.safe_load(actual_path.read_text(encoding="utf-8"))
        actual["body"]["asOf"] = "2027-10-05"
        actual["body"]["observations"].append({"id": "campaign-readiness-held", "sequence": 1,
                                                 "projectObjectId": "campaign-readiness",
                                                 "actual": {"at": "2027-09-25"}})
        actual_path = tmp_path / "actual.yaml"
        actual_path.write_text(yaml.safe_dump(actual, sort_keys=False), encoding="utf-8")
    scene = tmp_path / "scene.json"
    svg = tmp_path / "out.svg"
    monkeypatch.setattr(sys, "argv", ["chrona", "render", str(project_path), "--actual", str(actual_path),
                                      "--preset", str(preset / "preset.yaml"), "--output", str(svg),
                                      "--emit-scene", str(scene)])
    main()
    return json.loads(scene.read_text(encoding="utf-8"))["surfaces"][0], svg.read_text(encoding="utf-8")


def _row_of(surface: dict, object_id: str) -> str:
    return next(row["id"] for row in surface["rows"] if object_id in {item.split(":")[-1] for item in row.get("items", ())}
                or row["id"].split(":")[-1] == object_id or row["id"] == object_id)


def _primitive(surface: dict, prefix: str) -> dict:
    return next(item for item in surface["primitives"] if item["id"].startswith(prefix))


def test_attached_gates_sit_on_the_host_row_with_title_and_date(tmp_path, monkeypatch):
    surface, svg = _render(tmp_path, monkeypatch)
    rows = {row["id"]: row["bounds"] for row in surface["rows"]}
    host = next(bounds for row_id, bounds in rows.items() if row_id.endswith("campaign"))
    assert not any(row_id.endswith(gate) for row_id in rows for gate in GATES)  # no row of their own
    for object_id, (title, at) in GATES.items():
        mark = _primitive(surface, f"planned:campaign:{object_id}")["bounds"]
        centre = mark["block"] + mark["blockSize"] / 2
        assert host["block"] <= centre <= host["block"] + host["blockSize"]
        label = _primitive(surface, f"member-label:campaign:{object_id}")
        day, month = at[8:], {"09": "Sep", "10": "Oct"}[at[5:7]]
        assert label["text"].startswith(f"{title} · {day} {month}")
        assert title in "".join(ElementTree.fromstring(svg).itertext())


def test_own_row_restores_a_row_per_point(tmp_path, monkeypatch):
    surface, _ = _render(tmp_path, monkeypatch, points="own-row")
    rows = [row["id"] for row in surface["rows"]]
    for gate in GATES:
        assert any(row_id.endswith(gate) for row_id in rows)


def test_attached_gates_share_host_lane_and_keep_facts_in_svg(tmp_path, monkeypatch):
    surface, svg = _render(tmp_path, monkeypatch, lanes=True, with_delta=True)
    host = next(item for item in surface["primitives"]
                if item["sourceRef"] == "campaign" and item["id"].startswith("planned:"))
    visible_text = "".join(ElementTree.fromstring(svg).itertext())
    for object_id, (title, at) in GATES.items():
        mark = next(item for item in surface["primitives"]
                    if item["sourceRef"] == object_id and item["id"].startswith("planned:"))
        assert mark["laneRowId"] == host["laneRowId"]
        label = next(item for item in surface["primitives"]
                     if item["sourceRef"] == object_id and item["id"].startswith("member-label:"))
        day, month = at[8:], {"09": "Sep", "10": "Oct"}[at[5:7]]
        expected = f"{title} · {day} {month}"
        assert label["text"].startswith(expected)
        assert expected in visible_text
    assert "+1d" in next(item["text"] for item in surface["primitives"]
                          if item["sourceRef"] == "campaign-readiness"
                          and item["id"].startswith("member-label:"))
    assert "+1d" in visible_text


def test_lane_packing_without_attached_restores_independent_membership(tmp_path, monkeypatch):
    surface, _ = _render(tmp_path, monkeypatch, lanes=True, packing=["explicit"])
    lane_by_source = {item["sourceRef"]: item["laneRowId"] for item in surface["primitives"]
                      if item["id"].startswith("planned:") and item["sourceRef"] in {*GATES, "campaign"}}
    for gate in GATES:
        assert lane_by_source[gate] != lane_by_source["campaign"]


def test_committed_example_has_two_intermediate_gates_with_visible_lane_facts(tmp_path, monkeypatch):
    example = ROOT / "examples/attached-milestones"
    project = yaml.safe_load((example / "project.yaml").read_text(encoding="utf-8"))
    host = project["objects"]["campaign"]["schedule"]
    gates = ("readiness", "range-clearance")
    for gate in gates:
        point = project["objects"][gate]
        assert point["attachesTo"] == "campaign"
        assert host["start"] < point["schedule"]["at"] < host["end"]

    preset = tmp_path / "preset"
    monkeypatch.setattr(sys, "argv", ["chrona", "preset", "copy", "mission-light", "--output", str(preset)])
    main()
    scene = tmp_path / "scene.json"
    svg = tmp_path / "attached.svg"
    monkeypatch.setattr(sys, "argv", ["chrona", "render", str(example / "project.yaml"),
                                      "--actual", str(example / "actual.yaml"),
                                      "--preset", str(preset / "preset.yaml"),
                                      "--output", str(svg), "--emit-scene", str(scene)])
    main()
    surface = json.loads(scene.read_text(encoding="utf-8"))["surfaces"][0]
    visible_text = "".join(ElementTree.fromstring(svg.read_text(encoding="utf-8")).itertext())
    marks = {item["sourceRef"]: item for item in surface["primitives"]
             if item["id"].startswith("planned:")}
    for gate in gates:
        assert marks[gate]["laneRowId"] == marks["campaign"]["laneRowId"]
        label = next(item["text"] for item in surface["primitives"]
                     if item["sourceRef"] == gate and item["id"].startswith("member-label:"))
        assert label in visible_text
        assert project["objects"][gate]["title"] in label
    assert "Readiness review · 30 Sep · +1d" in visible_text
    assert "Range clearance · 12 Oct" in visible_text
