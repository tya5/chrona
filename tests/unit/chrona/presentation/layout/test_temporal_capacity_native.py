"""Native temporal marks consume the sealed table/timeline inline-capacity fact."""
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_composer import compose_surface_layout, prepare_surface_candidate
from chrona.presentation.layout.temporal_capacity import TemporalInlineCapacity
from chrona.presentation.model.projection import ReviewItem, ReviewProjection, ReviewLaneRowProjection, ReviewRowProjection
from chrona.presentation.review.lane_membership import Lane, LaneAssignment, LaneMembership
from tests.unit.chrona.presentation.layout.test_surface_slot_allocation import _request


def _with_allocation(request, width: str):
    manifest = replace(request.layout_manifest, decisions=tuple(
        replace(item, bounds=replace(item.bounds, inline_size=Decimal(width)))
        if item.source == "timeline" else item
        for item in request.layout_manifest.decisions))
    measured, capacity = request.measured_sources, request.temporal_capacity
    if "timeline" in measured.measurements:
        measurements = dict(measured.measurements)
        old = measurements["timeline"]
        measurements["timeline"] = replace(old, preferred_inline=Decimal("500"))
        measured = replace(measured, measurements=measurements)
    capacity = TemporalInlineCapacity.from_manifest(manifest, measured)
    return replace(request, layout_manifest=manifest, measured_sources=measured, temporal_capacity=capacity)


def _point_projection(*, lane: bool = False):
    item = ReviewItem("gate", "Gate", "point", {"at": date(2026, 1, 1)}, None, None,
                      ("planned",), item_id="member-view", source_kind="primary")
    if not lane:
        return ReviewProjection((item,), (date(2026, 1, 1), date(2026, 1, 3)), (), ())
    row = ReviewRowProjection("row-gate", "Gate", "", "member-view", (item,))
    membership = LaneMembership((Lane("lane-gate", "", ("member-view",)),), (
        LaneAssignment("member-view", "lane-gate", "", "dates", "fixed"),))
    return ReviewProjection((item,), (date(2026, 1, 1), date(2026, 1, 3)), (), (),
                            rows=(row,), lane_membership=membership,
                            lane_rows=(ReviewLaneRowProjection("lane-gate", "", (item,), ("member-view",)),))


@pytest.mark.parametrize("kind", ["span", "point"])
def test_zero_width_native_timeline_refuses_ordinary_span_and_point(kind):
    request = _request()
    if kind == "point":
        projection = _point_projection()
    else:
        projection = replace(request.projection, window=(date(2026, 1, 1), date(2026, 1, 3)))
    request = replace(request, projection=projection)
    request = _with_allocation(request, "0")
    with pytest.raises(LayoutError, match="E_LAYOUT_TEMPORAL_INLINE_CAPACITY") as error:
        prepare_surface_candidate(request)
    assert error.value.path == "/layoutManifest/sources/timeline"


def test_zero_width_fixed_lane_timeline_refuses_native_point():
    request = replace(_request(), projection=_point_projection(lane=True))
    request = _with_allocation(request, "0")
    with pytest.raises(LayoutError, match="E_LAYOUT_TEMPORAL_INLINE_CAPACITY"):
        prepare_surface_candidate(request)


def test_table_timeline_composition_requires_the_capacity_fact():
    request = replace(_request(), temporal_capacity=None)
    with pytest.raises(LayoutError, match="E_PRESENTATION_MEASUREMENTS_REQUIRED") as error:
        prepare_surface_candidate(request)
    assert error.value.path == "/temporalCapacity"


def test_narrow_positive_timeline_keeps_native_point_geometry_and_valid_wide_control():
    projection = _point_projection()
    base = replace(_request(), projection=projection)
    narrow = _with_allocation(base, "10")
    prepared = prepare_surface_candidate(narrow)
    assert prepared.inline.scale.range_end > prepared.inline.scale.range_start
    assert prepared.inline.request.temporal_capacity.allocated_inline == Decimal(10)
    compose_surface_layout(narrow, prepared=prepared)

    wide = prepare_surface_candidate(_with_allocation(base, "500"))
    assert wide.inline.scale.range_end > wide.inline.scale.range_start
    assert wide.inline.request.temporal_capacity.allocated_inline == Decimal(500)
