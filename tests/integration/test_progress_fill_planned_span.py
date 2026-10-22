"""The `actual` progress fill measures the planned span and a finished Actual draws none (#1869, Spec 61 section 1)."""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.surface_marks import actual_progress_fraction
from tests.integration.test_realized_legends import _detail, _paint_ink, _swatches
from tests.support import synthetic_review as sr

AS_OF = "2026-02-11"  # 10 days after the observed starts


def _render(tmp_path, observations, *, lanes: bool, detail=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    source = sr.project({
        "long": sr.span("long", date(2026, 2, 1), 40, title="Long plan"),
        "short": sr.span("short", date(2026, 2, 1), 5, title="Short plan"),
        "done": sr.span("done", date(2026, 2, 1), 20, title="Done"),
    })
    parts = sr.bundle("executive-light")
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    if lanes:
        parts["view"] = sr.lane_view(parts["view"])
    parts["view"]["body"]["progressFill"] = {"source": "actual"}
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "planned-span", "body": {
        "asOf": AS_OF, "observations": [
            {"id": f"{ref}-observed", "sequence": 1, "projectObjectId": ref, "actual": body}
            for ref, body in observations.items()]}}
    return sr.render(tmp_path, source, presentation=parts, actual=actual, viewport=(1800, 1000), detail=detail)


def _widths(rendered, purpose):
    return {item.source_ref: item.bounds[2] for item in rendered.surface.primitives if item.purpose == purpose}


@pytest.mark.parametrize("lanes", [False, True], ids=["rows", "lanes"])
def test_open_actual_fill_is_progress_times_the_planned_span_clipped_to_the_actual(tmp_path, lanes):
    rendered = _render(tmp_path, {
        "long": {"start": "2026-02-01", "progress": 0.35},   # 0.35 x 40 days = 14 days > the 10 observed: clipped
        "short": {"start": "2026-02-01", "progress": 0.5},   # 0.5 x 5 days = 2.5 days inside the 10 observed
    }, lanes=lanes)
    planned, actual, fill = (_widths(rendered, name) for name in ("planned", "actual", "progress-fill"))

    assert fill["short"] == pytest.approx(0.5 * planned["short"], rel=0.02)
    assert fill["short"] < 0.3 * actual["short"]          # not 50 % of the elapsed span
    assert fill["long"] == pytest.approx(actual["long"], rel=0.02)   # 0.35 x 40 days exceeds the 10 days seen: clipped
    assert fill["long"] < planned["long"] * 0.35 + 0.5


@pytest.mark.parametrize("lanes", [False, True], ids=["rows", "lanes"])
def test_finished_actual_draws_no_fill_and_is_recognised_by_its_legend_key(tmp_path, lanes):
    detail = _detail(("actual", "Actual"), ("progressFill", "Progress"))
    finished = {"done": {"start": "2026-02-01", "finish": "2026-02-10", "progress": 1.0}}

    only_finished = _render(tmp_path / "finished", finished, lanes=lanes, detail=detail)
    mixed = _render(tmp_path / "mixed", {**finished, "short": {"start": "2026-02-01", "progress": 0.5}},
                    lanes=lanes, detail=detail)

    for rendered in (only_finished, mixed):
        marks = [item for item in rendered.surface.primitives if item.purpose == "actual" and item.source_ref == "done"]
        keys = _swatches(rendered, "actual")
        assert marks and keys
        assert _paint_ink(marks[0].paint) in {_paint_ink(item.paint) for item in keys}
    assert not [item for item in only_finished.surface.primitives if item.purpose == "progress-fill"]
    assert not _swatches(only_finished, "progress-fill")
    assert {item.source_ref for item in mixed.surface.primitives if item.purpose == "progress-fill"} == {"short"}
    assert len(_swatches(mixed, "progress-fill")) == 1


def test_fraction_falls_back_to_the_host_without_a_comparable_span():
    host = SimpleNamespace(bounds=SimpleNamespace(inline_size=100))
    planned = SimpleNamespace(bounds=SimpleNamespace(inline_size=40))
    nothing = SimpleNamespace(bounds=SimpleNamespace(inline_size=0))

    assert actual_progress_fraction(0.5, {"start": date(2026, 2, 1)}, host, planned) == pytest.approx(0.2)
    assert actual_progress_fraction(0.5, {"start": date(2026, 2, 1)}, host, None) == 0.5      # unmatched Actual
    assert actual_progress_fraction(0.5, {"start": date(2026, 2, 1)}, host, nothing) == 0.5   # planned has no extent
    assert actual_progress_fraction(0.5, {"at": date(2026, 2, 1)}, host, planned) == 0.5      # a point Actual
    assert actual_progress_fraction(1.0, {"start": date(2026, 2, 1)}, host, SimpleNamespace(
        bounds=SimpleNamespace(inline_size=400))) == 1.0                                       # clipped to the host
    assert actual_progress_fraction(1.0, {"start": date(2026, 2, 1), "finish": date(2026, 2, 5)}, host, planned) is None
