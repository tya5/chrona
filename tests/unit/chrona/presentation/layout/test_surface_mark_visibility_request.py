from dataclasses import replace
from datetime import date
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_base import prepare_surface_base, prepare_surface_inline
from chrona.presentation.layout.surface_mark_visibility import (
    ItemMarkVisibilityIndex, ensure_request_mark_visibility_index,
)
from chrona.presentation.layout.surface_composer import prepare_surface_natural_candidate
from chrona.presentation.layout.surface_quality import Rect
from chrona.presentation.layout.lane_projection import folded_instance_id
from chrona.presentation.layout.surface_marks import compose_surface_marks
from tests.unit.chrona.presentation.layout.test_surface_axis_tier_geometry import _axis_request


def test_request_index_is_created_once_and_carried_by_immutable_replacements():
    request = _axis_request(())
    prepared = ensure_request_mark_visibility_index(request)

    assert isinstance(prepared.mark_visibility_index, ItemMarkVisibilityIndex)
    assert ensure_request_mark_visibility_index(prepared) is prepared
    changed_unrelated = replace(prepared, capabilities={"svg": True})
    assert ensure_request_mark_visibility_index(changed_unrelated).mark_visibility_index is (
        prepared.mark_visibility_index)


@pytest.mark.parametrize("change", ["projection", "as_of"])
def test_cached_index_rejects_stale_projection_or_as_of(change):
    request = _axis_request(())
    prepared = ensure_request_mark_visibility_index(request)
    if change == "projection":
        stale = replace(prepared, projection=replace(prepared.projection))
    else:
        stale = replace(prepared, surface_content=SimpleNamespace(as_of=date(2026, 1, 2)))

    with pytest.raises(LayoutError, match="E_LAYOUT_WINDOW_CLIP"):
        ensure_request_mark_visibility_index(stale)


def test_direct_inline_prepares_index_after_validating_window():
    request = _axis_request(())
    assert request.mark_visibility_index is None

    inline = prepare_surface_inline(request)

    assert isinstance(inline.request.mark_visibility_index, ItemMarkVisibilityIndex)
    assert inline.request.mark_visibility_index.projection is request.projection


def test_direct_inline_keeps_projection_error_precedence_before_index_creation():
    request = _axis_request(())
    invalid_projection = replace(request.projection, window=(date(2026, 2, 2), date(2026, 2, 2)))
    invalid = replace(request, projection=invalid_projection)

    with pytest.raises(LayoutError, match="E_PRESENTATION_PROJECTION_REQUIRED"):
        prepare_surface_inline(invalid)


def test_candidate_natural_prefix_carries_same_prepared_index():
    request = _axis_request(())

    natural = prepare_surface_natural_candidate(request)
    index = natural.inline.request.mark_visibility_index

    assert isinstance(index, ItemMarkVisibilityIndex)
    assert index.projection is request.projection
    assert ensure_request_mark_visibility_index(natural.inline.request).mark_visibility_index is index


def test_prepared_selection_is_reused_by_provisional_and_final_mark_composition(monkeypatch):
    from chrona.presentation.layout import mark_geometry, surface_mark_visibility
    from chrona.presentation.layout.surface_marks import compose_surface_marks

    request = _axis_request(())
    selected = []
    original = surface_mark_visibility.select_item_mark_facets

    def counted(**kwargs):
        selected.append((kwargs["item"], kwargs["source_kind"]))
        return original(**kwargs)

    def forbidden(**_kwargs):
        pytest.fail("real provisional/final composition must not reselect prepared facets")

    monkeypatch.setattr(surface_mark_visibility, "select_item_mark_facets", counted)
    monkeypatch.setattr(mark_geometry, "select_item_mark_facets", forbidden)
    base = prepare_surface_base(request)
    index = base.request.mark_visibility_index
    assert isinstance(index, ItemMarkVisibilityIndex)
    assert selected == [(request.projection.items[0], "combined")]

    compose_surface_marks(base, lane_owner=lambda _row, _item: None)

    assert selected == [(request.projection.items[0], "combined")]


