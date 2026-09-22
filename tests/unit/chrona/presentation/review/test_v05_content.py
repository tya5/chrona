from datetime import date

import pytest

from chrona.presentation.model.projection import ReviewItem, ReviewProjection
from chrona.presentation.model.surface_content import SummaryContent
from chrona.presentation.review.v05_content import normalize_summary_content, normalize_v05_surface_content


EMPTY_SUMMARY = SummaryContent(())


def test_optional_content_is_selected_only_from_current_project_and_view():
    projection = ReviewProjection((ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 2)}, None, None, ()),), (date(2026, 1, 1), date(2026, 1, 2)), (), ())
    project = {"relations": ({"id": "r", "from": {"object": "a"}, "to": {"object": "a"}},), "annotations": {"n": {"text": "note"}}}
    view = {"body": {"tableColumns": ({"id": "Name", "source": "title", "missing": "blank"},), "visibility": {"relations": "semantic", "annotations": "none"}}}
    value = normalize_v05_surface_content(projection, project, view, summary=EMPTY_SUMMARY)
    assert value.table_cells == (("a", "Name", "A"),)
    assert value.relations[0]["id"] == "r"
    assert value.notes == (("n", "note"),)


def test_calendar_closures_come_only_from_project_calendar_exceptions():
    projection = ReviewProjection((ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 5)}, None, None, ()),),
                                  (date(2026, 1, 1), date(2026, 1, 5)), (), ())
    project = {"project": {"calendar": "standard"},
               "calendars": {"standard": {"working_days": ["mon", "tue", "wed", "thu", "fri"],
                                           "exceptions": [{"date": "2026-01-01", "working": True}]}},
               "relations": (), "annotations": {}}
    view = {"body": {"tableColumns": (), "visibility": {"relations": "none", "annotations": "none"}}}

    value = normalize_v05_surface_content(projection, project, view, summary=EMPTY_SUMMARY)

    assert value.calendar_closed == (date(2026, 1, 3), date(2026, 1, 4))


def test_structured_temporal_and_annotation_presentation_is_normalized():
    projection = ReviewProjection((ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 5)}, None, None, ()),),
                                  (date(2026, 1, 1), date(2026, 1, 5)), (), ())
    view = {"body": {"tableColumns": (), "visibility": {"labels": {"members": True}, "relations": "none", "annotations": "presentation"},
                     "timePresentation": {"axisLevel": "week", "asOf": "hidden", "calendarClosed": False},
                     "annotationPresentation": "numbered", "annotations": [{"id": "note", "text": "Watch this"}]}}
    value = normalize_v05_surface_content(projection, {"relations": (), "annotations": {}}, view,
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
    content = normalize_summary_content(summary, projection, {"body": {"asOf": "2026-02-03"}})
    value = normalize_v05_surface_content(projection, {"relations": (), "annotations": {}}, view,
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
    content = normalize_summary_content(summary, projection, {"body": {"asOf": "2026-03-04"}})
    value = normalize_v05_surface_content(projection, {"relations": (), "annotations": {}}, view,
                                          actual_set={"body": {"asOf": "2026-03-04"}}, summary=content)
    assert tuple((run.content, run.typography_role) for run in value.summary.runs) == (
        ("figures", "summary"), ("2026-03-04", "metric"), ("as of", "summary"),
        ("2026-03-08", "metric"), ("launch", "summary"), ("1 / 0", "metric"), ("behind / ahead", "summary"),
    )


def test_target_view_contract_normalizes_plot_labels_marker_and_axis():
    projection = ReviewProjection((ReviewItem("a", "A", "span", {"start": date(2026, 3, 1), "end": date(2026, 3, 2)}, None, 2, ()),),
                                  (date(2026, 3, 1), date(2026, 3, 8)), (), ())
    view = {"body": {"tableColumns": (),
                     "visibility": {"labels": {"placement": "plot", "content": ["title", "finishDelta"], "side": "auto"},
                                    "relations": "none", "annotations": {"mode": "presentation", "marker": "numbered"}},
                     "axis": {"levels": [{"unit": "quarter", "format": "year-quarter"}, {"unit": "month", "format": "short-month"}], "ticks": "week"},
                     "markers": [{"kind": "asOf", "source": "actual", "label": "as of"}], "shading": {"nonWorking": False}}}
    value = normalize_v05_surface_content(projection, {"relations": (), "annotations": {}}, view,
                                          actual_set={"body": {"asOf": "2026-03-04"}}, summary=EMPTY_SUMMARY)
    assert value.label_placement == "plot"
    assert value.label_content == ("title", "finishDelta")
    assert value.label_side == "auto"
    assert value.label_overflow == "diagnose"
    assert value.axis_levels == (("quarter", "year-quarter"), ("month", "short-month"))
    assert value.axis_ticks == "week"
    assert value.as_of_label == "as of"


@pytest.mark.parametrize(("argument", "value", "diagnostic"), (
    ("actual_set", {"asOf": "2026-03-04"}, "E_PRESENTATION_ACTUAL_SET_SHAPE"),
    ("detail", {"legend": ()}, "E_PRESENTATION_DETAIL_PROFILE_SHAPE"),
))
def test_optional_resources_require_their_current_body_envelope(argument, value, diagnostic):
    projection = ReviewProjection((), (date(2026, 3, 1), date(2026, 3, 8)), (), ())
    view = {"body": {"tableColumns": (), "visibility": {"labels": False, "relations": "none", "annotations": "none"}}}
    with pytest.raises(ValueError, match=diagnostic):
        normalize_v05_surface_content(projection, {"relations": (), "annotations": {}}, view,
                                      summary=EMPTY_SUMMARY, **{argument: value})


def test_summary_profile_requires_the_current_body_envelope():
    projection = ReviewProjection((), (date(2026, 3, 1), date(2026, 3, 8)), (), ())
    with pytest.raises(ValueError, match="E_PRESENTATION_SUMMARY_PROFILE_SHAPE"):
        normalize_summary_content({"panels": ()}, projection, None)
