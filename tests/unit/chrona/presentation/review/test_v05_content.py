from dataclasses import replace
from datetime import date

import pytest

from chrona.presentation.model.color_scale import ResolvedColorScale
from chrona.presentation.model.axis_color_scale import AxisBandFillSpec, AxisBandScaleError
from chrona.presentation.model.projection import (
    ObservationState, ReviewItem, ReviewProjection, ReviewRowProjection, ReviewLaneRowProjection,
)
from chrona.presentation.model.surface_content import HeadingContent, SummaryContent, TableCellContent, TableContent
from chrona.presentation.review.lane_membership import Lane, LaneAssignment, LaneMembership
from chrona.presentation.table_presentation import BooleanPresencePresentation
from chrona.presentation.review.v05_content import (
    _column_width, _group_headers, _resource_body, compose_heading, legend_entries, normalize_axis_tiers, normalize_summary_content, normalize_v05_surface_content, normalize_v05_table_content,
)
from chrona.presentation.contracts.resources import (
    LegendEntry, ReviewDetailInput, SummaryMetric, SummaryPanelInput, SummaryProfileInput, TableColumn, ViewComparison, ViewGroupHeader, ViewGrouping, ViewInput,
    ViewHeading, ViewLaneLabel, ViewLaneTable, ViewRows, ViewVisibility, ViewWindow, freeze,
)


EMPTY_SUMMARY = SummaryContent(())


def test_axis_band_fill_scale_is_retained_as_typed_intent_and_absence_stays_none():
    view = typed_view({"body": {"tableColumns": (), "visibility": {}, "axis": {"tiers": [
        {"unit": "quarter", "every": 1, "role": "band",
         "fillScale": {"scale": "phase", "key": "interval", "containingTier": 2}},
        {"unit": "month", "every": 1, "role": "band"},
    ]}}})

    tiers = normalize_axis_tiers(view, locale="en-US")

    assert tiers[0].fill_scale == AxisBandFillSpec("phase", "interval", 2)
    assert tiers[1].fill_scale is None


def test_axis_fill_scale_on_wrong_tier_uses_the_scale_target_diagnostic_and_tier_pointer():
    view = typed_view({"body": {"tableColumns": (), "visibility": {}, "axis": {"tiers": [
        {"unit": "month", "every": 1, "role": "band"},
        {"unit": "month", "every": 1, "role": "labels",
         "fillScale": {"scale": "phase", "key": "alternating"}},
    ]}}})

    with pytest.raises(AxisBandScaleError, match="E_PRESENTATION_AXIS_SCALE_TARGET") as error:
        normalize_axis_tiers(view, locale="en-US")
    assert error.value.path == "/view/body/axis/tiers/1/fillScale"
    assert error.value.detail == "target must be a fixed-unit band tier"


def test_compose_heading_returns_immutable_named_content_and_keeps_project_title_default():
    view = typed_view({"body": {"tableColumns": (), "visibility": {}}})
    assert compose_heading(view, {"project": {"title": "HALCYON"}}, None, "en-US") == HeadingContent("HALCYON")


def test_compose_heading_formats_kicker_title_and_subtitle_from_the_same_closed_facts():
    view = replace(
        typed_view({"body": {"tableColumns": (), "visibility": {}}}),
        heading=ViewHeading(title="{project} board", subtitle="Calendar {calendar}",
                            date_form="day-month-year", kicker="Episode {asOf} · {project}"),
    )

    content = compose_heading(
        view,
        {"project": {"title": "HALCYON", "calendar": "engineering"}},
        {"kind": "actual-set", "body": {"asOf": "2026-08-20"}},
        "en-US",
    )

    assert content == HeadingContent("HALCYON board", "Calendar engineering", "Episode 20 Aug 2026 · HALCYON")


def _calendar_heading(calendars, calendar="engineering"):
    view = replace(typed_view({"body": {"tableColumns": (), "visibility": {}}}),
                   heading=ViewHeading(subtitle="{calendar}", date_form="day-month-year"))
    project = {"project": {"title": "P", "calendar": calendar}, "calendars": calendars}
    return compose_heading(view, project, None, "en-US").subtitle