@pytest.mark.parametrize("occurrence_kind", ["row", "lane-final", "folded"])
def test_final_composition_looks_up_row_lane_alias_and_folded_selection(
        monkeypatch, occurrence_kind):
    from chrona.presentation.layout import mark_geometry, surface_mark_visibility
    from chrona.presentation.layout.surface_marks import compose_surface_marks
    from chrona.presentation.layout.surface_mark_visibility import (
        MarkOccurrence, MarkOccurrenceKind, build_item_mark_visibility_index,
    )
    from chrona.presentation.model.projection import (
        FoldedPointProjection, ReviewItem, ReviewLaneRowProjection, ReviewProjection,
        ReviewRowProjection,
    )
    from chrona.presentation.review.lane_membership import Lane, LaneAssignment, LaneMembership

    item = ReviewItem("object", "Object", "point", {"at": date(2026, 2, 3)}, None, None,
                      ("planned",), item_id="item", source_kind="primary")
    as_of = None
    row = ReviewRowProjection("row:source", "Row", "group", "item", (item,))
    projection = ReviewProjection((item,), (date(2026, 2, 1), date(2026, 2, 5)), (), (), rows=(row,))
    lane_owner = lambda _row, _item: None
    expected_instance_id = "row:source:item"
    expected_kind = MarkOccurrenceKind.ROW
    container_id = "row:source"
    review_row = SimpleNamespace(row_id="row:source", items=(item,), member_item_ids=("item",),
                                 rollup_presentation="none")
    group_placements = ()
    final_rows = (SimpleNamespace(row_id="row:source", bounds=Rect(0, 0, 100, 10)),)

    if occurrence_kind == "lane-final":
        membership = LaneMembership((Lane("lane:final", "group", ("item",)),), (
            LaneAssignment("item", "lane:final", "group", "dates", "fixed"),
        ))
        projection = replace(
            projection, lane_membership=membership,
            lane_rows=(ReviewLaneRowProjection("lane:final", "group", (item,), ("item",)),),
        )
        expected_kind = MarkOccurrenceKind.LANE_FINAL
        container_id = "lane:final"
        expected_instance_id = "lane:final:item"
        review_row = SimpleNamespace(row_id="lane:final", items=(item,), member_item_ids=("item",),
                                     rollup_presentation="none")
        final_rows = (SimpleNamespace(row_id="lane:final", bounds=Rect(0, 0, 100, 10)),)
        lane_owner = lambda _row, _item: ("lane:final", "item")
    elif occurrence_kind == "folded":
        folded = FoldedPointProjection(item, "group:folded")
        projection = replace(projection, rows=(), folded_points=(folded,))
        expected_kind = MarkOccurrenceKind.FOLDED
        container_id = "group:folded"
        expected_instance_id = folded_instance_id(folded, item)
        review_row = None
        final_rows = ()
        group_placements = (SimpleNamespace(
            group_id="group:folded", header_bounds=Rect(0, 0, 100, 10)),)

    index = build_item_mark_visibility_index(projection, as_of=as_of)
    key = MarkOccurrence(expected_kind, container_id, "item", "object", "primary")
    expected_selection = index.lookup(key, projection=projection, as_of=as_of).selection
    request = SimpleNamespace(
        projection=projection, mark_visibility_index=index,
        presentation_contract=SimpleNamespace(time=SimpleNamespace(as_of=as_of)),
        surface_content=SimpleNamespace(progress_fill_source=None), theme_tokens=object(),
    )
    track = SimpleNamespace(instance_id=expected_instance_id, block=0.0, block_size=4.0)
    timeline = SimpleNamespace(slot_id="timeline")
    base = SimpleNamespace(
        request=request,
        review_rows=(review_row,) if review_row is not None else (),
        rows=final_rows, tracks=(track,) if review_row is not None else (),
        scale=None, timeline=timeline, role_geometries={}, mark_block_size=4,
        groups=group_placements, mark_band_allocation=None, metric_values={},
    )
    seen = []

    def compose(**kwargs):
        seen.append(kwargs["selection"])
        return SimpleNamespace(marks=(), diagnostics=(), diagnostic_provenance=(), absences=())

    def forbidden(**_kwargs):
        pytest.fail("a prepared occurrence must not reselect source facets")

    monkeypatch.setattr(surface_mark_visibility, "select_item_mark_facets", forbidden)
    monkeypatch.setattr(mark_geometry, "select_item_mark_facets", forbidden)
    monkeypatch.setattr("chrona.presentation.layout.surface_marks.compose_item_marks", compose)

    compose_surface_marks(base, lane_owner=lane_owner)

    assert seen == [expected_selection]


def test_request_without_projection_fails_before_cache_preparation():
    request = replace(_axis_request(()), projection=None)
    with pytest.raises(LayoutError, match="E_PRESENTATION_PROJECTION_REQUIRED"):
        ensure_request_mark_visibility_index(request)


def test_index_binding_does_not_follow_equal_but_distinct_projection():
    request = _axis_request(())
    prepared = ensure_request_mark_visibility_index(request)
    equal_projection = replace(request.projection)
    assert equal_projection == request.projection
    assert equal_projection is not request.projection
    with pytest.raises(LayoutError, match="E_LAYOUT_WINDOW_CLIP"):
        ensure_request_mark_visibility_index(replace(prepared, projection=equal_projection))
