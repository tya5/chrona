"""Band, ground and rule end at the same edge (#880 item 3).

The temporal scale is inset by what point marks protrude (#501), so the window maps to a range narrower than the timeline
slot. The axis rule and the row bands covered the whole slot while the axis band cells, closed days and period bands stopped
at the window edge, leaving a strip the last milestone's diamond stood in. Proven on a synthetic Project through a packaged
bundle (a milestone on the last day of the window), so no corpus edit can change what these tests prove.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_geometry import extend_to_plot_edges
from chrona.presentation.layout.surface_quality import ScalePlacement
from tests.support import synthetic_review as sr
from tests.support.legacy_axis import use_legacy_six_tier_axis

WINDOW = {"mode": "explicit", "start": "2026-01-01", "end": "2026-04-01"}
FEBRUARY = {"title": "February", "start": "2026-02-01", "end": "2026-03-01"}
WHOLE = {"title": "Whole window", "start": "2025-12-01", "end": "2026-06-01"}


def _render(tmp_path: Path, *, milestone: date = date(2026, 3, 31), periods=("february", "whole")):
    # Mondays only: both window edges (Thursday 2026-01-01 and Tuesday 2026-03-31) are closed days.
    source = sr.with_calendar(sr.project({"a": sr.span("a", date(2026, 1, 5), 40), "g": sr.point("g", milestone)}),
                              ("mon",))
    source["periods"] = {"february": FEBRUARY, "whole": WHOLE}
    parts = use_legacy_six_tier_axis(sr.bundle("executive-light"))
    parts["view"]["body"]["window"] = dict(WINDOW)
    parts["view"]["body"]["periods"] = [{"id": item} for item in periods]
    parts["theme"]["body"]["roles"]["period-band"] = {
        "backgroundTreatment": "fill", "backgroundPaintOrder": 11, "opacity": "opacity.axis-band"}
    parts["theme"]["body"]["colorBindings"].pop("period-band.stroke", None)  # the packaged band is an outline
    parts["theme"]["body"]["colorBindings"]["period-band.fill"] = "accent"
    directory = tmp_path / "render"
    directory.mkdir()
    return sr.render(directory, source, presentation=parts)


def _span(item) -> tuple[float, float]:
    inline, _, size, _ = (float(value) for value in item.bounds)
    return inline, inline + size


def _slot_span(rendered) -> tuple[float, float]:
    slot = next(item for item in rendered.surface.slots if item.slot_id == "timeline")
    inline, _, size, _ = (float(value) for value in slot.bounds)
    return inline, inline + size


def _of(rendered, purpose: str) -> list:
    return [item for item in rendered.surface.primitives if item.purpose == purpose]


def _gap() -> float:
    """The axis band's declared cell gap in the packaged Theme, read from the Theme."""
    theme = sr.bundle("executive-light")["theme"]["body"]
    return float(theme["values"][theme["roles"]["axis-band-decoration2"]["cellGap"]]["value"])


def _x(rendered, day: date) -> float:
    scale = rendered.surface.scale_manifest
    return scale.origin + (day - scale.domain_start).days * scale.unit_ratio


def test_the_fixture_has_a_margin_the_scale_does_not_cover(tmp_path):
    rendered = _render(tmp_path)
    left, right = _slot_span(rendered)
    scale = rendered.surface.scale_manifest

    assert scale.range_start > left + 1 and scale.range_end < right - 1


def test_band_ground_and_rule_end_at_the_same_edge(tmp_path):
    rendered = _render(tmp_path)
    left, right = _slot_span(rendered)

    rule = _span(next(item for item in rendered.surface.primitives if item.purpose == "axis-rule"))
    assert rule == pytest.approx((left, right))
    bands = sorted((_span(item) for item in _of(rendered, "axis-band")))
    assert bands[0][0] == pytest.approx(left) and max(end for _, end in bands) == pytest.approx(right)
    closed = sorted(_span(item) for item in _of(rendered, "calendar-closed"))
    assert closed[0][0] == pytest.approx(left) and closed[-1][1] == pytest.approx(right)
    ground = [_span(item) for item in _of(rendered, "row-decoration")]
    assert ground and all(span[1] == pytest.approx(right) for span in ground)


