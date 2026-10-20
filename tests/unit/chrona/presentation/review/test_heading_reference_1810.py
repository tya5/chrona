from datetime import date
from types import SimpleNamespace

from chrona.presentation.contracts.resources import (
    TableColumn, ViewComparison, ViewHeading, ViewInput, ViewRows,
    ViewVisibility, ViewWindow, freeze,
)
from chrona.presentation.model.projection import (
    ForecastComparisonFact, ReviewItem, ReviewProjection,
)
from chrona.presentation.model.surface_content import HeadingContent, SummaryContent
from chrona.presentation.heading_text import HeadingPart
from chrona.presentation.review.profile_connections import resolve_profile_connections
from chrona.presentation.review.v05_content import (
    _as_of_label, compose_heading, missing_heading_fact_warnings, normalize_v05_surface_content,
    normalize_v05_table_content,
)
from chrona.presentation.layout.surface_render_plan import uses_independent_view_heading
from chrona.core.forecast import ForecastItem


def _view(*, header=True, heading=None, markers=(), wording=None):
    column = TableColumn(
        "Delta", freeze({"comparisonFacet": "finishDelta"}), "signedDays", "blank",
        header=freeze({"wording": "column.finishDelta"}) if header is True else "Change",
        header_wording_key="column.finishDelta" if header else None,
    )
    return ViewInput(
        selection=None, grouping=None, ordering=None,
        window=ViewWindow("selected-planned", None, None, 0),
        comparison=ViewComparison(None, "optional", None, None, ()),
        visibility=ViewVisibility(False, "none", "none"),
        table_columns=(column,), annotations=(), rows=ViewRows("automatic", ()),
        axis=None, markers=tuple(freeze(item) for item in markers), shading=None,
        time_presentation=None, annotation_presentation=None, heading=heading,
        wording=freeze(wording) if wording is not None else None,
    )


def _projection(*, forecast=False, snapshot=False):
    item = ReviewItem("task", "Task", "span",
                      {"start": date(2026, 1, 1), "finish": date(2026, 1, 5)},
                      None, 3, ())
    if forecast:
        item = ReviewItem(
            "task", "Task", "span", item.planned, None, 3, (),
            forecast=ForecastComparisonFact(
                ForecastItem({"start": date(2026, 1, 1), "finish": date(2026, 1, 7)}, False), 5))
    return ReviewProjection(
        (item,), (date(2026, 1, 1), date(2026, 1, 10)), (), (),
        bound_comparison_sources=frozenset({"snapshot"} if snapshot else ()),
    )


def _resolve_header(view, projection, *, actual_set=None):
    view = resolve_profile_connections(view, None, None, project_object_ids=frozenset()).view
    table = normalize_v05_table_content(projection, {}, view, actual_set=actual_set)
    return view.table_columns[0].header_wording_key, table.columns[0].header


def test_finish_delta_header_uses_the_comparison_reference_shown_and_preserves_overrides():
    actual_set = {"body": {"asOf": "2026-01-08", "observations": []}}
    assert _resolve_header(_view(), _projection(), actual_set=actual_set) == (
        "column.finishDelta", "Δ vs plan")
    assert _resolve_header(_view(), _projection(forecast=True)) == (
        "column.finishDelta", "Δ vs plan")
    assert _resolve_header(_view(), _projection(forecast=True, snapshot=True)) == (
        "column.finishDelta", "Δ vs baseline")
    assert _resolve_header(_view(wording={"keys": {"column.finishDelta": "Schedule variance"}}),
                           _projection(forecast=True, snapshot=True)) == (
        "column.finishDelta", "Schedule variance")
    assert _resolve_header(_view(header=False), _projection(forecast=True, snapshot=True))[1] == "Change"


def test_heading_and_as_of_marker_share_marker_date_form_and_name_table():
    view = _view(
        heading=ViewHeading(title="Report {asOf}", subtitle="Calendar: {calendar}", date_form="day-month"),
        markers=({"kind": "asOf", "source": "actual", "label": "As of",
                  "date": {"form": "localized-date", "nameTable": "ja-JP"}},),
    )
    actual = {"body": {"asOf": "2026-03-04", "observations": []}}
    project = {"project": {"title": "Plan", "calendar": "main"},
               "calendars": {"main": {"title": "Work days"}}, "relations": (), "annotations": {}}
    heading = compose_heading(view, project, actual, "en-US")
    assert isinstance(heading, HeadingContent)
    assert heading.title == "Report 2026/03/04"
    assert heading.subtitle == "Calendar: Work days"
    content = normalize_v05_surface_content(
        _projection(), project, view, actual_set=actual, summary=SummaryContent(()))
    assert content.as_of_label == "As of 2026/03/04"


def test_declared_marker_without_date_keeps_its_copy_while_heading_uses_heading_date_form():
    view = _view(
        heading=ViewHeading(title="Report {asOf}", date_form="day-month"),
        markers=({"kind": "asOf", "source": "actual", "label": "As of"},),
    )
    actual = {"body": {"asOf": "2026-03-04", "observations": []}}
    project = {"project": {"title": "Plan"}, "relations": (), "annotations": {}}
    heading = compose_heading(view, project, actual, "en-US")
    assert isinstance(heading, HeadingContent)
    assert heading.title == "Report 4 Mar"

    content = normalize_v05_surface_content(
        _projection(), project, view, actual_set=actual, summary=SummaryContent(()))
    assert content.as_of_label == "As of"
    assert _as_of_label({"kind": "asOf", "source": "actual", "label": "As of"},
                        date(2026, 3, 4), "en-US", heading_date_form="day-month") == "As of"


def test_heading_fact_warning_is_typed_pointed_and_keeps_empty_fact_fallback():
    view = _view(heading=ViewHeading(
        title="{asOf}",
        subtitle=(HeadingPart("at {calendar}"),),
    ))
    warnings = missing_heading_fact_warnings(
        view, {"project": {"title": "Plan"}}, None)
    assert [(item.code, item.fact, item.source_ref) for item in warnings] == [
        ("W_PRESENTATION_HEADING_FACT_MISSING", "asOf", "/body/heading/title"),
        ("W_PRESENTATION_HEADING_FACT_MISSING", "calendar", "/body/heading/subtitle/0/text"),
    ]
    assert warnings[0].scene_diagnostic().endswith(
        '{"fact":"asOf","sourceRef":"/body/heading/title"}')
    assert missing_heading_fact_warnings(
        _view(heading=ViewHeading(title="{asOf} {calendar}")),
        {"project": {"title": "Plan", "calendar": "main"}},
        {"body": {"asOf": "2026-01-01"}}) == ()


def test_network_heading_fact_warnings_follow_resolved_view_heading_admission():
    legacy_title = SimpleNamespace(profile={"root": {"kind": "slot", "id": "whole", "source": "title"}})
    independent_parts = SimpleNamespace(profile={"root": {"kind": "group", "children": []}})
    assert not uses_independent_view_heading("dependency-network", legacy_title)
    assert uses_independent_view_heading("dependency-network", independent_parts)
    assert not uses_independent_view_heading("table-timeline", independent_parts)
