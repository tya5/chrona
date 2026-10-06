"""Synthetic closure evidence for comparison stack geometry (#1149)."""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.mark_band_allocation import compose_mark_band
from chrona.presentation.layout.presentation import (
    MarkBandFrame, MarkGeometry, RowPlacement, minimum_track_block_extent, place_mark_tracks,
)
from chrona.presentation.model.projection import ObservationState


def geometries(planned=0.4):
    return {
        "planned": MarkGeometry(planned, (1 - planned) / 2, 0, 0),
        "missing-actual": MarkGeometry(0.3, 0.35, 1, 0),
        "actual": MarkGeometry(0.2, 0.4, 2, 0),
        "snapshot": MarkGeometry(0.7, 0.15, 3, 0, 0.5, 0.25),
    }


def stack(gap=2, padding=1):
    return SimpleNamespace(members=(("planned", "missing-actual"), ("actual",)),
                           gap=Decimal(gap), frame_roles=("snapshot",), frame_padding=Decimal(padding))


@pytest.mark.parametrize("track", [10, 16, 30, 100])
def test_stack_order_gap_center_and_frame_are_completed(track):
    allocation = compose_mark_band(track_size=track, role_geometries=geometries(), stack=stack())
    first, second = allocation.slots
    assert second.block - (first.block + first.block_size) == pytest.approx(2)
    assert (first.block + second.block + second.block_size) / 2 == pytest.approx(track / 2)
    for role in first.roles:
        start, height = allocation.span_bounds(role)
        assert start + height / 2 == pytest.approx(first.block + first.block_size / 2)
    frame = allocation.frames[0]
    assert frame.block == pytest.approx(first.block - 1)
    assert frame.block_size == pytest.approx(second.block + second.block_size - first.block + 2)
    assert allocation.symbol_bounds("snapshot") == (track * 0.25, track * 0.5)


def test_changing_one_height_recenters_without_changing_gap():
    before = compose_mark_band(track_size=30, role_geometries=geometries(), stack=stack())
    after = compose_mark_band(track_size=30, role_geometries=geometries(0.6), stack=stack())
    assert after.slots[0].block < before.slots[0].block
    assert after.slots[1].block > before.slots[1].block
    assert (after.frames[0].block + after.frames[0].block_size / 2) == pytest.approx(15)


def test_oversize_stack_completes_signed_bounds_and_outer_requirement():
    allocation = compose_mark_band(track_size=10, role_geometries=geometries(), stack=stack(8, 3))
    assert allocation.slots[0].block < 0
    assert allocation.outer_extent > allocation.track_size
    assert len(allocation.diagnostics) == 1
    assert allocation.diagnostics[0].startswith("W_LAYOUT_MARK_STACK_OVERFLOW:")


def test_no_stack_retains_legacy_band_arithmetic():
    roles = geometries()
    allocation = compose_mark_band(track_size=16, role_geometries=roles)
    for role, geometry in roles.items():
        assert allocation.span_bounds(role) == (16 * geometry.offset, 16 * geometry.height)
        assert allocation.symbol_bounds(role) == tuple(16 * value for value in geometry.symbol_extent)
    assert allocation.outer_extent == 16
    assert allocation.slots == allocation.frames == allocation.diagnostics == ()


@pytest.mark.parametrize("count", [1, 2])
def test_oversize_stack_reserves_outer_extent_and_independent_track_pitch(count):
    roles = geometries()
    allocation = compose_mark_band(track_size=10, role_geometries=roles, stack=stack(8, 3))
    row = SimpleNamespace(row_id="r", group_id=None, items=tuple(
        SimpleNamespace(item_id=f"a{i}", object_id=f"a{i}", track="stacked", source_kind="primary",
                        actual={}, observation_state=ObservationState.DUE_UNOBSERVED)
        for i in range(count)))
    required = minimum_track_block_extent(review_row=row, mark_block_size=10, role_geometries=roles,
                                         mark_band_allocation=allocation)
    assert required == pytest.approx(count * allocation.outer_extent)
    tracks = place_mark_tracks(review_rows=(row,), row_placements=(RowPlacement("r", None, (0, 0, 100, required)),),
                               mark_block_size=10, role_geometries=roles, mark_band_allocation=allocation)
    previous_end = 0
    for track in tracks:
        frame = MarkBandFrame.from_track(track, None, roles, allocation)
        start, height = frame.role_bounds("snapshot")
        assert start >= previous_end - 1e-9
        assert start + height <= required + 1e-9
        assert start + height / 2 == pytest.approx(track.block + track.block_size / 2)
        previous_end = start + height
