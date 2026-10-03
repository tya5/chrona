"""The as-of chip below the plot, with its block reserved under the last row (#1063).

Synthetic Projects through the packaged `executive-light` bundle (lane rows by default, automatic rows by removing
the View's `rows`); no test reads `examples/`.
"""
from __future__ import annotations

from datetime import date

import pytest

from chrona.presentation.layout.asof_foot_reserve import below_plot_reserve
from chrona.presentation.model.theme_tokens import ThemeTokenView
from tests.support import synthetic_review as sr

ACTUAL = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
          "body": {"asOf": "2026-02-20", "observations": []}}
FALLBACK = "W_LAYOUT_ASOF_BELOW_PLOT_FALLBACK"
ROW_MODES = pytest.mark.parametrize("rows", ["lanes", "automatic"])


def _render(directory, *, placement, viewport=(1600, None), distribution=None, fixed_timeline=None,
            as_of="2026-02-20", rows="lanes", preset="executive-light"):
    directory.mkdir(parents=True, exist_ok=True)
    source = sr.project({"a": sr.span("a", date(2026, 2, 2), 40, title="Alpha"),
                         "b": sr.span("b", date(2026, 3, 9), 20, title="Beta")})
    parts = sr.bundle(preset)
    marker = next(item for item in parts["view"]["body"]["markers"] if item["kind"] == "asOf")
    if placement != "top":
        marker["placement"] = placement
    if distribution is not None:
        parts["layout"]["reviewSurface"]["rowDistribution"] = distribution
    if fixed_timeline is not None:
        sr.fix_block(parts, "timeline", fixed_timeline)
    if rows == "automatic":  # the preset draws lane rows; this is the automatic row mode
        parts["view"]["body"]["rows"] = {"mode": "automatic"}
    actual = {**ACTUAL, "body": {**ACTUAL["body"], "asOf": as_of}}
    return sr.render(directory, source, presentation=parts, actual=actual, viewport=viewport)


def _parts(rendered):
    primitives = {item.scene_id: item for item in rendered.surface.primitives}
    slots = {slot.slot_id: slot for slot in rendered.surface.slots}
    return primitives["as-of-label"], primitives["as-of"], slots


def _reserve(preset="executive-light") -> float:
    theme = {**sr.bundle(preset)["theme"], "version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme"}
    return below_plot_reserve(ThemeTokenView(theme))


def _reserved(rendered) -> float:
    label, rule, _ = _parts(rendered)
    return (label.bounds[1] - rule.points[-1][1]) + label.bounds[3]  # the gap above the chip plus the chip


@ROW_MODES
def test_the_chip_sits_below_the_plot_centred_on_the_rule_and_clear_of_rows_and_marks(tmp_path, rows):
    rendered = _render(tmp_path, placement="below-plot", rows=rows)
    label, rule, _ = _parts(rendered)
    assert label.bounds[1] >= rule.points[-1][1]  # A1: the top is at or below the plot's bottom edge
    assert label.bounds[0] + label.bounds[2] / 2 == pytest.approx(rule.points[0][0])  # A3: centred on the as-of x
    row_bottom = max(row.bounds[1] + row.bounds[3] for row in rendered.surface.rows)
    assert label.bounds[1] >= row_bottom - 1e-6  # A2: clear of every row
    for mark in (item for item in rendered.surface.primitives if item.scene_id.startswith("planned:")):
        assert label.bounds[1] >= mark.bounds[1] + mark.bounds[3]  # A2: clear of every mark
    assert FALLBACK not in " ".join(rendered.surface.diagnostics)


@ROW_MODES
def test_the_slot_below_moves_down_by_exactly_the_reserved_block(tmp_path, rows):
    foot = _render(tmp_path / "foot", placement="foot", rows=rows)
    below = _render(tmp_path / "below", placement="below-plot", rows=rows)
    foot_slots, below_slots = _parts(foot)[2], _parts(below)[2]
    reserved = _reserved(below)
    for slot_id in ("legend", "notes", "group-details"):
        # A4: exactly the reserved block, up to the whole-unit rounding of a content-sized surface extent.
        assert below_slots[slot_id].bounds[1] - foot_slots[slot_id].bounds[1] == pytest.approx(reserved, abs=1.0)
    assert below.surface.canvas_bounds[3] - foot.surface.canvas_bounds[3] == pytest.approx(reserved, abs=1.0)
    # The reservation is the one Layout computes from the Theme: the chip line, its padding and the gap.
    assert reserved == pytest.approx(_reserve())


