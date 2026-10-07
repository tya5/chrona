"""Natural axis/header prefix geometry is available before row placement."""
from dataclasses import replace
from decimal import Decimal

import pytest

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_composer import (
    prepare_surface_content, prepare_surface_natural_geometry,
)
from chrona.presentation.layout.surface_axis import measure_surface_axis
from tests.unit.chrona.presentation.layout.test_surface_axis_tier_geometry import _axis_request
from chrona.presentation.model.surface_content import AxisTier


def test_natural_prefix_and_completed_prefix_share_exact_candidate_demand(monkeypatch):
    from chrona.presentation.layout import surface_base

    request = _axis_request((AxisTier("month", 1, "grid-major"),))

    def forbidden(*args, **kwargs):
        pytest.fail("natural prefix geometry must not depend on placed rows or tracks")

    for name in ("place_rows", "place_mark_tracks", "place_lane_mark_tracks"):
        monkeypatch.setattr(surface_base, name, forbidden)

    natural = prepare_surface_natural_geometry(request)
    completed = prepare_surface_content(request)
    assert natural.row_viewport == completed.row_viewport
    assert natural.axis_summary.label_tiers == completed.axis.placements.label_tiers
    assert natural.axis_measurement == measure_surface_axis(request, completed.inline.scale)
    assert natural.table == completed.table
    assert natural.required_timeline_block() == completed.required_timeline_block()


def test_final_axis_admission_reuses_natural_measurements_and_prefix_batches(monkeypatch):
    from chrona.presentation.layout import surface_composer

    request = _axis_request((AxisTier("month", 1, "grid-major"),))
    natural = prepare_surface_natural_geometry(request)

    def forbidden(*args, **kwargs):
        pytest.fail("final admission must consume candidate natural geometry without rebuilding it")

    for name in ("prepare_surface_inline", "measure_surface_axis", "summarize_surface_axis_vertical",
                 "prepare_table_header_seed", "complete_slot_headings"):
        monkeypatch.setattr(surface_composer, name, forbidden)
    completed = prepare_surface_content(request, natural=natural)
    assert completed.axis.placements.shapes
    assert completed.row_viewport == natural.row_viewport


def test_tiny_host_natural_summary_succeeds_before_native_axis_admission(monkeypatch):
    from chrona.presentation.layout import surface_composer
    from chrona.presentation.layout.surface_base import prepare_surface_inline as prepare_inline

    request = _axis_request((AxisTier("quarter", 1, "band"), AxisTier("month", 1, "band")))

    def tiny_inline(value):
        inline = prepare_inline(value)
        axis = inline.by_source["timeline-axis"]
        tiny_axis = replace(axis, bounds=replace(axis.bounds, block_size=Decimal(1)))
        return replace(inline, by_source={**inline.by_source, "timeline-axis": tiny_axis})

    monkeypatch.setattr(surface_composer, "prepare_surface_inline", tiny_inline)
    natural = prepare_surface_natural_geometry(request)
    assert natural.axis_summary.max_rect_block_end is not None
    with pytest.raises(LayoutError) as caught:
        prepare_surface_content(request)
    assert caught.value.diagnostic_id == "E_PRESENTATION_AXIS_OVERFLOW"
    assert caught.value.path == "/view/body/axis/tiers/0"
    assert caught.value.detail == "band-lane:0"
