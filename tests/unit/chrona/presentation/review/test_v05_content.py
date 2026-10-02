from dataclasses import replace
from datetime import date

import pytest

from chrona.presentation.model.color_scale import ResolvedColorScale
from chrona.presentation.model.projection import (
    ObservationState, ReviewItem, ReviewProjection, ReviewRowProjection, ReviewLaneRowProjection,
)
from chrona.presentation.model.surface_content import SummaryContent, TableCellContent, TableContent
from chrona.presentation.review.lane_membership import Lane, LaneAssignment, LaneMembership
from chrona.presentation.table_presentation import BooleanPresencePresentation
from chrona.presentation.review.v05_content import (
    legend_entries, normalize_summary_content, normalize_v05_surface_content, normalize_v05_table_content,
)
from chrona.presentation.contracts.resources import (
    LegendEntry, ReviewDetailInput, SummaryMetric, SummaryPanelInput, SummaryProfileInput, TableColumn, ViewComparison, ViewGrouping, ViewInput,
    ViewLaneLabel, ViewLaneTable, ViewRows, ViewVisibility, ViewWindow, freeze,
)


EMPTY_SUMMARY = SummaryContent(())


def test_lane_plot_label_defaults_preserve_authored_content_and_side():
    projection = ReviewProjection((), (date(2026, 1, 1), date(2026, 1, 2)), (), ())
    table = TableContent((), (), (), None, ())
    view = typed_view({"body": {"rows": {"mode": "lanes"}, "visibility": {
        "labels": {"placement": "plot"}, "relations": "none", "annotations": "none",
    }}})
    default = normalize_v05_surface_content(projection, {"relations": (), "annotations": {}}, view,
                                            summary=EMPTY_SUMMARY, table=table)
    assert (default.label_content, default.label_side, default.label_overflow) == (
        ("title", "finishDelta"), "auto", "suppress")

    authored = replace(view, visibility=replace(
        view.visibility, labels=freeze({"placement": "plot", "content": ["title"], "side": "inside"}),
        fallback=freeze({"labels": ["inside", "end", "suppress"]}),
    ))
    selected = normalize_v05_surface_content(projection, {"relations": (), "annotations": {}}, authored,
                                             summary=EMPTY_SUMMARY, table=table)
    assert (selected.label_content, selected.label_side, selected.label_fallback) == (
        ("title",), "inside", ("inside", "end", "suppress"))


def test_lane_table_content_uses_exact_membership_and_no_member_table_subject():
    host = ReviewItem("host", "Host title", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 3)},
                      None, None, (), group_id="g", group_label="Group title", item_id="host")
    point = ReviewItem("gate", "Gate title", "point", {"at": date(2026, 1, 2)}, None, None, (),
                       group_id="g", group_label="Group title", item_id="gate", attached_to="host")
    lane_id = 'review-lane:["generated","g","host"]'
    membership = LaneMembership(
        (Lane(lane_id, "g", ("host", "gate")),),
        (LaneAssignment("host", lane_id, "g", "single", "host"),
         LaneAssignment("gate", lane_id, "g", "attached", "host")),
    )
    projection = ReviewProjection(
        (host, point), (date(2026, 1, 1), date(2026, 1, 3)), (), (),
        lane_membership=membership,
        lane_rows=(ReviewLaneRowProjection(lane_id, "g", (host, point), ("host", "gate")),),
    )
    view = replace(typed_view({"body": {"tableColumns": (), "visibility": {}}}),
                   rows=ViewRows("lanes", (), lane_table=ViewLaneTable(ViewLaneLabel.LANE, True)))

    table = normalize_v05_table_content(projection, {"entities": {"g": {"title": "Entity group"}}}, view)

    assert [column.column_id for column in table.columns] == ["Lane", "Items"]
    assert [(cell.object_id, cell.column_id, cell.content) for cell in table.cells] == [
        (lane_id, "Lane", "Entity group"), (lane_id, "Items", "2"),
    ]
    assert table.cell_objects == ()
    assert table.row_levels[0].keys == (lane_id,)


def test_ungrouped_attached_lane_uses_host_title_not_generated_identity():
    host = ReviewItem("host", "Campaign title", "span", {}, None, None, (), item_id="host")
    gate = ReviewItem("gate", "Readiness title", "point", {}, None, None, (),
                      item_id="gate", attached_to="host")
    lane_id = 'review-lane:["generated","","host"]'
    membership = LaneMembership(
        (Lane(lane_id, "", ("host", "gate")),),
        (LaneAssignment("host", lane_id, "", "single", "host"),
         LaneAssignment("gate", lane_id, "", "attached", "host")),
    )
    projection = ReviewProjection(
        (host, gate), (date(2026, 1, 1), date(2026, 1, 2)), (), (),
        lane_membership=membership,
        lane_rows=(ReviewLaneRowProjection(lane_id, "", (host, gate), ("host", "gate")),),
    )
    view = replace(typed_view({"body": {"tableColumns": (), "visibility": {}}}),
                   rows=ViewRows("lanes", (), lane_table=ViewLaneTable(ViewLaneLabel.LANE, True)))

    table = normalize_v05_table_content(projection, {}, view)
    assert [cell.content for cell in table.cells] == ["Campaign title", "2"]
    group_view = replace(view, rows=replace(view.rows, lane_table=ViewLaneTable(ViewLaneLabel.GROUP, True)))
    assert normalize_v05_table_content(projection, {}, group_view).cells[0].content == ""


