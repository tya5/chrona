from datetime import date
from dataclasses import replace
import inspect
import pytest

from chrona.presentation.model.projection import ReviewItem, _roles, build_review_projection, shared_track_member_key
from chrona.presentation.model.surface_content import table_value
from chrona.presentation.contracts.resources import (
    ViewComparison, ViewGrouping, ViewInput, ViewOrdering, ViewRow, ViewRowItem, ViewRows, ViewSelection,
    ViewVisibility, ViewWindow, freeze,
)
from chrona.scheduling.scheduler import ScheduleAnalysis


def test_shared_track_member_order_is_one_finite_model_policy():
    members = tuple(ReviewItem("item", kind, "span", {}, None, None, (), source_kind=kind, track="shared")
                    for kind in ("actual", "primary", "scenario", "snapshot"))
    assert [item.source_kind for _, item in sorted(enumerate(members), key=lambda pair: shared_track_member_key(pair[1], pair[0]))] == [
        "snapshot", "scenario", "primary", "actual",
    ]


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
        ViewVisibility(False, "none", "none"), (), (),
        ViewRows(rows["mode"], tuple(parsed_rows)), None, (), None, None, None)


def test_projection_exposes_only_fact_derived_role_inputs() -> None:
    assert set(inspect.signature(build_review_projection).parameters).isdisjoint({"style", "theme"})
    assert _roles(None, None) == ("planned", "missing-actual")
    assert _roles({"start": date(2026, 1, 1)}, 3, critical=True) == (
        "planned", "actual", "variance-behind", "critical",
    )
    assert _roles({"at": date(2026, 1, 1)}, -2) == ("planned", "actual", "variance-ahead")
    assert _roles({"at": date(2026, 1, 1)}, 0) == ("planned", "actual", "variance-on-plan")


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


def test_explicit_row_selects_each_named_scenario_by_its_declared_id():
    project = {"objects": {"task": {"title": "Current", "fields": {}}}, "entities": {}}
    view = ViewInput(None, None, None, ViewWindow("selected-planned", None, None, 0),
        ViewComparison(None, "optional", None, None, ()), ViewVisibility(False, "none", "none"), (), (),
        ViewRows("explicit", (ViewRow("r", None, 0, None, None, None, (
            ViewRowItem("early", "scenario", "task", "stacked", scenario_id="early"),
            ViewRowItem("late", "scenario", "task", "stacked", scenario_id="late"),)),)), None, (), None, None, None)
    projection = build_review_projection(project, {"task": {"start": date(2026, 2, 1), "end": date(2026, 2, 2)}}, view, None,
        scenarios={
            "early": ({"objects": {"task": {"title": "Early", "fields": {}}}}, {"task": {"start": date(2026, 1, 1), "end": date(2026, 1, 2)}}),
            "late": ({"objects": {"task": {"title": "Late", "fields": {}}}}, {"task": {"start": date(2026, 3, 1), "end": date(2026, 3, 2)}}),
        })
    assert [(item.scenario_id, item.title) for item in projection.rows[0].items] == [("early", "Early"), ("late", "Late")]


def test_automatic_rows_overlay_the_selected_scenario_on_the_shared_track():
    project = {"objects": {"task": {"title": "Current", "fields": {}}}, "entities": {}}
    view = ViewInput(None, None, None, ViewWindow("selected-planned", None, None, 0),
        ViewComparison("scenario", "optional", None, None, (), scenario_id="recovery"),
        ViewVisibility(False, "none", "none"), (), (), ViewRows("automatic", ()), None, (), None, None, None)
    projection = build_review_projection(project, {"task": {"start": date(2026, 2, 1), "end": date(2026, 2, 2)}}, view, None,
        scenarios={"recovery": (
            {"objects": {"task": {"title": "Recovery", "fields": {}}}},
            {"task": {"start": date(2026, 1, 1), "end": date(2026, 1, 2)}},
        )})

    assert [(item.item_id, item.source_kind, item.scenario_id, item.track, item.title) for item in projection.rows[0].items] == [
        ("task", "combined", None, "shared", "Current"),
        ("scenario:recovery:task", "scenario", "recovery", "shared", "Recovery"),
    ]


def test_automatic_predecessor_policy_folds_a_point_with_one_selected_span_predecessor():
    project = {"objects": {"task": {"title": "Task", "fields": {}}, "gate": {"title": "Gate", "fields": {}}},
               "entities": {}, "relations": [{"id": "task-gate", "from": {"object": "task"}, "to": {"object": "gate"}}]}
    view = ViewInput(None, None, None, ViewWindow("selected-planned", None, None, 0),
        ViewComparison(None, "optional", None, None, ()), ViewVisibility(False, "none", "none"), (), (),
        ViewRows("automatic", (), "predecessor"), None, (), None, None, None)
    projection = build_review_projection(project, {"task": {"start": date(2026, 1, 1), "end": date(2026, 1, 2)},
                                                   "gate": {"at": date(2026, 1, 2)}}, view, None)
    assert [(row.row_id, [item.object_id for item in row.items]) for row in projection.rows] == [("task", ["task", "gate"])]
    assert projection.rows[0].items[1].track == "shared"


