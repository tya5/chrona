"""A View-selected Snapshot delta renders without Actual or forecast flags."""
from datetime import date
from xml.etree import ElementTree

import pytest

from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from tests.support import synthetic_review as sr


def _request(tmp_path, *, snapshot, priority=None):
    current = sr.project({
        "task": sr.span("task", date(2026, 2, 2), 10),
        "gate": sr.point("gate", date(2026, 2, 12)),
        "new": sr.point("new", date(2026, 2, 13)),
    })
    baseline = sr.project({
        "task": sr.span("task", date(2026, 2, 2), 7),
        "gate": sr.point("gate", date(2026, 2, 9)),
    })
    parts = sr.bundle("executive-light")
    view = parts["view"]["body"]
    view["rows"] = {"mode": "automatic", "points": "own-row"}
    view["window"] = {"mode": "explicit", "start": "2026-02-01", "end": "2026-02-20"}
    view["comparison"] = {"baseline": "primary", "actual": "optional",
        "observationSelection": "latest", "deltaUnit": "calendar-days", "facets": ["planned", "snapshotFinishDelta"]}
    view["tableColumns"] = [
        {"id": "Task", "source": "title", "missing": "blank", "align": "start", "width": "content", "headerOrientation": "horizontal"},
        {"id": "Baseline", "header": {"wording": "column.finishDelta"},
         "source": {"comparisonFacet": "snapshotFinishDelta"}, "format": "signedDays",
         "missing": "blank", "align": "end", "width": "content", "headerOrientation": "horizontal"},
        {"id": "Actual", "source": {"comparisonFacet": "finishDelta"}, "format": "signedDays",
         "missing": "blank", "align": "end", "width": "content", "headerOrientation": "horizontal"},
    ]
    if priority is not None:
        view["tableColumns"][1]["priority"] = priority
    paths = {kind: sr._write(tmp_path / f"{kind}.yaml", value) for kind, value in parts.items()}
    return DraftRenderRequest(project=sr._write(tmp_path / "project.yaml", current),
        target_kind="svg", view=paths["view"], theme=paths["theme"], scheme=paths["scheme"],
        layout=paths["layout"], viewport="1600x900",
        snapshot=sr._write(tmp_path / "snapshot.yaml", baseline) if snapshot else None)


@pytest.mark.parametrize("snapshot", [False, True])
def test_view_snapshot_delta_reaches_actual_svg_without_actual_or_forecast(tmp_path, snapshot):
    rendered = render_draft(_request(tmp_path, snapshot=snapshot)).rendered
    primitives = rendered.surface.primitives
    assert not any(item.scene_id == "column:Actual" for item in primitives)
    headers = tuple(item for item in primitives if item.scene_id == "column:Baseline")
    if not snapshot:
        assert headers == ()
        assert not any("Baseline" in item.scene_id for item in primitives)
        return
    assert len(headers) == 1 and headers[0].text == "Δ vs baseline"
    cells = tuple(item for item in primitives if item.purpose == "table-cell" and item.table_column_id == "Baseline")
    assert sorted(item.text for item in cells) == ["", "+3d", "+3d"]
    assert all(item.visual_role == "text" for item in cells)
    assert not any("*" in item.text for item in cells)
    svg = ElementTree.fromstring(rendered.artifact.content)
    visible = {item.attrib.get("data-scene-id"): "".join(item.itertext()) for item in svg.iter()
               if item.attrib.get("data-scene-id")}
    assert visible[headers[0].scene_id] == "Δ vs baseline"
    assert sum(visible.get(item.scene_id) == "+3d" for item in cells) == 2


@pytest.mark.parametrize("priority", ["preferred", "required"])
def test_declared_priority_keeps_unbound_snapshot_column_without_fabricating_values(tmp_path, priority):
    rendered = render_draft(_request(tmp_path, snapshot=False, priority=priority)).rendered
    primitives = rendered.surface.primitives
    header = next(item for item in primitives if item.scene_id == "column:Baseline")
    assert header.text == "Δ vs baseline"
    cells = tuple(item for item in primitives
                  if item.purpose == "table-cell" and item.table_column_id == "Baseline")
    assert len(cells) == 3 and all(item.text == "" for item in cells)
    assert not any(item.scene_id == "column:Actual" for item in primitives)
    svg = ElementTree.fromstring(rendered.artifact.content)
    visible = {item.attrib.get("data-scene-id"): "".join(item.itertext()) for item in svg.iter()
               if item.attrib.get("data-scene-id")}
    assert visible[header.scene_id] == "Δ vs baseline"
    assert all(visible.get(item.scene_id, "") == "" for item in cells)