def test_lane_table_group_label_repeats_blank_and_lane_labels_use_project_titles():
    first = ReviewItem("a", "Private member title A", "span", {}, None, None, (), group_id="g", item_id="a")
    second = ReviewItem("b", "Private member title B", "span", {}, None, None, (), group_id="g", item_id="b")
    lanes = (Lane("lane-a", "g", ("a",), "key-a"), Lane("lane-b", "g", ("b",), "key-b"))
    membership = LaneMembership(lanes, (
        LaneAssignment("a", "lane-a", "g", "explicit", "key-a"),
        LaneAssignment("b", "lane-b", "g", "explicit", "key-b"),
    ))
    projection = ReviewProjection(
        (first, second), (date(2026, 1, 1), date(2026, 1, 2)), (), (),
        lane_membership=membership,
        lane_rows=(ReviewLaneRowProjection("lane-a", "g", (first,)),
                   ReviewLaneRowProjection("lane-b", "g", (second,))),
    )
    view = replace(typed_view({"body": {"tableColumns": (), "visibility": {}}}),
                   rows=ViewRows("lanes", (), lane_table=ViewLaneTable(ViewLaneLabel.GROUP, True)))

    group_table = normalize_v05_table_content(projection, {"entities": {"g": {"title": "Group"}}}, view)
    assert [(cell.object_id, cell.column_id, cell.content) for cell in group_table.cells] == [
        ("lane-a", "Lane", "Group"), ("lane-a", "Items", "1"),
        ("lane-b", "Lane", ""), ("lane-b", "Items", "1"),
    ]

    lane_view = replace(view, rows=replace(view.rows, lane_table=ViewLaneTable(ViewLaneLabel.LANE, False)))
    lane_table = normalize_v05_table_content(projection, {}, lane_view)
    assert [cell.content for cell in lane_table.cells] == [
        "Private member title A", "Private member title B",
    ]


def test_lane_table_disambiguates_multiple_multi_member_lanes_in_one_group():
    items = tuple(ReviewItem(identifier, title, "span", {}, None, None, (),
                             group_id="g", item_id=identifier)
                  for identifier, title in (("a", "Alpha"), ("b", "Beta"),
                                            ("c", "Gamma"), ("d", "Delta")))
    lanes = (Lane("lane-a", "g", ("a", "b"), "key-a"),
             Lane("lane-b", "g", ("c", "d"), "key-b"))
    membership = LaneMembership(lanes, tuple(
        LaneAssignment(item_id, lane.lane_id, "g", "explicit", lane.explicit_key)
        for lane in lanes for item_id in lane.member_item_ids))
    projection = ReviewProjection(items, (date(2026, 1, 1), date(2026, 1, 2)), (), (),
                                  lane_membership=membership,
                                  lane_rows=(ReviewLaneRowProjection("lane-a", "g", items[:2], ("a", "b")),
                                             ReviewLaneRowProjection("lane-b", "g", items[2:], ("c", "d"))))
    view = replace(typed_view({"body": {"tableColumns": (), "visibility": {}}}),
                   rows=ViewRows("lanes", (), lane_table=ViewLaneTable(ViewLaneLabel.LANE, False)))

    table = normalize_v05_table_content(projection, {"entities": {"g": {"title": "Group"}}}, view)

    assert [cell.content for cell in table.cells] == ["Group — Alpha", "Group — Gamma"]


def test_lane_table_fails_when_project_titles_are_missing_instead_of_showing_ids():
    item = ReviewItem("object-id", "object-id", "span", {}, None, None, (),
                      group_id="g", item_id="object-id")
    lane = Lane("generated-lane-id", "g", ("object-id",))
    membership = LaneMembership((lane,), (LaneAssignment("object-id", lane.lane_id, "g", "single", "object-id"),))
    projection = ReviewProjection((item,), (date(2026, 1, 1), date(2026, 1, 2)), (), (),
                                  lane_membership=membership,
                                  lane_rows=(ReviewLaneRowProjection(lane.lane_id, "g", (item,), ("object-id",)),))
    view = replace(typed_view({"body": {"tableColumns": (), "visibility": {}}}),
                   rows=ViewRows("lanes", (), lane_table=ViewLaneTable(ViewLaneLabel.LANE, False)))

    with pytest.raises(ValueError, match="E_REVIEW_LANE_TITLE_MISSING:object-id"):
        normalize_v05_table_content(projection, {}, view)


def typed_view(value):
    body = value["body"]
    grouping = body.get("grouping")
    visibility = body.get("visibility", {})
    return ViewInput(
        None,
        ViewGrouping(grouping["by"], grouping.get("field"), tuple(grouping.get("order", ())), grouping.get("missing"), grouping.get("presentation"), grouping.get("depth"), grouping.get("rollup")) if grouping else None,
        None,
        ViewWindow(body.get("window", {}).get("mode", "selected-planned"), None, None, 0),
        ViewComparison(None, body.get("comparison", {}).get("actual", "optional"), None, None, ()),
        ViewVisibility(visibility.get("labels", False), visibility.get("relations", "none"), visibility.get("annotations", "none")),
        tuple(TableColumn(item["id"], item["source"],
                          (BooleanPresencePresentation(item["format"]["whenTrue"], item["format"]["whenFalse"])
                           if isinstance(item.get("format"), dict) else item.get("format", "text")), item["missing"],
                          item.get("align", "start"), item.get("width", "content"))
              for item in body.get("tableColumns", ())),
        tuple(freeze(item) for item in body.get("annotations", ())), ViewRows(body.get("rows", {}).get("mode", "automatic"), ()),
        freeze(body.get("axis")) if body.get("axis") else None, tuple(freeze(item) for item in body.get("markers", ())),
        freeze(body.get("shading")) if body.get("shading") else None,
        freeze(body.get("timePresentation")) if body.get("timePresentation") else None,
        body.get("annotationPresentation"),
    )


