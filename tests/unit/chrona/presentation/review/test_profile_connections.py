from dataclasses import replace
from types import SimpleNamespace

import pytest

from chrona.core.figures import FigureSpec, PeriodFact
from chrona.presentation.contracts.resources import (
    ContractError, LegendEntry, ReviewDetailInput, SummaryMetric, SummaryPanelInput,
    SummaryProfileInput, ViewComparison, ViewInput, ViewProfileBinding, ViewRowMode,
    ViewRows, ViewVisibility, ViewWindow, _view_figures, _view_profile_bindings,
    freeze, _summary_input,
)
from chrona.presentation.review.profile_connections import (
    ProfileConnectionError, resolve_profile_connections, validate_period_legend_sources,
)


def _view(*, bindings=(), figures=(), wording=None):
    return ViewInput(
        None, None, None, ViewWindow("selected-planned", None, None, 0),
        ViewComparison(None, "optional", "latest", "calendar-days", ()),
        ViewVisibility(False, "none", "none"), (), (), ViewRows(ViewRowMode.AUTOMATIC, ()),
        None, (), None, None, None,
        figures=tuple(figures), profile_bindings=tuple(bindings),
        wording=freeze(wording) if wording is not None else None,
    )


def _summary(*panels):
    return SummaryProfileInput(tuple(panels))


def _panel(panel_id, *metrics):
    return SummaryPanelInput(panel_id, None, "lines", tuple(metrics))


def _metric(metric_id, source, *, label="Before", scope=None, fmt="date"):
    return SummaryMetric(metric_id, label, freeze(source) if isinstance(source, dict) else source, fmt, scope)


def _figure_binding(name="countdown", *, period="launch"):
    figure = FigureSpec(name, "daysUntil", to=PeriodFact(period, "end"), path=f"/body/bindings/{name}/figure")
    return ViewProfileBinding(name, figure=figure, path=f"/body/bindings/{name}")


def test_binding_figure_parser_reuses_figure_grammar_and_keeps_escaped_source_pointer():
    binding, = _view_profile_bindings({
        "target/a~b": {"figure": {"kind": "daysUntil", "to": {"period": "launch", "side": "end"}}}
    }, ())

    assert binding.figure.figure_id == "target/a~b"
    assert binding.figure.to == PeriodFact("launch", "end")
    assert binding.figure.path == "/body/bindings/target~1a~0b/figure"


def test_binding_figure_id_collision_with_explicit_view_figure_points_to_binding():
    explicit = _view_figures(({
        "id": "countdown", "kind": "daysUntil", "to": {"period": "launch", "side": "end"},
    },))

    with pytest.raises(ContractError) as error:
        _view_profile_bindings({
            "countdown": {"figure": {"kind": "daysUntil", "to": {"period": "launch", "side": "end"}}}
        }, explicit)

    assert error.value.diagnostic_id == "E_VIEW_BINDING_FIGURE_COLLISION"
    assert error.value.source_ref == "/body/bindings/countdown"


def test_resolver_binds_metric_and_overrides_typed_caption_and_arbitrary_legend_role():
    view = _view(bindings=(_figure_binding(),), wording={
        "summary": {"panel.metric": "DAYS"}, "legend": {"custom-note": "Note"},
    })
    summary = _summary(_panel("panel", _metric("metric", {"slot": "countdown"})))
    detail = ReviewDetailInput((), (), (LegendEntry("custom-note", "Old"),), None)

    result = resolve_profile_connections(view, summary, detail, project_object_ids=frozenset())

    assert result.summary.panels[0].metrics[0].source == freeze({"figure": "countdown"})
    assert result.summary.panels[0].metrics[0].label == "DAYS"
    assert result.detail.legend == (LegendEntry("custom-note", "Note"),)
    assert result.omissions == ()


