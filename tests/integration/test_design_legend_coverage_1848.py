"""Each approved design keys every band role it draws exactly once, weekend apart from holiday (#1848)."""
from __future__ import annotations

import json
import sys

import pytest

from chrona.app.cli import main

DESIGNS = ("target-b", "yuya", "titlecard", "marquee", "sunday")
CODE = "W_LEGEND_ROLE_UNKEYED"
PLAN = """\
version: timeline/v0.7
project: {id: keys, title: Legend keys, calendar: office}
calendars:
  office:
    working_days: [mon, tue, wed, thu, fri]
    exceptions: [{date: '2026-11-26', working: false}]
objects:
  a: {type: task, title: Build, schedule: {mode: fixed-span, start: '2026-11-16', end: '2026-12-07'}}
  b: {type: task, title: Test, schedule: {mode: fixed-span, start: '2026-12-07', end: '2026-12-21'}}
relations:
- {id: a-b, type: dependency, from: {object: a, endpoint: end}, to: {object: b, endpoint: start}, lag: 0d}
"""
ACTUAL = """\
version: chrona/actual-set/v0.3
kind: actual-set
id: keys-observed
body:
  asOf: '2026-11-30'
  observations:
  - {id: a-1, sequence: 1, projectObjectId: a, actual: {start: '2026-11-16', openUntil: asOf, progress: 0.5}}
"""


def _primitives(node):
    if isinstance(node, dict):
        if "purpose" in node:
            yield node
        for value in node.values():
            yield from _primitives(value)
    elif isinstance(node, list):
        for value in node:
            yield from _primitives(value)


@pytest.mark.parametrize("design", DESIGNS)
def test_every_drawn_band_has_one_matching_key(tmp_path, monkeypatch, capsys, design):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "plan.yaml").write_text(PLAN, encoding="utf-8")
    (tmp_path / "actual.yaml").write_text(ACTUAL, encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["chrona", "render", "plan.yaml", "--actual", "actual.yaml", "--preset", design,
                                      "--output", "out.svg", "--emit-scene", "out.scene.json"])
    main()
    result = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    primitives = list(_primitives(json.loads((tmp_path / "out.scene.json").read_text(encoding="utf-8"))))

    assert result["status"] == "ok", result
    drawn = {role: {item["paint"]["fill"] for item in primitives if item["purpose"] == role}
             for role in ("calendar-closed", "calendar-exception")}
    assert drawn["calendar-closed"] and drawn["calendar-exception"]
    swatches = {role: [item for item in primitives if item["purpose"] == "legend-swatch" and item["sourceRef"] == role]
                for role in drawn}
    labels = {role: [item["text"] for item in primitives
                     if item["purpose"] == "legend-label" and item["sourceRef"] == role] for role in drawn}
    for role in drawn:
        assert len(swatches[role]) == 1 and len(labels[role]) == 1, (role, swatches[role], labels[role])
        assert {swatches[role][0]["paint"]["fill"]} == drawn[role], role
    assert drawn["calendar-closed"] != drawn["calendar-exception"]
    assert "holiday" not in labels["calendar-closed"][0].lower()
    unkeyed = [item["diagnostic"] for item in result["warnings"] if item["code"] == CODE]
    # sunday draws its progress fill in its actual ink, so the legend keeps no separate Progress key (#1848 report).
    assert unkeyed == ([] if design != "sunday" else [CODE + ':{"drawnAs":"progress-fill","role":"progressFill"}'])