def typed_summary(value):
    body = value["body"]
    panels = []
    for panel in body["panels"]:
        declared = panel["metrics"]
        entries = declared.items() if isinstance(declared, dict) else ((item["id"], item) for item in declared)
        metrics = tuple(
            SummaryMetric(metric_id, definition.get("label", metric_id), definition["source"], definition["format"], definition.get("scope"))
            if isinstance(definition, dict) else (metric_id, definition)
            for metric_id, definition in entries
        )
        panels.append(SummaryPanelInput(panel["id"], panel.get("title"), panel.get("presentation", "lines"), metrics))
    return SummaryProfileInput(tuple(panels))


def test_scale_legend_entry_label_prefers_the_entitys_declared_title():
    # #427: a colour-scale legend entry shows entities.<id>.title when the
    # project declares one, falling back to the raw field value otherwise.
    projection = ReviewProjection(
        (ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 2)}, None, None, (),
                    fields={"owner": "bus"}, source_kind="primary"),
         ReviewItem("b", "B", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 2)}, None, None, (),
                    fields={"owner": "ground"}, source_kind="primary")),
        (date(2026, 1, 1), date(2026, 1, 2)), (), ())
    project = {"relations": (), "annotations": {}, "entities": {"bus": {"title": "Spacecraft bus"}}}
    view = {"body": {"tableColumns": (), "visibility": {}}}
    color_scale = ResolvedColorScale("owner", "planned", "owner", ("bus", "ground"),
                                     (("bus", "#111111"), ("ground", "#222222")))
    value = normalize_v05_surface_content(projection, project, typed_view(view), summary=EMPTY_SUMMARY,
                                          color_scale=color_scale)
    legend = dict(value.legend_entries)
    assert legend["scale:owner:bus"] == "Spacecraft bus"
    assert legend["scale:owner:ground"] == "ground"


def test_optional_content_is_selected_only_from_current_project_and_view():
    projection = ReviewProjection((ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 2)}, None, None, ()),), (date(2026, 1, 1), date(2026, 1, 2)), (), ())
    project = {"relations": ({"id": "r", "from": {"object": "a"}, "to": {"object": "a"}},), "annotations": {"n": {"text": "note"}}}
    view = {"body": {"tableColumns": ({"id": "Name", "source": "title", "missing": "blank"},), "visibility": {"relations": "semantic", "annotations": "none"}}}
    value = normalize_v05_surface_content(projection, project, typed_view(view), summary=EMPTY_SUMMARY)
    assert value.table_cells == (TableCellContent("a", "Name", "A", "tableCell"),)
    assert value.relations[0].relation_id == "r"
    assert value.notes == (("n", "note"),)


def test_view_annotation_ladder_normalizes_to_typed_candidates() -> None:
    projection = ReviewProjection((), (date(2026, 1, 1), date(2026, 1, 2)), (), ())
    view = typed_view({"body": {
        "visibility": {"relations": "none", "annotations": "all"},
        "annotations": ({"id": "callout", "purpose": "callout",
                         "anchor": {"kind": "object", "id": "a", "facet": "planned", "endpoint": "at"},
                         "placement": {"side": "above", "alignment": "center"}, "text": "Check"},),
    }})
    value = normalize_v05_surface_content(projection, {}, view, summary=EMPTY_SUMMARY)
    assert value.annotations[0].fallback_ladder == ("rail",)
    assert value.annotations[0].candidates[0].region.kind == "slot"
    assert value.annotations[0].candidates[0].search.kind == "row-aligned"
    assert value.annotations[0].candidates[0].connector.kind == "leader"


def test_table_column_intent_is_normalized_before_layout_ingress():
    projection = ReviewProjection((), (date(2026, 1, 1), date(2026, 1, 2)), (), ())
    view = {"body": {"tableColumns": (
        {"id": "Delta", "source": "totalFloat", "missing": "em-dash", "align": "end", "width": {"fr": 2}},
        {"id": "Title", "source": "title", "missing": "em-dash", "align": "start",
         "width": {"minmax": {"min": "content", "max": "fill"}}},
    ), "visibility": {"relations": "none", "annotations": "none"}}}
    value = normalize_v05_surface_content(projection, {"relations": (), "annotations": {}}, typed_view(view), summary=EMPTY_SUMMARY)
    assert [(column.column_id, column.align, column.width.minimum, column.width.maximum, column.width.fraction)
            for column in value.table_columns] == [("Delta", "end", "ellipsis", "fr", 2.0),
                                                    ("Title", "start", "content", "fill", 1.0)]


def test_axis_name_table_override_is_normalized_independently_of_context_locale():
    projection = ReviewProjection((), (date(2026, 1, 1), date(2026, 2, 1)), (), ())
    label = {"form": "short-month", "align": "start", "overflow": "visible-overflow",
             "orientation": "horizontal", "nameTable": "en-US"}
    view = typed_view({"body": {"axis": {"tiers": [
        {"unit": "month", "every": 1, "role": "labels", "label": label},
    ]}, "visibility": {"relations": "none", "annotations": "none"}}})
    value = normalize_v05_surface_content(projection, {}, view, summary=EMPTY_SUMMARY, locale="ja-JP")
    assert value.axis_tiers[0].label.name_table_id == "en-US"

    label.pop("nameTable")
    view = typed_view({"body": {"axis": {"tiers": [
        {"unit": "month", "every": 1, "role": "labels", "label": label},
    ]}, "visibility": {"relations": "none", "annotations": "none"}}})
    value = normalize_v05_surface_content(projection, {}, view, summary=EMPTY_SUMMARY, locale="ja-JP")
    assert value.axis_tiers[0].label.name_table_id == "ja-JP"


