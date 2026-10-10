"""Typed horizontal axis-tier geometry exists independently of retained interval labels (#1100)."""
from dataclasses import replace
from copy import deepcopy
from datetime import date
from decimal import Decimal

import pytest
from xml.etree import ElementTree

from chrona.presentation.layout.model import LayoutError, SlotHeading
from chrona.presentation.layout.slot_heading import content_slot

from chrona.presentation.layout.surface_axis import (
    AxisPlotGrid, SurfaceAxisFrame, axis_label_lane_geometry, complete_axis_plot, compose_axis,
    measure_axis_tier, measure_surface_axis, prepare_surface_axis, summarize_surface_axis_vertical,
)
from chrona.presentation.layout.surface_base import prepare_surface_base
from chrona.presentation.layout.surface_quality import SurfaceLayoutRequest
from chrona.presentation.model.presentation_contract import normalize_presentation_input
from chrona.presentation.model.surface_content import AxisLabelIntent, AxisSecondaryIntent, AxisTier
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.model.semantic_registry import semantic_binding
from tests.unit.chrona.presentation.scene import test_v05_builder as base


@pytest.mark.parametrize("orientation,rotation", [("horizontal", 0), ("rotate-cw", 90), ("rotate-ccw", -90)])
@pytest.mark.parametrize("scale", [1, 0.5])
@pytest.mark.parametrize("transform,advance", [("none", 2), ("uppercase", 12)])
def test_axis_run_bounds_measure_the_painted_glyph_at_one_compression(orientation, rotation, scale, transform, advance):
    from chrona.presentation.layout.surface_axis import _axis_text_run_geometry
    from chrona.presentation.layout.text import measured_text_bounds, scaled_metric
    from chrona.presentation.model.theme_tokens import TextTreatment

    class Font:
        def width(self, content, size):
            return sum(12 if char == "M" else 2 for char in content) * size

    treatment = TextTreatment("Test", 400, 10, 1, 0, transform, "proportional", horizontal_scale=scale)
    run = _axis_text_run_geometry(content="m", inline=20, baseline_block=30,
        treatment=treatment, metrics=scaled_metric(Font(), scale), orientation=orientation)

    assert run.content == "m"
    assert run.bounds == measured_text_bounds(inline=20, baseline_block=30,
        width=advance * 10 * scale, height=10, font_size=10, rotation=rotation)


def _axis_request(tiers):
    item = base.ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2027, 1, 1)}, None, None, ())
    projection = base.ReviewProjection((item,), (date(2026, 1, 1), date(2027, 1, 1)), (), ())
    measured = base.MeasuredSources({"title": base._title_measurement()}, {"title": base.SourceInput(("Plan",))},
                                    {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                     "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8),
                                     "timeline.mark.blockSize": Decimal(8)})
    content = base.surface_content(axis_tiers=tiers)
    value = base.build_scene_input(projection=projection, surface_content=content,
                                   layout_manifest=base._manifest("title", "table", "timeline", "timeline-axis"),
                                   resolved_theme=base._theme(), font_metrics=base._Font(), measured_sources=measured,
                                   capabilities={"svg": True})
    request = SurfaceLayoutRequest(
        projection=value.projection, presentation_contract=normalize_presentation_input(content),
        surface_content=content, layout_manifest=value.layout_manifest, measured_sources=value.measured_sources,
        theme_tokens=value.theme_tokens, font_metrics=value.font_metrics, capabilities=dict(value.capabilities))
    return request


def _axis_batch(tiers):
    prepared = prepare_surface_base(_axis_request(tiers))
    return compose_axis(prepared.request, prepared)


def test_equal_calendar_band_intervals_in_distinct_lanes_keep_both_label_tiers():
    tiers = (
        AxisTier("quarter", 1, "band"),
        AxisTier("quarter", 1, "labels", AxisLabelIntent(
            "quarter", (), "center", "visible-overflow", "horizontal", "en-US")),
        AxisTier("quarter", 1, "band"),
        AxisTier("quarter", 1, "labels", AxisLabelIntent(
            "year-quarter", (), "center", "visible-overflow", "horizontal", "en-US")),
    )
    _summary, prepared, _frame, _measured = _summary_matches_native(_axis_request(tiers))
    batch = prepared.placements
    bands = {shape.placement_id: shape for shape in batch.shapes}
    for tier_index, band_index in ((1, 0), (3, 2)):
        labels = [item for item in batch.text
                  if item.placement_id.startswith(f"axis-label:{tier_index}:")]
        assert len(labels) == 4
        for label in labels:
            index = label.placement_id.rsplit(":", 1)[1]
            assert label.host_placement_id == f"axis-band-rect:{band_index}:{index}"
            band = bands[label.host_placement_id].bounds
            assert band.block <= label.bounds.block
            assert label.bounds.block + label.bounds.block_size <= band.block + band.block_size
    assert not any(item.startswith("W_LAYOUT_AXIS_LABEL_THINNED") for item in batch.diagnostics)


@pytest.mark.parametrize("gap", [20, 30])
def test_painted_cell_gap_omits_secondary_or_thins_primary_without_visible_targets(gap):
    tiers = (AxisTier("month", 1, "band"), AxisTier("month", 1, "labels", AxisLabelIntent(
        "short-month", (), "center", "visible-overflow", "horizontal", "en-US",
        AxisSecondaryIntent("numeric-month", "en-US", "axisSecondary", "inline"))))
    request = _axis_request(tiers)
    theme = deepcopy(base._theme())
    theme["body"]["values"].update({
        "secondary-size": {"type": "number", "value": 8},
        "cell-gap": {"type": "number", "value": gap},
    })
    theme["body"]["roles"]["axis-band-decoration"]["cellGap"] = "cell-gap"
    theme["body"]["roles"]["axisSecondary"] = {
        "fontFamily": "body", "fontWeight": "regular", "fontSize": "secondary-size",
        "lineHeight": "line", "letterSpacing": "letter-spacing", "textTransform": "text-transform",
        "numericSpacing": "numeric-spacing",
    }
    batch = _axis_batch_for_request(replace(request, theme_tokens=ThemeTokenView(theme)))
    outcome = batch.tier_outcomes[1].intervals[1]
    assert not batch.visible_label_overflows
    if gap == 20:
        assert outcome.disposition == "placed"
        assert outcome.secondary_disposition == "omitted" and outcome.secondary_reason == "does-not-fit"
        assert outcome.candidate_id in {item.placement_id for item in batch.text}
        assert "axis-label-secondary:1:1" not in {item.placement_id for item in batch.text}
        assert "W_LAYOUT_AXIS_SECONDARY_OMITTED:axis-label:1:1:does-not-fit" in batch.diagnostics
    else:
        assert outcome.disposition == "thinned" and outcome.reason == "label-does-not-fit"
        assert outcome.candidate_id not in {item.placement_id for item in batch.text}
        assert outcome.candidate_id not in batch.label_targets.values()
        assert outcome.secondary_label is None and outcome.secondary_disposition is None


