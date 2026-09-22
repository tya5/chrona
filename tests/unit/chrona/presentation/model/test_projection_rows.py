from datetime import date

from chrona.presentation.model.projection import build_review_projection
from chrona.presentation.model.surface_content import table_value
from chrona.presentation.contracts.resources import (
    ViewComparison, ViewGrouping, ViewInput, ViewOrdering, ViewRow, ViewRowItem, ViewRows, ViewSelection,
    ViewVisibility, ViewWindow, freeze,
)


def typed_view(value):
    body = value["body"]
    rows = body["rows"]
    parsed_rows = []
    for row in rows.get("items", ()):
        items = tuple(
            ViewRowItem(item["id"], item["source"]["kind"], item["source"]["object"], item.get("track", "stacked"))
            for item in row.get("items", ())
        )
        parsed_rows.append(ViewRow(str(row["id"]), row.get("label"), int(row["depth"]), row.get("parentRow"),
                                   row.get("group"), row.get("tableSubject"), items))
    selection = body.get("selection", {}).get("include", {})
    grouping = body.get("grouping")
    ordering = body.get("ordering")
    return ViewInput(
        ViewSelection(tuple(selection.get("ids", ())), tuple(selection.get("types", ()))) if selection else None,
        ViewGrouping(grouping["by"], grouping.get("field"), tuple(grouping.get("order", ())), grouping.get("missing"), grouping.get("presentation"), grouping.get("depth"), grouping.get("rollup")) if grouping else None,
        ViewOrdering(ordering["by"], ordering["direction"], ordering["tieBreak"]) if ordering else None,
        ViewWindow(body["window"]["mode"], body["window"].get("start"), body["window"].get("end"), body["window"].get("marginDays", 0)),
        ViewComparison(None, body["comparison"]["actual"], None, None, tuple(body["comparison"].get("facets", ()))),
        ViewVisibility(False, "none", "none"), freeze({}), (), (),
        ViewRows(rows["mode"], tuple(parsed_rows)), None, (), None, None, None)


def test_explicit_row_composes_serial_task_and_milestone_under_one_owner():
    project = {"objects": {
        "design": {"title": "Design", "fields": {"owner": "A"}},
        "implement": {"title": "Implement", "fields": {"owner": "A"}},
        "gate": {"title": "Gate", "fields": {"owner": "A"}},
    }, "entities": {}}
    view = {"body": {
        "comparison": {"actual": "optional"},
        "window": {"mode": "selected-planned"},
        "rows": {"mode": "explicit", "items": [{
            "id": "owner-a", "depth": 0, "label": "Owner A", "group": "firmware",
            "tableSubject": "design", "items": [
                {"id": "design", "source": {"kind": "primary", "object": "design"}},
                {"id": "implement", "source": {"kind": "primary", "object": "implement"}},
                {"id": "gate", "source": {"kind": "primary", "object": "gate"}},
            ],
        }]},
    }}
    projection = build_review_projection(project, {
        "design": {"start": date(2026, 1, 1), "end": date(2026, 1, 5)},
        "implement": {"start": date(2026, 1, 5), "end": date(2026, 1, 10)},
        "gate": {"at": date(2026, 1, 10)},
    }, typed_view(view), None)

    assert len(projection.rows) == 1
    row = projection.rows[0]
    assert (row.row_id, row.label, row.group_id, row.table_subject_id) == ("owner-a", "Owner A", "firmware", "design")
    assert [(item.item_id, item.object_id, item.source_kind) for item in row.items] == [
        ("design", "design", "primary"), ("implement", "implement", "primary"), ("gate", "gate", "primary")]


