"""Real-render regression for declared colour encoding across gate modes (#1756)."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from xml.etree import ElementTree

import yaml

from chrona.presentation.scene.serialization import scene_document
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from tests.support import synthetic_review as sr


RISK = "#b21f35"


def _write(path, value):
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    return path


def _source():
    source = sr.project({
        "task": sr.span("task", date(2026, 1, 5), 5, owner="risk-high"),
        "gate": sr.point("gate", date(2026, 1, 12), title="Release gate", owner="risk-high"),
    }, [{"id": "task-gate", "type": "dependency", "lag": "0wd",
         "from": {"object": "task", "endpoint": "end"},
         "to": {"object": "gate", "endpoint": "at"}}])
    source["project"].update(id="gate-encoding-modes", calendar="weekdays")
    source["calendars"] = {"weekdays": {"working_days": ["mon", "tue", "wed", "thu", "fri"]}}
    return source


def _presentation(*, gate_role=True):
    parts = sr.bundle("executive-light")
    parts["view"]["body"]["colorEncoding"] = {
        "target": "planned", "source": {"field": "owner"}, "scale": "risk", "domain": ["risk-high"]}
    parts["theme"]["body"].setdefault("colorScales", {})["risk"] = {
        "slots": {"risk-high": "risk-high"}}
    parts["scheme"]["body"]["categories"]["risk-high"] = RISK
    if gate_role:
        # The existing point-paint rule only gives a gate its distinct
        # canonical semantic when the Theme explicitly declares that role.
        parts["theme"]["body"]["roles"]["gate"] = {"strokeWidth": "stroke-width"}
        parts["theme"]["body"]["colorBindings"].update({"gate.fill": "text", "gate.stroke": "text"})
    else:
        parts["theme"]["body"]["roles"].pop("gate", None)
        parts["theme"]["body"]["colorBindings"].pop("gate.fill", None)
        parts["theme"]["body"]["colorBindings"].pop("gate.stroke", None)
    return parts


def _render(tmp_path, *, forecast=False, gate_role=True):
    tmp_path.mkdir(parents=True, exist_ok=True)
    source = _source()
    parts = _presentation(gate_role=gate_role)
    project_path = _write(tmp_path / "project.yaml", source)
    actual_path = _write(tmp_path / "actual.yaml", {
        "version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
        "body": {"asOf": "2026-01-08", "observations": [
            {"id": "actual-task", "projectObjectId": "task", "sequence": 1,
             "actual": {"start": "2026-01-06"}}]}})
    snapshot_path = _write(tmp_path / "snapshot.yaml", deepcopy(source))
    view_path = _write(tmp_path / "view.yaml", parts["view"])
    theme_path = _write(tmp_path / "theme.yaml", parts["theme"])
    scheme_path = _write(tmp_path / "scheme.yaml", parts["scheme"])
    layout_path = _write(tmp_path / "layout.yaml", parts["layout"])
    request = DraftRenderRequest(
        project_path, "svg", preset="executive-light", view=view_path, theme=theme_path, scheme=scheme_path,
        layout=layout_path,
        actual=actual_path if forecast else None,
        snapshot=snapshot_path if forecast else None, forecast=forecast,
        viewport="1600xauto")
    return render_draft(request).rendered


def _mark(rendered, source_ref, *, purpose=None):
    return next(item for item in rendered.surface.primitives
                if item.source_ref == source_ref and item.kind in {"Rect", "Symbol"}
                and (purpose is None or item.purpose == purpose))


def _svg_fill(rendered, scene_id):
    content = rendered.artifact.content
    root = ElementTree.fromstring(content)
    node = next(item for item in root.iter() if item.attrib.get("data-scene-id") == scene_id)
    return node.attrib.get("fill")


def test_view_planned_target_uses_canonical_point_semantic_for_gate_and_forecast(tmp_path):
    ordinary = _render(tmp_path / "ordinary")
    ordinary_gate = _mark(ordinary, "gate")
    ordinary_task = _mark(ordinary, "task")
    assert ordinary_gate.scene_id.endswith(":gate")
    assert ordinary_gate.encoding is None
    assert ordinary_gate.paint.fill != RISK
    assert ordinary_task.encoding is not None and ordinary_task.paint.fill == RISK

    forecast = _render(tmp_path / "forecast", forecast=True)
    forecast_gate = _mark(forecast, "gate", purpose="forecast")
    assert forecast_gate.purpose == "forecast"
    assert forecast_gate.encoding is not None
    assert forecast_gate.encoding.value == "risk-high"
    assert forecast_gate.paint.fill == RISK
    assert _svg_fill(forecast, forecast_gate.scene_id) == RISK
    serialized = next(item for surface in scene_document(forecast.scene)["surfaces"]
                      for item in surface["primitives"] if item["id"] == forecast_gate.scene_id)
    assert serialized["encoding"] == forecast_gate.encoding.as_mapping()

    # Without an explicit Theme gate role, the established point fallback is
    # planned, so the ordinary point is eligible under the same View selector.
    default_gate = _render(tmp_path / "default-gate", gate_role=False)
    fallback_gate = _mark(default_gate, "gate")
    assert fallback_gate.encoding is not None
    assert fallback_gate.paint.fill == forecast_gate.paint.fill == RISK
    assert _svg_fill(default_gate, fallback_gate.scene_id) == RISK