def _axis_batch_for_request(request):
    prepared = prepare_surface_base(request)
    return compose_axis(prepared.request, prepared)


def test_unpainted_band_keeps_logical_containment_without_inventing_a_host():
    tiers = (AxisTier("month", 1, "band"), AxisTier("month", 1, "labels", AxisLabelIntent(
        "long-month", (), "center", "visible-overflow", "horizontal", "en-US")))
    request = _axis_request(tiers)
    theme = deepcopy(base._theme())
    theme["body"]["roles"]["axis-band-decoration"]["backgroundTreatment"] = "none"
    request = replace(request, theme_tokens=ThemeTokenView(theme))
    _summary, prepared, _frame, _measured = _summary_matches_native(request)
    batch = prepared.placements
    assert batch.text and all(item.host_placement_id is None for item in batch.text)
    assert not any(item.placement_id.startswith("axis-band-rect:") for item in batch.shapes)
    september = next(item for item in batch.tier_outcomes[1].intervals if item.label == "September")
    assert september.disposition == "thinned"
    assert september.candidate_id not in batch.label_targets.values()
    assert not batch.visible_label_overflows


def _summary_matches_native(request, *, axis_block_size=None):
    base_geometry = prepare_surface_base(request)
    axis_slot = base_geometry.by_source["timeline-axis"]
    if axis_block_size is not None:
        axis_slot = replace(axis_slot, bounds=replace(axis_slot.bounds, block_size=axis_block_size))
    frame = SurfaceAxisFrame(base_geometry.scale, base_geometry.timeline, axis_slot,
                             base_geometry.metric_values)
    measured = measure_surface_axis(request, frame.scale)
    summary = summarize_surface_axis_vertical(request, frame, measured)
    prepared = prepare_surface_axis(request, frame, measured=measured)
    bounds = tuple(item.bounds for item in (*prepared.placements.shapes, *prepared.placements.text))
    expected_end = max((item.block + item.block_size for item in bounds), default=None)
    assert summary.max_rect_block_end == expected_end
    assert summary.label_tiers == prepared.placements.label_tiers
    return summary, prepared, frame, measured


def test_horizontal_tier_geometry_shares_the_placed_baseline_despite_thinned_months():
    tier = AxisTier("month", 1, "labels", AxisLabelIntent(
        "long-month", (), "center", "thin-with-record", "horizontal", "en-US"))

    batch = _axis_batch((tier,))

    assert len(batch.label_tiers) == 1
    geometry, = batch.label_tiers
    assert geometry.tier_index == 0
    assert geometry.bounds.inline_size > 0
    assert geometry.bounds.block_size > 0
    assert any(outcome.disposition == "thinned" for outcome in batch.tier_outcomes[0].intervals)
    placed = tuple(item for item in batch.text if item.placement_id.startswith("axis-label:0:"))
    assert placed
    assert all(item.baseline[1] == geometry.baseline_block for item in placed)


def test_pre_row_axis_closes_mixed_rotated_labels_and_defers_only_full_height_grid_endpoints():
    tiers = (
        AxisTier("quarter", 1, "band"),
        AxisTier("month", 1, "grid-major"),
        AxisTier("month", 1, "labels", AxisLabelIntent(
            "long-month", (), "center", "thin-with-record", "rotate-cw", "en-US")),
        AxisTier("quarter", 1, "grid-minor"),
        AxisTier("quarter", 1, "labels", AxisLabelIntent(
            "quarter", (), "center", "visible-overflow", "horizontal", "en-US")),
    )
    request = _axis_request(tiers)
    base_geometry = prepare_surface_base(request)
    frame = SurfaceAxisFrame(base_geometry.scale, base_geometry.timeline,
                             base_geometry.by_source["timeline-axis"], base_geometry.metric_values)
    prepared = prepare_surface_axis(request, frame)
    rotated_measurement = measure_axis_tier(request, base_geometry.scale, 2, tiers[2])
    # Width-only tier measurement cannot admit September's 54px rotated
    # block into this 48px axis host. Final geometry must thin that run.
    completed = prepared.placements.tier_outcomes[2]
    assert replace(completed, intervals=rotated_measurement.outcomes) == rotated_measurement.tier_outcome
    for before, after in zip(rotated_measurement.outcomes, completed.intervals, strict=True):
        if before.label == "September":
            assert before.disposition == "placed" and before.label_fits
            assert after.disposition == "thinned" and not after.label_fits
            assert after.reason == "label-does-not-fit"
            assert after.candidate_id not in {item.placement_id for item in prepared.placements.text}
            decision = next(item for item in prepared.placements.decisions
                            if item.decision_id == after.candidate_id)
            assert decision.requested_ladder == ("axis-cell-containment", "suppress")
            assert decision.selected_rung == "suppress" and decision.outcome == "suppressed"
        else:
            assert after == before
    assert set(rotated_measurement.diagnostics) <= set(prepared.placements.diagnostics)
    candidate_measurement = measure_surface_axis(request, base_geometry.scale)
    assert prepare_surface_axis(request, frame, measured=candidate_measurement) == prepared
    grids = tuple(shape for shape in prepared.ordered_shapes if isinstance(shape, AxisPlotGrid))
    assert grids
    assert not any(shape.placement_id.startswith("axis-grid:") for shape in prepared.placements.shapes)
    assert any(text.orientation == "rotate-cw" for text in prepared.placements.text)
    assert len(prepared.placements.label_tiers) == 1
    complete = complete_axis_plot(prepared, base_geometry.plot)
    assert complete == compose_axis(request, base_geometry)
    assert tuple(shape.placement_id for shape in complete.shapes) == tuple(
        shape.placement_id for shape in prepared.ordered_shapes)

    moved_plot = replace(base_geometry.plot, block=Decimal(300), block_size=Decimal(55))
    moved = complete_axis_plot(prepared, moved_plot)
    assert replace(moved, shapes=()) == replace(complete, shapes=())
    grid_ids = {grid.placement_id for grid in grids}
    for previous, current in zip(complete.shapes, moved.shapes, strict=True):
        if previous.placement_id in grid_ids:
            assert current.bounds.block == 300 and current.bounds.block_size == 55
            assert current.points == ((float(current.bounds.inline), 300.0),
                                      (float(current.bounds.inline), 355.0))
        else:
            assert current == previous