@ROW_MODES
def test_under_fill_rows_give_up_exactly_the_reserved_block_in_a_fixed_surface(tmp_path, rows):
    foot = _render(tmp_path / "foot", placement="foot", viewport=(1600, 900), distribution="fill", rows=rows)
    below = _render(tmp_path / "below", placement="below-plot", viewport=(1600, 900), distribution="fill", rows=rows)
    label, rule, below_slots = _parts(below)
    foot_rule = _parts(foot)[1]
    assert foot_rule.points[-1][1] - rule.points[-1][1] == pytest.approx(_reserved(below))  # the plot is shorter by R
    slot = below_slots["timeline"]
    assert label.bounds[1] + label.bounds[3] == pytest.approx(slot.bounds[1] + slot.bounds[3])  # the chip ends the slot
    assert below.surface.canvas_bounds == foot.surface.canvas_bounds
    assert FALLBACK not in " ".join(below.surface.diagnostics)


@ROW_MODES
def test_under_pack_a_roomy_surface_keeps_its_rows_and_uses_the_strip(tmp_path, rows):
    foot = _render(tmp_path / "foot", placement="foot", viewport=(1600, 900), distribution="pack", rows=rows)
    below = _render(tmp_path / "below", placement="below-plot", viewport=(1600, 900), distribution="pack", rows=rows)
    label, rule, _ = _parts(below)
    assert rule.points == _parts(foot)[1].points  # rows and plot unchanged
    assert label.bounds[1] >= rule.points[-1][1]


@ROW_MODES
def test_without_room_the_chip_falls_back_inside_the_plot_with_the_diagnostic(tmp_path, rows):
    rendered = _render(tmp_path, placement="below-plot", viewport=(1600, 900), fixed_timeline=70, rows=rows)
    label, rule, _ = _parts(rendered)
    assert any(item.startswith(FALLBACK) for item in rendered.surface.diagnostics)
    assert label.bounds[1] + label.bounds[3] <= rule.points[-1][1] + 1e-6  # today's inside placement
    assert label.bounds[1] >= rule.points[0][1]


def test_a_reservation_that_does_not_fit_leaves_the_rows_as_they_were(tmp_path):
    # A fixed timeline a little taller than its rows but shorter than rows plus the chip block: nothing is reserved,
    # so under `fill` the rows still take the whole slot, exactly as with the plot-foot placement.
    foot = _render(tmp_path / "foot", placement="foot", viewport=(1600, 900), distribution="fill",
                   fixed_timeline=110, rows="automatic")
    below = _render(tmp_path / "below", placement="below-plot", viewport=(1600, 900), distribution="fill",
                    fixed_timeline=110, rows="automatic")
    assert _parts(below)[1].points == _parts(foot)[1].points
    assert any(item.startswith(FALLBACK) for item in below.surface.diagnostics)


def test_existing_placements_are_unaffected_by_the_reservation_code(tmp_path):
    top = _render(tmp_path / "top", placement="top")
    foot = _render(tmp_path / "foot", placement="foot")
    assert top.surface.canvas_bounds == foot.surface.canvas_bounds == (0.0, 0.0, 1600.0, 275.0)
    assert not any(FALLBACK in item for item in top.surface.diagnostics + foot.surface.diagnostics)


@ROW_MODES
def test_at_the_window_edge_the_chip_moves_beside_the_rule_and_stays_in_the_slot(tmp_path, rows):
    rendered = _render(tmp_path, placement="below-plot", as_of="2026-02-02", rows=rows)
    label, rule, slots = _parts(rendered)
    assert label.bounds[1] >= rule.points[-1][1]
    assert label.bounds[0] >= slots["timeline"].bounds[0] - 1e-6  # the centred position would leave the slot


def test_an_as_of_outside_the_window_reserves_nothing_and_draws_no_chip(tmp_path):
    rendered = _render(tmp_path / "out", placement="below-plot", as_of="2027-01-01")
    plain = _render(tmp_path / "plain", placement="top", as_of="2027-01-01")
    assert rendered.surface.canvas_bounds == plain.surface.canvas_bounds
    assert not any(item.scene_id == "as-of-label" for item in rendered.surface.primitives)
    assert not any(FALLBACK in item for item in rendered.surface.diagnostics)
