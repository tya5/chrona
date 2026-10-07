"""Natural axis/header prefix geometry is available before row placement."""
from dataclasses import replace
from decimal import Decimal

import pytest

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_composer import (
    prepare_surface_candidate, prepare_surface_content, prepare_surface_natural_candidate,
    prepare_surface_natural_geometry,
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
    from chrona.presentation.layout import surface_preparation

    request = _axis_request((AxisTier("month", 1, "grid-major"),))
    natural = prepare_surface_natural_geometry(request)

    def forbidden(*args, **kwargs):
        pytest.fail("final admission must consume candidate natural geometry without rebuilding it")

    for name in ("prepare_surface_inline", "measure_surface_axis", "summarize_surface_axis_vertical",
                 "prepare_table_header_seed", "complete_slot_headings"):
        monkeypatch.setattr(surface_preparation, name, forbidden)
    completed = prepare_surface_content(request, natural=natural)
    assert completed.axis.placements.shapes
    assert completed.row_viewport == natural.row_viewport


def test_tiny_host_natural_summary_succeeds_before_native_axis_admission(monkeypatch):
    from chrona.presentation.layout import surface_preparation
    from chrona.presentation.layout.surface_base import prepare_surface_inline as prepare_inline

    request = _axis_request((AxisTier("quarter", 1, "band"), AxisTier("month", 1, "band")))

    def tiny_inline(value):
        inline = prepare_inline(value)
        axis = inline.by_source["timeline-axis"]
        tiny_axis = replace(axis, bounds=replace(axis.bounds, block_size=Decimal(1)))
        return replace(inline, by_source={**inline.by_source, "timeline-axis": tiny_axis})

    monkeypatch.setattr(surface_preparation, "prepare_surface_inline", tiny_inline)
    natural = prepare_surface_natural_geometry(request)
    assert natural.axis_summary.max_rect_block_end is not None
    with pytest.raises(LayoutError) as caught:
        prepare_surface_content(request)
    assert caught.value.diagnostic_id == "E_PRESENTATION_AXIS_OVERFLOW"
    assert caught.value.path == "/view/body/axis/tiers/0"
    assert caught.value.detail == "band-lane:0"


def test_width_changed_lane_natural_and_completed_candidates_recompute_preflight():
    from chrona.presentation.model.projection import build_review_projection
    from tests.unit.chrona.presentation.scene.test_relation_ghost_endpoints import (
        MODES, PLACED, PROJECT, SNAPSHOT,
    )

    projection = build_review_projection(PROJECT, PLACED, MODES["lanes"], None,
                                         snapshot_project=PROJECT, snapshot_placements=SNAPSHOT)
    original = replace(_axis_request((AxisTier("month", 1, "grid-major"),)), projection=projection)
    original = replace(original, measured_sources=replace(original.measured_sources, metric_values={
        **original.measured_sources.metric_values,
        "text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4")}))
    initial = prepare_surface_natural_candidate(original)
    stale = initial.inline.request.fixed_lane_preflight
    assert stale is not None
    assert stale.seed_inline_frame.timeline_inline_size == Decimal(500)

    manifest = replace(original.layout_manifest, decisions=tuple(
        replace(item, bounds=replace(item.bounds, inline_size=Decimal(250)))
        if item.source in {"timeline", "timeline-axis"} else item
        for item in original.layout_manifest.decisions))
    candidate = replace(original, layout_manifest=manifest, fixed_lane_preflight=stale)
    natural = prepare_surface_natural_candidate(candidate)
    completed = prepare_surface_candidate(candidate)
    natural_preflight = natural.inline.request.fixed_lane_preflight
    completed_preflight = completed.inline.request.fixed_lane_preflight

    assert natural_preflight is not None and natural_preflight is not stale
    assert completed_preflight is not None and completed_preflight is not stale
    assert natural_preflight.seed_inline_frame.timeline_inline_size == Decimal(250)
    assert completed_preflight.seed_inline_frame.timeline_inline_size == Decimal(250)
    assert natural.inline.scale is natural_preflight.scale
    assert completed.inline.scale is completed_preflight.scale
    assert natural.row_viewport == completed.row_viewport
    assert natural.axis_measurement == measure_surface_axis(candidate, natural.inline.scale)
    assert natural.axis_summary.label_tiers == completed.axis.placements.label_tiers
    assert natural.table == completed.table
    assert natural.required_timeline_block() == completed.required_timeline_block()