def test_rotated_label_lane_uses_measured_widths_and_returns_cursor():
    tier = AxisTier("month", 1, "labels", AxisLabelIntent(
        "long-month", (), "center", "thin-with-record", "rotate-cw", "en-US"))
    request = _axis_request((tier,))
    base_geometry = prepare_surface_base(request)
    measured = measure_axis_tier(request, base_geometry.scale, 0, tier)
    lane = axis_label_lane_geometry(tier_index=0, tier=tier, measured=measured,
                                    declared_lanes={}, running_offset=7.0)
    from chrona.presentation.layout.text import measure_text_width
    widths = tuple(measure_text_width(item.label or "", font_size=measured.axis_size,
        font_metrics=measured.metrics, letter_spacing=float(measured.treatment.letter_spacing),
        text_transform=measured.treatment.transform, numeric_spacing=measured.treatment.numeric_spacing)
        for item in measured.outcomes if item.disposition == "placed")
    assert lane.offset == 7.0
    assert lane.size == max(widths)
    assert lane.next_offset == lane.offset + lane.size
    assert lane.block > 0


def test_secondary_label_lane_uses_native_stacked_block_and_tolerance():
    tier = AxisTier("month", 1, "labels", AxisLabelIntent(
        "long-month", (), "center", "thin-with-record", "horizontal", "en-US",
        AxisSecondaryIntent("short-month", "en-US", "axisSecondary", "stacked")))
    request = _axis_request((tier,))
    theme = deepcopy(base._theme())
    theme["body"]["values"]["secondary-size"] = {"type": "number", "value": 8}
    theme["body"]["roles"]["axisSecondary"] = {
        "fontFamily": "body", "fontWeight": "regular", "fontSize": "secondary-size",
        "lineHeight": "line", "letterSpacing": "letter-spacing", "textTransform": "text-transform",
        "numericSpacing": "numeric-spacing",
    }
    request = replace(request, theme_tokens=ThemeTokenView(theme))
    base_geometry = prepare_surface_base(request)
    measured = measure_axis_tier(request, base_geometry.scale, 0, tier)
    lane = axis_label_lane_geometry(tier_index=0, tier=tier, measured=measured,
                                    declared_lanes={}, running_offset=0.0)
    from chrona.presentation.layout.axis_lanes import label_block
    from chrona.presentation.layout.surface_geometry import GEOMETRY_TOLERANCE
    assert lane.size == label_block(measured.treatment, measured.secondary) + float(GEOMETRY_TOLERANCE)
    assert lane.block == label_block(measured.treatment, measured.secondary)


def test_declared_label_lane_overrides_running_cursor_and_returns_declared_end():
    tier = AxisTier("quarter", 1, "labels", AxisLabelIntent(
        "quarter", (), "center", "thin-with-record", "horizontal", "en-US"))
    request = _axis_request((tier,))
    base_geometry = prepare_surface_base(request)
    measured = measure_axis_tier(request, base_geometry.scale, 0, tier)
    lane = axis_label_lane_geometry(tier_index=0, tier=tier, measured=measured,
                                    declared_lanes={0: (11.0, 22.0)}, running_offset=99.0)
    assert (lane.offset, lane.size, lane.next_offset) == (11.0, 22.0, 33.0)


@pytest.mark.parametrize("unit", ["auto", "rotate-cw"])
def test_cached_candidate_axis_measurement_matches_native_preparation(unit):
    label = AxisLabelIntent(
        None if unit == "auto" else "long-month",
        (("month", "long-month"), ("quarter", "quarter")) if unit == "auto" else (),
        "center", "thin-with-record", "horizontal" if unit == "auto" else unit, "en-US")
    tier = AxisTier("auto" if unit == "auto" else "month", 1, "labels", label)
    request = _axis_request((tier,))
    base_geometry = prepare_surface_base(request)
    frame = SurfaceAxisFrame(base_geometry.scale, base_geometry.timeline,
                             base_geometry.by_source["timeline-axis"], base_geometry.metric_values)
    expected = prepare_surface_axis(request, frame)
    measurement = measure_surface_axis(request, base_geometry.scale)
    actual = prepare_surface_axis(request, frame, measured=measurement)
    assert actual == expected


def test_cached_axis_preparation_does_not_remeasure_any_candidate_facts(monkeypatch):
    from chrona.presentation.layout import surface_axis

    tiers = (
        AxisTier("quarter", 1, "band"),
        AxisTier("month", 1, "labels", AxisLabelIntent(
            "long-month", (), "center", "thin-with-record", "rotate-cw", "en-US")),
    )
    request = _axis_request(tiers)
    base_geometry = prepare_surface_base(request)
    frame = SurfaceAxisFrame(base_geometry.scale, base_geometry.timeline,
                             base_geometry.by_source["timeline-axis"], base_geometry.metric_values)
    measured = measure_surface_axis(request, base_geometry.scale)
    expected = prepare_surface_axis(request, frame)

    def forbidden(*args, **kwargs):
        pytest.fail("cached candidate axis facts must be consumed without remeasurement")

    for name in ("measure_axis_tier", "plan_label_lanes", "plan_band_stack", "axis_label_lane_geometry"):
        monkeypatch.setattr(surface_axis, name, forbidden)
    assert prepare_surface_axis(request, frame, measured=measured) == expected


