from dataclasses import replace

import pytest

from chrona.core.figures import FigureSpec, PeriodFact
from chrona.presentation.contracts.resources import (
    ContractError, LegendEntry, ReviewDetailInput, SummaryMetric, SummaryPanelInput,
    SummaryProfileInput, ViewComparison, ViewInput, ViewProfileBinding, ViewRowMode,
    ViewRows, ViewVisibility, ViewWindow, _view_figures, _view_profile_bindings,
    freeze,
)
from chrona.presentation.review.profile_connections import ProfileConnectionError, resolve_profile_connections


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
    assert (omission.source_kind, omission.source_name, omission.code) == ("slot", "later", "I_SUMMARY_SLOT_UNBOUND")
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


def test_unbound_legacy_figure_omission_is_distinct_from_bound_figure_scope_errors():
    legacy = _summary(_panel("panel", _metric("m", {"figure": "missing"})))
    omission, = resolve_profile_connections(_view(), legacy, None, project_object_ids=frozenset()).omissions
    assert (omission.source_kind, omission.source_name, omission.code) == (
        "figure", "missing", "I_SUMMARY_FIGURE_UNBOUND")

    group = FigureSpec("group-count", "count", source="selected", scope="group")
    bound = _summary(_panel("panel", _metric("m", {"figure": "group-count"})))
    assert resolve_profile_connections(_view(figures=(group,)), bound, None,
                                       project_object_ids=frozenset()).omissions == ()


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


def test_legend_wording_is_limited_to_profile_roles_without_closing_role_vocabulary():
    detail = ReviewDetailInput((), (), (LegendEntry("project-defined", "Old"),), None)
    result = resolve_profile_connections(_view(wording={"legend": {"project-defined": "New"}}),
                                         None, detail, project_object_ids=frozenset())
    assert result.detail.legend == (LegendEntry("project-defined", "New"),)

    with pytest.raises(ProfileConnectionError) as error:
        resolve_profile_connections(_view(wording={"legend": {"not-present": "X"}}),
                                    None, detail, project_object_ids=frozenset())
    assert error.value.code == "E_VIEW_WORDING_UNKNOWN"
    assert error.value.source_ref == "/body/wording/legend/not-present"


def test_wording_error_pointer_escapes_selector_tokens():
    summary = _summary(_panel("panel", _metric("m", "count.selected")))
    with pytest.raises(ProfileConnectionError) as error:
        resolve_profile_connections(_view(wording={"summary": {"missing/a~b": "X"}}), summary, None,
                                    project_object_ids=frozenset())

    assert error.value.source_ref == "/body/wording/summary/missing~1a~0b"
