"""#1150: a size that must equal other sizes is derived when the Theme leaves it unbound.

Synthetic Project through the packaged `executive-light` bundle with Theme metric bindings removed or changed
here. No `examples/` input: a corpus edit cannot change what these tests prove.
"""
from __future__ import annotations

from datetime import date

import pytest

from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr


def _parts(*, row: float | None = None, padding: float | None = None, drop: tuple[str, ...] = (),
           explicit: dict[str, float] | None = None) -> dict:
    parts = sr.bundle("executive-light")
    body = parts["theme"]["body"]
    for metric, value in (("timeline.row.minBlockSize", row), ("timeline.row.paddingBlock", padding)):
        if value is not None:
            body["values"][body["metrics"][metric]]["value"] = value
    for metric, value in (explicit or {}).items():
        body["values"][body["metrics"][metric]]["value"] = value
    for metric in drop:
        del body["metrics"][metric]
    return parts


def _lanes(*, quarter: float | None = None, drop: tuple[str, ...] = (), explicit: dict[str, float] | None = None) -> dict:
    parts = _parts(drop=drop, explicit=explicit)
    if quarter is not None:
        parts["theme"]["body"]["values"]["axis-lane-quarter"]["value"] = quarter
    return parts


def _render(tmp_path, name: str, parts: dict):
    directory = tmp_path / name
    directory.mkdir()
    return sr.render(directory, sr.project({"t": sr.span("t", date(2026, 1, 5), 20)}), presentation=parts)


def _mark_block(rendered) -> float:
    return float(next(item for item in rendered.surface.primitives if item.purpose == "planned").bounds[3])


def _scene_bounds(rendered):
    return [(item.scene_id, tuple(float(value) for value in item.bounds)) for item in rendered.surface.primitives]


def test_an_unbound_track_is_the_row_less_a_padding_on_each_side_and_follows_the_row(tmp_path):
    short = _render(tmp_path, "short", _parts(row=40, padding=8, drop=("timeline.mark.blockSize",)))
    tall = _render(tmp_path, "tall", _parts(row=60, padding=8, drop=("timeline.mark.blockSize",)))

    assert _mark_block(short) == pytest.approx(24)
    assert _mark_block(tall) == pytest.approx(44)


def test_the_track_follows_the_padding_too(tmp_path):
    padded = _render(tmp_path, "padded", _parts(row=40, padding=12, drop=("timeline.mark.blockSize",)))

    assert _mark_block(padded) == pytest.approx(16)


def test_a_bound_track_wins_over_the_derivation(tmp_path):
    bound = _render(tmp_path, "bound", _parts(row=60, padding=8))

    assert _mark_block(bound) == pytest.approx(16)


def test_a_derived_track_equal_to_the_declared_one_changes_nothing(tmp_path):
    declared = _render(tmp_path, "declared", _parts(row=40, padding=8, explicit={"timeline.mark.blockSize": 24}))
    derived = _render(tmp_path, "derived", _parts(row=40, padding=8, drop=("timeline.mark.blockSize",)))

    assert _scene_bounds(derived) == _scene_bounds(declared)
    assert derived.scene.diagnostics == declared.scene.diagnostics


def test_a_derived_track_equal_to_the_declared_one_leaves_every_inline_position_alone(tmp_path):
    """Row 22 and padding 3 (a dense row) derive 16: the timeline must not move horizontally (#1150 finding)."""
    declared = _render(tmp_path, "declared", _parts(row=22, padding=3, explicit={"timeline.mark.blockSize": 16}))
    derived = _render(tmp_path, "derived", _parts(row=22, padding=3, drop=("timeline.mark.blockSize",)))

    assert _mark_block(derived) == pytest.approx(16)
    assert _scene_bounds(derived) == _scene_bounds(declared)


def test_a_track_the_row_cannot_hold_is_a_metric_diagnostic(tmp_path):
    with pytest.raises(RenderFailed) as error:
        _render(tmp_path, "none", _parts(row=16, padding=8, drop=("timeline.mark.blockSize",)))

    assert error.value.code == "E_LAYOUT_METRIC_REQUIRED"


_AXIS_AND_HEADER = ("timeline.axis.blockSize", "table.header.blockSize")


def _axis_bottom(rendered) -> float:
    return float(next(item for item in rendered.surface.primitives if item.purpose == "axis-rule").bounds[1])


def _first_row_top(rendered) -> float:
    return float(rendered.surface.rows[0].bounds[1])


def test_an_unbound_axis_is_the_sum_of_its_lanes_and_the_header_follows_it(tmp_path):
    """The packaged Theme declares lanes 24 + 22 (46) and binds the axis 46 and the header 44."""
    declared = _render(tmp_path, "declared", _lanes(explicit={"timeline.axis.blockSize": 46, "table.header.blockSize": 46}))
    derived = _render(tmp_path, "derived", _lanes(drop=_AXIS_AND_HEADER))

    assert _scene_bounds(derived) == _scene_bounds(declared)
    assert derived.scene.diagnostics == declared.scene.diagnostics


def test_changing_a_lane_moves_the_axis_and_the_table_header_together(tmp_path):
    short = _render(tmp_path, "short", _lanes(quarter=24, drop=_AXIS_AND_HEADER))
    tall = _render(tmp_path, "tall", _lanes(quarter=30, drop=_AXIS_AND_HEADER))

    assert _axis_bottom(tall) - _axis_bottom(short) == pytest.approx(6)
    # The table's first row starts where the header ends, so the header and the axis end together.
    assert _first_row_top(tall) - _first_row_top(short) == pytest.approx(6)


def test_a_bound_axis_and_header_win_over_the_derivation(tmp_path):
    bound = _render(tmp_path, "bound", _lanes(quarter=30, explicit={"timeline.axis.blockSize": 60, "table.header.blockSize": 60}))
    derived = _render(tmp_path, "derived", _lanes(quarter=30, drop=_AXIS_AND_HEADER))

    assert _axis_bottom(bound) - _axis_bottom(derived) == pytest.approx(60 - 52)


def test_an_unbound_header_is_the_bound_axis(tmp_path):
    header = _render(tmp_path, "header", _lanes(drop=("table.header.blockSize",), explicit={"timeline.axis.blockSize": 50}))
    both = _render(tmp_path, "both", _lanes(explicit={"timeline.axis.blockSize": 50, "table.header.blockSize": 50}))

    assert _scene_bounds(header) == _scene_bounds(both)