def test_surface_composer_completes_axis_and_captions_before_rows_and_only_then_plot_grids(monkeypatch):
    from chrona.presentation.layout import surface_composer
    from chrona.presentation.layout import surface_preparation

    request = _axis_request((
        AxisTier("month", 1, "grid-major"),
        AxisTier("month", 1, "labels", AxisLabelIntent(
            "long-month", (), "center", "thin-with-record", "horizontal", "en-US")),
    ))
    seen = []
    phases = ("prepare_surface_inline", "prepare_surface_axis", "complete_slot_headings",
              "prepare_surface_base", "complete_axis_plot")
    for name in phases:
        owner = surface_composer if name in {"prepare_surface_base", "complete_axis_plot"} else surface_preparation
        original = getattr(owner, name)

        def observed(*args, _name=name, _original=original, **kwargs):
            seen.append(_name)
            if _name == "prepare_surface_base":
                assert kwargs["inline"] is not None
            return _original(*args, **kwargs)

        monkeypatch.setattr(owner, name, observed)
    placement = surface_composer.compose_surface_layout(request).placement
    assert seen == list(phases)
    assert placement.rows
    assert any(shape.placement_id.startswith("axis-grid:") for shape in placement.shapes)


def test_closed_pre_row_geometry_is_reused_without_another_native_preparation(monkeypatch):
    from chrona.presentation.layout import surface_composer
    from chrona.presentation.layout import surface_preparation
    from chrona.presentation.renderers.v05_svg import render_v05_svg

    request = _axis_request((AxisTier("month", 1, "grid-major"), AxisTier("quarter", 1, "labels",
        AxisLabelIntent("quarter", (), "center", "thin-with-record", "horizontal", "en-US"))))
    prepared = surface_composer.prepare_surface_content(request)
    expected = surface_composer.compose_surface_layout(request, prepared=prepared)
    arguments = dict(projection=request.projection, surface_content=request.surface_content,
                     layout_manifest=request.layout_manifest, resolved_theme=base._theme(),
                     font_metrics=request.font_metrics, measured_sources=request.measured_sources,
                     capabilities={"svg": True}, viewport=(1000, 1000))
    expected_scene = base.compose_review_surface(base.build_scene_input(**arguments))
    expected_svg = render_v05_svg(expected_scene)
    scene_input = base.build_scene_input(**arguments, surface_preparation=prepared)
    assert scene_input.surface_preparation is prepared

    def forbidden(*args, **kwargs):
        pytest.fail("completed pre-row geometry must not be measured or allocated a second time")

    for name in ("prepare_surface_content", "prepare_surface_inline", "prepare_surface_axis",
                 "prepare_table_header_seed", "complete_slot_headings"):
        monkeypatch.setattr(surface_preparation, name, forbidden)
    assert surface_composer.compose_surface_layout(request, prepared=prepared) == expected
    scene = base.compose_review_surface(scene_input)
    assert scene == expected_scene
    assert render_v05_svg(scene) == expected_svg


def test_pre_row_geometry_exists_without_placing_any_rows_or_tracks(monkeypatch):
    from chrona.presentation.layout import surface_base, surface_composer

    def forbidden(*args, **kwargs):
        pytest.fail("natural sizing must never depend on already placed or fill-expanded rows")

    for name in ("place_rows", "place_mark_tracks", "place_lane_mark_tracks"):
        monkeypatch.setattr(surface_base, name, forbidden)
    prepared = surface_composer.prepare_surface_content(_axis_request((AxisTier("month", 1, "grid-major"),)))
    assert prepared.inline.review_rows
    assert prepared.axis.ordered_shapes
    assert prepared.row_viewport == prepared.inline.timeline.bounds


@pytest.mark.parametrize("block", ["top", "header-row", "axis-tier"])
def test_own_axis_caption_precedes_one_native_axis_solve_and_keeps_full_slot(block, monkeypatch):
    from chrona.presentation.layout import surface_composer, surface_preparation

    request = _axis_request((AxisTier("quarter", 1, "labels", AxisLabelIntent(
        "quarter", (), "center", "thin-with-record", "horizontal", "en-US")),))
    theme = deepcopy(base._theme())
    theme["body"]["roles"]["slot-heading"] = deepcopy(theme["body"]["roles"]["text"])
    request = replace(request, theme_tokens=ThemeTokenView(theme))
    manifest = replace(request.layout_manifest, decisions=tuple(
        replace(decision, heading=SlotHeading("Calendar", block=block))
        if decision.source == "timeline-axis" else decision
        for decision in request.layout_manifest.decisions))
    request = replace(request, layout_manifest=manifest)
    original = surface_preparation.prepare_surface_axis
    frames = []

    def observed(request, frame, **kwargs):
        frames.append(frame)
        return original(request, frame, **kwargs)

    monkeypatch.setattr(surface_preparation, "prepare_surface_axis", observed)
    result = surface_composer.compose_surface_layout(request)
    caption, = (text for text in result.placement.text
                if text.placement_id == "slot-heading:timeline-axis")
    assert len(frames) == 1
    full_axis = next(slot for slot in result.placement.slots if slot.source_ref == "timeline-axis")
    assert full_axis.bounds == next(decision.bounds for decision in manifest.decisions
                                    if decision.source == "timeline-axis")
    # text fallback: size14, line1.4, gap7 ->26.6 within the original48 allocation.
    assert frames[0].axis == content_slot(full_axis, Decimal("26.6"))
    assert caption.bounds.block == full_axis.bounds.block
    labels = [text for text in result.placement.text if text.placement_id.startswith("axis-label:")]
    assert labels
    assert all(text.bounds.block >= frames[0].axis.bounds.block for text in labels)
    # Exercise Scene projection and the actual adapter before schema admission is widened.
    from chrona.presentation.renderers.v05_svg import render_v05_svg
    scene = base.compose_review_surface(base.build_scene_input(
        projection=request.projection, surface_content=request.surface_content,
        layout_manifest=manifest, resolved_theme=theme, font_metrics=request.font_metrics,
        measured_sources=request.measured_sources, capabilities={"svg": True}, viewport=(1000, 1000)))
    svg = ElementTree.fromstring(render_v05_svg(scene))
    emitted = [node for node in svg.iter() if node.get("data-scene-id") == "slot-heading:timeline-axis"]
    assert len(emitted) == 1
    assert "".join(emitted[0].itertext()) == "Calendar"
    assert float(emitted[0].get("y")) == caption.baseline[1]


