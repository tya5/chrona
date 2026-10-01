"""A derived gate and the fixed-point gate at its derived date render byte-identical SVG and equal Scene (#788 slice 1, D6).

The presentation layers read placements, never the schedule mode, so the derived point needs no View, Layout or Scene
change. This is the twin property of design 5.1 (I1) carried through the draft render path, with an Actual on the gate.
"""
from __future__ import annotations

import copy
import dataclasses
from pathlib import Path

import yaml

from chrona.scheduling.scheduler import schedule
from chrona.usecases.draft_render import DraftRenderRequest, render_draft

PROJECT = {
    "version": "timeline/v0.7", "project": {"id": "twin", "title": "Derived gate twin", "calendar": "std"},
    "calendars": {"std": {"working_days": ["mon", "tue", "wed", "thu", "fri"],
                          "exceptions": [{"date": "2027-05-03", "working": False}]}},
    "objects": {
        "build": {"type": "task", "title": "Build", "schedule": {"mode": "fixed-span", "start": "2027-04-26", "end": "2027-05-07"}},
        "qa": {"type": "task", "title": "QA", "schedule": {"mode": "scheduled", "amount": "5wd"}},
        "launch": {"type": "gate", "title": "Launch", "schedule": {"mode": "scheduled-point"}},
    },
    "relations": [
        {"id": "b-q", "type": "dependency", "from": {"object": "build", "endpoint": "end"}, "to": {"object": "qa", "endpoint": "start"}},
        {"id": "q-l", "type": "dependency", "from": {"object": "qa", "endpoint": "end"}, "to": {"object": "launch", "endpoint": "at"}, "lag": "2wd"},
    ],
}
ACTUAL = {
    "version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "twin-observed",
    "body": {"asOf": "2027-05-24", "observations": [
        {"id": "launch-held", "sequence": 1, "projectObjectId": "launch", "actual": {"at": "2027-05-21"}}]},
}


def _write(path: Path, data: dict) -> Path:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def test_a_derived_gate_and_its_fixed_twin_render_byte_identical_svg_and_equal_scene(tmp_path):
    derived = copy.deepcopy(PROJECT)
    placed = schedule(derived)
    assert placed.ok and placed.placements["launch"]["at"].isoformat() == "2027-05-18"
    fixed = copy.deepcopy(PROJECT)
    fixed["objects"]["launch"]["schedule"] = {"mode": "fixed-point", "at": "2027-05-18"}
    actual = _write(tmp_path / "actual.yaml", ACTUAL)
    rendered = {}
    for with_actual in (False, True):
        results = [
            render_draft(DraftRenderRequest(project=_write(tmp_path / f"{name}.yaml", project), target_kind="svg",
                                            actual=actual if with_actual else None))
            for name, project in (("derived", derived), ("fixed", fixed))
        ]
        assert results[0].artifact.content == results[1].artifact.content
        # Provenance records the content identity of the Project source, which differs by construction.
        first, second = (dataclasses.replace(item.rendered.scene, provenance=None) for item in results)
        assert first == second
        assert b"Launch" in results[0].artifact.content
        rendered[with_actual] = results[0].artifact.content
    assert rendered[True] != rendered[False]  # the Actual on the derived gate is drawn