def test_heading_calendar_is_the_declared_title_else_the_id_else_empty():
    assert _calendar_heading({"engineering": {"title": "Engineering (JP)"}}) == "Engineering (JP)"
    assert _calendar_heading({"engineering": {}}) == "engineering"
    assert _calendar_heading({}) == "engineering"
    assert _calendar_heading({"other": {"title": "X"}}) == "engineering"
    assert _calendar_heading({"engineering": {"title": ""}}) == "engineering"
    assert _calendar_heading({}, calendar=None) == ""


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
    wrapped_view = replace(view, rows=replace(view.rows, lane_table=ViewLaneTable(ViewLaneLabel.LANE, True, "allow")))
    wrapped = normalize_v05_table_content(projection, {}, wrapped_view)
    assert all(column.text_wrap == "allow" for column in wrapped.columns)
    assert wrapped.cells == table.cells
    assert wrapped.row_levels == table.row_levels
    assert projection.lane_membership is membership
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

    with pytest.raises(ValueError, match="E_REVIEW_LANE_TITLE_MISSING:object-id") as error:
        normalize_v05_table_content(projection, {}, view)
    assert "/items/'object-id'/title='object-id'" in str(error.value)


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
        panels.append(SummaryPanelInput(panel["id"], panel.get("title"), panel.get("presentation", "lines"),
                                        metrics, panel.get("arrangement", "stack")))
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
    assert value.annotations[0].anchor_source_ref == "/body/annotations/0/anchor"
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
    assert value.annotations[0].anchor_source_ref == "/body/annotations/0/anchor"


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


def test_inline_summary_figures_retain_panel_and_metric_order_with_explicit_semantics():
    projection = ReviewProjection((), (date(2026, 3, 1), date(2026, 3, 9)), (), ())
    summary = {"body": {"panels": [{
        "id": "countdown", "title": "発射まで", "presentation": "figures", "arrangement": "inline",
        "metrics": [
            {"id": "days", "label": "DAYS", "source": "count.selected", "format": "count"},
            {"id": "variance", "label": "DELTA", "source": "count.knownFinishVariance", "format": "count"},
        ],
    }]}}

    content = normalize_summary_content(typed_summary(summary), projection, None)

    panel, = content.panels
    assert panel.arrangement == "inline"
    assert tuple((run.placement_id, run.content, run.typography_role, run.semantic_id) for run in panel.runs) == (
        ("summary:/panels/0/title", "発射まで", "summary-caption", "summaryCaption"),
        ("summary:/panels/0/metrics/0/value", "0", "metric", "summaryFigureValue"),
        ("summary:/panels/0/metrics/0/label", "DAYS", "summary-unit", "summaryUnit"),
        ("summary:/panels/0/metrics/1/value", "0", "metric", "summaryFigureValue"),
        ("summary:/panels/0/metrics/1/label", "DELTA", "summary-unit", "summaryUnit"),
    )


def test_inline_lines_and_shorthand_keep_combined_content_without_unit_inference():
    projection = ReviewProjection((), (date(2026, 3, 1), date(2026, 3, 9)), (), ())
    summary = {"body": {"panels": [
        {"id": "lines", "title": "Current", "presentation": "lines", "arrangement": "inline",
         "metrics": {"days": {"label": "DAYS", "source": "count.selected", "format": "count"}}},
        {"id": "raw", "title": "Literal", "arrangement": "inline", "metrics": {"note": "DAY: 0"}},
    ]}}

    content = normalize_summary_content(typed_summary(summary), projection, None)

    assert tuple((panel.arrangement, tuple((run.content, run.typography_role, run.semantic_id)
                                           for run in panel.runs)) for panel in content.panels) == (
        ("inline", (("Current", "summary-caption", "summaryCaption"),
                    ("DAYS: 0", "summary-caption", "summaryCaption"))),
        ("inline", (("Literal", "summary-caption", "summaryCaption"),
                    ("note: DAY: 0", "summary-caption", "summaryCaption"))),
    )