def test_axis_caption_keeps_existing_native_tick_capacity_guard():
    from chrona.presentation.layout.surface_composer import compose_surface_layout

    request = _axis_request((AxisTier("month", 1, "grid-major"),))
    theme = deepcopy(base._theme())
    theme["body"]["roles"]["slot-heading"] = deepcopy(theme["body"]["roles"]["text"])
    theme["body"]["values"]["tick-size"] = {"type": "number", "value": 30}
    theme["body"]["roles"][semantic_binding("axisGrid").scene_role]["tickLength"] = "tick-size"
    request = replace(request, theme_tokens=ThemeTokenView(theme))
    assert compose_surface_layout(request).placement.shapes  #30 fits the original48 allocation.
    request = replace(request, layout_manifest=replace(request.layout_manifest, decisions=tuple(
        replace(decision, heading=SlotHeading("Calendar")) if decision.source == "timeline-axis" else decision
        for decision in request.layout_manifest.decisions)))
    with pytest.raises(LayoutError, match="E_PRESENTATION_AXIS_OVERFLOW") as error:
        compose_surface_layout(request)
    assert error.value.path == "/view/body/axis/tiers/0"


@pytest.mark.parametrize("length", [None, 30, 100])
def test_tick_natural_requirement_is_measurable_before_candidate_capacity_admission(length):
    from chrona.presentation.layout.axis_lanes import axis_tick_requirement
    from chrona.presentation.layout.surface_axis import _axis_tick_length

    theme = deepcopy(base._theme())
    role = semantic_binding("axisGrid").scene_role
    if length is not None:
        theme["body"]["values"]["tick-size"] = {"type": "number", "value": length}
        theme["body"]["roles"][role]["tickLength"] = "tick-size"
    tokens = ThemeTokenView(theme)
    assert axis_tick_requirement(tokens, role, 2) == (None if length is None else Decimal(length))
    if length is None:
        assert _axis_tick_length(tokens, role, Decimal(1), 2) is None
    else:
        request = replace(_axis_request((AxisTier("month", 1, "grid-major"),)), theme_tokens=tokens)
        geometry = prepare_surface_base(request)
        capacity = measure_surface_axis(request, geometry.scale).capacity
        assert capacity.fits(geometry.by_source["timeline-axis"].bounds.block_size) is (length <= 48)
        with pytest.raises(LayoutError) as caught:
            _axis_tick_length(tokens, role, Decimal(1), 2)
        assert caught.value.diagnostic_id == "E_PRESENTATION_AXIS_OVERFLOW"
        assert caught.value.path == "/view/body/axis/tiers/2"
        assert caught.value.detail == f"tick-length:{role}"
        assert _axis_tick_length(tokens, role, Decimal(length), 2) == Decimal(length)
        if length > geometry.by_source["timeline-axis"].bounds.block_size:
            frame = SurfaceAxisFrame(geometry.scale, geometry.timeline,
                                    geometry.by_source["timeline-axis"], geometry.metric_values)
            measurement = measure_surface_axis(request, geometry.scale)
            with pytest.raises(LayoutError) as cached_error:
                prepare_surface_axis(request, frame, measured=measurement)
            with pytest.raises(LayoutError) as native_error:
                prepare_surface_axis(request, frame)
            assert (cached_error.value.diagnostic_id, cached_error.value.path, cached_error.value.detail) == (
                native_error.value.diagnostic_id, native_error.value.path, native_error.value.detail)


def test_axis_capacity_plan_keeps_exact_tick_band_and_secondary_comparators():
    from math import inf, nextafter

    from chrona.presentation.layout.surface_axis import AxisCapacityPlan
    from chrona.presentation.layout.surface_geometry import GEOMETRY_TOLERANCE

    tick = AxisCapacityPlan(((0, Decimal("10")),), (), (), ())
    assert not tick.fits(Decimal("9.999999"))
    assert tick.fits(Decimal("10"))

    band_end = 10.0
    band_boundary = band_end - float(GEOMETRY_TOLERANCE)
    band = AxisCapacityPlan((), ((0, band_end),), (), ())
    for block in (nextafter(band_boundary, -inf), band_boundary, nextafter(band_boundary, inf)):
        decimal_block = Decimal.from_float(block)
        assert band.fits(decimal_block) == (band_end <= float(decimal_block) + float(GEOMETRY_TOLERANCE))

    secondary_end = 10.0
    secondary = AxisCapacityPlan((), (), ((0, secondary_end),), ())
    for block in (nextafter(secondary_end, -inf), secondary_end, nextafter(secondary_end, inf)):
        decimal_block = Decimal.from_float(block)
        assert secondary.fits(decimal_block) == (secondary_end <= float(decimal_block))


@pytest.mark.parametrize("length", [0, -3])
def test_tick_requirement_keeps_invalid_declarations_separate_from_short_host(length):
    from chrona.presentation.layout.axis_lanes import axis_tick_requirement

    theme = deepcopy(base._theme())
    role = semantic_binding("axisGrid").scene_role
    theme["body"]["values"]["tick-size"] = {"type": "number", "value": length}
    theme["body"]["roles"][role]["tickLength"] = "tick-size"
    with pytest.raises(LayoutError) as caught:
        axis_tick_requirement(ThemeTokenView(theme), role, 2)
    assert caught.value.diagnostic_id == "E_PRESENTATION_AXIS_INVALID"
    assert caught.value.path == "/view/body/axis/tiers/2"


def test_band_natural_measurement_precedes_but_does_not_bypass_strict_candidate_admission():
    from chrona.presentation.layout.axis_lanes import derived_axis_block_size
    from chrona.presentation.layout.surface_composer import prepare_surface_candidate

    request = _axis_request((AxisTier("quarter", 1, "band"), AxisTier("month", 1, "band")))
    natural = derived_axis_block_size(request.surface_content.axis_tiers,
                                     request.theme_tokens, request.font_metrics)
    assert natural > Decimal(10)
    for height in (Decimal(1), Decimal(10), natural):
        candidate = replace(request, layout_manifest=replace(request.layout_manifest, decisions=tuple(
            replace(item, bounds=replace(item.bounds, block_size=height))
            if item.source == "timeline-axis" else item for item in request.layout_manifest.decisions)))
        if height < natural:
            with pytest.raises(LayoutError) as caught:
                prepare_surface_candidate(candidate)
            assert caught.value.diagnostic_id == "E_PRESENTATION_AXIS_OVERFLOW"
            assert caught.value.path == "/view/body/axis/tiers/0"
        else:
            assert prepare_surface_candidate(candidate).axis.placements.shapes