def test_automatic_group_header_policy_keeps_point_out_of_table_rows_with_a_header_target():
    project = {"objects": {
        "task": {"title": "Task", "fields": {"owner": "delivery"}},
        "gate": {"title": "Gate", "fields": {"owner": "delivery"}},
    }, "entities": {}}
    view = ViewInput(None,
        ViewGrouping("field", "owner", (), "ungrouped", "header", None, None), None,
        ViewWindow("selected-planned", None, None, 0),
        ViewComparison(None, "optional", None, None, ()),
        ViewVisibility(freeze({"placement": "plot", "content": ("title",), "side": "auto"}), "none", "none"),
        (), (), ViewRows("automatic", (), "group-header"), None, (), None, None, None)
    projection = build_review_projection(project, {
        "task": {"start": date(2026, 1, 1), "end": date(2026, 1, 2)},
        "gate": {"at": date(2026, 1, 2)},
    }, view, None)

    assert [row.row_id for row in projection.rows] == ["task"]
    assert [(point.item.object_id, point.group_id, point.target_kind) for point in projection.folded_points] == [
        ("gate", "delivery", "group-header")]


def test_automatic_group_header_policy_requires_a_visible_plot_title():
    project = {"objects": {"gate": {"title": "Gate", "fields": {"owner": "delivery"}}}, "entities": {}}
    view = ViewInput(None,
        ViewGrouping("field", "owner", (), "ungrouped", "header", None, None), None,
        ViewWindow("selected-planned", None, None, 0),
        ViewComparison(None, "optional", None, None, ()),
        ViewVisibility(freeze({"placement": "table", "content": ("title",), "side": "auto"}), "none", "none"),
        (), (), ViewRows("automatic", (), "group-header"), None, (), None, None, None)

    with pytest.raises(ValueError, match="E_REVIEW_POINT_GROUP_HEADER_LABEL_REQUIRED"):
        build_review_projection(project, {"gate": {"at": date(2026, 1, 2)}}, view, None)


def test_projection_carries_current_and_snapshot_analysis_without_crossing_them():
    project = {"objects": {"task": {"title": "Current", "fields": {}}}, "entities": {}}
    historic = {"objects": {"task": {"title": "Historic", "fields": {}}}, "entities": {}}
    view = {"body": {"comparison": {"actual": "optional"}, "window": {"mode": "selected-planned"},
        "rows": {"mode": "explicit", "items": [{"id": "r", "depth": 0, "items": [
            {"id": "old", "source": {"kind": "snapshot", "object": "task"}},
            {"id": "now", "source": {"kind": "primary", "object": "task"}}]}]}}}
    current_analysis = ScheduleAnalysis({}, {"task": 3}, frozenset(), {"task": date(2026, 2, 2)})
    snapshot_analysis = ScheduleAnalysis({}, {"task": 0}, frozenset({"task"}), {"task": date(2026, 1, 2)})
    projection = build_review_projection(project, {"task": {"start": date(2026, 2, 1), "end": date(2026, 2, 2)}},
        typed_view(view), None, snapshot_project=historic,
        snapshot_placements={"task": {"start": date(2026, 1, 1), "end": date(2026, 1, 2)}},
        analysis=current_analysis, snapshot_analysis=snapshot_analysis)
    old, now = projection.rows[0].items
    assert (old.total_float, old.critical, now.total_float, now.critical) == (0, True, 3, False)
    assert table_value(now, project, "totalFloat") == 3


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


def test_object_type_selection_intersects_geometry_and_exclusion_before_rows():
    project = {"objects": {
        "task-span": {"type": "task", "title": "Task", "fields": {}},
        "gate-point": {"type": "gate", "title": "Gate", "fields": {}},
        "phase-span": {"type": "phase", "title": "Phase", "fields": {}},
    }, "entities": {}}
    view = typed_view({"body": {"comparison": {"actual": "optional"},
        "selection": {"include": {"types": ["span"], "objectTypes": ["task", "phase"]},
                      "exclude": {"objectTypes": ["phase"]}},
        "window": {"mode": "selected-planned"}, "rows": {"mode": "automatic"}}})
    view = replace(view, selection=ViewSelection(view.selection.ids, view.selection.types,
                                                  ("task", "phase"), ("phase",)))
    projection = build_review_projection(project, {
        "task-span": {"start": date(2026, 1, 1), "end": date(2026, 1, 2)},
        "gate-point": {"at": date(2026, 1, 2)},
        "phase-span": {"start": date(2026, 1, 2), "end": date(2026, 1, 3)},
    }, view, None)
    assert [item.object_id for item in projection.items] == ["task-span"]