def test_the_last_milestone_stands_on_the_band(tmp_path):
    rendered = _render(tmp_path)
    _, right = _slot_span(rendered)
    mark = next(item for item in rendered.surface.primitives
                if item.purpose == "planned" and item.scene_id.endswith(":g"))

    assert _span(mark)[1] <= right + 0.01
    assert max(end for _, end in (_span(item) for item in _of(rendered, "axis-band"))) >= _span(mark)[1]


def test_a_period_that_reaches_the_window_edge_reaches_the_plot_edge_and_one_inside_does_not(tmp_path):
    rendered = _render(tmp_path)
    left, right = _slot_span(rendered)
    bands = {item.source_ref: _span(item) for item in _of(rendered, "period-band")}

    assert bands["whole"] == pytest.approx((left, right))
    assert bands["february"] == pytest.approx((_x(rendered, date(2026, 2, 1)), _x(rendered, date(2026, 3, 1))))


def test_nothing_inside_the_window_moves(tmp_path):
    rendered = _render(tmp_path)
    cells = sorted(_span(item) for item in _of(rendered, "axis-band") if item.scene_id.startswith("axis-band-rect:3:"))

    # Month cells keep the Theme's cell gap between them, centred on the date coordinates of the month starts.
    gap = _gap()
    assert gap > 0
    for (_, end), (start, _) in zip(cells, cells[1:]):
        assert start - end == pytest.approx(gap)
    assert cells[1][0] == pytest.approx(_x(rendered, date(2026, 2, 1)) + gap / 2)
    assert cells[2][0] == pytest.approx(_x(rendered, date(2026, 3, 1)) + gap / 2)
    # The full-height grid lines stand at the interval starts, the first at the window start, not the plot edge.
    lines = sorted(item.points[0][0] for item in _of(rendered, "axis-grid") if item.bounds[3] > 8)
    assert lines[0] == pytest.approx(_x(rendered, date(2026, 1, 1)))
    # A closed day inside the window keeps its own day cell.
    inside = next(item for item in _of(rendered, "calendar-closed") if item.scene_id.endswith("2026-02-10"))
    assert _span(inside) == pytest.approx((_x(rendered, date(2026, 2, 10)), _x(rendered, date(2026, 2, 11))))


# --- the rule itself, on bare values -----------------------------------------------------------------------

PLOT = Rect(Decimal(100), Decimal(0), Decimal(1000), Decimal(50))


def _scale(start: float, end: float) -> ScalePlacement:
    return ScalePlacement("s", "primary", date(2026, 1, 1), date(2026, 2, 1), start, end, start, (end - start) / 31)


def test_a_cell_at_the_window_start_reaches_the_plot_start_only():
    assert extend_to_plot_edges(120.0, 300.0, scale=_scale(120.0, 1080.0), plot=PLOT) == (100.0, 300.0)


def test_a_cell_at_the_window_end_reaches_the_plot_end_only():
    assert extend_to_plot_edges(900.0, 1080.0, scale=_scale(120.0, 1080.0), plot=PLOT) == (900.0, 1100.0)


def test_a_cell_across_the_whole_window_reaches_both_edges():
    assert extend_to_plot_edges(120.0, 1080.0, scale=_scale(120.0, 1080.0), plot=PLOT) == (100.0, 1100.0)


def test_a_cell_inside_the_window_is_unchanged():
    assert extend_to_plot_edges(300.0, 900.0, scale=_scale(120.0, 1080.0), plot=PLOT) == (300.0, 900.0)


def test_a_scale_that_fills_the_plot_changes_nothing():
    assert extend_to_plot_edges(100.0, 1100.0, scale=_scale(100.0, 1100.0), plot=PLOT) == (100.0, 1100.0)


def test_a_cell_is_never_shrunk():
    # A scale that overhangs the plot (range outside it) keeps the cell as it is.
    assert extend_to_plot_edges(80.0, 1120.0, scale=_scale(80.0, 1120.0), plot=PLOT) == (80.0, 1120.0)
