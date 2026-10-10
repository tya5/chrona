"""Full allocation is immutable and reusable before any native geometry is closed."""
from dataclasses import FrozenInstanceError, fields, replace
from datetime import date
from decimal import Decimal

import pytest

from chrona.presentation.layout.model import LayoutError, Rect, SlotHeading
from chrona.presentation.layout.sources import MeasuredSources, SourceInput
from chrona.presentation.layout.surface_base import (
    prepare_surface_base, prepare_surface_inline, prepare_surface_slots,
)
from chrona.presentation.layout.surface_quality import SurfaceLayoutRequest
from chrona.presentation.layout.surface_composer import prepare_surface_candidate, prepare_surface_content
from chrona.presentation.model.projection import ReviewItem, ReviewProjection
from chrona.presentation.model.projection import ReviewLaneRowProjection, ReviewRowProjection
from chrona.presentation.review.lane_membership import Lane, LaneAssignment, LaneMembership
from chrona.presentation.model.surface_content import AxisLabelIntent, AxisTier
from chrona.presentation.model.presentation_contract import normalize_presentation_input
from chrona.presentation.model.theme_tokens import ThemeTokenView
from tests.unit.chrona.presentation.scene.test_v05_builder import (
    _Font, _manifest, _theme, _title_measurement, surface_content,
)


def _request():
    item = ReviewItem("a", "Activity", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 2)},
                      None, None, ())
    projection = ReviewProjection((item,), (date(2026, 1, 1), date(2026, 1, 3)), (), ())
    measured = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))}, {
        "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8),
        "timeline.mark.blockSize": Decimal(8)})
    content = surface_content()
    return SurfaceLayoutRequest(
        projection=projection, surface_content=content, presentation_contract=normalize_presentation_input(content),
        layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"),
        measured_sources=measured, theme_tokens=ThemeTokenView(_theme()), font_metrics=_Font())


def test_full_allocations_need_no_projection_measurement_fonts_or_row_geometry():
    request = _request()
    allocated = prepare_surface_slots(replace(request, projection=None, measured_sources=None,
                                             theme_tokens=None, font_metrics=None))
    sources = {slot.source_ref: slot for slot in allocated.slots}
    for decision in request.layout_manifest.decisions:
        assert sources[decision.source].bounds == decision.bounds
        assert sources[decision.source].slot_id == decision.source
    assert sources["review-surface"].bounds.inline == sources["table"].bounds.inline
    assert sources["review-surface"].bounds.inline + sources["review-surface"].bounds.inline_size == (
        sources["timeline"].bounds.inline + sources["timeline"].bounds.inline_size)
    with pytest.raises(FrozenInstanceError):
        allocated.slots = ()


def test_non_lane_candidate_keeps_native_preparation_and_natural_demand():
    request = _request()
    expected = prepare_surface_content(request)
    actual = prepare_surface_candidate(request)
    assert actual.row_viewport == expected.row_viewport
    assert actual.required_timeline_block() == expected.required_timeline_block()
    prepared_request = actual.inline.request
    assert prepared_request is not request
    assert request.mark_visibility_index is None
    assert prepared_request.mark_visibility_index is not None
    assert prepared_request.mark_visibility_index.projection is request.projection
    from chrona.presentation.layout.surface_mark_visibility import ensure_request_mark_visibility_index
    assert ensure_request_mark_visibility_index(prepared_request) is prepared_request


def test_lane_candidate_replaces_prior_preflight_from_exact_candidate_inputs(monkeypatch):
    from chrona.presentation.layout import surface_preparation

    original = _request()
    stale, current, completed = object(), object(), object()
    lane_item = replace(original.projection.items[0], item_id="member-view", source_kind="primary",
                        roles=("planned",))
    source_row = ReviewRowProjection("source-row", "Activity", "group", "member-view", (lane_item,))
    membership = LaneMembership((Lane("lane-final", "group", ("member-view",)),), (
        LaneAssignment("member-view", "lane-final", "group", "dates", "fixed"),
    ))
    projection = ReviewProjection(
        (lane_item,), original.projection.window, (), (), rows=(source_row,),
        lane_membership=membership,
        lane_rows=(ReviewLaneRowProjection("lane-final", "group", (lane_item,), ("member-view",)),),
    )
    candidate = replace(original, projection=projection, fixed_lane_preflight=stale)
    calls = []

    def preflight(**inputs):
        calls.append(inputs)
        return current

    def prepare(request):
        assert request.fixed_lane_preflight is current
        assert request.layout_manifest is candidate.layout_manifest
        assert request.surface_content is candidate.surface_content
        assert request.mark_visibility_index is not None
        assert request.mark_visibility_index.projection is candidate.projection
        return completed

    monkeypatch.setattr(surface_preparation, "preflight_fixed_lane_layout", preflight)
    monkeypatch.setattr(surface_preparation, "prepare_surface_content", prepare)
    assert prepare_surface_candidate(candidate) is completed
    assert calls == [dict(
        projection=candidate.projection, layout_manifest=candidate.layout_manifest,
        surface_content=candidate.surface_content, theme_tokens=candidate.theme_tokens,
        metric_values=candidate.measured_sources.metric_values,
        icon_assets=candidate.icon_assets, visual_requests=candidate.visual_requests,
        font_metrics=candidate.font_metrics)]
    assert candidate.fixed_lane_preflight is stale
    assert candidate.mark_visibility_index is None


