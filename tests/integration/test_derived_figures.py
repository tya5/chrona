"""#586 I586-2: View-declared derived figures, shown by a Summary Profile metric, rendered end to end.

A synthetic Project goes through the packaged `control-room-dark` bundle with a `summary` slot added to its
Layout Profile. No `examples/` input: the HALCYON countdown slide is evidence, not a gate.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date

import pytest

from chrona.presentation.model.closure import ClosureError
from chrona.usecases.render_review import RenderFailed, RenderRejected
from tests.support import synthetic_review as sr

AS_OF = "2026-02-20"
ACTUAL = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
          "body": {"asOf": AS_OF, "observations": []}}
SLOT = {"id": "summary", "kind": "slot", "source": "summary", "inlineSize": "content", "blockSize": "content",
        "place": {"inline": "start", "block": "start", "safety": "safe"}, "priority": "preferred",
        "overflow": "ellipsize-with-source"}
COUNTDOWN = {"id": "countdown", "kind": "daysUntil", "to": {"period": "window", "side": "start"}}


def _source(*, calendar: bool = True) -> dict:
    source = sr.project({"a": sr.span("a", date(2026, 1, 5), 40),
                         "launch": sr.point("launch", date(2026, 3, 20), owner="b"),
                         "build": sr.span("build", date(2026, 3, 2), 14)})
    # 2026-03-20 is a Friday; the window opens at the launch gate and runs to the end of March.
    source["periods"] = {"window": {"title": "Window", "start": {"object": "launch", "endpoint": "at"}, "end": "2026-03-30"}}
    if calendar:
        source["project"]["calendar"] = "standard"
        source["calendars"] = {"standard": {"working_days": ["mon", "tue", "wed", "thu", "fri"]},
                               "holiday": {"working_days": ["mon", "tue", "wed", "thu", "fri"],
                                           "exceptions": [{"date": "2026-02-23", "working": False}]}}
    return source


def _parts(*figures: dict, slot: bool = True) -> dict:
    parts = sr.bundle("control-room-dark")
    if figures:
        parts["view"]["body"]["figures"] = [deepcopy(item) for item in figures]
    if slot:
        parts["layout"]["root"]["children"].insert(1, deepcopy(SLOT))
    return parts


def _summary(*metrics: dict, presentation: str = "figures") -> dict:
    return {"version": "chrona/summary-profile/v0.1", "kind": "summary-profile", "id": "figures",
            "body": {"panels": [{"id": "key", "title": "Key figures", "presentation": presentation,
                                 "metrics": [dict(item) for item in metrics]}]}}


def _metric(figure: str = "countdown", *, format: str = "count", label: str = "DAYS", metric_id: str = "m") -> dict:
    return {"id": metric_id, "source": {"figure": figure}, "label": label, "format": format}


def _texts(rendered) -> dict[str, str]:
    return {item.scene_id: item.text for item in rendered.surface.primitives if item.scene_id.startswith("summary:")}


def _render(tmp_path, parts, summary, *, source=None, actual=ACTUAL):
    return sr.render(tmp_path, source or _source(), presentation=parts, actual=actual, summary=summary)


def test_a_countdown_shows_the_days_from_the_as_of_to_the_period_start_over_its_caption(tmp_path):
    texts = _texts(_render(tmp_path, _parts(COUNTDOWN), _summary(_metric(metric_id="countdown"))))
    # 2026-02-20 to 2026-03-20: February 2026 has 28 days.
    assert texts["summary:key:countdown:value"] == "28"
    assert texts["summary:key:countdown:caption"] == "DAYS"


def test_period_last_flows_through_the_view_contract_into_rendered_summary_text(tmp_path):
    figure = dict(COUNTDOWN, to={"period": "window", "side": "last"})
    rendered = _render(tmp_path, _parts(figure), _summary(_metric(metric_id="countdown")))
    # [March 20, March 30) closes on March 29: 37 days after February 20.
    assert _texts(rendered)["summary:key:countdown:value"] == "37"
    assert b">37<" in rendered.artifact.content


GROUP_COUNTDOWN = {"id": "group-countdown", "kind": "daysUntil", "scope": "group",
                   "to": {"group": "firstPlannedStart"}}


def test_group_countdowns_use_each_groups_selected_start_in_actual_svg(tmp_path):
    parts = _parts(COUNTDOWN, GROUP_COUNTDOWN, slot=False)
    parts["view"]["body"]["grouping"]["header"] = {
        "text": "{title} {figure:group-countdown} / {figure:countdown}", "ordinal": "arabic"}
    rendered = _render(tmp_path, parts, None)
    headers = {item.scene_id: item.text for item in rendered.surface.primitives if item.purpose == "group-header"}
    assert headers == {"group-header:a": "Team a -46 / 28", "group-header:b": "Team b 28 / 28"}
    assert b"Team a -46 / 28" in rendered.artifact.content
    assert b"Team b 28 / 28" in rendered.artifact.content


def test_current_group_facts_require_an_explicit_group_scope(tmp_path):
    figure = dict(GROUP_COUNTDOWN)
    del figure["scope"]
    error = _refused(tmp_path, figure)
    assert error.diagnostic_id == "E_VIEW_FIGURE_INVALID"
    assert error.source_ref == "/body/figures/0/scope"


def test_group_figures_cannot_be_shown_by_an_unscoped_summary(tmp_path):
    with pytest.raises(RenderFailed) as failure:
        _render(tmp_path, _parts(GROUP_COUNTDOWN), _summary(_metric("group-countdown")))
    assert failure.value.code == "E_FIGURE_SCOPE_UNAVAILABLE"


@pytest.mark.parametrize(("source", "expected"), [
    ("selected", "3"), ("recorded", "0"), ("dueUnobserved", "1"),
    ("notYetDue", "2"), ("unavailable", "0"), ("missingActual", "1"),
    ("knownFinishVariance", "0"), ("behind", "0"), ("ahead", "0"),
])
def test_every_closed_count_source_reaches_the_summary_svg(tmp_path, source, expected):
    figure = {"id": "n", "kind": "count", "source": source}
    rendered = _render(tmp_path, _parts(figure), _summary(_metric("n", metric_id="n")))
    assert _texts(rendered)["summary:key:n:value"] == expected
    assert f">{expected}<".encode() in rendered.artifact.content


def test_finish_delta_counts_use_observed_signs_not_a_forecast(tmp_path):
    actual = deepcopy(ACTUAL)
    actual["body"]["observations"] = [
        {"id": "a-observed", "sequence": 1, "projectObjectId": "a",
         "actual": {"start": "2026-01-05", "finish": "2026-02-16"}},
        {"id": "build-observed", "sequence": 1, "projectObjectId": "build",
         "actual": {"start": "2026-03-02", "finish": "2026-03-15"}},
    ]
    figures = tuple({"id": name, "kind": "count", "source": name}
                    for name in ("knownFinishVariance", "behind", "ahead"))
    rendered = _render(tmp_path, _parts(*figures),
                       _summary(*(_metric(f["id"], metric_id=f["id"]) for f in figures)), actual=actual)
    texts = _texts(rendered)
    assert texts["summary:key:knownFinishVariance:value"] == "2"
    assert texts["summary:key:behind:value"] == texts["summary:key:ahead:value"] == "1"


def test_missing_actual_count_without_as_of_refuses_the_render(tmp_path):
    with pytest.raises(RenderRejected) as failure:
        _render(tmp_path, _parts({"id": "n", "kind": "count", "source": "missingActual"}),
                _summary(_metric("n")), actual=None)
    assert [(d.id, d.path) for d in failure.value.diagnostics] == [
        ("E_FIGURE_COUNT_UNAVAILABLE", "/body/figures/0/source")]


@pytest.mark.parametrize("formatter", ["date", "signedDays"])
def test_count_figures_cannot_claim_date_or_day_units(tmp_path, formatter):
    with pytest.raises(RenderFailed) as failure:
        _render(tmp_path, _parts({"id": "n", "kind": "count", "source": "selected"}),
                _summary(_metric("n", format=formatter)))
    assert failure.value.code == "E_PRESENTATION_SUMMARY_FORMAT"


def test_count_figures_are_group_relative_without_counting_lane_occurrences(tmp_path):
    parts = _parts({"id": "n", "kind": "count", "source": "selected", "scope": "group"}, slot=False)
    parts["view"]["body"]["grouping"]["header"] = {"text": "{title} {figure:n}", "ordinal": "arabic"}
    rendered = _render(tmp_path, parts, None)
    assert {item.scene_id: item.text for item in rendered.surface.primitives if item.purpose == "group-header"} == {
        "group-header:a": "Team a 2", "group-header:b": "Team b 1"}


@pytest.mark.parametrize(("format", "expected"), [("count", "28"), ("text", "28"), ("signedDays", "+28d")])
def test_the_metric_format_applies_to_a_figure(tmp_path, format, expected):
    texts = _texts(_render(tmp_path, _parts(COUNTDOWN), _summary(_metric(format=format, metric_id="countdown"))))
    assert texts["summary:key:countdown:value"] == expected


def test_a_lines_panel_shows_the_caption_and_the_value(tmp_path):
    texts = _texts(_render(tmp_path, _parts(COUNTDOWN), _summary(_metric(metric_id="countdown"), presentation="lines")))
    assert texts["summary:key:countdown"] == "DAYS: 28"


def test_a_target_in_the_past_is_negative(tmp_path):
    figure = {"id": "since", "kind": "daysUntil", "from": {"object": "launch", "endpoint": "at"}, "to": "asOf"}
    texts = _texts(_render(tmp_path, _parts(figure), _summary(_metric("since", format="signedDays", metric_id="since"))))
    assert texts["summary:key:since:value"] == "-28d"


def test_working_days_use_the_project_default_calendar_or_a_named_one(tmp_path):
    figures = (
        {"id": "default", "kind": "daysUntil", "to": {"object": "launch", "endpoint": "at"}, "days": "working"},
        {"id": "named", "kind": "daysUntil", "to": {"object": "launch", "endpoint": "at"}, "days": "working",
         "calendar": "holiday"},
        {"id": "length", "kind": "daysIn", "period": "window", "days": "working"},
        {"id": "span", "kind": "daysIn", "period": "window"})
    summary = _summary(*(_metric(item["id"], metric_id=item["id"]) for item in figures))
    texts = _texts(_render(tmp_path, _parts(*figures), summary))
    # Friday 2026-02-20 to Friday 2026-03-20 is four weeks: 20 working days; the holiday calendar closes Mon 02-23.
    assert texts["summary:key:default:value"] == "20"
    assert texts["summary:key:named:value"] == "19"
    # The window [03-20, 03-30) is Fri 20 .. Sun 29: Fri 20, Mon 23 .. Fri 27 are working days.
    assert texts["summary:key:length:value"] == "6"
    assert texts["summary:key:span:value"] == "10"


def test_a_period_reference_follows_the_object_it_names(tmp_path):
    source = _source()
    source["objects"]["launch"]["schedule"]["at"] = "2026-03-27"
    texts = _texts(_render(tmp_path, _parts(COUNTDOWN), _summary(_metric(metric_id="countdown")), source=source))
    assert texts["summary:key:countdown:value"] == "35"


def test_declared_figures_that_nothing_shows_leave_the_scene_unchanged(tmp_path):
    (tmp_path / "declared").mkdir()
    (tmp_path / "plain").mkdir()
    declared = _render(tmp_path / "declared", _parts(COUNTDOWN, slot=False), None)
    plain = _render(tmp_path / "plain", _parts(slot=False), None)
    assert declared.surface.primitives == plain.surface.primitives
    assert declared.artifact.content == plain.artifact.content


def test_a_summary_without_a_figure_source_is_unchanged_by_a_figure_declaration(tmp_path):
    metric = {"id": "n", "source": "count.selected", "label": "selected", "format": "count"}
    (tmp_path / "with").mkdir()
    (tmp_path / "without").mkdir()
    with_figures = _render(tmp_path / "with", _parts(COUNTDOWN), _summary(metric))
    without = _render(tmp_path / "without", _parts(), _summary(metric))
    assert with_figures.surface.primitives == without.surface.primitives
    assert with_figures.artifact.content == without.artifact.content


# ---------------------------------------------------------------- missing facts


def _rejected(tmp_path, parts, *, source=None, actual=ACTUAL):
    with pytest.raises(RenderRejected) as failure:
        _render(tmp_path, parts, _summary(_metric(metric_id="countdown")), source=source, actual=actual)
    return failure.value.diagnostics


def test_a_figure_naming_an_undeclared_period_is_refused_with_the_declared_ones(tmp_path):
    figure = {"id": "countdown", "kind": "daysUntil", "to": {"period": "freeze", "side": "start"}}
    (found,) = _rejected(tmp_path, _parts(figure))
    assert found.id == "E_FIGURE_PERIOD_UNKNOWN" and "freeze" in found.message and "window" in found.message
    assert found.path == "/body/figures/0/to/period"


def test_a_figure_naming_an_unknown_object_or_endpoint_is_refused(tmp_path):
    unknown = {"id": "countdown", "kind": "daysUntil", "to": {"object": "ghost", "endpoint": "at"}}
    assert [item.id for item in _rejected(tmp_path, _parts(unknown))] == ["E_FIGURE_OBJECT_UNKNOWN"]
    (tmp_path / "endpoint").mkdir()
    point_start = {"id": "countdown", "kind": "daysUntil", "to": {"object": "launch", "endpoint": "start"}}
    (found,) = _rejected(tmp_path / "endpoint", _parts(point_start))
    assert found.id == "E_FIGURE_ENDPOINT_UNAVAILABLE" and "offers at" in found.message


def test_an_as_of_figure_without_an_actual_set_is_refused_not_blanked(tmp_path):
    (found,) = _rejected(tmp_path, _parts(COUNTDOWN), actual=None)
    assert found.id == "E_FIGURE_ASOF_MISSING"


def test_working_days_without_a_calendar_are_refused(tmp_path):
    figure = {"id": "countdown", "kind": "daysIn", "period": "window", "days": "working"}
    (found,) = _rejected(tmp_path, _parts(figure), source=_source(calendar=False))
    assert found.id == "E_FIGURE_CALENDAR_UNAVAILABLE"
    (tmp_path / "named").mkdir()
    named = dict(figure, calendar="ghost")
    (found,) = _rejected(tmp_path / "named", _parts(named))
    assert found.id == "E_FIGURE_CALENDAR_UNAVAILABLE" and "ghost" in found.message


def test_an_unused_figure_with_a_missing_fact_still_refuses_the_render(tmp_path):
    figure = {"id": "unused", "kind": "daysUntil", "to": {"period": "freeze", "side": "start"}}
    with pytest.raises(RenderRejected) as failure:
        _render(tmp_path, _parts(figure), _summary(_metric("unused", metric_id="m")))
    assert [item.id for item in failure.value.diagnostics] == ["E_FIGURE_PERIOD_UNKNOWN"]
    (tmp_path / "bare").mkdir()
    with pytest.raises(RenderRejected):
        _render(tmp_path / "bare", _parts(figure, slot=False), None)


def test_every_finding_of_several_figures_is_reported_together(tmp_path):
    figures = ({"id": "one", "kind": "daysIn", "period": "nowhere"},
               {"id": "two", "kind": "daysUntil", "to": {"object": "ghost", "endpoint": "at"}})
    codes = [item.id for item in _rejected(tmp_path, _parts(*figures))]
    assert codes == ["E_FIGURE_PERIOD_UNKNOWN", "E_FIGURE_OBJECT_UNKNOWN"]


def test_a_metric_naming_an_undeclared_figure_is_refused_with_the_declared_ones(tmp_path):
    with pytest.raises(RenderFailed) as failure:
        _render(tmp_path, _parts(COUNTDOWN), _summary(_metric("missing", metric_id="m")))
    assert failure.value.code == "E_VIEW_FIGURE_UNKNOWN"
    assert "missing" in failure.value.message and "countdown" in failure.value.message
    assert failure.value.source_ref == "/body/panels/key/metrics/m"


def test_a_metric_naming_a_figure_when_the_view_declares_none_says_none(tmp_path):
    with pytest.raises(RenderFailed) as failure:
        _render(tmp_path, _parts(), _summary(_metric("countdown", metric_id="m")))
    assert failure.value.code == "E_VIEW_FIGURE_UNKNOWN" and "declared: none" in failure.value.message


def test_a_figure_cannot_be_formatted_as_a_date(tmp_path):
    with pytest.raises(RenderFailed) as failure:
        _render(tmp_path, _parts(COUNTDOWN), _summary(_metric(format="date", metric_id="m")))
    assert failure.value.code == "E_PRESENTATION_SUMMARY_FORMAT"


# ---------------------------------------------------------------- the contract


def _refused(tmp_path, *figures: dict) -> ClosureError:
    with pytest.raises(ClosureError) as failure:
        _render(tmp_path, _parts(*figures, slot=False), None)
    return failure.value


def test_two_figures_with_one_id_are_refused_at_the_contract(tmp_path):
    error = _refused(tmp_path, COUNTDOWN, dict(COUNTDOWN, to={"period": "window", "side": "end"}))
    assert error.diagnostic_id == "E_VIEW_FIGURE_DUPLICATE"


@pytest.mark.parametrize("figure_id", ["a{b", "a}b", "has space", "tab\there", "bell\x07", "del\x7f"])
def test_an_id_a_placeholder_could_not_name_is_refused(tmp_path, figure_id):
    error = _refused(tmp_path, dict(COUNTDOWN, id=figure_id))
    assert error.diagnostic_id in {"E_VIEW_FIGURE_INVALID", "E_VIEW_SCHEMA"}


def test_a_calendar_with_calendar_days_is_a_dead_declaration(tmp_path):
    error = _refused(tmp_path, dict(COUNTDOWN, calendar="standard"))
    assert error.diagnostic_id == "E_VIEW_FIGURE_INVALID" and error.source_ref == "/body/figures/0/calendar"
    (tmp_path / "explicit").mkdir()
    explicit = _refused(tmp_path / "explicit", dict(COUNTDOWN, days="calendar", calendar="standard"))
    assert explicit.diagnostic_id == "E_VIEW_FIGURE_INVALID"


@pytest.mark.parametrize("figure", [
    {"id": "f", "kind": "weeksUntil", "to": "asOf"},                                       # outside the closed kind set
    {"id": "f", "kind": "daysUntil"},                                                       # no target
    {"id": "f", "kind": "daysIn"},                                                          # no period
    {"id": "f", "kind": "daysUntil", "to": "tomorrow"},                                      # outside the closed fact set
    {"id": "f", "kind": "daysUntil", "to": {"period": "window", "side": "middle"}},
    {"id": "f", "kind": "daysUntil", "to": {"object": "launch", "endpoint": "finish"}},
    {"id": "f", "kind": "daysUntil", "to": {"period": "window", "side": "start"}, "days": "weekly"},
    {"id": "f", "kind": "daysUntil", "to": {"period": "window", "side": "start"}, "scale": 2},
    {"id": "f", "kind": "daysUntil", "to": {"period": "window", "side": "start", "object": "launch"}},
    {"id": "", "kind": "daysUntil", "to": "asOf"},
])
def test_nothing_outside_the_closed_kinds_and_facts_is_accepted(tmp_path, figure):
    assert _refused(tmp_path, figure).diagnostic_id == "E_VIEW_SCHEMA"


def test_a_summary_metric_cannot_name_a_figure_with_a_scope(tmp_path):
    metric = dict(_metric(metric_id="m"), scope="subtree")
    with pytest.raises(ClosureError):
        _render(tmp_path, _parts(COUNTDOWN), _summary(metric))