def test_grouped_summary_ids_are_structural_and_keep_authored_source_refs():
    projection = ReviewProjection((), (date(2026, 3, 1), date(2026, 3, 9)), (), ())
    summary = {"body": {"panels": [
        {"id": "same:/panel", "title": "First", "presentation": "figures", "arrangement": "inline",
         "metrics": [{"id": "metric:/value", "label": "unit", "source": "count.selected", "format": "count"}]},
        {"id": "same:/panel", "title": "Second", "presentation": "lines", "arrangement": "stack",
         "metrics": [{"id": "metric:/value", "label": "count", "source": "count.selected", "format": "count"}]},
    ]}}

    content = normalize_summary_content(typed_summary(summary), projection, None)

    runs = content.runs
    assert [run.placement_id for run in runs] == [
        "summary:/panels/0/title", "summary:/panels/0/metrics/0/value", "summary:/panels/0/metrics/0/label",
        "summary:/panels/1/title", "summary:/panels/1/metrics/0/text",
    ]
    assert len({run.placement_id for run in runs}) == len(runs)
    assert [run.source_ref for run in runs] == ["same:/panel"] * len(runs)
    assert [run.semantic_id for run in runs] == [
        "summaryCaption", "summaryFigureValue", "summaryUnit", "summaryHeader", "summaryMetric",
    ]
    assert [run.typography_role for run in runs] == [
        "summary-caption", "metric", "summary-unit", "summary", "summary",
    ]


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
    with pytest.raises(ValueError, match="E_PRESENTATION_SUMMARY_SOURCE") as error:
        normalize_summary_content(typed_summary(summary), projection, None)
    assert "subtree objectId='programme'" in str(error.value)


def test_summary_format_diagnostic_names_metric_path_and_format_value():
    projection = ReviewProjection((), (date(2026, 3, 1), date(2026, 3, 4)), (), ())
    summary = typed_summary({"body": {"panels": [{"id": "pulse", "metrics": {
        "forecast": {"source": "count.selected", "format": "romanNumeral"},
    }}]}})
    with pytest.raises(ValueError, match="E_PRESENTATION_SUMMARY_FORMAT") as error:
        normalize_summary_content(summary, projection, None)
    assert "/panels/0/metrics/0/format='romanNumeral'" in str(error.value)


def test_table_width_and_resource_shape_diagnostics_name_invalid_operands():
    with pytest.raises(ValueError, match="E_VIEW_TABLE_WIDTH") as width_error:
        _column_width({"fixedPx": 137})
    assert "fields=['fixedPx']" in str(width_error.value)
    with pytest.raises(ValueError, match="E_PRESENTATION_ACTUAL_SET_SHAPE") as shape_error:
        _resource_body({"asOf": "2026-03-04"}, "ACTUAL_SET")
    assert "/actual_set/body" in str(shape_error.value)


def test_summary_unknown_source_names_metric_pointer_and_requested_source():
    projection = ReviewProjection((), (date(2026, 3, 1), date(2026, 3, 4)), (), ())
    summary = typed_summary({"body": {"panels": [{"id": "pulse", "metrics": {
        "forecast": {"source": "vendor.opaque", "format": "text"},
    }}]}})
    with pytest.raises(ValueError, match="E_PRESENTATION_SUMMARY_SOURCE") as error:
        normalize_summary_content(summary, projection, None)
    assert "/panels/0/metrics/0/source='vendor.opaque'" in str(error.value)


def test_group_header_secondary_diagnostic_names_entity_field_and_value():
    item = ReviewItem("obj", "Object", "span", {}, None, None, (), group_id="team-omega",
                      group_label="Omega", item_id="obj")
    projection = ReviewProjection((item,), (date(2026, 3, 1), date(2026, 3, 4)), (), (),
                                  rows=(ReviewRowProjection("row", "Omega", "team-omega", "obj", (item,)),))
    grouping = ViewGrouping("field", "team", (), None, "header", None, None,
                            header=ViewGroupHeader("{title} · {secondary}", secondary_field="division"))
    view = replace(typed_view({"body": {"tableColumns": (), "visibility": {}}}), grouping=grouping)
    with pytest.raises(ValueError, match="E_REVIEW_GROUP_HEADER_SECONDARY") as error:
        _group_headers(projection, {"entities": {"team-omega": {"fields": {"division": "  "}}}}, view)
    assert "/entities/'team-omega'/fields/'division'='  '" in str(error.value)


