from __future__ import annotations

import yaml

from chrona.resources import default_preset_root
from chrona.usecases.draft_render import DraftRenderRequest, render_draft


PROJECT = """\
version: timeline/v0.7
project: {id: draft-snapshot-test, title: Snapshot transport}
objects:
  task: {type: task, title: Plan, schedule: {mode: fixed-span, start: '2026-10-01', end: '2026-10-10'}}
  gate: {type: gate, title: Gate, schedule: {mode: fixed-point, at: '2026-10-20'}}
relations: []
"""


def _view(tmp_path, *, baseline: str, baseline_marks: str | None = None):
    value = yaml.safe_load(default_preset_root().joinpath(
        "bundles/editorial-readable-default/view.yaml").read_bytes())
    comparison = value["body"]["comparison"]
    comparison["baseline"] = baseline
    if baseline_marks is None:
        comparison.pop("baselineMarks", None)
    else:
        comparison["baselineMarks"] = baseline_marks
    path = tmp_path / f"view-{baseline}-{baseline_marks or 'none'}.yaml"
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    return path


def _generic_view(tmp_path, *, baseline: str):
    value = yaml.safe_load(default_preset_root().joinpath(
        "bundles/design-default/view.yaml").read_bytes())
    value["body"]["comparison"]["baseline"] = baseline
    path = tmp_path / f"generic-view-{baseline}.yaml"
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    return path


def _write_project(path, *, title: str, start: str, end: str):
    value = yaml.safe_load(PROJECT)
    value["project"]["title"] = title
    value["objects"]["task"]["schedule"]["start"] = start
    value["objects"]["task"]["schedule"]["end"] = end
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _write_actual(path):
    value = {
        "version": "chrona/actual-set/v0.3",
        "kind": "actual-set",
        "id": "draft-snapshot-actual",
        "body": {
            "asOf": "2026-11-15",
            "observations": [{
                "id": "task-finished-late", "sequence": 1, "projectObjectId": "task",
                "actual": {"start": "2026-10-01", "finish": "2026-11-10", "progress": 1},
            }],
        },
    }
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _mark_signature(rendered):
    return tuple(sorted(
        (item.scene_id, item.purpose, item.visual_role, item.bounds)
        for item in rendered.surface.primitives
        if item.purpose in {"planned", "snapshot"}
    ))


def test_draft_snapshot_is_inert_until_the_explicit_view_selects_snapshot(tmp_path):
    project = tmp_path / "project.yaml"
    snapshot = tmp_path / "snapshot-project.yaml"
    _write_project(project, title="Current", start="2026-10-01", end="2026-10-10")
    _write_project(snapshot, title="Baseline", start="2026-10-02", end="2026-10-08")
    view = _view(tmp_path, baseline="primary")
    source_bytes = {path: path.read_bytes() for path in (project, snapshot, view)}

    without_snapshot = render_draft(DraftRenderRequest(
        project=project, target_kind="svg", view=view,
    )).rendered
    with_snapshot = render_draft(DraftRenderRequest(
        project=project, target_kind="svg", view=view, snapshot=snapshot,
    )).rendered

    # Supplying a baseline does not override the explicit primary-baseline View.
    assert _mark_signature(with_snapshot) == _mark_signature(without_snapshot)
    assert not any(item.purpose == "snapshot" for item in with_snapshot.surface.primitives)
    assert "snapshot-project" in with_snapshot.read_inputs
    assert "snapshot-ref" not in with_snapshot.read_inputs
    assert with_snapshot.read_inputs - without_snapshot.read_inputs == {"snapshot-project"}
    assert {path: path.read_bytes() for path in source_bytes} == source_bytes


def test_draft_snapshot_selected_by_view_renders_changed_baseline_ghost_and_closes_typed_input(tmp_path):
    project = tmp_path / "project.yaml"
    snapshot = tmp_path / "snapshot-project.yaml"
    _write_project(project, title="Current", start="2026-10-01", end="2026-10-10")
    _write_project(snapshot, title="Baseline", start="2026-10-02", end="2026-10-08")
    view = _view(tmp_path, baseline="snapshot", baseline_marks="ghost-when-changed")
    source_bytes = {path: path.read_bytes() for path in (project, snapshot, view)}

    result = render_draft(DraftRenderRequest(
        project=project, target_kind="svg", view=view, snapshot=snapshot,
    )).rendered

    ghosts = [item for item in result.surface.primitives if item.purpose == "snapshot"]
    assert ghosts
    assert all(item.visual_role == "snapshot" for item in ghosts)
    assert "snapshot-project" in result.read_inputs
    assert "snapshot-ref" not in result.read_inputs
    assert result.artifact.content.startswith(b"<?xml") or b"<svg" in result.artifact.content[:256]
    assert {path: path.read_bytes() for path in source_bytes} == source_bytes


def test_generic_view_snapshot_default_without_a_snapshot_keeps_primary_review_unchanged(tmp_path):
    project = tmp_path / "project.yaml"
    actual = tmp_path / "actual.yaml"
    _write_project(project, title="Current", start="2026-10-01", end="2026-10-10")
    _write_actual(actual)
    primary_view = _generic_view(tmp_path, baseline="primary")
    snapshot_default_view = _generic_view(tmp_path, baseline="snapshot")
    source_bytes = {path: path.read_bytes() for path in (project, actual, primary_view, snapshot_default_view)}

    primary = render_draft(DraftRenderRequest(
        project=project, target_kind="svg", preset="target-b", view=primary_view, actual=actual,
    )).rendered
    snapshot_default = render_draft(DraftRenderRequest(
        project=project, target_kind="svg", preset="target-b", view=snapshot_default_view, actual=actual,
    )).rendered

    assert snapshot_default.artifact.content == primary.artifact.content
    assert snapshot_default.warning_records == primary.warning_records
    assert not any(item.purpose == "snapshot" for item in snapshot_default.surface.primitives)
    roles = {item.visual_role for item in snapshot_default.surface.primitives}
    assert "actual" in roles and "variance-behind" in roles
    assert any(item.kind == "Text" and item.purpose == "table-cell"
               and item.visual_role == "variance-behind"
               for item in snapshot_default.surface.primitives), [
                   (item.kind, item.purpose, item.text, item.visual_role, item.scene_id)
                   for item in snapshot_default.surface.primitives if item.kind == "Text"
               ]
    legend = tuple((item.scene_id, item.purpose, item.text, item.visual_role)
                   for item in snapshot_default.surface.primitives
                   if item.purpose in {"legend-label", "legend-swatch"})
    assert legend == tuple((item.scene_id, item.purpose, item.text, item.visual_role)
                           for item in primary.surface.primitives
                           if item.purpose in {"legend-label", "legend-swatch"})
    assert {path: path.read_bytes() for path in source_bytes} == source_bytes
