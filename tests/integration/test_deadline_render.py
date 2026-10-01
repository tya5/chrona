"""A missed deadline is a render warning and changes no byte of the picture (#792, #788 slice 3, D6).

`deadline` has no View mark yet (successor #822), so the SVG of a plan with a violated deadline is the SVG of the
same plan without it. The warning travels the one render ledger: stderr JSON, the Scene diagnostics list and the
MCP `warnings` field read the same record.
"""
from __future__ import annotations

import copy
from pathlib import Path

import yaml

from chrona.usecases.draft_render import DraftRenderRequest, render_draft, warning_payloads

PROJECT = {
    "version": "timeline/v0.7", "project": {"id": "dl-render", "title": "Deadline render"},
    "objects": {
        "qa": {"type": "task", "title": "QA", "schedule": {"mode": "fixed-span", "start": "2026-10-01", "end": "2026-10-08"}},
        "launch": {"type": "gate", "title": "Launch", "schedule": {"mode": "scheduled-point"}},
    },
    "relations": [
        {"id": "qa-launch", "type": "dependency", "from": {"object": "qa", "endpoint": "end"},
         "to": {"object": "launch", "endpoint": "at"}, "lag": "2d"},
    ],
}


def _render(tmp_path: Path, name: str, project: dict):
    path = tmp_path / f"{name}.yaml"
    path.write_text(yaml.safe_dump(project, sort_keys=False), encoding="utf-8")
    return render_draft(DraftRenderRequest(project=path, target_kind="svg"))


def test_a_missed_deadline_warns_on_the_ledger_and_leaves_the_svg_unchanged(tmp_path):
    late = copy.deepcopy(PROJECT)
    late["objects"]["qa"]["deadline"] = "2026-10-05"
    late["objects"]["launch"]["deadline"] = "2026-10-08"
    bare, flagged = _render(tmp_path, "bare", PROJECT), _render(tmp_path, "late", late)
    assert bare.artifact.content == flagged.artifact.content
    assert [item for item in warning_payloads(bare.rendered) if item["code"] == "W_DEADLINE"] == []
    warnings = [item for item in warning_payloads(flagged.rendered) if item["code"] == "W_DEADLINE"]
    assert [item["sourceRef"] for item in warnings] == ["/objects/qa/deadline", "/objects/launch/deadline"]
    assert {key: warnings[0][key] for key in ("severity", "object", "endpoint", "finish", "deadline", "daysLate")} == {
        "severity": "warning", "object": "qa", "endpoint": "end", "finish": "2026-10-08",
        "deadline": "2026-10-05", "daysLate": 3}
    assert warnings[1]["message"] == "launch finishes 2026-10-10, 2 days after its deadline 2026-10-08"
    assert all(item["diagnostic"].startswith("W_DEADLINE:") for item in warnings)
    assert [item for item in flagged.rendered.scene.diagnostics if item.startswith("W_DEADLINE:")] == [
        item["diagnostic"] for item in warnings]


def test_a_kept_deadline_adds_no_warning(tmp_path):
    kept = copy.deepcopy(PROJECT)
    kept["objects"]["qa"]["deadline"] = "2026-10-08"
    kept["objects"]["launch"]["deadline"] = "2026-10-10"
    rendered = _render(tmp_path, "kept", kept)
    assert not [item for item in warning_payloads(rendered.rendered) if item["code"] == "W_DEADLINE"]