def test_table_cell_semantics_follow_declared_source_not_item_role_order():
    ahead = ReviewItem("ahead", "Ahead", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 2)}, {}, -2, ("planned", "variance-ahead"))
    on_plan = ReviewItem("plan", "Plan", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 2)}, {}, 0, ("variance-behind",))
    behind = ReviewItem("behind", "Behind", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 2)}, {}, 4, ("variance-ahead",))
    unknown = ReviewItem("unknown", "Unknown", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 2)}, {}, None, ("variance-behind",))
    missing = ReviewItem("missing", "Missing", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 2)}, None, None, (), observation_state=ObservationState.DUE_UNOBSERVED)
    projection = ReviewProjection((ahead, on_plan, behind, unknown, missing), (date(2026, 1, 1), date(2026, 1, 3)), (), ())
    view = {"body": {"tableColumns": (
        {"id": "Delta", "source": {"comparisonFacet": "finishDelta"}, "format": "signedDays", "missing": "em-dash"},
        {"id": "Missing", "source": {"comparisonFacet": "missingActual"},
         "format": {"kind": "presence", "whenTrue": "Missing", "whenFalse": "Recorded"}, "missing": "em-dash"},
        {"id": "Title", "source": "title", "missing": "em-dash"},
    ), "visibility": {"relations": "none", "annotations": "none"}}}
    value = normalize_v05_surface_content(projection, {"relations": (), "annotations": {}}, typed_view(view), summary=EMPTY_SUMMARY)
    selected = {(cell.object_id, cell.column_id): cell.semantic_id for cell in value.table_cells}
    assert [selected[(item, "Delta")] for item in ("ahead", "plan", "behind", "unknown")] == ["tableVarianceAhead", "tableVarianceOnTrack", "tableVarianceBehind", "tableCell"]
    assert selected[("missing", "Missing")] == "missingActualCell"
    assert all(selected[(item, "Title")] == "tableCell" for item in ("ahead", "plan", "behind", "unknown", "missing"))


def test_missing_actual_summary_counts_due_absences_and_requires_as_of():
    projection = ReviewProjection(tuple(
        ReviewItem(state.value, state.value, "span", {"start": date(2027, 8, 1), "end": date(2027, 8, 20)},
                   None, None, (), observation_state=state)
        for state in ObservationState), (date(2027, 8, 1), date(2027, 8, 21)), (), ())
    summary = typed_summary({"body": {"panels": [{"id": "facts", "metrics": {
        "missing": {"label": "Missing", "source": "count.missingActual", "format": "count"},
    }}]}})
    present = normalize_summary_content(summary, projection, {"body": {"asOf": "2027-08-20"}})
    absent = normalize_summary_content(summary, projection, None)
    assert "Missing: 1" in tuple(run.content for run in present.runs)
    assert "Missing: unknown" in tuple(run.content for run in absent.runs)


def test_critical_relation_mode_uses_only_scheduler_driving_relations():
    projection = ReviewProjection((
        ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 2)}, None, None, (), critical=True),
        ReviewItem("b", "B", "span", {"start": date(2026, 1, 2), "end": date(2026, 1, 3)}, None, None, (), critical=True),
        ReviewItem("c", "C", "span", {"start": date(2026, 1, 2), "end": date(2026, 1, 3)}, None, None, (), critical=False),
    ), (date(2026, 1, 1), date(2026, 1, 3)), (), (), driving_relations=frozenset({"relation:0:critical"}))
    project = {"relations": (
        {"id": "critical", "from": {"object": "a"}, "to": {"object": "b"}},
        {"id": "slack", "from": {"object": "a"}, "to": {"object": "c"}},
    ), "annotations": {}}
    view = {"body": {"tableColumns": (), "visibility": {"relations": "critical", "annotations": "none"}}}
    value = normalize_v05_surface_content(projection, project, typed_view(view), summary=EMPTY_SUMMARY)
    assert value.relations[0].relation_id == "critical"
    assert value.relations[0].semantic_id == "dependency-critical"
    assert value.relations[0].source_endpoint == "end"
    assert value.relations[0].target_endpoint == "start"


def test_calendar_closures_come_only_from_project_calendar_exceptions():
    projection = ReviewProjection((ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 5)}, None, None, ()),),
                                  (date(2026, 1, 1), date(2026, 1, 5)), (), ())
    project = {"project": {"calendar": "standard"},
               "calendars": {"standard": {"working_days": ["mon", "tue", "wed", "thu", "fri"],
                                           "exceptions": [{"date": "2026-01-01", "working": True}]}},
               "relations": (), "annotations": {}}
    view = {"body": {"tableColumns": (), "visibility": {"relations": "none", "annotations": "none"}}}

    value = normalize_v05_surface_content(projection, project, typed_view(view), summary=EMPTY_SUMMARY)

    assert value.calendar_closed == (date(2026, 1, 3), date(2026, 1, 4))
    assert value.calendar_exceptions == ()


