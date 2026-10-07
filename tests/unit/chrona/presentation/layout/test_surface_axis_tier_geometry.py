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
    AxisPlotGrid, SurfaceAxisFrame, complete_axis_plot, compose_axis, prepare_surface_axis,
)
from chrona.presentation.layout.surface_base import prepare_surface_base
from chrona.presentation.layout.surface_quality import SurfaceLayoutRequest
from chrona.presentation.model.presentation_contract import normalize_presentation_input
from chrona.presentation.model.surface_content import AxisLabelIntent, AxisTier
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.model.semantic_registry import semantic_binding
from tests.unit.chrona.presentation.scene import test_v05_builder as base


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


def test_surface_composer_completes_axis_and_captions_before_rows_and_only_then_plot_grids(monkeypatch):
    from chrona.presentation.layout import surface_composer

    request = _axis_request((
        AxisTier("month", 1, "grid-major"),
        AxisTier("month", 1, "labels", AxisLabelIntent(
            "long-month", (), "center", "thin-with-record", "horizontal", "en-US")),
    ))
    seen = []
    phases = ("prepare_surface_inline", "prepare_surface_axis", "complete_slot_headings",
              "prepare_surface_base", "complete_axis_plot")
    for name in phases:
        original = getattr(surface_composer, name)

        def observed(*args, _name=name, _original=original, **kwargs):
            seen.append(_name)
            if _name == "prepare_surface_base":
                assert kwargs["inline"] is not None
            return _original(*args, **kwargs)

        monkeypatch.setattr(surface_composer, name, observed)
    placement = surface_composer.compose_surface_layout(request).placement
    assert seen == list(phases)
    assert placement.rows
    assert any(shape.placement_id.startswith("axis-grid:") for shape in placement.shapes)


@pytest.mark.parametrize("block", ["top", "header-row", "axis-tier"])
def test_own_axis_caption_precedes_one_native_axis_solve_and_keeps_full_slot(block, monkeypatch):
    from chrona.presentation.layout import surface_composer

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
    original = surface_composer.prepare_surface_axis
    frames = []

    def observed(request, frame):
        frames.append(frame)
        return original(request, frame)

    monkeypatch.setattr(surface_composer, "prepare_surface_axis", observed)
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
