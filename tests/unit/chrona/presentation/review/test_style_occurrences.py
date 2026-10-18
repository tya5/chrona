from dataclasses import replace
from datetime import date
from types import SimpleNamespace

from chrona.presentation.model.field_roles import FieldDescriptor, FieldRoleBindings
from chrona.presentation.model.projection import (
    FoldedPointProjection,
    ReviewItem,
    ReviewLaneRowProjection,
    ReviewProjection,
    ReviewRowProjection,
)
from chrona.presentation.model.style_rules import StyleOccurrenceKey
from chrona.presentation.model.hierarchy_names import member_name_key
from chrona.presentation.review.lane_membership import Lane, LaneAssignment, LaneMembership
from chrona.presentation.review.style_occurrences import collect_surface_style_facts


DAY = date(2026, 1, 3)


def _content(*, show_member_labels=True, label_content=("title",), label_side="auto",
             label_fallback=(), attached_labels=(), columns=(), cells=()):
    return SimpleNamespace(
        as_of=DAY,
        attached_labels=attached_labels,
        label_content=label_content,
        label_fallback=label_fallback,
        label_side=label_side,
        show_member_labels=show_member_labels,
        table_cells=cells,
        table_columns=columns,
    )


def _item(object_id="task", *, source_kind="primary", item_id="member", source_type="point",
          planned=None, actual=None, finish_delta=1, roles=("critical",), field_bindings=None,
          fields=None, forecast=None, presentation=None):
    return ReviewItem(
        object_id=object_id,
        title=object_id.title(),
        source_type=source_type,
        planned=planned or {"at": DAY},
        actual=actual,
        finish_delta=finish_delta,
        roles=roles,
        item_id=item_id,
        source_kind=source_kind,
        field_bindings=field_bindings or FieldRoleBindings(),
        fields=fields or {},
        forecast=forecast,
        presentation=presentation,
    )


def _projection(*, items=(), rows=(), folded=(), rows_resolved=True,
                lane_membership=None, comparison_facets=()):
    return ReviewProjection(
        tuple(items), (DAY, date(2026, 1, 4)), (), (), tuple(rows),
        comparison_facets=tuple(comparison_facets),
        folded_points=tuple(folded), lane_membership=lane_membership,
        rows_resolved=rows_resolved,
    )


def test_collector_uses_canonical_gate_mark_and_finite_label_candidates():
    item = _item(actual=None)
    row = ReviewRowProjection("row-a", "Task", "", item.item_id, (item,))

    facts = collect_surface_style_facts(
        _projection(items=(item,), rows=(row,)),
        _content(label_side="auto", label_fallback=("inside", "end")),
        gate_declared=True,
    )

    mark, = (fact for fact in facts.occurrences if fact.primitive_family == "mark")
    assert mark.key == StyleOccurrenceKey(
        "task", "primary", "gate", "row-a", "member", occurrence_kind="row")
    assert mark.purpose == "planned" and mark.original_roles == ("critical",)
    assert mark.comparison_category == "behind"
    text_keys = {fact.key for fact in facts.occurrences if fact.primitive_family == "label"}
    assert StyleOccurrenceKey("task", "primary", "memberLabel", "row-a", "member",
                              occurrence_kind="row") in text_keys
    assert StyleOccurrenceKey("task", "primary", "memberLabelInsidePlanned", "row-a", "member",
                              occurrence_kind="row") in text_keys


