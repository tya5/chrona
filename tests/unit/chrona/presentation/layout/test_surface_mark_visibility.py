from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from chrona.presentation.layout import surface_mark_visibility as visibility_module
from chrona.presentation.layout.lane_projection import LaneProjectionInstance
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_mark_visibility import (
    ItemMarkVisibilityIndex, MarkOccurrence, MarkOccurrenceKind,
    build_item_mark_visibility_index,
    outside_window_provenance,
)
from chrona.presentation.model.projection import (
    FoldedPointProjection, ReviewItem, ReviewLaneRowProjection, ReviewProjection,
    ReviewRowProjection, WindowMode,
)
from chrona.presentation.review.lane_membership import (
    Lane, LaneAssignment, LaneMembership,
)


D1 = date(2026, 2, 1)
D3 = date(2026, 2, 3)
D5 = date(2026, 2, 5)
D7 = date(2026, 2, 7)


def _item(object_id="object", *, item_id="item", source_kind="combined",
          source_type="span", planned=None, actual=None):
    planned = planned or {"start": D1, "end": D7}
    return ReviewItem(
        object_id, object_id, source_type, planned, actual, None, ("planned",),
        item_id=item_id, source_kind=source_kind,
    )


def _projection(*, items=(), rows=(), lane=False, folded=(), mode=WindowMode.EXPLICIT):
    lane_membership = None
    lane_rows = ()
    if lane:
        row = rows[0]
        member_id = row.items[0].item_id or row.items[0].object_id
        lane_membership = LaneMembership(
            (Lane("lane:final", row.group_id, (member_id,)),),
            (LaneAssignment(member_id, "lane:final", row.group_id, "dates", "fixed"),),
        )
        lane_rows = (ReviewLaneRowProjection(
            "lane:final", row.group_id, row.items, (member_id,),
        ),)
    return ReviewProjection(
        tuple(items), (D3, D5), (), (), rows=tuple(rows),
        folded_points=tuple(folded), lane_membership=lane_membership,
        lane_rows=lane_rows, window_mode=mode,
    )


def _row(item, row_id="row:source"):
    return ReviewRowProjection(row_id, "Row", "group", item.item_id, (item,))


def test_row_index_is_immutable_and_keeps_clipped_source_facts():
    item = _item(source_kind="primary")
    projection = _projection(rows=(_row(item),))
    index = build_item_mark_visibility_index(projection, as_of=None)
    key = MarkOccurrence(MarkOccurrenceKind.ROW, "row:source", "item", "object", "primary")
    result = index.lookup(key, projection=projection, as_of=None)

    assert result is index.entries[key]
    assert result.selection.facets[0].start == D1
    assert (result.facets[0].visible_start, result.facets[0].visible_finish) == (D3, D5)
    assert result.facets[0].cut_start and result.facets[0].cut_finish
    with pytest.raises(TypeError):
        index.entries[key] = result
    with pytest.raises(FrozenInstanceError):
        result.instance_id = "changed"


def test_lane_source_and_final_alias_share_one_result_and_select_once(monkeypatch):
    item = _item(source_kind="primary")
    projection = _projection(rows=(_row(item),), lane=True)
    calls = []
    original = visibility_module.select_item_mark_facets

    def counted(**kwargs):
        calls.append(kwargs["item"])
        return original(**kwargs)

    monkeypatch.setattr(visibility_module, "select_item_mark_facets", counted)
    index = build_item_mark_visibility_index(projection, as_of=None)

    source_key = MarkOccurrence(MarkOccurrenceKind.LANE_SOURCE,
                                "row:source", "item", "object", "primary")
    final_key = MarkOccurrence(MarkOccurrenceKind.LANE_FINAL,
                               "lane:final", "item", "object", "primary")
    source = index.lookup(source_key, projection=projection, as_of=None)
    final = index.lookup(final_key, projection=projection, as_of=None)
    assert source is final
    assert calls == [item]
    assert source.instance_id == "row%3Asource:item"
    warning = outside_window_provenance(index)
    assert warning.diagnostic == "W_LAYOUT_OUTSIDE_WINDOW:table-timeline"
    assert tuple(subject.source_ref for subject in warning.subjects) == ("/objects/object",)


