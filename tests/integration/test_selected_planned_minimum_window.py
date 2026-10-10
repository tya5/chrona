"""Selected-planned windows keep sparse schedules and their labels inside the plot."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml
import pytest

from chrona.resources import builtin_preset_source_root
from tests.support import synthetic_review as sr


def _editorial_default_parts() -> dict:
    parts = sr.bundle("editorial")
    root = builtin_preset_source_root("presets/bundles/editorial-readable-default")
    parts["view"] = yaml.safe_load(root.joinpath("view.yaml").read_bytes())
    return parts


def _case(case: str) -> tuple[dict, tuple[str, ...]]:
    start = date(2026, 1, 5)
    if case == "eleven-day-span":
        return sr.project({"span": sr.span("span", start, 11, title="Eleven day span")}), ("span",)
    if case == "one-day-span":
        return sr.project({"span": sr.span("span", start, 1, title="One day span")}), ("span",)
    if case == "single-gate":
        return sr.project({"gate": sr.point("gate", start, title="Single gate")}), ("gate",)
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