def test_unbound_slot_retains_original_metric_and_index_in_omission_fact():
    summary = _summary(_panel("panel", _metric("first", "count.selected"),
                              _metric("later", {"slot": "later"})))

    result = resolve_profile_connections(_view(), summary, None, project_object_ids=frozenset())

    assert len(result.summary.panels[0].metrics) == 2
    assert result.omissions == (result.omissions[0],)
    omission, = result.omissions
    assert (omission.panel_index, omission.metric_index, omission.panel_id, omission.metric_id) == (0, 1, "panel", "later")
    assert (omission.source_kind, omission.source_name, omission.code) == ("slot", "later", "W_SUMMARY_SLOT_UNBOUND")
    assert omission.source_ref == "/body/panels/0/metrics/1/source"


def test_binding_to_undeclared_slot_is_pointed_error():
    with pytest.raises(ProfileConnectionError) as error:
        resolve_profile_connections(_view(bindings=(ViewProfileBinding("typo", object_id="obj", path="/body/bindings/typo"),)),
                                     _summary(_panel("panel", _metric("m", "count.selected"))), None,
                                     project_object_ids=frozenset({"obj"}))

    assert error.value.code == "E_VIEW_BINDING_UNKNOWN"
    assert error.value.source_ref == "/body/bindings/typo"


def test_bound_missing_object_is_error_but_valid_unselected_object_source_is_preserved():
    binding = ViewProfileBinding("plan", object_id="missing", path="/body/bindings/plan")
    summary = _summary(_panel("panel", _metric("m", {"slot": "plan"})))
    with pytest.raises(ProfileConnectionError) as error:
        resolve_profile_connections(_view(bindings=(binding,)), summary, None,
                                    project_object_ids=frozenset({"other"}))
    assert error.value.code == "E_FIGURE_OBJECT_UNKNOWN"
    assert error.value.source_ref == "/body/bindings/plan/object"

    result = resolve_profile_connections(_view(bindings=(replace(binding, object_id="valid"),)), summary, None,
                                         project_object_ids=frozenset({"valid"}))
    assert result.summary.panels[0].metrics[0].source == freeze({"object": "valid", "facet": "planned"})


def test_subtree_scope_is_checked_after_binding_and_only_allows_object_binding():
    summary = _summary(_panel("panel", _metric("m", {"slot": "slot"}, scope="subtree")))
    object_result = resolve_profile_connections(
        _view(bindings=(ViewProfileBinding("slot", object_id="root", path="/body/bindings/slot"),)),
        summary, None, project_object_ids=frozenset({"root"}))
    assert object_result.summary.panels[0].metrics[0].source == freeze({"object": "root", "facet": "planned"})

    with pytest.raises(ProfileConnectionError) as error:
        resolve_profile_connections(_view(bindings=(_figure_binding("slot"),)), summary, None,
                                    project_object_ids=frozenset())
    assert error.value.code == "E_PRESENTATION_SUMMARY_SOURCE"
    assert error.value.source_ref == "/body/panels/0/metrics/0/source"


def test_map_metric_scope_error_uses_the_authored_escaped_metric_key():
    summary = _summary_input(freeze({"panels": [{"id": "panel", "metrics": {
        "metric/a~b": {"source": {"slot": "slot"}, "format": "count", "scope": "subtree"}}}]}))
    with pytest.raises(ProfileConnectionError) as error:
        resolve_profile_connections(_view(bindings=(_figure_binding("slot"),)), summary, None,
                                    project_object_ids=frozenset())
    assert error.value.source_ref == "/body/panels/0/metrics/metric~1a~0b/source"
    assert error.value.component == "presentation"