def test_tier_measurement_is_available_before_tiny_multiband_host_rejection():
    tiers = (AxisTier("year", 1, "band"), AxisTier("quarter", 1, "band"))
    request = _axis_request(tiers)
    base_geometry = prepare_surface_base(request)
    measurement = measure_surface_axis(request, base_geometry.scale)
    assert not measurement.capacity.fits(Decimal(1))
    frame = SurfaceAxisFrame(base_geometry.scale, base_geometry.timeline,
                             replace(base_geometry.by_source["timeline-axis"],
                                     bounds=replace(base_geometry.by_source["timeline-axis"].bounds,
                                                    block_size=Decimal(1))),
                             base_geometry.metric_values)
    measured = tuple(measure_axis_tier(request, base_geometry.scale, index, tier)
                     for index, tier in enumerate(tiers))
    assert tuple(item.tier_outcome.tier_index for item in measured) == (0, 1)
    assert all(item.intervals for item in measured)
    measurement = measure_surface_axis(request, base_geometry.scale)
    with pytest.raises(LayoutError) as caught:
        prepare_surface_axis(request, frame, measured=measurement)
    assert caught.value.diagnostic_id == "E_PRESENTATION_AXIS_OVERFLOW"
    assert caught.value.path == "/view/body/axis/tiers/0"
    assert caught.value.detail == "band-lane:0"
    with pytest.raises(LayoutError) as native:
        prepare_surface_axis(request, frame)
    assert (native.value.diagnostic_id, native.value.path, native.value.detail) == (
        caught.value.diagnostic_id, caught.value.path, caught.value.detail)


def test_measurement_preserves_secondary_selection_consumed_by_strict_axis_preparation():
    tier = AxisTier("month", 1, "labels", AxisLabelIntent(
        "long-month", (), "center", "thin-with-record", "horizontal", "en-US",
        AxisSecondaryIntent("short-month", "en-US", "axisSecondary", "stacked")))
    request = _axis_request((tier,))
    theme = deepcopy(base._theme())
    theme["body"]["values"]["secondary-size"] = {"type": "number", "value": 8}
    theme["body"]["roles"]["axisSecondary"] = {
        "fontFamily": "body", "fontWeight": "regular", "fontSize": "secondary-size",
        "lineHeight": "line", "letterSpacing": "letter-spacing", "textTransform": "text-transform",
        "numericSpacing": "numeric-spacing",
    }
    request = replace(request, theme_tokens=ThemeTokenView(theme))
    base_geometry = prepare_surface_base(request)
    measured = measure_axis_tier(request, base_geometry.scale, 0, tier)
    frame = SurfaceAxisFrame(base_geometry.scale, base_geometry.timeline,
                             base_geometry.by_source["timeline-axis"], base_geometry.metric_values)
    prepared = prepare_surface_axis(request, frame)
    assert measured.secondary is not None
    assert measured.tier_outcome == prepared.placements.tier_outcomes[0]
    assert any(item.secondary_disposition == "placed" for item in measured.outcomes)
    candidate_measurement = measure_surface_axis(request, base_geometry.scale)
    assert prepare_surface_axis(request, frame, measured=candidate_measurement) == prepared


def test_secondary_declared_lane_mismatch_is_a_fixed_capacity_failure():
    tier = AxisTier("month", 1, "labels", AxisLabelIntent(
        "long-month", (), "center", "thin-with-record", "horizontal", "en-US",
        AxisSecondaryIntent("short-month", "en-US", "axisSecondary", "stacked")))
    request = _axis_request((tier,))
    theme = deepcopy(base._theme())
    theme["body"]["values"]["secondary-size"] = {"type": "number", "value": 8}
    theme["body"]["values"]["axis-lane"] = {"type": "number", "value": 1}
    theme["body"]["roles"]["axisSecondary"] = {
        "fontFamily": "body", "fontWeight": "regular", "fontSize": "secondary-size",
        "lineHeight": "line", "letterSpacing": "letter-spacing", "textTransform": "text-transform",
        "numericSpacing": "numeric-spacing",
    }
    theme["body"]["roles"]["axis"]["laneBlockSize"] = "axis-lane"
    request = replace(request, theme_tokens=ThemeTokenView(theme))
    base_geometry = prepare_surface_base(request)
    measurement = measure_surface_axis(request, base_geometry.scale)
    assert measurement.capacity.declared_secondary_mismatches == (0,)
    assert not measurement.capacity.fits(Decimal(100))
    frame = SurfaceAxisFrame(base_geometry.scale, base_geometry.timeline,
                             base_geometry.by_source["timeline-axis"], base_geometry.metric_values)
    with pytest.raises(LayoutError) as caught:
        prepare_surface_axis(request, frame, measured=measurement)
    assert caught.value.diagnostic_id == "E_PRESENTATION_AXIS_OVERFLOW"
    assert caught.value.path == "/view/body/axis/tiers/0"
    assert caught.value.detail == "secondary-lane:0"
    with pytest.raises(LayoutError) as native:
        prepare_surface_axis(request, frame)
    assert (native.value.diagnostic_id, native.value.path, native.value.detail) == (
        caught.value.diagnostic_id, caught.value.path, caught.value.detail)


def test_undeclared_secondary_capacity_follows_rotated_label_lane_offset():
    from math import inf, nextafter

    tiers = (
        AxisTier("month", 1, "labels", AxisLabelIntent(
            "long-month", (), "center", "thin-with-record", "rotate-cw", "en-US")),
        AxisTier("quarter", 1, "labels", AxisLabelIntent(
            "quarter", (), "center", "thin-with-record", "horizontal", "en-US",
            AxisSecondaryIntent("quarter", "en-US", "axisSecondary", "stacked"))),
    )
    request = _axis_request(tiers)
    theme = deepcopy(base._theme())
    theme["body"]["values"]["secondary-size"] = {"type": "number", "value": 8}
    theme["body"]["roles"]["axisSecondary"] = {
        "fontFamily": "body", "fontWeight": "regular", "fontSize": "secondary-size",
        "lineHeight": "line", "letterSpacing": "letter-spacing", "textTransform": "text-transform",
        "numericSpacing": "numeric-spacing",
    }
    request = replace(request, theme_tokens=ThemeTokenView(theme))
    base_geometry = prepare_surface_base(request)
    measurement = measure_surface_axis(request, base_geometry.scale)
    lanes = dict(measurement.label_lanes)
    assert lanes[0].offset == 0.0
    assert lanes[1].offset == lanes[0].next_offset
    secondary_end = dict(measurement.capacity.secondary_lane_ends)[1]
    assert secondary_end == lanes[1].offset + lanes[1].size
    boundary = Decimal.from_float(secondary_end)
    assert measurement.capacity.fits(boundary)
    below = Decimal.from_float(nextafter(secondary_end, -inf))
    assert not measurement.capacity.fits(below)


