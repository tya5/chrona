"""A finish delta sits at the finish side of its bar when a dependency leaves that edge (#1702)."""
from __future__ import annotations

import yaml

from chrona.usecases.draft_render import DraftRenderRequest, render_draft

PROJECT = {
    "version": "timeline/v0.7",
    "project": {"id": "slip", "title": "Finish slip", "calendar": "standard"},
    "calendars": {"standard": {"working_days": ["mon", "tue", "wed", "thu", "fri"]}},
    "objects": {
        "design": {"type": "task", "title": "Design", "schedule": {
            "mode": "scheduled", "amount": "8wd", "anchor": {"start": "2027-01-11"}}},
        "build": {"type": "task", "title": "Build", "schedule": {"mode": "scheduled", "amount": "8wd"}},
        "ship": {"type": "task", "title": "Ship", "schedule": {"mode": "scheduled", "amount": "5wd"}},
    },
    "relations": [
        {"id": "design-build", "type": "dependency", "from": {"object": "design", "endpoint": "end"},
         "to": {"object": "build", "endpoint": "start"}, "lag": "0d"},
        {"id": "build-ship", "type": "dependency", "from": {"object": "build", "endpoint": "end"},
         "to": {"object": "ship", "endpoint": "start"}, "lag": "0d"},
    ],
}
ACTUAL = {
    "version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "slip-observed",
    "body": {"asOf": "2027-02-01", "observations": [
        {"id": "design-1", "sequence": 1, "projectObjectId": "design",
         "actual": {"start": "2027-01-11", "finish": "2027-01-25", "progress": 1}},
        {"id": "build-1", "sequence": 1, "projectObjectId": "build",
         "actual": {"start": "2027-01-26", "finish": "2027-02-09", "progress": 1}},
    ]},
}


def render_slip(directory):
    project = directory / "plan.yaml"
    actual = directory / "actual.yaml"
    project.write_text(yaml.safe_dump(PROJECT, sort_keys=False), encoding="utf-8")
    actual.write_text(yaml.safe_dump(ACTUAL, sort_keys=False), encoding="utf-8")
    return render_draft(DraftRenderRequest(project=project, target_kind="svg", actual=actual,
                                           viewport="700xauto")).rendered


def test_default_preset_finish_delta_follows_the_bar_finish_edge(tmp_path):
    rendered = render_slip(tmp_path)
    primitives = rendered.surface.primitives
    deltas = [item for item in primitives if item.kind == "Text" and item.scene_id.startswith("variance:")]
    assert {item.text for item in deltas} >= {"+2d"}
    for delta in deltas:
        host = next(item for item in primitives
                    if item.scene_id.startswith("actual:")
                    and item.scene_id.endswith(delta.source_ref) and item.kind != "Text")
        finish_edge = host.bounds[0] + host.bounds[2]
        assert delta.bounds[0] >= finish_edge - 1.0, (delta.scene_id, delta.bounds, host.bounds)
