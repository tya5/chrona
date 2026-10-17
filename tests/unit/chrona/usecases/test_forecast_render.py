"""Common opt-in ingress reaches completed Layout/Scene, not an adapter shift."""
from dataclasses import replace

import yaml
import pytest

from chrona.usecases.draft_render import DraftRenderRequest, render_draft, warning_payloads
from chrona.usecases.render_review import RenderFailed, RenderRejected
from chrona.presentation.model.semantic_registry import semantic_binding


def _request(tmp_path):
    project = {"version": "timeline/v0.7", "project": {"id": "forecast-render", "calendar": "weekdays"},
               "calendars": {"weekdays": {"working_days": ["mon", "tue", "wed", "thu", "fri"]}},
               "objects": {
                   "a": {"type": "task", "title": "Design", "schedule": {"mode": "fixed-span", "start": "2026-01-05", "end": "2026-01-07"}},
                   "b": {"type": "task", "title": "Build", "schedule": {"mode": "scheduled", "amount": "2wd"}}},
               "relations": [{"id": "a-b", "type": "dependency", "from": {"object": "a", "endpoint": "end"},
                              "to": {"object": "b", "endpoint": "start"}}]}
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
              "body": {"asOf": "2026-01-09", "observations": [
                  {"id": "a-1", "projectObjectId": "a", "sequence": 1, "actual": {"start": "2026-01-08"}}]}}
    path, actual_path = tmp_path / "project.yaml", tmp_path / "actual.yaml"
    path.write_text(yaml.safe_dump(project, sort_keys=False), encoding="utf-8")
    actual_path.write_text(yaml.safe_dump(actual), encoding="utf-8")
    return DraftRenderRequest(path, "svg", preset="technical-print", actual=actual_path)


def test_forecast_draft_completes_truthful_marks_required_deltas_and_info(tmp_path):
    result = render_draft(replace(_request(tmp_path), forecast=True))
    surface = result.rendered.surface
    marks = [primitive for primitive in surface.primitives if primitive.purpose == "forecast"]
    assert {mark.source_ref for mark in marks} == {"a", "b"}
    assert all(mark.visual_role == "planned" for mark in marks)
    deltas = [primitive for primitive in surface.primitives if primitive.purpose == "forecast-finish-delta"]
    assert len(deltas) == 2
    assert all(primitive.text.endswith("*") for primitive in deltas)
    payloads = warning_payloads(result.rendered)
    moved = [item for item in payloads if item["code"] == "I_FORECAST_MOVED"]
    assert len(moved) == 1 and moved[0]["details"]["count"] == 2
    assert "Forecast (* estimated)" in result.artifact.content.decode()


def test_forecast_delta_purpose_is_distinct_but_reuses_ordinary_paint_roles():
    for ordinary_id, forecast_id, role in (
        ("finishDelta", "forecastFinishDelta", "variance-on-track"),
        ("varianceAhead", "forecastVarianceAhead", "variance-ahead"),
        ("varianceBehind", "forecastVarianceBehind", "variance-behind"),
    ):
        ordinary = semantic_binding(ordinary_id)
        forecast = semantic_binding(forecast_id)
        assert ordinary.purpose == "finish-delta"
        assert forecast.purpose == "forecast-finish-delta"
        assert forecast.purpose != ordinary.purpose
        assert (forecast.scene_role, forecast.theme_role) == (role, role)
        assert (forecast.scene_role, forecast.theme_role) == (ordinary.scene_role, ordinary.theme_role)


def test_omitted_and_false_forecast_keep_artifact_bytes(tmp_path):
    request = _request(tmp_path)
    omitted = render_draft(request)
    explicit_false = render_draft(replace(request, forecast=False))
    assert omitted.artifact.content == explicit_false.artifact.content
    assert not any(primitive.purpose == "forecast" for primitive in omitted.rendered.surface.primitives)


def test_forecast_requires_actual_and_a_capable_view_without_changing_default_preset(tmp_path):
    request = _request(tmp_path)
    with pytest.raises(RenderRejected) as missing:
        render_draft(replace(request, actual=None, forecast=True))
    assert missing.value.diagnostics[0].id == "E_FORECAST_ACTUAL_REQUIRED"
    with pytest.raises(RenderFailed) as incapable:
        render_draft(replace(request, preset=None, forecast=True))
    assert incapable.value.code == "E_FORECAST_PRESENTATION_REQUIRED"


def test_forecast_retains_snapshot_ghost_even_for_primary_comparison_view(tmp_path):
    request = _request(tmp_path)
    result = render_draft(replace(request, forecast=True, snapshot=request.project))
    ghosts = {primitive.source_ref for primitive in result.rendered.surface.primitives if primitive.purpose == "snapshot"}
    assert ghosts == {"a", "b"}
    labels = [primitive for primitive in result.rendered.surface.primitives if primitive.purpose == "member-label"]
    assert {primitive.source_ref for primitive in labels} == {"a", "b"}
    assert len(labels) == 2
    assert all(primitive.source_kind != "snapshot" for primitive in labels)
    deltas = [primitive for primitive in result.rendered.surface.primitives
              if primitive.purpose == "forecast-finish-delta"]
    assert {primitive.source_ref for primitive in deltas} == {"a", "b"}
    assert not any(note["code"] == "W_DRAFT_SNAPSHOT_NOT_DRAWN" for note in result.notes)


def test_observed_overlap_warning_survives_forecast_render_and_scene(tmp_path):
    request = _request(tmp_path)
    actual = yaml.safe_load(request.actual.read_text(encoding="utf-8"))
    actual["body"]["observations"] = [
        {"id": "a-1", "projectObjectId": "a", "sequence": 1,
         "actual": {"start": "2026-01-05", "finish": "2026-01-09"}},
        {"id": "b-1", "projectObjectId": "b", "sequence": 1,
         "actual": {"start": "2026-01-08"}},
    ]
    request.actual.write_text(yaml.safe_dump(actual, sort_keys=False), encoding="utf-8")

    result = render_draft(replace(request, forecast=True, snapshot=request.project))
    payloads = warning_payloads(result.rendered)
    warnings = [item for item in payloads if item["code"] == "W_FORECAST_OBSERVED_START_BEFORE_BOUND"]
    assert len(warnings) == 1
    warning = warnings[0]
    assert warning["severity"] == "warning"
    assert warning["details"]["object"] == "b"
    assert warning["details"]["placed"] == "2026-01-08"
    assert warning["details"]["from"]["value"] == "2026-01-09"
    assert warning["details"]["overlapDays"] == 1
    assert not any(item["code"] == "E_FIXED_TARGET_VIOLATION" for item in payloads)
    assert warning["diagnostic"] in result.rendered.scene.diagnostics