def test_calendar_exception_closures_are_explicit_and_view_eligible():
    projection = ReviewProjection((), (date(2026, 1, 1), date(2026, 1, 4)), (), ())
    project = {"project": {"calendar": "standard"}, "calendars": {"standard": {
        "working_days": ["mon", "tue", "wed", "thu", "fri"],
        "exceptions": [{"date": "2026-01-02", "working": False}],
    }}, "relations": (), "annotations": {}}
    view = {"body": {"tableColumns": (), "visibility": {"relations": "none", "annotations": "none"},
                      "shading": {"nonWorking": False, "exceptions": True}}}
    value = normalize_v05_surface_content(projection, project, typed_view(view), summary=EMPTY_SUMMARY)
    assert value.calendar_closed == (date(2026, 1, 2),)
    assert value.calendar_exceptions == (date(2026, 1, 2),)


def test_actual_missing_display_uses_item_kind_and_actual_cutoff():
    projection = ReviewProjection((
        ReviewItem("active", "Active", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 10)}, None, None, ()),
        ReviewItem("future", "Future", "span", {"start": date(2026, 1, 11), "end": date(2026, 1, 20)}, None, None, ()),
        ReviewItem("gate", "Gate", "point", {"at": date(2026, 1, 5)}, None, None, ()),
    ), (date(2026, 1, 1), date(2026, 1, 20)), (), ())
    view = {"body": {"tableColumns": ({"id": "Actual", "source": {"facet": "actual"}, "format": "dateRange", "missing": "in-progress"},),
                     "visibility": {"labels": False, "relations": "none", "annotations": "none"}}}
    value = normalize_v05_surface_content(projection, {"relations": (), "annotations": {}}, typed_view(view),
                                          actual_set={"body": {"asOf": "2026-01-05"}}, summary=EMPTY_SUMMARY)
    assert value.table_cells == (TableCellContent("active", "Actual", "in progress", "tableCell"), TableCellContent("future", "Actual", "—", "tableCell"), TableCellContent("gate", "Actual", "—", "tableCell"))


def test_date_range_is_compact_and_retains_cross_year_precision():
    projection = ReviewProjection((ReviewItem("a", "A", "span", {"start": date(2026, 12, 31), "end": date(2027, 1, 2)}, None, None, ()),),
                                  (date(2026, 12, 1), date(2027, 2, 1)), (), ())
    view = {"body": {"tableColumns": ({"id": "Plan", "source": {"facet": "planned"}, "format": "dateRange", "missing": "em-dash"},),
                     "visibility": {"labels": False, "relations": "none", "annotations": "none"}}}
    value = normalize_v05_surface_content(projection, {"relations": (), "annotations": {}}, typed_view(view), summary=EMPTY_SUMMARY)
    assert value.table_cells == (TableCellContent("a", "Plan", "31 Dec 2026 – 02 Jan 2027", "tableCell"),)


def test_scenario_table_facts_use_the_table_subject_and_missing_policy():
    scenario = ReviewItem("task", "Delayed", "span", {"start": date(2026, 2, 1), "end": date(2026, 2, 2)},
                          None, None, (), item_id="delayed", source_kind="scenario", scenario_id="delayed")
    primary = ReviewItem("task", "Current", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 2)},
                         None, None, (), item_id="current", source_kind="primary")
    projection = ReviewProjection((primary,), (date(2026, 1, 1), date(2026, 2, 2)), (), (),
                                  (ReviewRowProjection("scenario", "Scenario", "", "delayed", (primary, scenario)),))
    view = {"body": {"tableColumns": (
        {"id": "Scenario", "source": {"scenario": "title"}, "missing": "em-dash"},
        {"id": "Scenario id", "source": {"scenario": "id"}, "missing": "em-dash"},
    ), "visibility": {"labels": False, "relations": "none", "annotations": "none"}}}
    value = normalize_v05_surface_content(projection, {"scenarios": {"delayed": {"title": "Delayed launch"}},
                                                        "relations": (), "annotations": {}}, typed_view(view), summary=EMPTY_SUMMARY)
    assert value.table_cells == (TableCellContent("scenario", "Scenario", "Delayed launch", "tableCell"), TableCellContent("scenario", "Scenario id", "delayed", "tableCell"))


def test_scenario_summary_facts_are_stable_and_limited_to_selected_sources():
    early = ReviewItem("task", "Early", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 2)},
                       None, None, (), item_id="early", source_kind="scenario", scenario_id="early")
    late = ReviewItem("task", "Late", "span", {"start": date(2026, 2, 1), "end": date(2026, 2, 2)},
                      None, None, (), item_id="late", source_kind="scenario", scenario_id="late")
    projection = ReviewProjection((), (date(2026, 1, 1), date(2026, 2, 2)), (), (),
                                  (ReviewRowProjection("r", "", "", "early", (late, early)),))
    summary = {"body": {"panels": [{"id": "facts", "metrics": {
        "ids": {"label": "Scenarios", "source": {"scenario": "id"}, "format": "text"},
        "titles": {"label": "Hypotheses", "source": {"scenario": "title"}, "format": "text"},
    }}]}}
    content = normalize_summary_content(typed_summary(summary), projection, None,
                                        {"scenarios": {"late": {"title": "Late launch"}, "early": {"title": "Early launch"}}})
    assert tuple(run.content for run in content.runs) == (
        "facts", "Scenarios: early, late", "Hypotheses: Early launch, Late launch")