def test_table_cell_joins_exact_source_item_and_preserves_view_cell_as_virtual():
    bindings = FieldRoleBindings(
        (("responsible", "owner"),),
        (("task", (FieldDescriptor("owner", "enum", enum_values=("ops", "design")),)),
         ("not-selected", (FieldDescriptor("risk", "string"),))),
    )
    item = _item(source_kind="snapshot", item_id="snapshot-track", source_type="span",
                 planned={"start": DAY, "end": date(2026, 1, 4)},
                 field_bindings=bindings, fields={"owner": "ops"})
    row = ReviewRowProjection("snapshot-row", "Task", "", item.item_id, (item,))
    subject_key = StyleOccurrenceKey("task", "snapshot", "tableVarianceBehind", "snapshot-row",
                                     "snapshot-track", "finish", "table-cell")
    view_key = StyleOccurrenceKey("virtual-row", "view", "tableCell", "virtual-row", "",
                                  "title", "table-cell")
    columns = (SimpleNamespace(column_id="finish", column_source=(("comparisonFacet", "finishDelta"),)),
               SimpleNamespace(column_id="title", column_source="title"))
    cells = (SimpleNamespace(style_key=subject_key, column_id="finish", semantic_id="tableVarianceBehind"),
             SimpleNamespace(style_key=view_key, column_id="title", semantic_id="tableCell"))

    facts = collect_surface_style_facts(
        _projection(items=(item,), rows=(row,)), _content(columns=columns, cells=cells))

    by_key = {fact.key: fact for fact in facts.occurrences}
    table = by_key[subject_key]
    assert table.purpose == "table-cell" and table.primitive_family == "label"
    assert table.column_source == (("comparisonFacet", "finishDelta"),)
    assert table.comparison_category == "behind"
    assert [(fact.name, fact.value, fact.kind) for fact in table.fields] == [("owner", "ops", "enum")]
    assert by_key[view_key].fields == () and by_key[view_key].original_roles == ()

    declarations = {(fact.name, fact.kind, fact.aliases) for fact in facts.field_catalogue}
    assert ("owner", "enum", ("responsible",)) in declarations
    assert ("risk", "string", ()) in declarations
    assert all(not fact.present and fact.value is None for fact in facts.field_catalogue)


def test_collector_uses_lane_source_and_folded_keys_without_auto_for_resolved_empty_rows():
    lane_item = _item("lane-task", item_id="member-a")
    folded_item = _item("folded-task", item_id="member-b")
    row = ReviewRowProjection("source-row", "Lane", "", lane_item.item_id, (lane_item,))
    folded = FoldedPointProjection(folded_item, "group-a")
    projection = _projection(items=(lane_item,), rows=(row,), folded=(folded,),
                             lane_membership=object())

    facts = collect_surface_style_facts(projection, _content(show_member_labels=False))

    keys = {fact.key for fact in facts.occurrences}
    assert StyleOccurrenceKey("lane-task", "primary", "planned", "source-row", "member-a",
                              occurrence_kind="lane-source") in keys
    assert StyleOccurrenceKey("folded-task", "primary", "planned", "group-a", "member-b",
                              occurrence_kind="folded") in keys
    assert not any(key.occurrence_kind == "auto" for key in keys)


def test_text_candidates_include_preferred_inside_but_not_folded_or_key_row_inside():
    preferred = _item("preferred", presentation={"label": {"side": "inside"}})
    folded_item = _item("folded")
    key_row_item = _item("key-row")
    rows = (
        ReviewRowProjection("preferred-row", "Preferred", "", preferred.item_id, (preferred,)),
        ReviewRowProjection("key-row-id", "Key row", "", key_row_item.item_id,
                            (key_row_item,), key_row=True),
    )
    folded = FoldedPointProjection(folded_item, "folded-group")
    projection = _projection(items=(preferred, key_row_item), rows=rows, folded=(folded,))

    facts = collect_surface_style_facts(
        projection, _content(label_side="auto", label_fallback=("end",)))

    inside_keys = {fact.key for fact in facts.occurrences
                   if fact.key.semantic_id == "memberLabelInsidePlanned"}
    assert StyleOccurrenceKey("preferred", "primary", "memberLabelInsidePlanned",
                              "preferred-row", "member",
                              occurrence_kind="row") in inside_keys
    assert not any(key.row_id == "folded-group" for key in inside_keys)
    assert not any(key.row_id == "key-row-id" for key in inside_keys)


def test_attached_lane_style_presence_uses_lane_container_not_source_row_id():
    item = _item("attached", item_id="attached-instance")
    item = replace(item, attached_to="host")
    row = ReviewRowProjection("source-row", "Attached", "", item.item_id, (item,))
    lane_id = "lane-host"
    membership = LaneMembership((Lane(lane_id, "", (item.item_id,)),),
        (LaneAssignment(item.item_id, lane_id, "", "attached", "host"),))
    projection = _projection(items=(item,), rows=(row,), lane_membership=membership)
    projection = replace(projection, lane_rows=(ReviewLaneRowProjection(
        lane_id, "", (item,), (item.item_id,)),))
    content = _content(show_member_labels=False,
        attached_labels=((member_name_key(item, lane_id), "Path / Attached · 03 Jan · +1d"),))

    facts = collect_surface_style_facts(projection, content)

    assert StyleOccurrenceKey("attached", "primary", "memberLabel", "source-row",
                              "attached-instance", occurrence_kind="lane-source") in {
        fact.key for fact in facts.occurrences if fact.primitive_family == "label"
    }
