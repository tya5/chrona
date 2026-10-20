"""Final keys cover point states once per completed figure under each owner (#1847)."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path
from xml.etree import ElementTree

import yaml

from chrona.resources import builtin_preset_source_root, safe_load
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from tests.support import synthetic_review as sr


def _request(tmp_path: Path, *, actual: bool, forecast: bool):
    source = sr.with_calendar(sr.project({
        "work": sr.span("work", date(2026, 2, 2), 5, owner="team", title="Design work"),
        "planned": sr.point("planned", date(2026, 2, 9), owner="team", title="Planned gate"),
        "observed": sr.point("observed", date(2026, 2, 10), owner="team", title="Observed gate"),
        "forecast": {"type": "gate", "title": "Forecast gate", "fields": {"owner": "team"},
                     "schedule": {"mode": "scheduled-point"}},
    }, [{"id": "work-forecast", "type": "dependency", "lag": "0wd",
         "from": {"object": "work", "endpoint": "end"},
         "to": {"object": "forecast", "endpoint": "at"}}]), name="weekdays")
    parts = sr.bundle("executive-light")
    parts["view"]["body"]["window"] = {
        "mode": "explicit", "start": "2026-02-01", "end": "2026-02-22"}
    parts["view"]["body"]["rows"] = {"mode": "automatic", "points": "own-row"}
    if forecast:
        parts["view"]["body"]["comparison"]["baseline"] = "snapshot"
        parts["view"]["body"]["comparison"]["baselineMarks"] = "ghost"
        parts["view"]["body"]["comparison"]["facets"] = ["planned", "actual", "finishDelta"]
        parts["view"]["body"]["tableColumns"] = [
            {"id": "Task", "source": "title", "missing": "em-dash", "align": "start",
             "width": "content", "headerOrientation": "horizontal"},
            {"id": "Delta", "source": {"comparisonFacet": "finishDelta"}, "format": "signedDays",
             "missing": "blank", "align": "end", "width": "content", "headerOrientation": "horizontal"},
        ]
    else:
        parts["view"]["body"]["comparison"]["baseline"] = "primary"
        parts["view"]["body"]["comparison"].pop("baselineMarks", None)
        parts["view"]["body"]["comparison"]["facets"] = ["planned", "actual"]
    parts["view"]["body"]["visibility"]["labels"] = {
        "placement": "plot", "content": ["title", "finishDelta"] if forecast else ["title"],
        "side": "end", "overflow": "suppress"}
    # Keep the normal Theme geometry/paint pipeline, while making each state
    # visibly distinct so its final legend witness can be checked in the SVG.
    theme = parts["theme"]["body"]
    theme["roles"].setdefault("actual", {})
    theme["roles"]["actual"]["symbol"] = "actual-symbol"
    theme["values"]["actual-symbol"] = {"type": "symbol", "value": {"shape": "circle"}}
    theme["roles"].setdefault("forecast", {})
    theme["roles"]["forecast"]["symbol"] = "forecast-symbol"
    theme["values"]["forecast-symbol"] = {"type": "symbol", "value": {"shape": "diamond"}}
    theme["roles"]["planned"]["symbol"] = "planned-symbol"
    theme["values"]["planned-symbol"] = {"type": "symbol", "value": {"shape": "chevron"}}

    detail_root = builtin_preset_source_root("presets/bundles/executive-light")
    detail = safe_load(detail_root.joinpath("detail.yaml").read_bytes())
    detail["body"]["legend"] = [{"role": "milestone", "label": "Gate"}]
    project_path = sr._write(tmp_path / "project.yaml", source)
    view_path = sr._write(tmp_path / "view.yaml", parts["view"])
    theme_path = sr._write(tmp_path / "theme.yaml", parts["theme"])
    scheme_path = sr._write(tmp_path / "scheme.yaml", parts["scheme"])
    layout_path = sr._write(tmp_path / "layout.yaml", parts["layout"])
    detail_path = sr._write(tmp_path / "detail.yaml", detail)
    actual_path = None
    if actual:
        actual_doc = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
                      "body": {"asOf": "2026-02-12", "observations": [
                           {"id": "gate-observed", "projectObjectId": "observed", "sequence": 1,
                           "actual": {"at": "2026-02-11"}}]}}
        actual_path = sr._write(tmp_path / "actual.yaml", actual_doc)
    snapshot_path = sr._write(tmp_path / "snapshot.yaml", deepcopy(source))
    return DraftRenderRequest(
        project=project_path, target_kind="svg", view=view_path, theme=theme_path,
        scheme=scheme_path, layout=layout_path, detail=detail_path, actual=actual_path,
        snapshot=snapshot_path if forecast else None, forecast=forecast, viewport="1600x900")


def _legend(rendered):
    primitives = rendered.surface.primitives
    marks = tuple(item for item in primitives if item.purpose == "legend-swatch")
    labels = tuple(item for item in primitives if item.purpose == "legend-label")
    return marks, labels


def _svg_elements(rendered):
    return {item.attrib.get("data-scene-id"): item
            for item in ElementTree.fromstring(rendered.artifact.content).iter()
            if item.attrib.get("data-scene-id")}


def _ink_signature(item):
    x, y, width, height = item.bounds
    geometry = tuple((command.kind, tuple(
        (round((px - x) / width, 4), round((py - y) / height, 4))
        for px, py in command.points)) for command in item.symbol.outline)
    return geometry, item.paint


def test_milestone_owner_emits_final_actual_forecast_keys_and_svg_glyphs(tmp_path):
    rendered = render_draft(_request(tmp_path, actual=True, forecast=True)).rendered
    point_marks = tuple(item for item in rendered.surface.primitives
                        if item.kind == "Symbol" and item.purpose in {"planned", "actual", "forecast"}
                        and item.source_kind == "object")
    swatches, labels = _legend(rendered)
    state_swatches = tuple(item for item in swatches if item.source_ref.startswith("milestone:"))
    state_labels = tuple(item for item in labels if item.source_ref.startswith("milestone:"))

    assert {item.purpose for item in point_marks} == {"actual", "forecast"}
    assert {item.source_ref for item in point_marks if item.purpose == "actual"} == {"observed"}
    assert {item.text for item in state_labels} == {"Gate · Actual", "Gate · Forecast (* estimated)"}
    assert len(state_swatches) == len(state_labels) == 2
    # Distinct state witnesses remain distinct even when the owning Detail role is shared.
    assert len({item.scene_id for item in state_swatches}) == 2
    assert {_ink_signature(item) for item in state_swatches} == {_ink_signature(item) for item in point_marks}
    assert len({_ink_signature(item) for item in state_swatches}) == 2
    for mark in point_marks:
        matches = [swatch for swatch in state_swatches
                   if swatch.purpose == "legend-swatch"
                   and _ink_signature(swatch) == _ink_signature(mark)]
        assert len(matches) == 1, f"{mark.purpose} mark must have exactly one matching state key"

    svg = _svg_elements(rendered)
    for swatch in state_swatches:
        assert swatch.scene_id in svg
        assert svg[swatch.scene_id].tag.endswith("path")
        assert svg[swatch.scene_id].attrib.get("fill") == swatch.paint.fill
    for mark in point_marks:
        assert svg[mark.scene_id].attrib.get("fill") == mark.paint.fill


def test_point_specific_states_include_planned_and_actual_keys(tmp_path):
    rendered = render_draft(_request(tmp_path, actual=True, forecast=False)).rendered
    point_marks = tuple(item for item in rendered.surface.primitives
                        if item.kind == "Symbol" and item.purpose in {"planned", "actual"}
                        and item.source_kind == "object")
    swatches, labels = _legend(rendered)
    state_swatches = tuple(item for item in swatches if item.source_ref.startswith("milestone:"))
    state_labels = tuple(item for item in labels if item.source_ref.startswith("milestone:"))

    assert {item.purpose for item in point_marks} == {"planned", "actual"}
    assert {item.text for item in state_labels} == {"Gate · Planned", "Gate · Actual"}
    assert len(state_swatches) == len(state_labels) == 2
    assert {_ink_signature(item) for item in state_swatches} == {_ink_signature(item) for item in point_marks}
    for mark in point_marks:
        assert sum(_ink_signature(swatch) == _ink_signature(mark) for swatch in state_swatches) == 1
    svg = _svg_elements(rendered)
    assert all(item.scene_id in svg and svg[item.scene_id].tag.endswith("path") for item in state_swatches)
    assert all(svg[item.scene_id].attrib.get("fill") == item.paint.fill for item in (*state_swatches, *point_marks))


def test_single_final_point_state_keeps_owner_label_and_omits_hidden_keys(tmp_path):
    rendered = render_draft(_request(tmp_path, actual=False, forecast=False)).rendered
    point_marks = tuple(item for item in rendered.surface.primitives
                        if item.kind == "Symbol" and item.purpose in {"planned", "actual", "forecast"}
                        and item.source_kind == "object")
    swatches, labels = _legend(rendered)

    assert {item.purpose for item in point_marks} == {"planned"}
    assert {item.source_ref for item in point_marks} == {"planned", "observed", "forecast"}
    assert len(swatches) == len(labels) == 1
    assert all(_ink_signature(mark) == _ink_signature(swatches[0]) for mark in point_marks)
    assert labels[0].text == "Gate"
    assert swatches[0].scene_id in _svg_elements(rendered)
    assert not any(text in rendered.artifact.content.decode("utf-8")
                   for text in ("Gate · Actual", "Gate · Forecast"))


def test_identical_planned_and_actual_figures_share_one_faithful_svg_key(tmp_path):
    request = _request(tmp_path, actual=True, forecast=False)
    theme = yaml.safe_load(request.theme.read_text())
    # An identical declared treatment must not produce duplicate visual keys.
    theme["body"]["roles"]["actual"] = dict(theme["body"]["roles"]["planned"])
    theme["body"]["colorBindings"]["actual.fill"] = theme["body"]["colorBindings"]["planned.fill"]
    sr._write(request.theme, theme)
    rendered = render_draft(request).rendered
    points = tuple(item for item in rendered.surface.primitives
                   if item.kind == "Symbol" and item.source_kind == "object"
                   and item.purpose in {"planned", "actual"})
    swatches, labels = _legend(rendered)
    assert {item.purpose for item in points} == {"planned", "actual"}
    assert len(swatches) == len(labels) == 1
    assert labels[0].text == "Gate"
    assert {_ink_signature(item) for item in points} == {_ink_signature(swatches[0])}
    svg = _svg_elements(rendered)
    assert all(item.scene_id in svg and svg[item.scene_id].tag.endswith("path")
               for item in (*points, *swatches))
    assert all(svg[item.scene_id].attrib.get("fill") == item.paint.fill
               for item in (*points, *swatches))