def test_structured_temporal_and_annotation_presentation_is_normalized():
    projection = ReviewProjection((ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 5)}, None, None, ()),),
                                  (date(2026, 1, 1), date(2026, 1, 5)), (), ())
    view = {"body": {"tableColumns": (), "visibility": {"labels": {"members": True}, "relations": "none", "annotations": "presentation"},
                         "axis": {"tiers": [{"unit": "week", "every": 1, "role": "labels", "label": {"form": "iso-week", "align": "start", "overflow": "visible-overflow", "orientation": "horizontal"}}]},
                         "timePresentation": {"asOf": "hidden", "calendarClosed": False},
                     "annotationPresentation": "numbered", "annotations": [{"id": "note", "purpose": "note", "anchor": {"kind": "object", "id": "a", "facet": "planned", "endpoint": "finish"}, "placement": {"side": "end", "alignment": "center"}, "text": "Watch this"}]}}
    value = normalize_v05_surface_content(projection, {"relations": (), "annotations": {}}, typed_view(view),
                                          actual_set={"body": {"asOf": "2026-01-03"}}, summary=EMPTY_SUMMARY)
    assert value.show_member_labels is True
    assert value.axis_tiers[0].unit == "week"
    assert value.as_of is None
    assert value.calendar_closed == ()
    assert value.annotations[0].annotation_id == "note"
    assert value.annotations[0].content == "Watch this"
    assert value.annotations[0].number == 1


def test_annotation_anchor_end_is_normalized_to_finish_at_ingress():
    # I662 S4a: `end` aliases `finish` in a View anchor and is normalised once, because the endpoint text appears in Scene ids.
    projection = ReviewProjection((ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 5)}, None, None, ()),),
                                  (date(2026, 1, 1), date(2026, 1, 5)), (), ())

    def annotation(endpoint):
        return {"id": endpoint, "purpose": "note", "anchor": {"kind": "object", "id": "a", "facet": "planned", "endpoint": endpoint},
                "placement": {"side": "end", "alignment": "center"}, "text": "Watch this"}

    view = {"body": {"tableColumns": (), "visibility": {"labels": {"members": True}, "relations": "none", "annotations": "presentation"},
                     "axis": {"tiers": [{"unit": "week", "every": 1, "role": "labels", "label": {"form": "iso-week", "align": "start", "overflow": "visible-overflow", "orientation": "horizontal"}}]},
                     "timePresentation": {"asOf": "hidden", "calendarClosed": False}, "annotationPresentation": "numbered",
                     "annotations": [annotation(endpoint) for endpoint in ("end", "finish", "start", "at", "body")]}}
    value = normalize_v05_surface_content(projection, {"relations": (), "annotations": {}}, typed_view(view),
                                          actual_set={"body": {"asOf": "2026-01-03"}}, summary=EMPTY_SUMMARY)
    assert [item.anchor["endpoint"] for item in value.annotations] == ["finish", "finish", "start", "at", "body"]
    assert [item.anchor["endpoint"] for item in value.annotations if item.annotation_id == "end"] == ["finish"]


def test_typed_summary_figures_resolve_projection_and_actual_facts():
    projection = ReviewProjection((
        ReviewItem("a", "A", "point", {"at": date(2026, 2, 4)}, {"at": date(2026, 2, 5)}, None, ()),
        ReviewItem("b", "B", "span", {"start": date(2026, 2, 1), "end": date(2026, 2, 3)}, None, 2, ()),
    ), (date(2026, 2, 1), date(2026, 2, 8)), (), ())
    summary = {"body": {"panels": [{"id": "facts", "metrics": {
        "as_of": {"label": "As of", "source": "actual.asOf", "format": "date"},
        "next": {"label": "Next", "source": "planned.nextPoint", "format": "date"},
        "selected": {"label": "Selected", "source": "count.selected", "format": "count"},
        "variance": {"label": "Variance", "source": "count.knownFinishVariance", "format": "count"},
    }}]}}
    view = {"body": {"tableColumns": (), "visibility": {"labels": False, "relations": "none", "annotations": "none"}}}
    content = normalize_summary_content(typed_summary(summary), projection, {"body": {"asOf": "2026-02-03"}})
    value = normalize_v05_surface_content(projection, {"relations": (), "annotations": {}}, typed_view(view),
                                          actual_set={"body": {"asOf": "2026-02-03"}}, summary=content)
    assert tuple((run.content, run.typography_role) for run in value.summary.runs) == (
        ("facts", "summary"), ("As of: 2026-02-03", "summary"), ("Next: 2026-02-04", "summary"),
        ("Selected: 2", "summary"), ("Variance: 1", "summary"),
    )


def test_target_summary_figure_list_form_is_resolved_without_copied_values():
    projection = ReviewProjection((
        ReviewItem("launch", "Launch", "point", {"at": date(2026, 3, 8)}, None, None, ()),
        ReviewItem("late", "Late", "span", {"start": date(2026, 3, 1), "end": date(2026, 3, 2)}, None, 4, ()),
    ), (date(2026, 3, 1), date(2026, 3, 9)), (), ())
    summary = {"body": {"panels": [{"id": "figures", "presentation": "figures", "metrics": [
        {"id": "as-of", "label": "as of", "source": {"actual": "asOf"}, "format": "date"},
        {"id": "launch", "label": "launch", "source": {"object": "launch", "facet": "planned"}, "format": "date"},
        {"id": "variance", "label": "behind / ahead", "source": {"counts": "finishDelta"}, "format": "text"},
    ]}]}}
    view = {"body": {"tableColumns": (), "visibility": {"labels": False, "relations": "none", "annotations": "none"}}}
    content = normalize_summary_content(typed_summary(summary), projection, {"body": {"asOf": "2026-03-04"}})
    value = normalize_v05_surface_content(projection, {"relations": (), "annotations": {}}, typed_view(view),
                                          actual_set={"body": {"asOf": "2026-03-04"}}, summary=content)
    assert tuple((run.content, run.typography_role) for run in value.summary.runs) == (
        ("figures", "summary"), ("2026-03-04", "metric"), ("as of", "summary"),
        ("2026-03-08", "metric"), ("launch", "summary"), ("1 / 0", "metric"), ("behind / ahead", "summary"),
    )