def test_unbound_legacy_figure_omission_is_distinct_from_bound_figure_scope_errors():
    legacy = _summary(_panel("panel", _metric("m", {"figure": "missing"})))
    omission, = resolve_profile_connections(_view(), legacy, None, project_object_ids=frozenset()).omissions
    assert (omission.source_kind, omission.source_name, omission.code) == (
        "figure", "missing", "I_SUMMARY_FIGURE_UNBOUND")

    group = FigureSpec("group-count", "count", source="selected", scope="group")
    bound = _summary(_panel("panel", _metric("m", {"figure": "group-count"})))
    assert resolve_profile_connections(_view(figures=(group,)), bound, None,
                                       project_object_ids=frozenset()).omissions == ()


def test_dormant_summary_bindings_and_wording_drop_generated_aliases_but_keep_explicit_figures():
    explicit = FigureSpec("explicit-count", "count", source="selected")
    view = _view(bindings=(_figure_binding("dormant-countdown"),), figures=(explicit,), wording={
        "summary": {"missing.panel": "Dormant copy"},
    })

    result = resolve_profile_connections(view, None, None, project_object_ids=frozenset())

    assert result.summary is None
    assert result.omissions == ()
    assert result.view.wording["summary"]["missing.panel"] == "Dormant copy"
    assert result.view.figures == (explicit,)
    assert result.view.profile_bindings == view.profile_bindings


def test_summary_wording_uses_exact_dotted_key_and_handles_ambiguity_and_unknown_keys():
    summary = _summary(_panel("panel.with.dot", _metric("metric.with.dot", "count.selected")))
    result = resolve_profile_connections(_view(wording={
        "summary": {"panel.with.dot.metric.with.dot": "Exact"},
    }), summary, None, project_object_ids=frozenset())
    assert result.summary.panels[0].metrics[0].label == "Exact"

    duplicate = _summary(_panel("same", _metric("m", "count.selected")),
                         _panel("same", _metric("m", "count.selected")))
    with pytest.raises(ProfileConnectionError) as ambiguous:
        resolve_profile_connections(_view(wording={"summary": {"same.m": "X"}}), duplicate, None,
                                    project_object_ids=frozenset())
    assert ambiguous.value.code == "E_VIEW_WORDING_AMBIGUOUS"
    assert ambiguous.value.source_ref == "/body/wording/summary/same.m"

    with pytest.raises(ProfileConnectionError) as unknown:
        resolve_profile_connections(_view(wording={"summary": {"missing.m": "X"}}), summary, None,
                                    project_object_ids=frozenset())
    assert unknown.value.code == "E_VIEW_WORDING_UNKNOWN"
    assert unknown.value.source_ref == "/body/wording/summary/missing.m"

    legacy = _summary(_panel("panel", ("note", "Original copy")))
    legacy_result = resolve_profile_connections(_view(wording={"summary": {"panel.note": "PROMO"}}), legacy,
                                                None, project_object_ids=frozenset())
    assert legacy_result.summary.panels[0].metrics == (("note", "Original copy"),)
    assert legacy_result.view.wording["summary"]["panel.note"] == "PROMO"


def test_summary_wording_overrides_panel_title_without_mutating_profile_and_checks_collisions():
    panel = _panel("panel.with.dot", _metric("metric", "count.selected"))
    panel = replace(panel, title="Original title")
    summary = _summary(panel)
    view = _view(wording={"summary": {"panel.with.dot.title": "RC まで"}})

    result = resolve_profile_connections(view, summary, None, project_object_ids=frozenset())

    assert result.summary.panels[0].title == "RC まで"
    assert result.summary.panels[0].id == "panel.with.dot"
    assert summary.panels[0].title == "Original title"
    assert view.wording["summary"]["panel.with.dot.title"] == "RC まで"

    collision = _summary(_panel("panel", _metric("title", "count.selected")))
    with pytest.raises(ProfileConnectionError) as metric_collision:
        resolve_profile_connections(_view(wording={"summary": {"panel.title": "Override"}}), collision, None,
                                    project_object_ids=frozenset())
    assert metric_collision.value.code == "E_VIEW_WORDING_AMBIGUOUS"
    assert metric_collision.value.source_ref == "/body/wording/summary/panel.title"

    duplicate_panels = _summary(_panel("duplicate"), _panel("duplicate"))
    with pytest.raises(ProfileConnectionError) as duplicate_collision:
        resolve_profile_connections(_view(wording={"summary": {"duplicate.title": "Override"}}),
                                    duplicate_panels, None, project_object_ids=frozenset())
    assert duplicate_collision.value.code == "E_VIEW_WORDING_AMBIGUOUS"

    with pytest.raises(ProfileConnectionError) as unknown:
        resolve_profile_connections(_view(wording={"summary": {"unknown/a~b.title": "X"}}), summary, None,
                                    project_object_ids=frozenset())
    assert unknown.value.code == "E_VIEW_WORDING_UNKNOWN"
    assert unknown.value.source_ref == "/body/wording/summary/unknown~1a~0b.title"


