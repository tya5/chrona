"""Project context-group ordering and role-bound summary omission (#1626)."""
from __future__ import annotations

from datetime import date

import pytest

from chrona.presentation.contracts import ClosureIdentity, parse_contract
from chrona.presentation.model.field_role_view import resolve_field_role_view
from chrona.presentation.model.info_diagnostics import FieldGroupingSummariesOmitted, UnboundFieldRole
from chrona.usecases.draft_render import warning_payloads
from tests.support import synthetic_review as sr


def _source(*, responsible_role: bool = False, ungrouped: bool = False):
    # Declaration, alphabetic ID and earliest-start orders intentionally differ.
    objects = {
        "z-design": {"type": "group", "title": "Design", "schedule": {"mode": "rollup"}},
        "design-task": {**sr.span("design-task", date(2026, 3, 2), 5, owner="blue"), "parent": "z-design"},
        "a-build": {"type": "group", "title": "Build", "schedule": {"mode": "rollup"}},
        "build-task": {**sr.span("build-task", date(2026, 1, 5), 5, owner="green"), "parent": "a-build"},
        "m-release": {"type": "group", "title": "Release", "schedule": {"mode": "rollup"}},
        "release-task": {**sr.span("release-task", date(2026, 2, 2), 5, owner="gold"), "parent": "m-release"},
    }
    if ungrouped:
        objects["ungrouped-task"] = sr.span("ungrouped-task", date(2026, 1, 1), 2,
                                              owner="blue", title="Ungrouped work")
    source = sr.project(objects, responsible_field_role=False)
    if responsible_role:
        source["fieldRoles"] = {"responsible": "owner"}
    return source


def _parts(grouping):
    parts = sr.bundle("executive-light")
    body = parts["view"]["body"]
    body["selection"]["exclude"]["objectTypes"] = []
    body["grouping"] = grouping
    body["rows"] = {"mode": "automatic"}
    return parts


def _render(tmp_path, source, grouping):
    tmp_path.mkdir(parents=True, exist_ok=True)
    parts = _parts(grouping)
    return sr.render(tmp_path, source, presentation=parts)


def _group_header_order(rendered):
    return [item.text for item in rendered.surface.primitives
            if item.kind == "Text" and item.purpose == "group-header"]


def test_unbound_role_context_groups_default_to_project_declaration_order(tmp_path):
    rendered = _render(tmp_path, _source(ungrouped=True), {
        "by": {"fieldRole": "responsible"}, "fallback": "hierarchy",
        "missing": "Unassigned", "presentation": "header",
    })

    assert _group_header_order(rendered) == ["Design", "Build", "Release"]
    ungrouped = next(item for item in rendered.surface.primitives
                     if item.kind == "Text" and item.text == "Ungrouped work")
    first_group = min(item.bounds[1] for item in rendered.surface.primitives
                      if item.kind == "Text" and item.purpose == "group-header")
    assert ungrouped.bounds[1] < first_group
    assert not any(isinstance(item, UnboundFieldRole) and item.role == "responsible"
                   for item in rendered.info_diagnostics)


def test_root_group_context_order_preserves_explicit_order_and_earliest_start(tmp_path):
    explicit = _render(tmp_path / "explicit", _source(), {
        "by": {"fieldRole": "responsible"}, "fallback": "hierarchy",
        "missing": "Unassigned", "presentation": "header",
        "order": ["m-release", "z-design", "a-build"],
    })
    earliest = _render(tmp_path / "earliest", _source(), {
        "by": {"fieldRole": "responsible"}, "fallback": "hierarchy",
        "missing": "Unassigned", "presentation": "header",
        "order": {"by": "earliestPlannedStart"},
    })

    assert _group_header_order(explicit) == ["Release", "Design", "Build"]
    assert _group_header_order(earliest) == ["Build", "Release", "Design"]


def test_bound_role_grouping_omits_selected_group_summaries_and_transports_count(tmp_path):
    rendered = _render(tmp_path, _source(responsible_role=True), {
        "by": {"fieldRole": "responsible"}, "fallback": "hierarchy",
        "missing": "Unassigned", "presentation": "header",
    })

    assert {item.source_ref for item in rendered.surface.primitives
            if item.purpose == "planned"} == {"design-task", "build-task", "release-task"}
    assert _group_header_order(rendered) == ["Team blue", "Team gold", "Team green"]
    (info,) = [item for item in rendered.info_diagnostics
               if isinstance(item, FieldGroupingSummariesOmitted)]
    assert info.count == 3
    payload, = [item for item in warning_payloads(rendered)
                if item["code"] == "I_VIEW_FIELD_GROUP_SUMMARIES_OMITTED"]
    assert payload["severity"] == "info" and payload["count"] == 3
    assert info.scene_diagnostic() in rendered.scene.diagnostics


def test_filtered_out_group_summaries_do_not_increase_omission_count(tmp_path):
    parts = _parts({
        "by": {"fieldRole": "responsible"}, "fallback": "hierarchy",
        "missing": "Unassigned", "presentation": "header",
    })
    parts["view"]["body"]["selection"]["exclude"]["objectTypes"] = ["group"]
    rendered = sr.render(tmp_path, _source(responsible_role=True), presentation=parts)

    assert not any(isinstance(item, FieldGroupingSummariesOmitted)
                   for item in rendered.info_diagnostics)


def test_bound_grouping_resolution_is_idempotent_and_retains_role_origin():
    parts = _parts({"by": {"fieldRole": "responsible"}, "fallback": "hierarchy",
                    "missing": "Unassigned", "presentation": "header"})
    parsed = parse_contract(ClosureIdentity("view", parts["view"]["id"], "test",
                                            "sha256:" + "a" * 64), parts["view"])
    view = parsed.view
    project = _source(responsible_role=True)

    once, _ = resolve_field_role_view(view, project)
    twice, _ = resolve_field_role_view(once, project)

    assert once.grouping.field == twice.grouping.field == "owner"
    assert once.grouping.field_role == twice.grouping.field_role == "responsible"


@pytest.mark.parametrize("count", [0, True])
def test_omission_info_rejects_nonpositive_or_boolean_counts(count):
    with pytest.raises(ValueError, match="positive count"):
        FieldGroupingSummariesOmitted(count)


def test_direct_field_and_none_grouping_keep_summary_rows(tmp_path):
    source = _source(responsible_role=True)
    direct = _render(tmp_path / "direct", source, {
        "by": "field", "field": "owner", "missing": "Unassigned", "presentation": "header",
    })
    ungrouped = _render(tmp_path / "none", source, {"by": "none"})

    for rendered in (direct, ungrouped):
        assert {item.source_ref for item in rendered.surface.primitives
                if item.purpose == "planned"} == {
                    "z-design", "design-task", "a-build", "build-task", "m-release", "release-task"}
        assert not any(isinstance(item, FieldGroupingSummariesOmitted)
                       for item in rendered.info_diagnostics)