def test_width_changed_lane_candidate_closes_real_preflight_and_scene_from_same_manifest():
    from chrona.presentation.model.projection import build_review_projection
    from chrona.presentation.scene.v05_builder import build_scene_input, compose_review_surface
    from tests.unit.chrona.presentation.scene.test_relation_ghost_endpoints import (
        MODES, PLACED, PROJECT, SNAPSHOT,
    )

    projection = build_review_projection(PROJECT, PLACED, MODES["lanes"], None,
                                         snapshot_project=PROJECT, snapshot_placements=SNAPSHOT)
    original = replace(_request(), projection=projection)
    original = replace(original, measured_sources=replace(original.measured_sources, metric_values={
        **original.measured_sources.metric_values,
        "text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4")}))
    initial = prepare_surface_candidate(original)
    assert initial.inline.request.fixed_lane_preflight is not None
    manifest = replace(original.layout_manifest, decisions=tuple(
        replace(item, bounds=replace(item.bounds, inline_size=Decimal(250)))
        if item.source in {"timeline", "timeline-axis"} else item
        for item in original.layout_manifest.decisions))
    candidate = replace(original, layout_manifest=manifest,
                        fixed_lane_preflight=initial.inline.request.fixed_lane_preflight)
    current = prepare_surface_candidate(candidate)
    preflight = current.inline.request.fixed_lane_preflight
    assert preflight is not candidate.fixed_lane_preflight
    assert preflight.seed_inline_frame.timeline_inline_size == Decimal(250)
    assert candidate.fixed_lane_preflight.seed_inline_frame.timeline_inline_size == Decimal(500)
    assert current.inline.scale is preflight.scale
    value = build_scene_input(
        projection=projection, surface_content=candidate.surface_content, layout_manifest=manifest,
        resolved_theme=_theme(), font_metrics=candidate.font_metrics,
        measured_sources=candidate.measured_sources, capabilities={"svg": True},
        fixed_lane_preflight=preflight, surface_preparation=current)
    prepared_surface = compose_review_surface(value)
    native_surface = compose_review_surface(replace(value, surface_preparation=None))
    assert prepared_surface == native_surface


def test_preallocated_surface_base_is_exactly_identical_and_does_not_allocate_twice(monkeypatch):
    request = _request()
    expected = prepare_surface_base(request)
    allocation = prepare_surface_slots(request)

    def forbidden(*args, **kwargs):
        pytest.fail("an already prepared allocation must not be rebuilt")

    monkeypatch.setattr("chrona.presentation.layout.surface_base.prepare_surface_slots", forbidden)
    actual = prepare_surface_base(request, allocation=allocation)
    for field in fields(expected):
        if field.name != "review_rows":
            assert getattr(actual, field.name) == getattr(expected, field.name), field.name
    # Legacy fallback rows are transient objects; compare every declared fact,
    # not their newly allocated object identities.
    for left, right in zip(actual.review_rows, expected.review_rows, strict=True):
        assert {name: getattr(left, name) for name in vars(type(left)) if not name.startswith("_")} == {
            name: getattr(right, name) for name in vars(type(right)) if not name.startswith("_")}
    assert actual.slots is allocation.slots


