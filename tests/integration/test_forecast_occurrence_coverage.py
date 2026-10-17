"""Forecast delta channels cover each projected occurrence, including folded and shared rows."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import pytest
import yaml

from chrona.resources import builtin_preset_source_root, safe_load
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr


def _write(path, value):
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    return path


def _parts(*, placement: str, folded: bool = False, explicit: bool = False):
    root = builtin_preset_source_root("presets/bundles/technical-print")
    view = safe_load(root.joinpath("view.yaml").read_bytes())
    body = view["body"]
    body["comparison"]["baseline"] = "snapshot"
    body["comparison"]["baselineMarks"] = "ghost"
    if folded:
        body["grouping"] = {
            "by": {"fieldRole": "responsible"}, "fallback": "hierarchy",
            "missing": "Other", "presentation": "header",
        }
        body["rows"] = {"mode": "automatic", "points": "group-header"}
    if explicit:
        body.pop("grouping", None)
        body.pop("selection", None)
        body.pop("ordering", None)
        body["rows"] = {"mode": "explicit", "items": [{
            "id": "shared", "depth": 0, "label": "Shared work",
            "tableSubject": "primary-a",
            "items": [
                {"id": "snapshot-a", "track": "shared",
                 "source": {"kind": "snapshot", "object": "a"}},
                {"id": "primary-a", "track": "shared",
                 "source": {"kind": "primary", "object": "a"}},
                {"id": "snapshot-b", "track": "shared",
                 "source": {"kind": "snapshot", "object": "b"}},
                {"id": "primary-b", "track": "shared",
                 "source": {"kind": "primary", "object": "b"}},
            ],
        }]}
    else:
        body["rows"] = {"mode": "automatic", "points": "group-header" if folded else "own-row"}
    body["tableColumns"] = [
        {"id": "Task", "source": "title", "missing": "em-dash", "align": "start",
         "width": "content", "headerOrientation": "horizontal"},
        {"id": "Delta", "source": {"comparisonFacet": "finishDelta"}, "format": "signedDays",
         "missing": "blank", "align": "end", "width": "content", "headerOrientation": "horizontal"},
    ]
    body["visibility"]["labels"] = {
        # Folded headers require a plot title to exist; table-only still has no
        # plot delta channel, so its finish delta must be refused for coverage.
        "placement": "plot" if folded and placement == "table" else placement,
        "content": ["title", "finishDelta"] if placement in {"plot", "both"} else ["title"],
        "side": "end", "overflow": "suppress",
    }
    return view


def _project(*, folded: bool = False, folded_count: int = 1):
    objects = {
        "a": {"type": "task", "title": "Design", "fields": {"owner": "team"},
              "schedule": {"mode": "fixed-span", "start": "2026-01-05", "end": "2026-01-12"}},
    }
    relations = []
    if folded:
        for index in range(folded_count):
            gate_id = "gate" if index == 0 else f"gate-{index + 1}"
            objects[gate_id] = {"type": "gate", "title": f"Review gate {index + 1}",
                                "fields": {"owner": "team"},
                                "schedule": {"mode": "scheduled-point"}}
            relations.append({"id": f"a-{gate_id}", "type": "dependency", "lag": "0wd",
                              "from": {"object": "a", "endpoint": "end"},
                              "to": {"object": gate_id, "endpoint": "at"}})
    else:
        objects["b"] = {"type": "task", "title": "Build", "fields": {"owner": "team"},
                         "schedule": {"mode": "fixed-span", "start": "2026-03-02", "end": "2026-03-09"}}
    source = sr.project(objects, relations)
    source["project"].update(id="forecast-occurrences", calendar="weekdays")
    source["calendars"] = {"weekdays": {"working_days": ["mon", "tue", "wed", "thu", "fri"]}}
    if folded:
        source["entities"]["team"]["title"] = "Delivery team"
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
              "body": {"asOf": "2026-01-12", "observations": [
                  {"id": f"actual-{object_id}", "projectObjectId": object_id, "sequence": 1,
                   "actual": {"start": start}}
                  for object_id, start in (("a", "2026-01-08"), ("b", "2026-03-05"))
                  if object_id in objects
              ]}}
    return source, actual


def _request(tmp_path, *, placement: str, folded: bool = False, explicit: bool = False,
             folded_count: int = 1, theme_path=None, viewport: str = "1600xauto"):
    project, actual = _project(folded=folded, folded_count=folded_count)
    project_path = _write(tmp_path / "project.yaml", project)
    actual_path = _write(tmp_path / "actual.yaml", actual)
    snapshot_path = _write(tmp_path / "snapshot.yaml", deepcopy(project))
    view_path = _write(tmp_path / "view.yaml", _parts(
        placement=placement, folded=folded, explicit=explicit))
    return DraftRenderRequest(project_path, "svg", preset="technical-print", view=view_path,
                              theme=theme_path,
                              actual=actual_path, snapshot=snapshot_path, forecast=True,
                              viewport=viewport)


def _large_delta_chip_theme(path):
    root = builtin_preset_source_root("presets/bundles/technical-print")
    theme = safe_load(root.joinpath("theme.yaml").read_bytes())
    body = theme["body"]
    body["values"]["chip-padding"]["value"] = 2.0
    body["values"]["delta-chip-min"] = {"type": "number", "value": 56.0}
    body["roles"]["finish-delta-chip"] = {
        "backgroundTreatment": "fill", "chipPadding": "chip-padding",
        "chipMinBlockSize": "delta-chip-min",
    }
    body["colorBindings"]["finish-delta-chip.fill"] = "text"
    return _write(path, theme)


def _forecast_marks(rendered):
    return [item for item in rendered.surface.primitives if item.purpose == "forecast"]


def _forecast_deltas(rendered):
    return [item for item in rendered.surface.primitives
            if item.kind == "Text" and item.purpose == "forecast-finish-delta"]


def test_folded_forecast_point_gets_required_plot_delta_and_keeps_its_fold(tmp_path):
    result = render_draft(_request(tmp_path, placement="plot", folded=True)).rendered

    forecasts = _forecast_marks(result)
    gate_marks = [item for item in forecasts if item.source_ref == "gate"]
    assert len(gate_marks) == 1
    assert gate_marks[0].visual_role == "planned"
    assert gate_marks[0].scene_id.startswith("planned:group-header:team:gate")
    deltas = [item for item in _forecast_deltas(result)
              if item.scene_id == "variance:group-header:team:gate"]
    assert len(deltas) == 1 and deltas[0].text.endswith("*")
    assert "Forecast (* estimated)" in result.artifact.content.decode("utf-8")
    assert not any(item.scene_id in {"forecast:row:gate", "forecast:gate", "planned:gate"}
                   for item in result.surface.primitives)


def test_table_only_folded_point_refuses_with_stable_occurrence_identity(tmp_path):
    request = _request(tmp_path, placement="table", folded=True)

    with pytest.raises(RenderFailed) as failure:
        render_draft(request)

    assert failure.value.code == "E_FORECAST_PRESENTATION_REQUIRED"
    assert "group-header:team:gate" in failure.value.message


def test_folded_forecast_chip_footprints_pack_and_are_required_route_obstacles(tmp_path, monkeypatch):
    from chrona.presentation.layout import surface_route_label_plan as route_plan

    captured = []
    compose = route_plan.compose_surface_routes

    def capture(context):
        captured.append(context.required_label_obstacle_ids)
        return compose(context)

    monkeypatch.setattr(route_plan, "compose_surface_routes", capture)
    theme_path = _large_delta_chip_theme(tmp_path / "theme.yaml")
    request = _request(tmp_path, placement="plot", folded=True,
                       folded_count=2, theme_path=theme_path, viewport="2400xauto")
    view = safe_load(Path(request.view).read_bytes())
    view["body"]["window"] = {"mode": "explicit", "start": "2026-01-01", "end": "2026-12-01"}
    _write(Path(request.view), view)
    result = render_draft(request).rendered

    deltas = {item.scene_id: item for item in _forecast_deltas(result)
              if item.scene_id.startswith("variance:group-header:")}
    assert set(deltas) == {"variance:group-header:team:gate",
                           "variance:group-header:team:gate-2"}
    chips = {item.scene_id: item for item in result.surface.primitives
             if item.purpose == "label-chip" and item.scene_id.startswith("chip:variance:group-header")}
    assert set(chips) == {f"chip:{scene_id}" for scene_id in deltas}
    for scene_id, delta in deltas.items():
        chip = chips[f"chip:{scene_id}"]
        assert delta.text.endswith("*")
        assert chip.bounds[1] <= delta.bounds[1]
        assert chip.bounds[1] + chip.bounds[3] >= delta.bounds[1] + delta.bounds[3]
        assert chip.bounds[3] >= 56.0

    marks = [item for item in _forecast_marks(result) if item.source_ref in {"gate", "gate-2"}]
    assert len(marks) == 2 and marks[0].bounds[1] != marks[1].bounds[1]
    (group,) = result.surface.groups
    assert group.header_bounds[3] >= 112.0
    assert captured and all({
        "variance:group-header:team:gate", "label-footprint:variance:group-header:team:gate",
        "variance:group-header:team:gate-2", "label-footprint:variance:group-header:team:gate-2",
    } <= ids for ids in captured)


def test_explicit_shared_row_table_subject_covers_only_one_primary(tmp_path):
    request = _request(tmp_path, placement="table", explicit=True)

    with pytest.raises(RenderFailed) as failure:
        render_draft(request)

    assert failure.value.code == "E_FORECAST_PRESENTATION_REQUIRED"
    assert "shared:primary-b" in failure.value.message


@pytest.mark.parametrize("placement", ("plot", "both"))
def test_explicit_shared_row_plot_channel_covers_each_primary_occurrence(tmp_path, placement):
    result = render_draft(_request(tmp_path, placement=placement, explicit=True)).rendered

    marks = {item.source_ref for item in _forecast_marks(result)}
    assert marks == {"a", "b"}
    deltas = _forecast_deltas(result)
    assert {item.source_ref for item in deltas} == {"a", "b"}
    assert all(item.text.endswith("*") for item in deltas)
