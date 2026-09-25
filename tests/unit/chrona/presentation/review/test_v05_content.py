from datetime import date

import pytest

from chrona.presentation.model.projection import ReviewItem, ReviewProjection, ReviewRowProjection
from chrona.presentation.model.surface_content import SummaryContent
from chrona.presentation.review.v05_content import normalize_summary_content, normalize_v05_surface_content
from chrona.presentation.contracts.resources import (
    SummaryMetric, SummaryPanelInput, SummaryProfileInput, TableColumn, ViewComparison, ViewGrouping, ViewInput,
    ViewRows, ViewVisibility, ViewWindow, freeze,
)


EMPTY_SUMMARY = SummaryContent(())


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
        tuple(TableColumn(item["id"], item["source"], item.get("format", "text"), item["missing"],
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


def test_optional_content_is_selected_only_from_current_project_and_view():
    projection = ReviewProjection((ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 2)}, None, None, ()),), (date(2026, 1, 1), date(2026, 1, 2)), (), ())
    project = {"relations": ({"id": "r", "from": {"object": "a"}, "to": {"object": "a"}},), "annotations": {"n": {"text": "note"}}}
    view = {"body": {"tableColumns": ({"id": "Name", "source": "title", "missing": "blank"},), "visibility": {"relations": "semantic", "annotations": "none"}}}
    value = normalize_v05_surface_content(projection, project, typed_view(view), summary=EMPTY_SUMMARY)
    assert value.table_cells == (("a", "Name", "A"),)
    assert value.relations[0].relation_id == "r"
    assert value.notes == (("n", "note"),)


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
    assert value.table_cells == (("active", "Actual", "in progress"), ("future", "Actual", "—"), ("gate", "Actual", "—"))


def test_date_range_is_compact_and_retains_cross_year_precision():
    projection = ReviewProjection((ReviewItem("a", "A", "span", {"start": date(2026, 12, 31), "end": date(2027, 1, 2)}, None, None, ()),),
                                  (date(2026, 12, 1), date(2027, 2, 1)), (), ())
    view = {"body": {"tableColumns": ({"id": "Plan", "source": {"facet": "planned"}, "format": "dateRange", "missing": "em-dash"},),
                     "visibility": {"labels": False, "relations": "none", "annotations": "none"}}}
    value = normalize_v05_surface_content(projection, {"relations": (), "annotations": {}}, typed_view(view), summary=EMPTY_SUMMARY)
    assert value.table_cells == (("a", "Plan", "31 Dec 2026 – 02 Jan 2027"),)


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
    assert value.table_cells == (("scenario", "Scenario", "Delayed launch"), ("scenario", "Scenario id", "delayed"))


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
                     "timePresentation": {"axisLevel": "week", "asOf": "hidden", "calendarClosed": False},
                     "annotationPresentation": "numbered", "annotations": [{"id": "note", "text": "Watch this"}]}}
    value = normalize_v05_surface_content(projection, {"relations": (), "annotations": {}}, typed_view(view),
                                          actual_set={"body": {"asOf": "2026-01-03"}}, summary=EMPTY_SUMMARY)
    assert value.show_member_labels is True
    assert value.axis_level == "week"
    assert value.as_of is None
    assert value.calendar_closed == ()
    assert value.annotations == ({"id": "note", "text": "Watch this", "number": 1},)


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
                     "axis": {"levels": [{"unit": "quarter", "format": "year-quarter"}, {"unit": "month", "format": "short-month"}], "ticks": "week"},
                     "markers": [{"kind": "asOf", "source": "actual", "label": "as of"}], "shading": {"nonWorking": False}}}
    value = normalize_v05_surface_content(projection, {"relations": (), "annotations": {}}, typed_view(view),
                                          actual_set={"body": {"asOf": "2026-03-04"}}, summary=EMPTY_SUMMARY)
    assert value.label_placement == "plot"
    assert value.label_content == ("title", "finishDelta")
    assert value.label_side == "auto"
    assert value.label_overflow == "diagnose"
    assert value.axis_levels == (("quarter", "year-quarter"), ("month", "short-month"))
    assert value.axis_ticks == "week"
    assert value.as_of_label == "as of"


def test_actual_set_requires_the_current_body_envelope():
    projection = ReviewProjection((), (date(2026, 3, 1), date(2026, 3, 8)), (), ())
    view = {"body": {"tableColumns": (), "visibility": {"labels": False, "relations": "none", "annotations": "none"}}}
    with pytest.raises(ValueError, match="E_PRESENTATION_ACTUAL_SET_SHAPE"):
        normalize_v05_surface_content(projection, {"relations": (), "annotations": {}}, typed_view(view),
                                      summary=EMPTY_SUMMARY, actual_set={"asOf": "2026-03-04"})
