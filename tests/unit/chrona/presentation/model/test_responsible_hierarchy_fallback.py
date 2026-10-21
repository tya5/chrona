"""An unbound responsible grouping may use Project root groups, not tree expansion."""
from datetime import date

from chrona.presentation.contracts import ClosureIdentity, parse_contract
from chrona.presentation.contracts.resources import _PrivateGroupingMode
from chrona.presentation.model.field_role_view import resolve_field_role_view
from chrona.presentation.model.projection import build_review_projection
from tests.support import synthetic_review as sr


def _view(*, fallback="hierarchy", role_column=False):
    parts = sr.bundle("executive-light")
    body = parts["view"]["body"]
    body["grouping"] = {"by": {"fieldRole": "responsible"}, "fallback": fallback,
                        "missing": "Unassigned", "presentation": "header",
                        "header": {"text": "{title}"}}
    if role_column:
        body["rows"] = {"mode": "automatic"}
        body["tableColumns"] = [
            {"id": "Task", "source": "title", "missing": "em-dash", "align": "start",
             "width": {"fr": 1}, "headerOrientation": "horizontal"},
            {"id": "Responsible", "source": {"fieldRole": "responsible"},
             "missing": "em-dash", "align": "start", "width": {"fr": 1},
             "headerOrientation": "horizontal"},
        ]
    return parse_contract(
        ClosureIdentity("view", parts["view"]["id"], "draft", "sha256:" + "a" * 64),
        parts["view"]).view


def _project(*, bound=False):
    objects = {
        "root": {"type": "group", "title": "Root group", "schedule": {"mode": "rollup"}},
        "nested": {"type": "group", "title": "Nested group", "parent": "root",
                   "schedule": {"mode": "rollup"}},
        "intermediary": {"type": "task", "title": "Intermediary", "parent": "nested",
                         "fields": {}, "schedule": {"mode": "fixed-span", "start": "2026-01-01", "end": "2026-01-03"}},
        "inside": {"type": "task", "title": "Inside", "parent": "intermediary", "fields": {},
                   "schedule": {"mode": "fixed-span", "start": "2026-01-03", "end": "2026-01-05"}},
        "ungrouped": {"type": "gate", "title": "Ungrouped", "fields": {},
                      "schedule": {"mode": "fixed-point", "at": "2026-01-06"}},
    }
    source = {"objects": objects, "entities": {}}
    if bound:
        source["fieldRoles"] = {"responsible": "owner"}
        for object_id in ("inside", "ungrouped"):
            objects[object_id]["fields"]["owner"] = "eng"
    return source


def _placements():
    return {
        "root": {"start": date(2026, 1, 1), "end": date(2026, 1, 5)},
        "nested": {"start": date(2026, 1, 1), "end": date(2026, 1, 5)},
        "intermediary": {"start": date(2026, 1, 1), "end": date(2026, 1, 3)},
        "inside": {"start": date(2026, 1, 3), "end": date(2026, 1, 5)},
        "ungrouped": {"at": date(2026, 1, 6)},
    }


def test_unbound_responsible_uses_rootmost_group_headers_and_keeps_flat_items_ungrouped():
    project = _project()
    view, info = resolve_field_role_view(_view(), project)

    projection = build_review_projection(project, _placements(), view, None)

    assert view.grouping is not None and view.grouping.by is _PrivateGroupingMode.PROJECT_ROOT_GROUP
    assert not info
    assert {row.row_id for row in projection.rows} == {"intermediary", "inside", "ungrouped"}
    assert {row.group_id for row in projection.rows} == {"root", ""}
    assert next(row for row in projection.rows if row.row_id == "inside").group_id == "root"
    assert all(item.object_id not in {"root", "nested"} for item in projection.items)


def test_bound_responsible_remains_field_grouping_and_ordinary_hierarchy_remains_tree_expansion():
    project = _project(bound=True)
    bound, info = resolve_field_role_view(_view(), project)
    assert bound.grouping is not None and bound.grouping.by == "field" and bound.grouping.field == "owner"
    assert not info

    explicit = _view()
    from dataclasses import replace
    explicit = replace(explicit, grouping=replace(explicit.grouping, by="hierarchy", field_role=None,
                                                  fallback=None, depth="all", rollup="header"))
    expanded = build_review_projection(project, _placements(), explicit, None)
    assert expanded.hierarchy_grouping
    assert {item.object_id for item in expanded.items} == {"intermediary", "inside", "ungrouped"}


def test_hierarchy_fallback_with_no_group_ancestor_keeps_a_single_ungrouped_list():
    project = {"objects": {
        "one": {"type": "task", "title": "One", "fields": {}},
        "two": {"type": "gate", "title": "Two", "fields": {}},
    }, "entities": {}}
    view, info = resolve_field_role_view(_view(), project)

    projection = build_review_projection(project, {
        "one": {"start": date(2026, 1, 1), "end": date(2026, 1, 2)},
        "two": {"at": date(2026, 1, 3)},
    }, view, None)

    assert not info
    assert {row.group_id for row in projection.rows} == {""}
    assert {item.object_id for item in projection.items} == {"one", "two"}


def test_an_unbound_role_column_is_omitted_without_a_diagnostic_beside_the_handled_grouping():
    project = _project()
    view = _view(role_column=True)
    resolved, info = resolve_field_role_view(view, project)
    assert resolved.grouping is not None and resolved.grouping.by is _PrivateGroupingMode.PROJECT_ROOT_GROUP
    assert info == ()  # an omitted column is not reported (#1870)
    assert len(resolved.table_columns) == len(view.table_columns) - 1
