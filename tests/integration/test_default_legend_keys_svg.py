"""Native SVG evidence for default Snapshot/deadline keys (#1703)."""
from datetime import date
from xml.etree import ElementTree

import pytest

from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.model.surface_content import SurfaceLegendEntry
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderRequest, render_review
from tests.support import synthetic_review as sr


def _render(tmp_path, *, unkeyed=(), legend_slot=True, baseline_start=date(2026, 2, 2)):
    parts = sr.bundle("executive-light")
    body = parts["view"]["body"]
    body["window"] = {"mode": "explicit", "start": "2026-02-01", "end": "2026-02-21"}
    body["rows"] = {"mode": "automatic"}
    body["comparison"].update(baseline="snapshot", baselineMarks="ghost")
    body["deadlines"] = {"show": "all"}
    source = sr.project({"a": sr.span("a", date(2026, 2, 8), 5)})
    source["objects"]["a"]["deadline"] = "2026-02-10"
    baseline = sr.project({"a": sr.span("a", baseline_start, 4)})
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
              "body": {"asOf": "2026-02-20", "observations": [
                  {"id": "a", "sequence": 1, "projectObjectId": "a",
                   "actual": {"start": "2026-02-08", "finish": "2026-02-12"}}]}}
    detail = {"version": "chrona/review-detail-profile/v0.1", "id": "key-policy",
              "body": {"legend": [{"role": "planned", "label": "Planned"}]}}
    if unkeyed:
        detail["body"]["unkeyedLegendRoles"] = list(unkeyed)
    if not legend_slot:
        footer = next(node for node in parts["layout"]["root"]["children"] if node["id"] == "footer")
        footer["children"] = [node for node in footer["children"] if node.get("source") != "legend"]
    paths = {kind: sr._write(tmp_path / f"{kind}.yaml", value) for kind, value in parts.items()}
    draft = resolve_draft_render(
        project_path=sr._write(tmp_path / "project.yaml", source),
        snapshot_project_path=sr._write(tmp_path / "baseline.yaml", baseline),
        actual_path=sr._write(tmp_path / "actual.yaml", actual),
        detail_path=sr._write(tmp_path / "detail.yaml", detail),
        view_path=paths["view"], theme_path=paths["theme"], scheme_path=paths["scheme"],
        layout_path=paths["layout"], viewport=(1800, 1000))
    return render_review(RenderRequest(
        closure=draft.closure, snapshot_root=draft.asset_root, asset_root=draft.asset_root,
        scheduler=ReferenceScheduler(), renderer=V05SvgRenderer(), draft_auto_block=draft.auto_block))


@pytest.mark.parametrize("unkeyed", [(), ("snapshot", "deadlineMark")])
def test_drawn_snapshot_and_deadline_have_default_svg_keys_unless_detail_opts_out(tmp_path, unkeyed):
    rendered = _render(tmp_path, unkeyed=unkeyed)
    primitives = rendered.surface.primitives
    assert any(item.purpose == "snapshot" for item in primitives)
    assert any(item.purpose == "deadline-mark" for item in primitives)
    roles = {item.visual_role for item in primitives if item.purpose == "legend-swatch"}
    root = ElementTree.fromstring(rendered.artifact.content)
    texts = {"".join(item.itertext()) for item in root.iter() if item.tag.endswith("}text")}
    deadline_key_id = SurfaceLegendEntry("deadlineMark", "Deadline").swatch_placement_id
    deadline_keys = tuple(item for item in primitives if item.scene_id == deadline_key_id)
    if unkeyed:
        assert not roles & {"snapshot", "deadline-mark"}
        assert not deadline_keys
        assert not texts & {"Baseline", "Deadline"}
    else:
        assert "snapshot" in roles
        assert len(deadline_keys) == 1
        assert deadline_keys[0].paint.stroke is not None
        svg_key = next(item for item in root.iter()
                       if item.get("data-scene-id") == deadline_key_id)
        assert svg_key.get("stroke") not in {None, "none"}
        assert {"Baseline", "Deadline"} <= texts


def test_default_candidates_do_not_create_a_legend_slot(tmp_path):
    rendered = _render(tmp_path, legend_slot=False)
    assert any(item.purpose == "snapshot" for item in rendered.surface.primitives)
    assert any(item.purpose == "deadline-mark" for item in rendered.surface.primitives)
    assert not any(item.scene_id.startswith(("legend:", "legend-swatch:"))
                   for item in rendered.surface.primitives)


def test_snapshot_default_is_filtered_when_its_painted_occurrence_is_outside_the_window(tmp_path):
    rendered = _render(tmp_path, baseline_start=date(2026, 1, 2))
    root = ElementTree.fromstring(rendered.artifact.content)
    texts = {"".join(item.itertext()) for item in root.iter() if item.tag.endswith("}text")}
    assert "Baseline" not in texts
    assert "Deadline" in texts