def test_group_header_ordinal_error_names_form_and_group_inventory():
    groups = tuple(f"group-{index}" for index in range(1, 4001))
    items = tuple(ReviewItem(f"obj-{index}", f"Object {index}", "span", {}, None, None, (),
                             group_id=group, item_id=f"obj-{index}")
                  for index, group in enumerate(groups, start=1))
    rows = tuple(ReviewRowProjection(f"row-{index}", item.title, group, item.item_id, (item,))
                 for index, (group, item) in enumerate(zip(groups, items, strict=True), start=1))
    projection = ReviewProjection(items, (date(2026, 3, 1), date(2026, 3, 4)), (), (), rows=rows)
    grouping = ViewGrouping("field", "team", (), None, "header", None, None,
                            header=ViewGroupHeader("{ordinal} {title}", ordinal="roman"))
    view = replace(typed_view({"body": {"tableColumns": (), "visibility": {}}}), grouping=grouping)
    with pytest.raises(ValueError, match="E_REVIEW_GROUP_ORDINAL_RANGE") as error:
        _group_headers(projection, {}, view)
    assert "groups=['group-1'" in str(error.value) and "ordinal='roman'" in str(error.value)


def test_lane_table_projection_diagnostic_names_missing_membership_operand():
    projection = ReviewProjection((), (date(2026, 3, 1), date(2026, 3, 4)), (), (),
                                  lane_rows=(ReviewLaneRowProjection("lane-ghost", "group", ()),))
    view = replace(typed_view({"body": {"tableColumns": (), "visibility": {}}}),
                   rows=ViewRows("lanes", (), lane_table=ViewLaneTable(ViewLaneLabel.LANE, False)))
    with pytest.raises(ValueError, match="E_REVIEW_LANE_TABLE_PROJECTION") as error:
        normalize_v05_table_content(projection, {}, view)
    assert "laneMembership=False, laneRows=1, laneTable=True" in str(error.value)


@pytest.mark.parametrize(("membership", "lane_row", "operand"), [
    (LaneMembership((), ()), ReviewLaneRowProjection("lane-ghost", "team-z", ()),
     "laneId='lane-ghost' is absent from membership lanes"),
    (LaneMembership((Lane("lane-empty", "team-z", ()),), ()),
     ReviewLaneRowProjection("lane-empty", "team-z", ()),
     "laneId='lane-empty' has no memberItemIds"),
])
def test_lane_table_projection_diagnostic_names_invalid_lane_identity_or_membership(membership, lane_row, operand):
    projection = ReviewProjection((), (date(2026, 3, 1), date(2026, 3, 4)), (), (),
                                  lane_membership=membership, lane_rows=(lane_row,))
    view = replace(typed_view({"body": {"tableColumns": (), "visibility": {}}}),
                   rows=ViewRows("lanes", (), lane_table=ViewLaneTable(ViewLaneLabel.LANE, False)))
    with pytest.raises(ValueError, match="E_REVIEW_LANE_TABLE_PROJECTION") as error:
        normalize_v05_table_content(projection, {}, view)
    assert operand in str(error.value)


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
    with pytest.raises(ValueError, match="E_PRESENTATION_ACTUAL_SET_SHAPE") as error:
        normalize_v05_surface_content(projection, {"relations": (), "annotations": {}}, typed_view(view),
                                      summary=EMPTY_SUMMARY, actual_set={"asOf": "2026-03-04"})
    assert "/actual_set/body" in str(error.value) and "type=NoneType" in str(error.value)


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
    with pytest.raises(ValueError, match="E_PRESENTATION_ANNOTATION_REFERENCE_MISSING") as error:
        normalize_v05_surface_content(projection, {"annotations": {}}, view, summary=EMPTY_SUMMARY)
    assert "/annotations/'missing'/text" in str(error.value)


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


def test_as_of_label_date_forms_day_month_and_day_month_year():
    """#991: `20 Aug` and `20 Aug 2027` beside the localized date, in both built-in tables."""
    from datetime import date as _date
    from chrona.presentation.review.v05_content import _as_of_label
    as_of = _date(2027, 8, 20)

    def marker(form, table=None):
        return {"kind": "asOf", "source": "actual", "label": "as of", "date": {"form": form, **({"nameTable": table} if table else {})}}
    assert _as_of_label(marker("day-month"), as_of, "en-US") == "as of 20 Aug"
    assert _as_of_label(marker("day-month-year"), as_of, "en-US") == "as of 20 Aug 2027"
    assert _as_of_label(marker("day-month", "ja-JP"), as_of, "en-US") == "as of 8月20日"
    assert _as_of_label(marker("day-month-year", "ja-JP"), as_of, "en-US") == "as of 2027年8月20日"
    assert _as_of_label(marker("localized-date"), as_of, "en-US") == "as of Aug 20, 2027"  # unchanged