def test_subtree_summary_normalizes_latest_selected_primary_planned_completion():
    projection = ReviewProjection((
        ReviewItem("programme", "Programme", "span", {"start": date(2026, 3, 1), "end": date(2026, 3, 4)}, None, None, (),
                   hierarchy_path=("programme",)),
        ReviewItem("build", "Build", "span", {"start": date(2026, 3, 2), "end": date(2026, 3, 9)}, None, None, (),
                   hierarchy_path=("programme", "build")),
        ReviewItem("launch", "Launch", "point", {"at": date(2026, 3, 12)}, None, None, (),
                   hierarchy_path=("programme", "launch")),
        ReviewItem("baseline", "Baseline", "span", {"start": date(2026, 3, 1), "end": date(2026, 4, 1)}, None, None, (),
                   item_id="baseline", source_kind="snapshot", hierarchy_path=("programme", "build")),
    ), (date(2026, 3, 1), date(2026, 3, 12)), (), (), hierarchy_grouping=True)
    summary = {"body": {"panels": [{"id": "completion", "metrics": {
        "planned": {"label": "Complete", "source": {"object": "programme", "facet": "planned"},
                    "scope": "subtree", "format": "date"},
    }}]}}

    content = normalize_summary_content(typed_summary(summary), projection, None)

    assert tuple(run.content for run in content.runs) == ("completion", "Complete: 2026-03-12")


@pytest.mark.parametrize("projection", (
    ReviewProjection((ReviewItem("programme", "Programme", "span", {"start": date(2026, 3, 1), "end": date(2026, 3, 4)}, None, None, (),
                                 hierarchy_path=("programme",)),), (date(2026, 3, 1), date(2026, 3, 4)), (), ()),
    ReviewProjection((ReviewItem("other", "Other", "span", {"start": date(2026, 3, 1), "end": date(2026, 3, 4)}, None, None, (),
                                 hierarchy_path=("other",)),), (date(2026, 3, 1), date(2026, 3, 4)), (), (), hierarchy_grouping=True),
))
def test_subtree_summary_rejects_non_hierarchy_or_unselected_root(projection):
    summary = {"body": {"panels": [{"id": "completion", "metrics": {
        "planned": {"source": {"object": "programme", "facet": "planned"}, "scope": "subtree", "format": "date"},
    }}]}}
    with pytest.raises(ValueError, match="E_PRESENTATION_SUMMARY_SOURCE"):
        normalize_summary_content(typed_summary(summary), projection, None)


def test_target_view_contract_normalizes_plot_labels_marker_and_axis():
    projection = ReviewProjection((ReviewItem("a", "A", "span", {"start": date(2026, 3, 1), "end": date(2026, 3, 2)}, None, 2, ()),),
                                  (date(2026, 3, 1), date(2026, 3, 8)), (), ())
    view = {"body": {"tableColumns": (),
                     "visibility": {"labels": {"placement": "plot", "content": ["title", "finishDelta"], "side": "auto"},
                                    "relations": "none", "annotations": {"mode": "presentation", "marker": "numbered"}},
                     "axis": {"tiers": [{"unit": "quarter", "every": 1, "role": "band"}, {"unit": "month", "every": 1, "role": "labels", "label": {"form": "short-month", "align": "start", "overflow": "visible-overflow", "orientation": "horizontal"}}]},
                     "markers": [{"kind": "asOf", "source": "actual", "label": "as of"}], "shading": {"nonWorking": False}}}
    value = normalize_v05_surface_content(projection, {"relations": (), "annotations": {}}, typed_view(view),
                                          actual_set={"body": {"asOf": "2026-03-04"}}, summary=EMPTY_SUMMARY)
    assert value.label_placement == "plot"
    assert value.label_content == ("title", "finishDelta")
    assert value.label_side == "auto"
    assert value.label_overflow == "visible-overflow"
    assert tuple((tier.unit, tier.role) for tier in value.axis_tiers) == (("quarter", "band"), ("month", "labels"))
    assert value.as_of_label == "as of"


def test_actual_set_requires_the_current_body_envelope():
    projection = ReviewProjection((), (date(2026, 3, 1), date(2026, 3, 8)), (), ())
    view = {"body": {"tableColumns": (), "visibility": {"labels": False, "relations": "none", "annotations": "none"}}}
    with pytest.raises(ValueError, match="E_PRESENTATION_ACTUAL_SET_SHAPE"):
        normalize_v05_surface_content(projection, {"relations": (), "annotations": {}}, typed_view(view),
                                      summary=EMPTY_SUMMARY, actual_set={"asOf": "2026-03-04"})


def test_project_annotation_reference_selects_text_once_and_leaves_notes_slot() -> None:
    """#466: a selected Project note is consumed once, not duplicated."""
    projection = ReviewProjection((), (date(2026, 1, 1), date(2026, 1, 2)), (), ())
    project = {"annotations": {"window": {"text": "Launch window closes soon."},
                                "other": {"text": "Unrelated note."}}}
    view = typed_view({"body": {
        "visibility": {"relations": "none", "annotations": "all"},
        "annotations": ({"id": "window-note", "purpose": "note",
                         "anchor": {"kind": "object", "id": "a", "facet": "planned", "endpoint": "at"},
                         "placement": {"side": "above", "alignment": "center"},
                         "projectAnnotation": "window"},),
    }})
    value = normalize_v05_surface_content(projection, project, view, summary=EMPTY_SUMMARY)
    assert value.annotations[0].content == "Launch window closes soon."
    assert value.notes == (("other", "Unrelated note."),)