def test_vertical_summary_matches_transformed_compressed_rotated_and_secondary_text_bounds():
    tiers = (
        AxisTier("month", 1, "labels", AxisLabelIntent(
            "long-month", (), "center", "thin-with-record", "rotate-cw", "en-US")),
        AxisTier("quarter", 1, "labels", AxisLabelIntent(
            "quarter", (), "center", "thin-with-record", "horizontal", "en-US",
            AxisSecondaryIntent("quarter", "en-US", "axisSecondary", "stacked"))),
    )
    request = _axis_request(tiers)
    class _SpacingFont:
        content_identity = "sha256:test-spacing"

        def width(self, value, size, *, letter_spacing=0):
            return len(value) * size / 2 + max(0, len(value) - 1) * letter_spacing

    request = replace(request, font_metrics=_SpacingFont())
    theme = deepcopy(base._theme())
    theme["body"]["values"]["text-transform"] = {"type": "textTransform", "value": "uppercase"}
    theme["body"]["values"]["letter-spacing"] = {"type": "number", "value": "0.75"}
    theme["body"]["values"]["horizontal-scale"] = {"type": "number", "value": "0.8"}
    theme["body"]["values"]["secondary-size"] = {"type": "number", "value": 8}
    theme["body"]["roles"]["axis"].update({
        "textTransform": "text-transform", "letterSpacing": "letter-spacing",
        "horizontalScale": "horizontal-scale"})
    theme["body"]["roles"]["axisSecondary"] = {
        **theme["body"]["roles"]["axis"], "fontSize": "secondary-size"}
    theme["body"]["roles"].pop("axis-rule", None)
    theme["body"]["roles"].pop("axis-cell-separator", None)
    request = replace(request, theme_tokens=ThemeTokenView(theme))
    summary, prepared, _frame, _measurement = _summary_matches_native(request, axis_block_size=Decimal(200))
    assert summary.label_tiers
    assert any(item.orientation == "rotate-cw" for item in prepared.placements.text)
    assert any(item.placement_id.startswith("axis-label-secondary:") for item in prepared.placements.text)
    assert all(item.horizontal_scale == 0.8 for item in prepared.placements.text)


@pytest.mark.parametrize("shared", [False, True])
def test_vertical_summary_matches_painted_multi_band_and_shared_band_rects(shared):
    if shared:
        tiers = (
            AxisTier("quarter", 1, "band"),
            AxisTier("quarter", 1, "labels", AxisLabelIntent(
                "quarter", (), "center", "thin-with-record", "horizontal", "en-US")),
            AxisTier("year", 1, "band"),
        )
    else:
        tiers = (AxisTier("quarter", 1, "band"), AxisTier("year", 1, "band"))
    request = _axis_request(tiers)
    if shared:
        theme = deepcopy(base._theme())
        theme["body"]["values"]["axis-lane"] = {"type": "number", "value": 18}
        theme["body"]["roles"]["axis"]["laneBlockSize"] = "axis-lane"
        request = replace(request, theme_tokens=ThemeTokenView(theme))
    summary, prepared, _frame, _measurement = _summary_matches_native(request)
    assert summary.max_rect_block_end is not None
    assert any(item.semantic_id in {"axisBandDecoration", "axisBandDecoration2"}
               for item in prepared.placements.shapes)


def test_vertical_summary_matches_tick_separator_and_rule_rects_but_not_deferred_full_grid():
    tiers = (
        AxisTier("month", 1, "grid-major"),
        AxisTier("month", 1, "labels", AxisLabelIntent(
            "long-month", (), "center", "thin-with-record", "horizontal", "en-US")),
    )
    request = _axis_request(tiers)
    theme = deepcopy(base._theme())
    theme["body"]["values"]["tick-size"] = {"type": "number", "value": 18}
    role = semantic_binding("axisGrid").scene_role
    theme["body"]["roles"][role]["tickLength"] = "tick-size"
    theme["body"]["roles"]["axis-cell-separator"] = {"stroke": "ink"}
    theme["body"]["roles"]["axis-rule"] = {"stroke": "ink"}
    summary, prepared, _frame, _measurement = _summary_matches_native(
        replace(request, theme_tokens=ThemeTokenView(theme)))
    assert summary.max_rect_block_end is not None
    assert any(item.placement_id.startswith("axis-grid:") for item in prepared.placements.shapes)
    assert any(item.placement_id.startswith("axis-separator:") for item in prepared.placements.shapes)
    assert any(item.placement_id == "axis-rule" for item in prepared.placements.shapes)

    deferred = _axis_request((AxisTier("month", 1, "grid-major"),))
    theme = deepcopy(base._theme())
    theme["body"]["roles"].pop("axis-rule", None)
    theme["body"]["roles"].pop("axis-cell-separator", None)
    deferred = replace(deferred, theme_tokens=ThemeTokenView(theme))
    summary, prepared, _frame, _measurement = _summary_matches_native(deferred)
    assert summary.max_rect_block_end is None
    assert prepared.ordered_shapes
    assert not prepared.placements.shapes


def test_vertical_summary_ignores_unpainted_bands_and_succeeds_for_tiny_host():
    request = _axis_request((AxisTier("quarter", 1, "band"),))
    theme = deepcopy(base._theme())
    role = semantic_binding("axisBandDecoration").scene_role
    theme["body"]["roles"][role]["backgroundTreatment"] = "none"
    theme["body"]["roles"].pop("axis-rule", None)
    theme["body"]["roles"].pop("axis-cell-separator", None)
    request = replace(request, theme_tokens=ThemeTokenView(theme))
    summary, prepared, _frame, _measurement = _summary_matches_native(request)
    assert summary.max_rect_block_end is None
    assert not any(item.placement_id.startswith("axis-band-rect:") for item in prepared.placements.shapes)

    tiny = _axis_request((AxisTier("quarter", 1, "band"), AxisTier("month", 1, "band")))
    base_geometry = prepare_surface_base(tiny)
    frame = SurfaceAxisFrame(base_geometry.scale, base_geometry.timeline,
                             replace(base_geometry.by_source["timeline-axis"],
                                     bounds=replace(base_geometry.by_source["timeline-axis"].bounds,
                                                    block_size=Decimal(1))),
                             base_geometry.metric_values)
    measured = measure_surface_axis(tiny, frame.scale)
    summary = summarize_surface_axis_vertical(tiny, frame, measured)
    assert summary.max_rect_block_end is not None
    with pytest.raises(LayoutError) as caught:
        prepare_surface_axis(tiny, frame, measured=measured)
    assert caught.value.diagnostic_id == "E_PRESENTATION_AXIS_OVERFLOW"
    assert caught.value.path == "/view/body/axis/tiers/0"
    assert caught.value.detail == "band-lane:0"