def test_prepared_inline_frame_reuses_mark_aware_scale_and_all_base_facts(monkeypatch):
    request = _request()
    allocation = prepare_surface_slots(request)
    expected = prepare_surface_base(request, allocation=allocation)
    inline = prepare_surface_inline(request, allocation=allocation)
    assert inline.scale == expected.scale
    assert inline.mark_band_allocation == expected.mark_band_allocation
    assert inline.slots is allocation.slots
    for left, right in zip(inline.review_rows, expected.review_rows, strict=True):
        assert {name: getattr(left, name) for name in vars(type(left)) if not name.startswith("_")} == {
            name: getattr(right, name) for name in vars(type(right)) if not name.startswith("_")}

    def forbidden(*args, **kwargs):
        pytest.fail("a supplied inline frame must not be prepared again")

    monkeypatch.setattr("chrona.presentation.layout.surface_base.prepare_surface_inline", forbidden)
    monkeypatch.setattr("chrona.presentation.layout.surface_base.prepare_surface_slots", forbidden)
    monkeypatch.setattr("chrona.presentation.layout.surface_base.required_row_block_extents", forbidden)
    actual = prepare_surface_base(request, inline=inline)
    for field in fields(expected):
        if field.name != "review_rows":
            assert getattr(actual, field.name) == getattr(expected, field.name), field.name
    for left, right in zip(actual.review_rows, expected.review_rows, strict=True):
        assert {name: getattr(left, name) for name in vars(type(left)) if not name.startswith("_")} == {
            name: getattr(right, name) for name in vars(type(right)) if not name.startswith("_")}


def test_natural_row_demand_is_closed_before_fill_and_not_recomputed_from_placed_rows():
    request = _request()
    inline = prepare_surface_inline(request)
    assert inline.row_requirements == (40.0,)
    assert inline.natural_block_requirement == Decimal(40)
    placed = prepare_surface_base(request, inline=inline)
    assert placed.rows[0].bounds.block_size == inline.timeline.bounds.block_size
    assert placed.rows[0].bounds.block_size > inline.natural_block_requirement
    assert inline.row_requirements == (40.0,)


def test_point_mark_inline_scale_closes_without_placing_any_shared_rows_or_tracks(monkeypatch):
    request = _request()
    point = replace(request.projection.items[0], source_type="point", planned={"at": date(2026, 1, 1)})
    request = replace(request, projection=replace(request.projection, items=(point,)))
    expected = prepare_surface_base(request)

    def forbidden(*args, **kwargs):
        pytest.fail("inline geometry must not place shared rows or tracks")

    monkeypatch.setattr("chrona.presentation.layout.surface_base.place_rows", forbidden)
    monkeypatch.setattr("chrona.presentation.layout.surface_base.place_mark_tracks", forbidden)
    monkeypatch.setattr("chrona.presentation.layout.surface_base.place_lane_mark_tracks", forbidden)
    inline = prepare_surface_inline(request)
    assert inline.scale == expected.scale
    assert inline.scale.range_start > float(inline.timeline.bounds.inline)
    assert inline.mark_band_allocation == expected.mark_band_allocation


def test_completed_row_viewport_changes_capacity_and_plot_without_rewriting_full_slots():
    request = _request()
    inline = prepare_surface_inline(request)
    full = inline.timeline.bounds
    viewport = Rect(full.inline, full.block + Decimal(30), full.inline_size, full.block_size - Decimal(30))
    placed = prepare_surface_base(request, inline=inline, row_viewport=viewport)
    assert placed.slots is inline.slots
    assert placed.timeline is inline.timeline
    assert placed.table is inline.table
    assert placed.by_source is inline.by_source
    assert placed.scale is inline.scale
    assert placed.rows[0].bounds.block == viewport.block
    assert placed.rows[-1].bounds.block + placed.rows[-1].bounds.block_size == full.block + full.block_size
    assert placed.plot == viewport
    assert all(track.block >= float(viewport.block) for track in placed.tracks)


def test_explicit_full_row_viewport_preserves_every_default_base_fact():
    request = _request()
    inline = prepare_surface_inline(request)
    expected = prepare_surface_base(request, inline=inline)
    actual = prepare_surface_base(request, inline=inline, row_viewport=inline.timeline.bounds)
    assert actual == expected


def test_below_plot_reserve_uses_content_capacity_not_the_full_slot(monkeypatch):
    request = _request()
    request = replace(request, surface_content=replace(
        request.surface_content, as_of=date(2026, 1, 2), as_of_label="As of", as_of_placement="below-plot"))
    monkeypatch.setattr("chrona.presentation.layout.surface_base.below_plot_reserve", lambda tokens: 20.0)
    inline = prepare_surface_inline(request)
    full = inline.timeline.bounds
    baseline = prepare_surface_base(request, inline=inline)
    assert baseline.as_of_foot_reserve == 20 and not baseline.as_of_foot_fallback
    viewport = Rect(full.inline, full.block + full.block_size - Decimal(50), full.inline_size, Decimal(50))
    placed = prepare_surface_base(request, inline=inline, row_viewport=viewport)
    assert placed.as_of_foot_reserve == 0 and placed.as_of_foot_fallback
    assert placed.slots is baseline.slots
    assert placed.rows[0].bounds.block == viewport.block