def test_project_annotation_reference_to_a_missing_id_is_a_stable_ingress_error() -> None:
    projection = ReviewProjection((), (date(2026, 1, 1), date(2026, 1, 2)), (), ())
    view = typed_view({"body": {
        "visibility": {"relations": "none", "annotations": "all"},
        "annotations": ({"id": "window-note", "purpose": "note",
                         "anchor": {"kind": "object", "id": "a", "facet": "planned", "endpoint": "at"},
                         "placement": {"side": "above", "alignment": "center"},
                         "projectAnnotation": "missing"},),
    }})
    with pytest.raises(ValueError, match="E_PRESENTATION_ANNOTATION_REFERENCE_MISSING"):
        normalize_v05_surface_content(projection, {"annotations": {}}, view, summary=EMPTY_SUMMARY)


def test_as_of_label_is_the_declared_text_and_a_date_only_in_a_declared_form():
    """#428: no date is appended unless the View states its form."""
    from datetime import date as _date
    from chrona.presentation.review.v05_content import _as_of_label
    as_of = _date(2027, 8, 20)
    assert _as_of_label({"kind": "asOf", "source": "actual", "label": "Today"}, as_of, "en-US") == "Today"
    dated = {"kind": "asOf", "source": "actual", "label": "as of", "date": {"form": "localized-date"}}
    assert _as_of_label(dated, as_of, "en-US") == "as of Aug 20, 2027"
    assert _as_of_label(dated, as_of, "ja-JP") == "as of 2027/08/20"
    assert _as_of_label({**dated, "date": {"form": "localized-date", "nameTable": "ja-JP"}}, as_of, "en-US") == "as of 2027/08/20"
    assert _as_of_label(None, as_of, "en-US") == "As of Aug 20, 2027"


def _scale_projection():
    items = tuple(ReviewItem(key, key.upper(), "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 2)},
                             None, None, (), fields={"owner": owner}, source_kind="primary")
                  for key, owner in (("a", "bus"), ("b", "ground")))
    return ReviewProjection(items, (date(2026, 1, 1), date(2026, 1, 2)), (), ())


def test_legend_entries_are_the_drawn_entries_detail_first_then_one_per_used_scale_value():
    # #497: Layout measures the legend slot from this list and draws the legend from it.
    project = {"relations": (), "annotations": {}, "entities": {"bus": {"title": "Spacecraft bus"}}}
    color_scale = ResolvedColorScale("owner", "planned", "owner", ("bus", "ground", "unused"),
                                     (("bus", "#111111"), ("ground", "#222222"), ("unused", "#333333")))
    detail = ReviewDetailInput((), (), (LegendEntry("planned", "Planned"),), None)

    entries = legend_entries(detail, project, _scale_projection(), color_scale, closed_days_drawn=True)

    assert entries == (("planned", "Planned"), ("scale:owner:bus", "Spacecraft bus"), ("scale:owner:ground", "ground"))
    drawn = normalize_v05_surface_content(_scale_projection(), project,
                                          typed_view({"body": {"tableColumns": (), "visibility": {}}}),
                                          summary=EMPTY_SUMMARY, color_scale=color_scale, detail=detail)
    assert drawn.legend_entries == entries


def test_without_a_scale_or_a_detail_profile_there_are_no_legend_entries():
    assert legend_entries(None, {}, _scale_projection(), None, closed_days_drawn=True) == ()


def test_a_project_without_a_default_calendar_has_no_closed_day():
    # #893: no declared calendar declares no closed day; the scheduler assumes no week either.
    projection = ReviewProjection((), (date(2026, 1, 1), date(2026, 1, 8)), (), ())
    view = typed_view({"body": {"tableColumns": (), "visibility": {"relations": "none", "annotations": "none"}}})
    for project in ({"relations": (), "annotations": {}},
                    {"project": {}, "calendars": {"standard": {"working_days": ["mon"]}}, "relations": (), "annotations": {}},
                    {"project": {"calendar": "missing"}, "calendars": {}, "relations": (), "annotations": {}}):
        value = normalize_v05_surface_content(projection, project, view, summary=EMPTY_SUMMARY)
        assert (value.calendar_closed, value.calendar_exceptions) == ((), ())


def test_the_closed_day_legend_key_is_listed_only_when_a_closed_day_is_selected():
    detail = ReviewDetailInput((), (), (LegendEntry("planned", "Planned"), LegendEntry("calendar-closed", "Weekend")), None)
    projection = _scale_projection()
    assert legend_entries(detail, {}, projection, None, closed_days_drawn=True) == (
        ("planned", "Planned"), ("calendar-closed", "Weekend"))
    assert legend_entries(detail, {}, projection, None, closed_days_drawn=False) == (("planned", "Planned"),)
    project = {"project": {"calendar": "standard"}, "calendars": {"standard": {"working_days": ["mon", "tue", "wed", "thu", "fri"]}},
               "relations": (), "annotations": {}}
    view = typed_view({"body": {"tableColumns": (), "visibility": {}}})
    window = ReviewProjection((), (date(2026, 1, 1), date(2026, 1, 8)), (), ())
    keyed = normalize_v05_surface_content(window, project, view, summary=EMPTY_SUMMARY, detail=detail)
    bare = normalize_v05_surface_content(window, {"relations": (), "annotations": {}}, view, summary=EMPTY_SUMMARY, detail=detail)
    assert [role for role, _ in keyed.legend_entries] == ["planned", "calendar-closed"]
    assert [role for role, _ in bare.legend_entries] == ["planned"]