@pytest.mark.parametrize("headed", [("table",), ("timeline",), ("timeline-axis",),
                                     ("table", "timeline", "timeline-axis")])
@pytest.mark.parametrize("label_side", ["auto", "inside"])
def test_native_captions_close_one_shared_row_floor_from_actual_headers_and_axis(headed, label_side, monkeypatch):
    from chrona.presentation.layout import surface_composer, surface_preparation

    request = _axis_request((AxisTier("month", 1, "grid-major"), AxisTier("quarter", 1, "labels",
        AxisLabelIntent("quarter", (), "center", "thin-with-record", "horizontal", "en-US"))))
    content = base.surface_content(table_columns=(("name", "Name"),), table_cells=(("a", "name", "Activity"),),
                                   axis_tiers=request.surface_content.axis_tiers,
                                   show_member_labels=True, label_placement="plot", label_content=("title",),
                                   label_side=label_side, label_overflow="suppress")
    theme = deepcopy(base._theme())
    theme["body"]["roles"]["slot-heading"] = deepcopy(theme["body"]["roles"]["text"])
    theme["body"]["values"]["large-header"] = {"type": "number", "value": 40}
    theme["body"]["roles"]["tableColumnLabel"] = {
        **theme["body"]["roles"]["text"], "fontSize": "large-header"}
    manifest = replace(request.layout_manifest, row_distribution="pack", decisions=tuple(
        replace(decision, heading=SlotHeading(f"Caption {decision.source}"))
        if decision.source in headed else decision for decision in request.layout_manifest.decisions))
    request = replace(request, surface_content=content, presentation_contract=normalize_presentation_input(content),
                      theme_tokens=ThemeTokenView(theme), layout_manifest=manifest,
                      measured_sources=replace(request.measured_sources, metric_values={
                          **request.measured_sources.metric_values, "timeline.mark.blockSize": Decimal(20)}))
    seed_owner = surface_preparation.prepare_table_header_seed
    seeds = []

    def observed(**kwargs):
        result = seed_owner(**kwargs)
        seeds.append(result)
        return result

    monkeypatch.setattr(surface_preparation, "prepare_table_header_seed", observed)
    domains = []
    for name in ("SurfaceMemberLabelContext", "SurfaceRoutesContext", "SurfaceAnnotationContext"):
        original = getattr(surface_composer, name)

        def observed_context(*args, _original=original, _name=name, **kwargs):
            context = _original(*args, **kwargs)
            domains.append((_name, context))
            return context

        monkeypatch.setattr(surface_composer, name, observed_context)
    placed = surface_composer.compose_surface_layout(request).placement
    assert len(seeds) == 1
    header, = (text for text in placed.text if text.placement_id == "column:name")
    assert header.bounds == seeds[0].header_text[0].bounds
    assert header.baseline == seeds[0].header_text[0].baseline
    full_timeline = next(slot for slot in placed.slots if slot.source_ref == "timeline")
    expected = max(full_timeline.bounds.block + (Decimal("26.6") if "timeline" in headed else 0),
                   header.bounds.block + header.bounds.block_size,
                   *(text.bounds.block + text.bounds.block_size for text in placed.text
                     if text.placement_id.startswith("axis-label:")))
    assert float(placed.rows[0].bounds.block) == float(expected)
    assert {name for name, _ in domains} == {
        "SurfaceMemberLabelContext", "SurfaceRoutesContext", "SurfaceAnnotationContext"}
    assert all(context.timeline_bounds[1] == float(expected) for _, context in domains)
    annotations = next(context for name, context in domains if name == "SurfaceAnnotationContext")
    assert float(annotations.timeline.bounds.block) == float(expected)
    assert annotations.by_source["timeline"].bounds == annotations.timeline.bounds
    assert not any(warning.placement_id == "column:name" for warning in placed.fit_warnings)
    assert all(mark.bounds.block >= expected for mark in placed.marks)
    assert all(text.bounds.block >= expected for text in placed.text if text.placement_id.startswith("cell:"))
    labels = [text for text in placed.text if text.placement_id.startswith("member-label:")
              and text.overflow != "suppressed"]
    if label_side == "inside":
        assert labels
    assert all(text.bounds.block >= expected for text in labels)
    assert {text.source_ref for text in placed.text if text.placement_id.startswith("slot-heading:")} == set(headed)
    for decision in manifest.decisions:
        assert next(slot for slot in placed.slots if slot.source_ref == decision.source).bounds == decision.bounds
    grids = [shape for shape in placed.shapes if shape.placement_id.startswith("axis-grid:")]
    assert grids and all(float(shape.bounds.block) == float(expected) for shape in grids)
    from chrona.presentation.renderers.v05_svg import render_v05_svg
    scene = base.compose_review_surface(base.build_scene_input(
        projection=request.projection, surface_content=content, layout_manifest=manifest,
        resolved_theme=theme, font_metrics=request.font_metrics, measured_sources=request.measured_sources,
        capabilities={"svg": True}, viewport=(1000, 1000)))
    svg = ElementTree.fromstring(render_v05_svg(scene))
    emitted = {node.get("data-scene-id"): node for node in svg.iter() if node.get("data-scene-id")}
    assert {key for key in emitted if key.startswith("slot-heading:")} == {
        f"slot-heading:{source}" for source in headed}
    assert float(emitted["column:name"].get("y")) == round(header.baseline[1], 3)
    cell = next(text for text in placed.text if text.placement_id == "cell:a:name")
    assert float(emitted["cell:a:name"].get("y")) == round(cell.baseline[1], 3)
