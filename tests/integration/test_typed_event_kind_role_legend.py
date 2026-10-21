"""Typed profile event kinds select point roles and matching final legend keys (#1847)."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from xml.etree import ElementTree

from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from tests.support import synthetic_review as sr


def _render(tmp_path: Path):
    project = sr.project({
        "milestone-event": {**sr.point("milestone-event", date(2026, 10, 6), title="Milestone event"),
                            "fields": {"eventKind": "milestone"}},
        "gate-event": {**sr.point("gate-event", date(2026, 10, 16), title="Gate event"),
                       "fields": {"eventKind": "gate"}},
    }, responsible_field_role=False)
    assert {item["type"] for item in project["objects"].values()} == {"gate"}
    project["extensions"] = [{"packageId": "row4-event-kind", "path": "profile.yaml",
                              "revision": "git:0123456789abcdef0123456789abcdef01234567"}]
    profile = {
        "version": "chrona/profile/v0.3", "packageId": "row4-event-kind",
        "requires": {"projectFormat": "timeline/v0.7"},
        "profiles": {"milestone": {"extends": "milestone"}, "gate": {"extends": "milestone"}},
        "fields": {"eventKind": {"type": "enum", "cardinality": "one", "required": True,
                                  "enumValues": ["milestone", "gate"]}},
    }
    parts = sr.bundle()
    parts["view"]["body"].update({
        "window": {"mode": "explicit", "start": "2026-10-01", "end": "2026-10-22"},
        "rows": {"mode": "automatic"},
        "selection": {"include": {"types": ["point"]}},
        "grouping": {"by": "none"},
    })
    parts["view"]["body"]["visibility"]["labels"] = {
        "placement": "plot", "content": ["title"], "side": "auto", "overflow": "suppress"}
    parts["theme"]["body"]["values"].update({
        "row4-milestone-symbol": {"type": "symbol", "value": {"shape": "diamond"}},
        "row4-gate-symbol": {"type": "symbol", "value": {"shape": "square"}},
    })
    roles = parts["theme"]["body"]["roles"]
    roles["point-milestone"] = {**roles["planned"], "symbol": "row4-milestone-symbol"}
    roles["point-gate"] = {**roles["planned"], "symbol": "row4-gate-symbol"}
    bindings = parts["theme"]["body"]["colorBindings"]
    bindings.update({
        "point-milestone.fill": "accent", "point-milestone.stroke": "text",
        "point-gate.fill": "positive", "point-gate.stroke": "text",
    })
    style = {"version": "chrona/style/v0.2", "kind": "style", "id": "row4-event-kind-style",
             "body": {"rules": [
                 {"id": "milestone-symbol", "when": {"semantic": "planned", "fields": [
                     {"source": {"field": "eventKind"}, "equals": "milestone"}]},
                  "then": {"role": "point-milestone"}},
                 {"id": "gate-symbol", "when": {"semantic": "planned", "fields": [
                     {"source": {"field": "eventKind"}, "equals": "gate"}]},
                  "then": {"role": "point-gate"}},
             ]}}
    detail = {"version": "chrona/review-detail-profile/v0.1", "id": "row4-event-kind-detail",
              "body": {"legend": [
                  {"role": "point-milestone", "label": "Milestone"},
                  {"role": "point-gate", "label": "Gate"},
              ]}}
    paths = {"project": sr._write(tmp_path / "project.yaml", project),
             "profile": sr._write(tmp_path / "profile.yaml", profile),
             "style": sr._write(tmp_path / "style.yaml", style),
             "detail": sr._write(tmp_path / "detail.yaml", detail)}
    resource_paths = {}
    for key in ("view", "theme", "scheme", "layout"):
        resource_paths[key] = sr._write(tmp_path / f"{key}.yaml", parts[key])
    return render_draft(DraftRenderRequest(
        project=paths["project"], target_kind="svg", view=resource_paths["view"],
        style=paths["style"], theme=resource_paths["theme"], scheme=resource_paths["scheme"],
        layout=resource_paths["layout"], detail=paths["detail"], viewport="1600x900",
    )).rendered


def _normalized_outline(item):
    x, y, width, height = item.bounds
    return tuple((command.kind, tuple((round((px - x) / width, 4), round((py - y) / height, 4))
                                     for px, py in command.points))
                 for command in item.symbol.outline)


def test_same_core_gate_event_kinds_drive_distinct_theme_marks_and_owned_keys(tmp_path):
    rendered = _render(tmp_path)
    marks = tuple(item for item in rendered.surface.primitives
                  if item.kind == "Symbol" and item.source_kind == "object" and item.purpose == "planned")
    swatches = tuple(item for item in rendered.surface.primitives if item.purpose == "legend-swatch")
    labels = tuple(item for item in rendered.surface.primitives if item.purpose == "legend-label")
    svg = {item.attrib.get("data-scene-id"): item
           for item in ElementTree.fromstring(rendered.artifact.content).iter()
           if item.attrib.get("data-scene-id")}

    assert {item.source_ref for item in marks} == {"milestone-event", "gate-event"}
    assert {item.theme_role for item in marks} == {"point-milestone", "point-gate"}
    assert {item.semantic_id for item in marks} == {"planned"}
    assert len({item.paint.fill for item in marks}) == 2
    assert {item.text for item in labels} == {"Milestone", "Gate"}
    assert {item.source_ref.split(":", 1)[0] for item in swatches} == {"point-milestone", "point-gate"}
    labels_by_key = {item.source_ref: item.text for item in labels}
    label_by_role = {"point-milestone": "Milestone", "point-gate": "Gate"}
    assert labels_by_key == {
        item.source_ref: label_by_role[item.source_ref.split(":", 1)[0]] for item in swatches}
    assert len(swatches) == len(labels) == 2
    for mark in marks:
        assert mark.scene_id in svg
        assert svg[mark.scene_id].tag.endswith("path")
        assert svg[mark.scene_id].attrib.get("fill") == mark.paint.fill
    for swatch in swatches:
        assert swatch.scene_id in svg
        assert svg[swatch.scene_id].tag.endswith("path")
        assert svg[swatch.scene_id].attrib.get("fill") == swatch.paint.fill
        role = swatch.source_ref.split(":", 1)[0]
        role_mark = next(mark for mark in marks if mark.theme_role == role)
        assert _normalized_outline(swatch) == _normalized_outline(role_mark)
        assert swatch.paint == role_mark.paint
    assert len({_normalized_outline(item) for item in marks}) == 2