def test_typed_namespaces_prevent_serialized_id_collisions():
    first = _item("object-1", item_id="c", source_kind="primary")
    second = _item("object-2", item_id="b:c", source_kind="primary")
    projection = _projection(rows=(_row(first, "a:b"), _row(second, "a")))
    index = build_item_mark_visibility_index(projection, as_of=None)
    first_key = MarkOccurrence(MarkOccurrenceKind.ROW, "a:b", "c", "object-1", "primary")
    second_key = MarkOccurrence(MarkOccurrenceKind.ROW, "a", "b:c", "object-2", "primary")
    assert first_key != second_key
    assert index.lookup(first_key, projection=projection, as_of=None) is not index.lookup(
        second_key, projection=projection, as_of=None)


def test_auto_uses_combined_semantics_and_object_identity():
    item = _item(source_kind="actual", actual={"start": D1, "finish": D7})
    projection = _projection(items=(item,), mode=WindowMode.SELECTED_PLANNED)
    index = build_item_mark_visibility_index(projection, as_of=None)
    key = MarkOccurrence(MarkOccurrenceKind.AUTO, "object", "item", "object", "combined")
    result = index.lookup(key, projection=projection, as_of=None)
    assert result.instance_id == "object"
    assert result.selection.source_kind == "combined"
    assert tuple(f.source.facet for f in result.facets) == ("planned", "actual")
    assert all(f.disposition == "contained" for f in result.facets)


def test_folded_occurrence_keeps_group_identity_and_disables_missing_actual():
    item = _item(source_kind="primary", actual=None)
    item = ReviewItem(
        item.object_id, item.title, item.source_type, item.planned, item.actual,
        item.finish_delta, ("planned",), item_id=item.item_id,
        source_kind=item.source_kind,
    )
    folded = FoldedPointProjection(item, "group:folded")
    projection = _projection(folded=(folded,))
    index = build_item_mark_visibility_index(projection, as_of=None)
    key = MarkOccurrence(MarkOccurrenceKind.FOLDED, "group:folded", "item", "object", "primary")
    result = index.lookup(key, projection=projection, as_of=None)
    assert result.instance_id == "group-header:group:folded:item"
    assert result.selection.missing_actual_eligible is False


def test_folded_open_actual_selection_does_not_emit_row_diagnostic():
    item = _item(actual={"openUntil": "asOf", "start": D1})
    folded = FoldedPointProjection(item, "group:folded")
    projection = _projection(folded=(folded,))
    index = build_item_mark_visibility_index(projection, as_of=None)
    key = MarkOccurrence(MarkOccurrenceKind.FOLDED, "group:folded", "item", "object", "combined")
    result = index.lookup(key, projection=projection, as_of=None)
    assert result.selection.diagnostics == ()
    assert any(absence.reason == "as-of-required" for absence in result.selection.absences)


def test_index_is_bound_to_exact_projection_and_as_of():
    item = _item(source_kind="primary")
    projection = _projection(rows=(_row(item),))
    index = build_item_mark_visibility_index(projection, as_of=D3)
    key = MarkOccurrence(MarkOccurrenceKind.ROW, "row:source", "item", "object", "primary")
    with pytest.raises(LayoutError, match="E_LAYOUT_WINDOW_CLIP"):
        index.lookup(key, projection=projection, as_of=None)
    equivalent = _projection(rows=(_row(item),))
    with pytest.raises(LayoutError, match="E_LAYOUT_WINDOW_CLIP"):
        index.lookup(key, projection=equivalent, as_of=D3)


def test_index_copies_input_mapping_before_wrapping_read_only():
    projection = _projection()
    key = MarkOccurrence(MarkOccurrenceKind.AUTO, "x", "x", "x", "combined")
    entries = {}
    index = ItemMarkVisibilityIndex(projection, None, entries)
    entries[key] = object()
    assert index.entries == {}


def test_lane_source_key_uses_typed_projection_occurrence_not_placement_string():
    instance = LaneProjectionInstance("row:source", "item/with/slash", "object", "primary")
    key = MarkOccurrence(MarkOccurrenceKind.LANE_SOURCE, instance.row_id,
                         instance.item_id, instance.object_id, instance.source_kind)
    assert instance.placement_key == "row%3Asource:item%2Fwith%2Fslash"
    assert key.container_id == instance.row_id
    assert key.item_id == instance.item_id