def test_legend_wording_is_limited_to_profile_roles_without_closing_role_vocabulary():
    detail = ReviewDetailInput((), (), (LegendEntry("project-defined", "Old", "p1"),), None)
    result = resolve_profile_connections(_view(wording={"legend": {"project-defined": "New"}}),
                                         None, detail, project_object_ids=frozenset())
    assert result.detail.legend == (LegendEntry("project-defined", "New", "p1"),)

    with pytest.raises(ProfileConnectionError) as error:
        resolve_profile_connections(_view(wording={"legend": {"not-present": "X"}}),
                                    None, detail, project_object_ids=frozenset())
    assert error.value.code == "E_VIEW_WORDING_UNKNOWN"
    assert error.value.source_ref == "/body/wording/legend/not-present"


def test_progress_legend_wording_is_valid_without_detail_but_does_not_create_an_entry():
    view = _view(wording={"legend": {"progressFill": "Observed progress"}})

    result = resolve_profile_connections(view, None, None, project_object_ids=frozenset())

    assert result.detail is None
    assert result.view.wording["legend"] == {"progressFill": "Observed progress"}

    detail = ReviewDetailInput((), (), (LegendEntry("progressFill", "Progress"),), None)
    with_entry = resolve_profile_connections(view, None, detail, project_object_ids=frozenset())
    assert with_entry.detail.legend == (LegendEntry("progressFill", "Observed progress"),)


@pytest.mark.parametrize("role", ("snapshot", "deadlineMark"))
def test_default_semantic_legend_wording_is_valid_without_detail_or_explicit_entry(role):
    view = _view(wording={"legend": {role: "Reviewer label"}})

    without_detail = resolve_profile_connections(view, None, None, project_object_ids=frozenset())
    assert without_detail.detail is None
    assert without_detail.view.wording["legend"] == {role: "Reviewer label"}

    detail = ReviewDetailInput((), (), (LegendEntry("planned", "Plan"),), None)
    with_detail = resolve_profile_connections(view, None, detail, project_object_ids=frozenset())
    assert with_detail.detail.legend == (LegendEntry("planned", "Plan"),)
    assert with_detail.view.wording["legend"] == {role: "Reviewer label"}


@pytest.mark.parametrize("role", ("snapshot", "deadlineMark"))
def test_explicit_default_role_keeps_order_while_view_wording_overrides_label(role):
    view = _view(wording={"legend": {role: "Reviewer label"}})
    detail = ReviewDetailInput((), (), (LegendEntry("planned", "Plan"),
                                        LegendEntry(role, "Detail label"),
                                        LegendEntry("actual", "Actual")), None)

    result = resolve_profile_connections(view, None, detail, project_object_ids=frozenset())

    assert tuple(entry.role for entry in result.detail.legend) == ("planned", role, "actual")
    assert result.detail.legend[1].label == "Reviewer label"


