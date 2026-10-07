"""Full allocation is immutable and reusable before any native geometry is closed."""
from dataclasses import FrozenInstanceError, fields, replace
from datetime import date
from decimal import Decimal

import pytest

from chrona.presentation.layout.model import LayoutError, SlotHeading
from chrona.presentation.layout.sources import MeasuredSources, SourceInput
from chrona.presentation.layout.surface_base import (
    prepare_surface_base, prepare_surface_inline, prepare_surface_slots,
)
from chrona.presentation.layout.surface_quality import SurfaceLayoutRequest
from chrona.presentation.model.projection import ReviewItem, ReviewProjection
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
    return SurfaceLayoutRequest(
        projection=projection, surface_content=surface_content(),
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
    actual = prepare_surface_base(request, inline=inline)
    for field in fields(expected):
        if field.name != "review_rows":
            assert getattr(actual, field.name) == getattr(expected, field.name), field.name
    for left, right in zip(actual.review_rows, expected.review_rows, strict=True):
        assert {name: getattr(left, name) for name in vars(type(left)) if not name.startswith("_")} == {
            name: getattr(right, name) for name in vars(type(right)) if not name.startswith("_")}


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
