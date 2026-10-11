"""Selected-planned windows keep sparse schedules and their labels inside the plot."""
from __future__ import annotations

from datetime import date
from dataclasses import replace
from importlib import import_module
from pathlib import Path

import pytest

from chrona.resources import safe_load
from chrona.usecases import preset_library
from chrona.usecases.failure_report import report_failure
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr


def _editorial_default_parts() -> dict:
    entry = next(item for item in preset_library._library()
                 if item["id"] == preset_library.DEFAULT_PRESET_ID)
    return {kind: safe_load(preset_library._read_member(preset_library._member(entry, member)))
            for kind, member in (("view", "view"), ("theme", "theme"),
                                 ("scheme", "colorScheme"), ("layout", "layout"))}


def _case(case: str) -> tuple[dict, tuple[str, ...]]:
    start = date(2027, 1, 4)
    if case == "eleven-day-span":
        return sr.project({"span": sr.span("span", start, 11, title="The only task")}), ("span",)
    if case == "one-day-span":
        return sr.project({"span": sr.span("span", start, 1, title="One day span")}), ("span",)
    if case == "single-gate":
        return sr.project({"gate": sr.point("gate", start, title="Go live")}), ("gate",)
    if case == "same-date-gates":
        return sr.project({
            "gate-a": sr.point("gate-a", start, title="Gate A"),
            "gate-b": sr.point("gate-b", start, title="Gate B"),
        }), ("gate-a", "gate-b")
    raise AssertionError(case)


def _strictly_inside_horizontal(bounds: tuple[float, float, float, float], host: tuple[float, float, float, float]) -> bool:
    x, _, width, _ = bounds
    left, _, host_width, _ = host
    return left < x and x + width < left + host_width


def _strictly_inside_vertical(bounds: tuple[float, float, float, float], host: tuple[float, float, float, float]) -> bool:
    _, y, _, height = bounds
    _, top, _, host_height = host
    return top < y and y + height < top + host_height


@pytest.mark.parametrize("case", ["eleven-day-span", "one-day-span", "single-gate", "same-date-gates"])
def test_selected_planned_default_pads_sparse_spans_and_gates(tmp_path: Path, case: str) -> None:
    source, object_ids = _case(case)
    render_dir = tmp_path / case
    render_dir.mkdir()
    rendered = sr.render(render_dir, source, presentation=_editorial_default_parts())

    surface = rendered.surface
    plot = next(slot for slot in surface.slots if slot.slot_id == "timeline").bounds
    marks = [item for item in surface.primitives
             if item.source_ref in object_ids and item.purpose in {"planned", "actual", "missingActual"}]
    labels = [item for item in surface.primitives
              if item.source_ref in object_ids and item.purpose == "member-label"]
    svg = rendered.artifact.content.decode("utf-8")
    suppressed = [warning for warning in surface.fit_warnings
                  if warning.code == "W_LAYOUT_LABEL_SUPPRESSED" and
                  any(object_id in warning.source_ref for object_id in object_ids)]

    assert {item.source_ref for item in marks} == set(object_ids)
    assert {item.source_ref for item in labels} == set(object_ids)
    assert all(f'data-scene-id="{item.scene_id}"' in svg for item in labels)
    assert not suppressed
    assert all(_strictly_inside_horizontal(item.bounds, plot) for item in marks)
    assert all(_strictly_inside_vertical(item.bounds, plot) for item in marks)
    assert all(_strictly_inside_horizontal(item.bounds, plot) for item in labels)

    scale = surface.scale_manifest
    assert scale is not None
    dates = []
    for object_id in object_ids:
        schedule = source["objects"][object_id]["schedule"]
        dates.extend(date.fromisoformat(schedule[key]) for key in ("start", "end", "at") if key in schedule)
    assert scale.domain_start < min(dates)
    assert max(dates) < scale.domain_end


def test_degenerate_completed_projection_keeps_owner_detail_in_public_diagnostic(tmp_path, monkeypatch):
    # Valid source selection normally prevents this internal fault. Inject it at
    # the projection boundary to test the real render/report path, not a mock report.
    render_module = import_module("chrona.usecases.render_review")
    original = render_module.build_review_projection
    at = date(2027, 1, 4)
    def degenerate(*args, **kwargs):
        return replace(original(*args, **kwargs), window=(at, at))
    monkeypatch.setattr(render_module, "build_review_projection", degenerate)
    with pytest.raises(RenderFailed) as caught:
        sr.render(tmp_path, sr.project({"gate": sr.point("gate", at)}),
                  presentation=_editorial_default_parts())
    diagnostic = report_failure(caught.value).payload()["diagnostics"][0]
    assert diagnostic["code"] == "E_PRESENTATION_PROJECTION_REQUIRED"
    assert diagnostic["sourceRef"] == "/projection/window"
    assert "2027, 1, 4" in diagnostic["message"]
    assert "gate" in diagnostic["message"]
    assert "positive Date window" in diagnostic["message"]
    assert "no further detail" not in diagnostic["message"]
