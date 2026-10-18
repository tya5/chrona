from datetime import date

import pytest

from chrona.presentation.layout.surface_mark_visibility import MarkOccurrenceKind
from chrona.presentation.layout.style_occurrences import StyleSourceOccurrences
from chrona.presentation.model.projection import (
    ReviewItem,
    ReviewLaneRowProjection,
    ReviewProjection,
    ReviewRowProjection,
)
from chrona.presentation.model.style_rules import StyleOccurrenceKey
from chrona.presentation.review.lane_membership import Lane, LaneAssignment, LaneMembership


def _item(*, object_id="object:1", item_id="member:1", source_kind="primary"):
    return ReviewItem(
        object_id, "Task", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 4)},
        None, None, ("planned",), item_id=item_id, source_kind=source_kind,
    )


def _key(subject, source, semantic, row="", member="", occurrence=""):
    return StyleOccurrenceKey(subject, source, semantic, row, member, occurrence_kind=occurrence)


def test_auto_row_folded_and_ordinary_keys_keep_distinct_occurrence_identity():
    item = _item()
    auto_projection = ReviewProjection((item,), (date(2026, 1, 1), date(2026, 1, 5)), (), ())
    auto = StyleSourceOccurrences.from_projection(auto_projection)
    assert auto.label_key(item, "ignored", "planned") == _key(
        "object:1", "combined", "planned", member="member:1", occurrence="auto"
    )

    ordinary_projection = ReviewProjection(
        (item,), (date(2026, 1, 1), date(2026, 1, 5)), (), (),
        rows=(ReviewRowProjection("row:a/1", "Task", "group", item.item_id, (item,)),),
    )
    ordinary = StyleSourceOccurrences.from_projection(ordinary_projection)
    first_row = ordinary.label_key(item, "row:a/1", "memberLabel")
    other_row = ordinary.label_key(item, "row:b/2", "memberLabel")
    folded = ordinary.label_key(item, "group-header:group:member:1", "memberLabel", folded=True)

    assert first_row == _key("object:1", "primary", "memberLabel", "row:a/1", "member:1", "row")
    assert other_row.row_id == "row:b/2" and other_row != first_row
    assert folded == _key("object:1", "primary", "memberLabel", "group-header:group:member:1",
                          "member:1", "folded")
    assert folded != first_row


def test_fixed_lane_final_alias_joins_original_row_source_without_decoding_ids():
    item = _item(object_id="object:with:colons", item_id="member:slash/value")
    row_id = "source:row/with:delimiters"
    lane_id = "fixed:lane/one"
    membership = LaneMembership(
        (Lane(lane_id, "group", (item.item_id,)),),
        (LaneAssignment(item.item_id, lane_id, "group", "dates", "fixed"),),
    )
    projection = ReviewProjection(
        (item,), (date(2026, 1, 1), date(2026, 1, 5)), (), (),
        rows=(ReviewRowProjection(row_id, "Task", "group", item.item_id, (item,)),),
        lane_membership=membership,
        lane_rows=(ReviewLaneRowProjection(lane_id, "group", (item,), (item.item_id,)),),
    )

    sources = StyleSourceOccurrences.from_projection(projection)
    final_alias = sources.occurrence(
        MarkOccurrenceKind.LANE_FINAL, lane_id, item.item_id, item.object_id, item.source_kind
    )
    key = final_alias.style_key("planned")
    label_key = sources.label_key(item, lane_id, "memberLabel")

    assert final_alias.kind is MarkOccurrenceKind.LANE_SOURCE
    assert final_alias.container_id == row_id
    assert key == _key(
        "object:with:colons", "primary", "planned", row_id, "member:slash/value", "lane-source"
    )
    assert label_key == _key(
        "object:with:colons", "primary", "memberLabel", row_id, "member:slash/value", "lane-source"
    )
    with pytest.raises(TypeError):
        sources.lane_sources[("other", "member", "object", "primary")] = final_alias