def test_heading_and_node_identity_do_not_change_full_source_allocations():
    request = _request()
    baseline = prepare_surface_slots(request)
    manifest = replace(request.layout_manifest, decisions=tuple(
        replace(decision, node_id=f"node-{decision.source}", heading=SlotHeading("Caption"))
        for decision in reversed(request.layout_manifest.decisions)))
    headed = prepare_surface_slots(replace(request, layout_manifest=manifest))
    assert headed.slots == baseline.slots
    assert tuple(decision.source for decision in headed.decisions) == tuple(
        sorted(decision.source for decision in manifest.decisions))
    assert all(decision.node_id.startswith("node-") for decision in headed.decisions)


def test_allocation_preserves_existing_manifest_and_missing_source_diagnostics():
    request = _request()
    with pytest.raises(LayoutError, match="E_PRESENTATION_LAYOUT_REQUIRED"):
        prepare_surface_slots(replace(request, layout_manifest=None))
    manifest = replace(request.layout_manifest, decisions=tuple(
        decision for decision in request.layout_manifest.decisions if decision.source != "timeline"))
    with pytest.raises(LayoutError, match="E_PRESENTATION_PRIMITIVE_MISSING"):
        prepare_surface_slots(replace(request, layout_manifest=manifest))


def test_pre_row_host_demand_uses_natural_rows_not_fill_expanded_capacity():
    request = _request()
    prepared = prepare_surface_content(request)
    placed = prepare_surface_base(request, inline=prepared.inline, row_viewport=prepared.row_viewport)
    assert prepared.required_timeline_block() == Decimal(40)
    assert prepared.required_timeline_block(foot_reserve=Decimal(20)) == Decimal(60)
    assert placed.rows[0].bounds.block_size > prepared.required_timeline_block()
    # A larger candidate may offer more surplus, but not larger natural demand.
    larger = replace(request, layout_manifest=replace(request.layout_manifest, decisions=tuple(
        replace(decision, bounds=replace(decision.bounds, block_size=decision.bounds.block_size + 500))
        if decision.source == "timeline" else decision for decision in request.layout_manifest.decisions)))
    assert prepare_surface_content(larger).required_timeline_block() == Decimal(40)


@pytest.mark.parametrize("headed", [("timeline",), ("table",), ("timeline-axis",),
                                    ("timeline", "table", "timeline-axis")])
def test_pre_row_host_demand_counts_the_native_prefix_once_from_full_timeline_origin(headed):
    from copy import deepcopy

    request = _request()
    theme = deepcopy(_theme())
    theme["body"]["roles"]["slot-heading"] = deepcopy(theme["body"]["roles"]["text"])
    content = surface_content(table_columns=(("name", "Name"),), table_cells=(("a", "name", "Activity"),),
                              axis_tiers=(AxisTier("month", 1, "labels", AxisLabelIntent(
                                  "long-month", (), "center", "thin-with-record", "horizontal", "en-US")),))
    manifest = replace(request.layout_manifest, decisions=tuple(
        replace(decision, heading=SlotHeading("Caption")) if decision.source in headed else decision
        for decision in request.layout_manifest.decisions))
    prepared = prepare_surface_content(replace(request, surface_content=content,
                                              presentation_contract=normalize_presentation_input(content),
                                              theme_tokens=ThemeTokenView(theme),
                                              layout_manifest=manifest))
    full = prepared.inline.timeline.bounds
    prefix = prepared.row_viewport.block - full.block
    assert prepared.headings.text
    assert prepared.table.header_text
    assert prepared.row_viewport.block >= prepared.table.header_end_block
    assert prepared.required_timeline_block(foot_reserve=Decimal(20)) == (
        max(Decimal(0), prefix) + prepared.inline.natural_block_requirement + 20)
    if "timeline" in headed:
        assert prefix >= prepared.headings.reserved("timeline")
        assert prepared.required_timeline_block() >= Decimal("66.6")


def test_empty_rows_do_not_gain_fill_expanded_natural_demand():
    request = _request()
    projection = replace(request.projection, items=())
    prepared = prepare_surface_content(replace(request, projection=projection))
    assert not prepared.headings.text
    assert prepared.headings.reserved("timeline") == 0
    assert prepared.required_timeline_block() == 0
