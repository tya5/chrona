"""Opt-in forecast deadlines share one Core verdict through native SVG output."""
from dataclasses import replace
from datetime import date
from xml.etree import ElementTree

import pytest
import yaml

from chrona.presentation.scene.serialization import scene_document, validate_scene_document
from chrona.usecases.draft_render import DraftRenderRequest, render_draft, warning_payloads
from tests.support import synthetic_review as sr


def _request(tmp_path, *, deadline="2026-01-12", folded=False, hidden=False):
    source = sr.with_calendar(sr.project({
        "a": sr.span("a", date(2026, 1, 5), 7, title="Work"),
        "gate": {"type": "gate", "title": "Gate", "fields": {"owner": "a"},
                 "schedule": {"mode": "scheduled-point"}},
    }, [{"id": "work-gate", "type": "dependency", "lag": "0wd",
         "from": {"object": "a", "endpoint": "end"},
         "to": {"object": "gate", "endpoint": "at"}}]))
    for item in source["objects"].values():
        item["deadline"] = deadline
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
              "body": {"asOf": "2026-01-12", "observations": [
                  {"id": "work-start", "projectObjectId": "a", "sequence": 1,
                   "actual": {"start": "2026-01-08"}}]}}
    parts = sr.bundle("technical-print")
    body = parts["view"]["body"]
    body["window"] = {"mode": "explicit", "start": "2026-01-01", "end": "2026-02-01"}
    body["rows"] = {"mode": "automatic", "points": "group-header" if folded else "own-row"}
    if folded:
        body["grouping"] = {"by": {"fieldRole": "responsible"}, "fallback": "hierarchy",
                            "missing": "Other", "presentation": "header"}
    body["visibility"]["labels"] = {
        "placement": "plot", "content": ["title", "finishDelta"], "side": "end", "overflow": "suppress"}
    body["deadlines"] = {"show": "all", "caption": {"template": "{daysLate} days late"}}
    if hidden:
        body["deadlines"]["overrides"] = {"a": {"show": "hidden"}, "gate": {"show": "hidden"}}
    return DraftRenderRequest(
        project=sr._write(tmp_path / "project.yaml", source), target_kind="svg", preset="technical-print",
        actual=sr._write(tmp_path / "actual.yaml", actual),
        view=sr._write(tmp_path / "view.yaml", parts["view"]))


def _marks(result, prefix):
    return {item.source_ref: item for item in result.rendered.surface.primitives
            if item.scene_id.startswith(prefix) and item.visual_role == "deadline-mark"}


def _warnings(result):
    return [item for item in warning_payloads(result.rendered) if item["code"] == "W_DEADLINE"]


@pytest.mark.parametrize("folded", [False, True])
def test_late_span_and_point_runs_end_at_forecast_and_warnings_name_the_same_finish(tmp_path, folded):
    result = render_draft(replace(_request(tmp_path, folded=folded), forecast=True))
    runs, ticks = _marks(result, "deadline-run:"), _marks(result, "deadline-tick:")
    assert set(runs) == set(ticks) == {"a", "gate"}
    assert {item["object"] for item in _warnings(result)} == {"a", "gate"}
    warnings = {item["object"]: item for item in _warnings(result)}
    assert {key: (item["finish"], item["daysLate"]) for key, item in warnings.items()} == {
        "a": ("2026-01-14", 2), "gate": ("2026-01-15", 3)}
    assert all(item["finishBasis"] == "forecast" and "forecast" in item["message"]
               for item in warnings.values())
    scale = result.rendered.surface.scale_manifest
    elements = {item.get("data-scene-id"): item for item in ElementTree.fromstring(result.artifact.content).iter()}
    for object_id, run in runs.items():
        assert run.bounds[0] == pytest.approx(ticks[object_id].bounds[0])
        # A span ends at its exclusive forecast boundary; a point's late stub
        # ends at the boundary after its occupied date.
        finish = date(2026, 1, 15 if object_id == "a" else 16)
        finish_x = scale.origin + (finish - scale.domain_start).days * scale.unit_ratio
        assert run.bounds[0] + run.bounds[2] == pytest.approx(finish_x)
        assert run.paint == ticks[object_id].paint  # ordinary deadline-mark, no estimated-only role
        assert elements[run.scene_id].tag.endswith("path")
        assert "d" in elements[run.scene_id].attrib
    captions = [item for item in result.rendered.surface.primitives if item.purpose == "deadline-caption"]
    # Optional captions keep their existing collision/omission policy.
    if not folded:
        assert captions
    assert {item.source_ref for item in captions} <= {"a", "gate"}
    caption_counts = {"a": "2 days late", "gate": "3 days late"}
    assert all(item.text == caption_counts[item.source_ref] for item in captions)
    validate_scene_document(scene_document(result.rendered.scene))


