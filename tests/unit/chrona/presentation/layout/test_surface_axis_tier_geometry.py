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


def test_closed_pre_row_geometry_is_reused_without_another_native_preparation(monkeypatch):
    from chrona.presentation.layout import surface_composer
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
        monkeypatch.setattr(surface_composer, name, forbidden)
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


@pytest.mark.parametrize("headed", [("table",), ("timeline",), ("timeline-axis",),
                                     ("table", "timeline", "timeline-axis")])
@pytest.mark.parametrize("label_side", ["auto", "inside"])
def test_native_captions_close_one_shared_row_floor_from_actual_headers_and_axis(headed, label_side, monkeypatch):
    from chrona.presentation.layout import surface_composer

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
    seed_owner = surface_composer.prepare_table_header_seed
    seeds = []

    def observed(**kwargs):
        result = seed_owner(**kwargs)
        seeds.append(result)
        return result

    monkeypatch.setattr(surface_composer, "prepare_table_header_seed", observed)
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
