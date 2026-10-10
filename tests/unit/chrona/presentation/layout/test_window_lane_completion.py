"""Final Layout retains omitted rows and closes original lane mark emission."""
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_composer import compose_surface_layout
from chrona.presentation.layout.surface_lanes import preflight_fixed_lane_layout
from chrona.presentation.model.projection import WindowMode
from tests.unit.chrona.presentation.layout.test_lane_item_footprints import _window_footprint_fixture
from tests.unit.chrona.presentation.layout.test_surface_axis_tier_geometry import _axis_request


def _request(*, point=False, all_outside=False, containing=False, mode=WindowMode.EXPLICIT):
    projection, _, _ = _window_footprint_fixture(point=point, all_outside=all_outside, mode=mode)
    if containing:
        projection = replace(projection, window=(date(2026, 1, 1), date(2026, 1, 10)))
    request = _axis_request(())
    request = replace(request, projection=projection,
                   surface_content=replace(request.surface_content, show_member_labels=False),
                   mark_visibility_index=None)
    preflight = preflight_fixed_lane_layout(projection=projection, layout_manifest=request.layout_manifest,
        surface_content=request.surface_content, theme_tokens=request.theme_tokens,
        metric_values=request.measured_sources.metric_values, icon_assets=request.icon_assets,
        visual_requests=request.visual_requests, font_metrics=request.font_metrics)
    return replace(request, fixed_lane_preflight=preflight)


@pytest.mark.parametrize("point", [False, True])
def test_fully_omitted_lane_keeps_allocated_tracks_and_typed_absences_without_fake_marks(point):
    composed = compose_surface_layout(_request(point=point, all_outside=True))
    placement = composed.placement
    assert placement.marks == placement.lane_emissions == ()
    assert len(placement.lane_window_absences) == 2
    assert {item.member_id for item in placement.lane_window_absences} == {"item-1", "item-6"}
    assert len(composed.track_placements) == 2
    assert placement.rows[0].lane_mark_band_block == min(Decimal(str(track.block)) for track in composed.track_placements)
    placement.assert_valid()


def test_mixed_lane_completes_only_admitted_mark_and_preserves_visible_row_band():
    placement = compose_surface_layout(_request()).placement
    assert {mark.source_ref for mark in placement.marks} == {"object-4"}
    assert {item.member_id for item in placement.lane_window_absences} == {"item-1", "item-6"}
    assert placement.rows[0].lane_mark_band_block == min(mark.bounds.block for mark in placement.marks)


def test_containing_explicit_lane_keeps_derived_placement_identical():
    explicit = compose_surface_layout(_request(containing=True)).placement
    derived = compose_surface_layout(_request(containing=True, mode=WindowMode.SELECTED_PLANNED)).placement
    assert explicit == derived
    assert explicit.lane_window_absences == ()


def test_missing_visible_final_mark_is_not_excused_by_an_unrelated_window_absence(monkeypatch):
    import chrona.presentation.layout.surface_composer as composer
    original = composer.compose_surface_marks
    def incomplete(*args, **kwargs):
        batch = original(*args, **kwargs)
        return replace(batch, marks=())
    monkeypatch.setattr(composer, "compose_surface_marks", incomplete)
    with pytest.raises(LayoutError, match="final-emission-mismatch"):
        compose_surface_layout(_request())


def test_duplicate_visible_mark_is_not_a_complete_emission(monkeypatch):
    import chrona.presentation.layout.surface_composer as composer
    original = composer.complete_surface_layout
    def duplicate(context):
        return original(replace(context, marks=(*context.marks, *context.marks)))
    monkeypatch.setattr(composer, "complete_surface_layout", duplicate)
    with pytest.raises(LayoutError, match="final-emission-mismatch"):
        compose_surface_layout(_request())


def test_wholly_omitted_row_still_requires_its_real_allocated_tracks(monkeypatch):
    import chrona.presentation.layout.surface_composer as composer
    original = composer.complete_surface_layout
    monkeypatch.setattr(composer, "complete_surface_layout",
                        lambda context: original(replace(context, tracks=())))
    with pytest.raises(LayoutError, match="E_LAYOUT_LANE_ROW_ANCHOR_INVALID"):
        compose_surface_layout(_request(all_outside=True))