@pytest.mark.parametrize("deadline", ["2026-01-15", "2026-01-16"])
def test_equal_or_earlier_forecast_finish_keeps_only_deadline_ticks(tmp_path, deadline):
    result = render_draft(replace(_request(tmp_path, deadline=deadline), forecast=True))
    assert set(_marks(result, "deadline-tick:")) == {"a", "gate"}
    assert not _marks(result, "deadline-run:")
    assert not _warnings(result)


def test_hidden_deadlines_do_not_hide_forecast_warnings(tmp_path):
    result = render_draft(replace(_request(tmp_path, hidden=True), forecast=True))
    assert not _marks(result, "deadline-tick:") and not _marks(result, "deadline-run:")
    assert len(_warnings(result)) == 2
    assert all(item["finishBasis"] == "forecast" for item in _warnings(result))


def test_explicit_window_omission_does_not_revert_the_forecast_warning_basis(tmp_path):
    request = _request(tmp_path)
    view = yaml.safe_load(request.view.read_text(encoding="utf-8"))
    view["body"]["window"]["end"] = "2026-01-10"
    # Keep the required forecast delta available in the table when its mark
    # endpoint is outside the plot; an out-of-window plot-only delta is refused.
    view["body"]["visibility"]["labels"]["placement"] = "table"
    view["body"]["visibility"]["labels"]["content"] = ["title"]
    view["body"]["tableColumns"] = [
        {"id": "Task", "source": "title", "missing": "em-dash", "align": "start",
         "width": "content", "headerOrientation": "horizontal"},
        {"id": "Delta", "source": {"comparisonFacet": "finishDelta"}, "format": "signedDays",
         "missing": "blank", "align": "end", "width": "content", "headerOrientation": "horizontal"},
    ]
    sr._write(request.view, view)
    result = render_draft(replace(request, forecast=True))
    assert not _marks(result, "deadline-tick:") and not _marks(result, "deadline-run:")
    assert {item["object"] for item in _warnings(result)} == {"a", "gate"}
    assert {item["object"]: item["finish"] for item in _warnings(result)} == {
        "a": "2026-01-14", "gate": "2026-01-15"}
    assert all(item["finishBasis"] == "forecast" for item in _warnings(result))


def test_no_forecast_retains_planned_geometry_and_inclusive_warning_payload(tmp_path):
    request = _request(tmp_path, deadline="2026-01-10")
    omitted, disabled = render_draft(request), render_draft(replace(request, forecast=False))
    assert omitted.artifact.content == disabled.artifact.content
    assert omitted.rendered.scene == disabled.rendered.scene
    warnings = _warnings(omitted)
    assert len(warnings) == 2
    assert {item["object"]: (item["finish"], item["daysLate"]) for item in warnings} == {
        "a": ("2026-01-11", 1), "gate": ("2026-01-12", 2)}
    assert all("finishBasis" not in item and "finishBasis" not in item.get("details", {})
               and "forecast" not in item["message"] for item in warnings)
    assert not any(item.purpose == "forecast" for item in omitted.rendered.surface.primitives)
