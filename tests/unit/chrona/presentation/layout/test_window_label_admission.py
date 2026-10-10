"""Independent original-endpoint and immutable label-cache oracles."""
from dataclasses import replace
from datetime import date

import pytest

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_mark_visibility import (
    MarkOccurrenceKind, build_item_mark_visibility_index,
)
from chrona.presentation.model.projection import ReviewItem, ReviewProjection, WindowMode
from chrona.presentation.layout.window_label_admission import WindowLabelAdmission, complete_window_label_admission
from tests.unit.chrona.presentation.layout.test_lane_item_footprints import _window_footprint_fixture


def _cache(*, finish=None, point=None, mode=WindowMode.EXPLICIT, source_kind="primary"):
    planned = {"at": date(2026, 1, point)} if point is not None else {
        "start": date(2026, 1, 1), "end": date(2026, 1, 11)}
    actual = {"start": date(2026, 1, 1), "finish": date(2026, 1, finish)} if finish else None
    item = ReviewItem("object", "Title", "point" if point is not None else "span",
                      planned, actual, None, ("planned",), item_id="item", source_kind=source_kind)
    projection = ReviewProjection((item,), (date(2026, 1, 5), date(2026, 1, 9)), (), (),
                                  window_mode=mode)
    index = build_item_mark_visibility_index(projection, as_of=None)
    occurrence = next(iter(index.entries))
    return item, projection, index, occurrence


@pytest.mark.parametrize("finish,outside", [(5, True), (6, False), (9, False), (10, True)])
def test_delta_admission_uses_original_actual_finish_not_clipped_host_finish(finish, outside):
    item, projection, index, occurrence = _cache(finish=finish)
    result = index.lookup_label(occurrence, projection=projection, as_of=None)
    assert result.host_facet == "planned" and not result.host_outside
    assert result.delta_anchor == date(2026, 1, finish)
    assert result.delta_anchor_facet == "actual"
    assert result.delta_outside is outside
    assert item.actual["finish"] == date(2026, 1, finish)


def test_delta_without_actual_finish_uses_original_plan_end_not_window_cut():
    _, projection, index, occurrence = _cache()
    result = index.lookup_label(occurrence, projection=projection, as_of=None)
    assert result.delta_anchor == date(2026, 1, 11)
    assert result.delta_anchor_facet == "planned" and result.delta_outside
    assert not result.host_outside


@pytest.mark.parametrize("point,outside", [(4, True), (5, False), (8, False), (9, True)])
def test_point_anchor_and_host_obey_half_open_window(point, outside):
    _, projection, index, occurrence = _cache(point=point)
    result = index.lookup_label(occurrence, projection=projection, as_of=None)
    assert result.host_outside is result.delta_outside is outside


def test_derived_window_never_changes_label_admission():
    _, projection, index, occurrence = _cache(mode=WindowMode.SELECTED_PLANNED)
    result = index.lookup_label(occurrence, projection=projection, as_of=None)
    assert not result.host_outside and not result.delta_outside
    assert result.delta_anchor == date(2026, 1, 11)


def test_lane_source_and_final_aliases_share_identical_label_admission_objects():
    projection, index, _ = _window_footprint_fixture()
    assert set(index.label_entries) == set(index.entries)
    for source in index.entries:
        if source.kind != MarkOccurrenceKind.LANE_SOURCE:
            continue
        alias = next(key for key in index.entries if key.kind == MarkOccurrenceKind.LANE_FINAL
                     and key.item_id == source.item_id and key.object_id == source.object_id)
        assert index.lookup_label(source, projection=projection, as_of=None) is index.lookup_label(
            alias, projection=projection, as_of=None)
    with pytest.raises(TypeError):
        index.label_entries[source] = None


def test_missing_or_stale_label_cache_fails_closed():
    _, projection, index, occurrence = _cache()
    missing = replace(index, label_entries={})
    with pytest.raises(LayoutError, match="missing-cache-entry"):
        missing.lookup_label(occurrence, projection=projection, as_of=None)
    with pytest.raises(LayoutError, match="request-mismatch"):
        index.lookup_label(occurrence, projection=replace(projection), as_of=None)


def test_non_temporal_missing_actual_host_is_not_excused_as_window_omission():
    item, projection, index, occurrence = _cache()
    original = index.entries[occurrence]
    visibility = replace(original, selection=replace(original.selection, source_kind="actual"), facets=())
    result = complete_window_label_admission(item, visibility,
        window_mode=projection.window_mode, window=projection.window)
    assert result.host_facet == "actual" and not result.host_outside


@pytest.mark.parametrize("changes", [
    {"host_outside": 1}, {"delta_anchor": None}, {"delta_anchor_facet": "cut"},
])
def test_invalid_original_anchor_facts_are_rejected(changes):
    with pytest.raises(LayoutError, match="invalid-original-anchor"):
        replace(WindowLabelAdmission("planned", False, "planned", date(2026, 1, 11), True), **changes)