def test_explicit_row_resolves_named_snapshot_item():
    project = {"objects": {"task": {"title": "Current", "fields": {}}}, "entities": {}}
    historic = {"objects": {"task": {"title": "Historic", "fields": {}}}, "entities": {}}
    view = {"body": {"comparison": {"actual": "optional"}, "window": {"mode": "selected-planned"},
        "rows": {"mode": "explicit", "items": [{"id": "r", "depth": 0, "items": [
            {"id": "old", "source": {"kind": "snapshot", "object": "task"}},
            {"id": "now", "source": {"kind": "primary", "object": "task"}}]}]}}}
    projection = build_review_projection(project, {"task": {"start": date(2026, 2, 1), "end": date(2026, 2, 2)}},
        typed_view(view), None, snapshot_project=historic,
        snapshot_placements={"task": {"start": date(2026, 1, 1), "end": date(2026, 1, 2)}})
    assert [(item.source_kind, item.title, item.planned["start"]) for item in projection.rows[0].items] == [
        ("snapshot", "Historic", date(2026, 1, 1)), ("primary", "Current", date(2026, 2, 1))]


def test_explicit_parent_row_must_assert_the_project_parent_edge():
    project = {"objects": {
        "programme": {"title": "Programme", "schedule": {"mode": "rollup"}},
        "task": {"title": "Task", "parent": "programme", "schedule": {"mode": "fixed"}},
    }, "entities": {}}
    view = {"body": {"comparison": {"actual": "optional"}, "window": {"mode": "selected-planned"},
        "rows": {"mode": "explicit", "items": [
            {"id": "programme", "depth": 0, "items": [{"id": "programme", "source": {"kind": "primary", "object": "programme"}}]},
            {"id": "task", "depth": 1, "parentRow": "programme", "items": [{"id": "task", "source": {"kind": "primary", "object": "task"}}]},
        ]}}}
    placements = {"programme": {"start": date(2026, 1, 1), "end": date(2026, 1, 3)},
                  "task": {"start": date(2026, 1, 1), "end": date(2026, 1, 2)}}
    assert [row.parent_row_id for row in build_review_projection(project, placements, typed_view(view), None).rows] == [None, "programme"]
    view["body"]["rows"]["items"][1]["parentRow"] = "task"
    import pytest
    with pytest.raises(ValueError, match="E_REVIEW_ROW_PARENT_MISMATCH"):
        build_review_projection(project, placements, typed_view(view), None)


def test_hierarchy_selection_expands_predicate_roots_to_the_inclusive_depth_limit():
    project = {"objects": {
        "programme": {"title": "Programme", "schedule": {"mode": "rollup"}},
        "design": {"title": "Design", "parent": "programme", "schedule": {"mode": "fixed"}},
        "build": {"title": "Build", "parent": "programme", "schedule": {"mode": "fixed"}},
        "detail": {"title": "Detail", "parent": "design", "schedule": {"mode": "fixed"}},
        "release": {"title": "Release", "schedule": {"mode": "fixed"}},
    }, "entities": {}}
    placements = {
        "programme": {"start": date(2026, 1, 1), "end": date(2026, 1, 10)},
        "design": {"start": date(2026, 1, 1), "end": date(2026, 1, 3)},
        "build": {"start": date(2026, 1, 4), "end": date(2026, 1, 6)},
        "detail": {"start": date(2026, 1, 2), "end": date(2026, 1, 3)},
        "release": {"start": date(2026, 1, 11), "end": date(2026, 1, 12)},
    }
    view = {"body": {
        "selection": {"include": {"ids": ["programme", "design"]}},
        "grouping": {"by": "hierarchy", "depth": 1, "rollup": "bar"},
        "ordering": {"by": "id", "direction": "ascending", "tieBreak": "id"},
        "comparison": {"actual": "optional"}, "window": {"mode": "selected-planned"},
        "rows": {"mode": "automatic"},
    }}
    projection = build_review_projection(project, placements, typed_view(view), None)
    assert [(row.row_id, row.depth, row.rollup_presentation) for row in projection.rows] == [
        ("programme", 0, "bar"), ("build", 1, "none"), ("design", 1, "none"),
    ]
    assert [(item.wbs_code, item.hierarchy_path) for item in projection.items] == [
        ("1", ("programme",)), ("1.2", ("programme", "build")), ("1.1", ("programme", "design")),
    ]
    design = projection.items[-1]
    assert table_value(design, project, "wbsCode") == "1.1"
    assert table_value(design, project, "path") == "Programme / Design"