@pytest.mark.parametrize(("roles", "explicit_role", "expected_index"), (
    (("snapshot",), "snapshot", 0),
    (("snapshot", "deadlineMark"), "deadlineMark", 1),
))
def test_detail_unkeyed_role_conflicting_with_explicit_entry_is_pointed_error(
        roles, explicit_role, expected_index):
    detail = ReviewDetailInput((), (), (LegendEntry(explicit_role, "Label"),), None,
                              unkeyed_legend_roles=roles)

    with pytest.raises(ProfileConnectionError) as error:
        resolve_profile_connections(_view(), None, detail, project_object_ids=frozenset())

    assert error.value.code == "E_DETAIL_LEGEND_POLICY"
    assert error.value.source_ref == f"/body/unkeyedLegendRoles/{expected_index}"


def test_actual_qualifier_wording_requires_actual_candidate_and_keeps_fragments_in_view():
    wording = {"legend": {
        "actual": "Observed",
        "actual-ahead": "early",
        "actual-on-track": "on plan",
        "actual-behind": "late",
    }}
    detail = ReviewDetailInput((), (), (
        LegendEntry("planned", "Plan"), LegendEntry("actual", "Actual"),
    ), None)

    result = resolve_profile_connections(_view(wording=wording), None, detail,
                                         project_object_ids=frozenset())

    assert result.detail.legend == (
        LegendEntry("planned", "Plan"), LegendEntry("actual", "Observed"),
    )
    assert result.view.wording["legend"] == wording["legend"]

    for qualifier in ("actual-ahead", "actual-on-track", "actual-behind"):
        with pytest.raises(ProfileConnectionError) as error:
            resolve_profile_connections(
                _view(wording={"legend": {qualifier: "fragment"}}), None,
                ReviewDetailInput((), (), (LegendEntry("planned", "Plan"),), None),
                project_object_ids=frozenset(),
            )
        assert error.value.code == "E_VIEW_WORDING_UNKNOWN"
        assert error.value.source_ref == f"/body/wording/legend/{qualifier}"


def test_period_legend_source_requires_one_selected_period_and_the_exact_visual_role():
    period = SimpleNamespace(period_id="p1", band_role="period-band:launch")
    validate_period_legend_sources(
        ReviewDetailInput((), (), (LegendEntry("period-band:launch", "Launch", "p1"),), None),
        (period,),
    )

    cases = (
        (ReviewDetailInput((), (), (LegendEntry("period-band:launch", "X", "missing"),), None),
         (period,), "E_REVIEW_LEGEND_PERIOD_SOURCE", "/body/legend/0/sourceRef"),
        (ReviewDetailInput((), (), (LegendEntry("period-band:launch", "X", "p1"),
                                    LegendEntry("period-band:launch", "Y", "p1")), None),
         (period,), "E_REVIEW_LEGEND_PERIOD_SOURCE", "/body/legend/1/sourceRef"),
        (ReviewDetailInput((), (), (LegendEntry("period-band:launch", "X", "p1"),), None),
         (period, period), "E_REVIEW_LEGEND_PERIOD_SOURCE", "/body/legend/0/sourceRef"),
        (ReviewDetailInput((), (), (LegendEntry("period-band", "X", "p1"),), None),
         (period,), "E_REVIEW_LEGEND_PERIOD_ROLE", "/body/legend/0/role"),
    )
    for detail, periods, code, pointer in cases:
        with pytest.raises(ProfileConnectionError) as error:
            validate_period_legend_sources(detail, periods)
        assert (error.value.code, error.value.source_ref, error.value.component) == (
            code, pointer, "review-detail-profile")


def test_wording_error_pointer_escapes_selector_tokens():
    summary = _summary(_panel("panel", _metric("m", "count.selected")))
    with pytest.raises(ProfileConnectionError) as error:
        resolve_profile_connections(_view(wording={"summary": {"missing/a~b": "X"}}), summary, None,
                                    project_object_ids=frozenset())

    assert error.value.source_ref == "/body/wording/summary/missing~1a~0b"
