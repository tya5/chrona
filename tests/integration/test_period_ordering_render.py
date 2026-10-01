"""A period whose references resolve to an empty range rejects the render, and a good one changes no byte (#582, S2).

Synthetic Project through the draft render path; no committed example is read.
"""
from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from chrona.usecases.render_review import RenderRejected

PROJECT = {
    "version": "timeline/v0.7", "project": {"id": "period-render", "title": "Period render"},
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


def test_an_empty_referenced_period_rejects_the_render_with_its_pointer(tmp_path):
    broken = copy.deepcopy(PROJECT)
    broken["periods"] = {"window": {"start": {"object": "launch", "endpoint": "at"}, "end": "2026-10-10"}}
    with pytest.raises(RenderRejected) as raised:
        _render(tmp_path, "broken", broken)
    assert [(item.id, item.path) for item in raised.value.diagnostics] == [("E_PROJECT_PERIOD_ORDER", "/periods/window")]


def test_an_in_order_referenced_period_changes_no_byte_of_the_picture(tmp_path):
    kept = copy.deepcopy(PROJECT)
    kept["periods"] = {"window": {"start": {"object": "qa", "endpoint": "end"}, "end": "2026-10-20"}}
    assert _render(tmp_path, "kept", kept).artifact.content == _render(tmp_path, "bare", PROJECT).artifact.content
