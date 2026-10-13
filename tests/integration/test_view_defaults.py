"""A Layout profile's `viewDefaults` supply the design members of a View (#1341, slice 1).

Synthetic Project through the packaged `executive-light` bundle; the committed corpus is not read.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date

import pytest

from chrona.presentation.contracts.diagnostics import (
    PresentationIngressRejected, PresentationResourceSource, collect_presentation_contracts,
)
from chrona.presentation.contracts.resources import ClosureIdentity
from chrona.presentation.contracts.view_defaults import (
    SPLIT_MEMBERS, WHOLE_MEMBERS, collect_column_style_diagnostics, merge_view_defaults,
)
from chrona.resources import schema_validator
from tests.support import synthetic_review as sr


def _source() -> dict:
    return sr.with_calendar(sr.project({"a": sr.span("a", date(2026, 2, 2), 30), "g": sr.point("g", date(2026, 3, 9))}))


def _move_design_to_the_layout(parts: dict, members=WHOLE_MEMBERS) -> dict:
    """Take the design members out of the View and put them, unchanged, in the Layout profile's `viewDefaults`."""
    body, moved = parts["view"]["body"], {}
    for name in members:
        if name in body:
            moved[name] = body.pop(name)
    parts["layout"]["viewDefaults"] = moved
    return moved


def _render(tmp_path, parts):
    return sr.render(tmp_path, _source(), presentation=parts)


def _sub(tmp_path, name):
    path = tmp_path / name
    path.mkdir()
    return path


def test_a_view_without_the_design_members_renders_as_the_view_that_declares_them(tmp_path):
    full = sr.bundle("executive-light")
    thin = deepcopy(full)
    moved = _move_design_to_the_layout(thin)

    assert moved and set(moved) <= set(WHOLE_MEMBERS) and not set(moved) & set(thin["view"]["body"])
    assert _render(_sub(tmp_path, "full"), full).artifact.content == _render(_sub(tmp_path, "thin"), thin).artifact.content


def test_a_member_the_view_declares_wins_over_the_design_whole(tmp_path):
    parts = sr.bundle("executive-light")
    declared = deepcopy(parts["view"]["body"]["axis"])
    parts["layout"]["viewDefaults"] = {"axis": {"tiers": []}, "shading": {"nonWorking": False, "exceptions": False}}

    merged = merge_view_defaults(parts["view"], parts["layout"]["viewDefaults"])

    assert merged["body"]["axis"] == declared  # the View's own member, not the default
    assert merged["body"]["shading"] == parts["view"]["body"].get("shading", {"nonWorking": False, "exceptions": False})


def test_without_viewdefaults_or_when_the_view_declares_every_member_nothing_changes(tmp_path):
    plain = sr.bundle("executive-light")
    full = deepcopy(plain)
    full["layout"]["viewDefaults"] = {name: deepcopy(plain["view"]["body"][name]) for name in WHOLE_MEMBERS if name in plain["view"]["body"]}

    assert _render(_sub(tmp_path, "plain"), plain).artifact.content == _render(_sub(tmp_path, "full"), full).artifact.content


def test_split_members_merge_one_level_down_and_create_omitted_members():
    view = {"version": "chrona/view/v0.28", "kind": "view", "id": "v", "body": {
        "surface": "table-timeline", "comparison": {"baseline": "snapshot", "deltaUnit": "working-days"}}}
    defaults = {"comparison": {"deltaUnit": "calendar-days", "baselineMarks": "ghost-when-changed"},
                "rows": {"mode": "lanes"}, "window": {"marginDays": 7}}

    merged = merge_view_defaults(view, defaults)

    assert merged["body"]["comparison"] == {"baseline": "snapshot", "deltaUnit": "working-days", "baselineMarks": "ghost-when-changed"}
    assert merged["body"]["rows"] == {"mode": "lanes"}
    assert merged["body"]["window"] == {"marginDays": 7}
    assert view["body"]["comparison"] == {"baseline": "snapshot", "deltaUnit": "working-days"}  # the input is not mutated


def test_slice_two_presentation_defaults_merge_without_replacing_connections():
    view = {"version": "chrona/view/v0.28", "kind": "view", "id": "v", "body": {
        "surface": "table-timeline",
        "heading": {"title": "View title"},
        "grouping": {"by": "field", "field": "owner", "missing": "Other",
                      "header": {"text": "View {title}"}},
        "colorEncoding": {"source": {"field": "risk"}, "domain": ["high", "low"]},
    }}
    defaults = {
        "heading": {"title": "{project}", "dateForm": "day-month"},
        "grouping": {"by": "type", "field": "ignored", "presentation": "header",
                     "header": {"text": "Default {ordinal}: {title}"},
                     "tint": {"scale": "risk-colors", "domain": ["high", "low"]}},
        "colorEncoding": {"scale": "risk-colors", "target": "planned",
                          "source": {"field": "ignored"}, "domain": "firstAppearance"},
    }
    before_view, before_defaults = deepcopy(view), deepcopy(defaults)

    merged = merge_view_defaults(view, defaults)

    assert merged["body"]["heading"] == {"title": "View title"}  # whole-member View override
    assert merged["body"]["grouping"] == {
        "by": "field", "field": "owner", "missing": "Other",
        "presentation": "header", "header": {"text": "View {title}"},
        "tint": {"scale": "risk-colors", "domain": ["high", "low"]},
    }
    assert merged["body"]["colorEncoding"] == {
        "source": {"field": "risk"}, "domain": ["high", "low"],
        "scale": "risk-colors", "target": "planned",
    }
    merged["body"]["grouping"]["tint"]["domain"].append("attached")
    assert view == before_view and defaults == before_defaults


@pytest.mark.parametrize("source", [
    "id", "title", "objectType", "entity", "rowIndex", "wbsCode", "path", "totalFloat",
    {"field": "owner"},
    {"comparisonFacet": "finishDelta"},
    {"facet": "planned"},
    {"scenario": "title"},
])
def test_named_column_style_is_selected_by_every_source_discriminator(source):
    discriminator = source if isinstance(source, str) else next(iter(source))
    column = {"id": f"c-{discriminator}", "source": deepcopy(source)}
    defaults = {"columnStyles": {discriminator: {"align": "center", "missing": "unknown"}}}

    merged = merge_view_defaults({"body": {"tableColumns": [column]}}, defaults)

    resolved, = merged["body"]["tableColumns"]
    assert resolved["source"] == source and resolved["id"] == column["id"]
    assert resolved["align"] == "center" and resolved["missing"] == "unknown"


def test_column_style_explicit_name_and_whole_property_overrides_are_pure():
    view = {"body": {"tableColumns": [
        {"id": "Task", "source": "title", "style": "compact",
         "text": {"wrap": "forbid"},
         "missingBy": {"unavailable": "blank"}},
    ]}}
    defaults = {"columnStyles": {
        "title": {"align": "start", "width": "content"},
        "compact": {"align": "end", "width": "fill", "endDisplay": "inclusive",
                    "text": {"wrap": "allow"},
                    "missingBy": {"inProgress": "em-dash", "unavailable": "unknown"}},
    }}
    before_view, before_defaults = deepcopy(view), deepcopy(defaults)

    merged = merge_view_defaults(view, defaults)
    resolved = merged["body"]["tableColumns"][0]

    assert resolved["style"] == "compact"
    assert resolved["align"] == "end" and resolved["width"] == "fill"  # explicit style overrides implicit `title`
    assert resolved["endDisplay"] == "inclusive"
    assert resolved["text"] == {"wrap": "forbid"}
    assert resolved["missingBy"] == {"unavailable": "blank"}  # property object replaces as a whole
    resolved["text"]["wrap"] = "allow"
    assert view == before_view and defaults == before_defaults


def test_malformed_column_style_inputs_are_left_for_view_validation():
    view = {"body": {"tableColumns": [None, {"id": "x", "source": {"field": "owner"},
                                                   "align": None}]}}
    before = deepcopy(view)

    assert merge_view_defaults(view, {"columnStyles": None}) == before
    assert merge_view_defaults(view, {"columnStyles": {"field": "not-a-style-map"}}) == before
    assert view == before


@pytest.mark.parametrize("style", [[], {"bad": "value"}, None, 42])
def test_malformed_explicit_style_is_not_repaired_or_used_as_a_mapping_key(style):
    view = {"body": {"tableColumns": [{"id": "Task", "source": "title", "style": style}]}}
    before = deepcopy(view)
    assert merge_view_defaults(view, {"columnStyles": {"title": {"align": "start"}}}) == before
    assert view == before


def test_unknown_explicit_column_style_reports_its_view_pointer():
    view = {"version": "chrona/view/v0.28", "kind": "view", "id": "v", "body": {
        "tableColumns": [{"id": "Task", "source": "title", "style": "missing-style"}],
    }}
    layout = {"version": "chrona/layout-profile/v0.10", "kind": "layout-profile", "id": "l",
              "viewDefaults": {"columnStyles": {"title": {"align": "start"}}}}
    sources = tuple(PresentationResourceSource(
        ClosureIdentity(kind, value["id"], "draft", "sha256:" + "a" * 64), value,
    ) for kind, value in (("view", view), ("layout-profile", layout)))

    findings = collect_column_style_diagnostics(sources)

    assert [(item.code, item.resource_kind, item.resource_identity, item.pointer)
            for item in findings] == [
        ("E_VIEW_COLUMN_STYLE_UNKNOWN", "view", "v", "/body/tableColumns/0/style")]


def test_unknown_column_style_ingress_collects_a_sibling_resource_error(tmp_path):
    parts = sr.bundle("editorial")
    parts["view"]["body"]["tableColumns"][0]["style"] = "missing-style"
    parts["layout"]["viewDefaults"] = {"columnStyles": {"title": {"align": "start"}}}
    parts["theme"]["body"]["undeclared"] = True

    with pytest.raises(PresentationIngressRejected) as raised:
        _render(tmp_path, parts)

    findings = raised.value.diagnostics
    assert any(item.code == "E_VIEW_COLUMN_STYLE_UNKNOWN" and item.resource_kind == "view"
               and item.pointer == "/body/tableColumns/0/style" for item in findings)
    assert any(item.code == "E_RESOURCE_SCHEMA" and item.resource_kind == "theme"
               for item in findings)


def test_all_unknown_styles_are_reported_in_column_order_without_exposing_a_view_contract():
    parts = sr.bundle("editorial")
    columns = parts["view"]["body"]["tableColumns"]
    for index, column in enumerate(columns):
        column["style"] = f"unknown-{index}"
    sources = tuple(PresentationResourceSource(
        ClosureIdentity(kind, value["id"], "draft", "sha256:" + "a" * 64), value,
    ) for kind, value in (("view", parts["view"]), ("layout-profile", parts["layout"])))
    result = collect_presentation_contracts(sources)
    assert [item.pointer for item in result.diagnostics if item.code == "E_VIEW_COLUMN_STYLE_UNKNOWN"] == [
        f"/body/tableColumns/{index}/style" for index in range(len(columns))]
    assert not any(item.identity.kind == "view" for item in result.contracts)


def test_synthetic_full_and_thin_column_style_views_render_identical_svg(tmp_path):
    full = sr.bundle("editorial")
    full["view"]["body"].pop("markers", None)  # This fixture has no Actual Set.
    full["view"]["body"]["tableColumns"].append({
        "id": "Plan", "source": {"facet": "planned"}, "format": "dateRange",
        "endDisplay": "inclusive", "missing": "em-dash", "align": "start",
        "width": "content", "headerOrientation": "horizontal", "text": {"wrap": "allow"},
    })
    thin = deepcopy(full)
    fields = ("format", "missing", "missingBy", "affixes", "zero", "textRole", "align",
              "headerOrientation", "width", "endDisplay", "text")
    styles = {}
    for column in thin["view"]["body"]["tableColumns"]:
        source = column["source"]
        name = source if isinstance(source, str) else next(iter(source))
        styles[name] = {field: deepcopy(column[field]) for field in fields if field in column}
        for field in fields:
            column.pop(field, None)
    thin["layout"]["viewDefaults"] = {"columnStyles": styles}

    assert styles["facet"]["endDisplay"] == "inclusive"
    assert "text" in styles["title"] and "text" in styles["facet"]
    full_render = _render(_sub(tmp_path, "styled-full"), full)
    thin_render = _render(_sub(tmp_path, "styled-thin"), thin)
    assert full_render.artifact.content == thin_render.artifact.content
    assert full_render.surface == thin_render.surface  # completed geometry, paint, and diagnostics
    assert full_render.scene.surfaces == thin_render.scene.surfaces
    assert full_render.scene.diagnostics == thin_render.scene.diagnostics


def test_thin_view_without_rows_renders_the_design_lane_mode(tmp_path):
    full = sr.bundle("executive-light")
    full["view"] = sr.lane_view(full["view"])
    thin = deepcopy(full)
    thin["layout"]["viewDefaults"] = {"rows": thin["view"]["body"].pop("rows")}

    assert "rows" not in thin["view"]["body"]
    assert merge_view_defaults(thin["view"], thin["layout"]["viewDefaults"])["body"]["rows"]["mode"] == "lanes"
    assert _render(_sub(tmp_path, "full"), full).artifact.content == _render(_sub(tmp_path, "thin"), thin).artifact.content


def test_omitted_split_member_copies_only_design_fields_and_does_not_mutate_defaults():
    view = {"body": {"surface": "table-timeline"}}
    defaults = {"rows": {"mode": "lanes", "packing": ["explicit"], "laneKey": "project-id"},
                "comparison": {"baselineMarks": "ghost-when-changed", "actual": "project-actual"},
                "window": {"marginDays": 7, "mode": "explicit", "start": "2026-01-01"}}
    before = deepcopy(defaults)

    merged = merge_view_defaults(view, defaults)

    assert merged["body"]["rows"] == {"mode": "lanes", "packing": ["explicit"]}
    assert merged["body"]["comparison"] == {"baselineMarks": "ghost-when-changed"}
    assert merged["body"]["window"] == {"marginDays": 7}
    merged["body"]["rows"]["packing"].append("attached")
    assert defaults == before and view == {"body": {"surface": "table-timeline"}}


@pytest.mark.parametrize("declared", [None, "invalid", []])
def test_explicit_malformed_split_member_is_not_repaired(declared):
    view = {"body": {"rows": declared}}
    assert merge_view_defaults(view, {"rows": {"mode": "lanes"}}) == view


def test_missing_window_connection_remains_a_view_validation_error(tmp_path):
    parts = sr.bundle("executive-light")
    parts["view"]["body"].pop("window", None)
    parts["layout"]["viewDefaults"] = {"window": {"marginDays": 7}}

    merged = merge_view_defaults(parts["view"], parts["layout"]["viewDefaults"])
    errors = list(schema_validator("view-v0.28.schema.yaml").iter_errors(merged))
    assert any(list(error.path) == ["body", "window"] and error.validator == "required"
               and "mode" in error.message for error in errors)

    with pytest.raises(Exception) as raised:
        _render(tmp_path, parts)
    assert "E_VIEW_SCHEMA" in str(raised.value)


def test_the_merged_view_is_validated_as_the_view_it_is(tmp_path):
    parts = sr.bundle("executive-light")
    parts["layout"]["viewDefaults"] = {"deadlines": {"show": "never-heard-of"}}

    with pytest.raises(Exception) as raised:
        _render(tmp_path, parts)
    assert "E_VIEW_SCHEMA" in str(raised.value)  # a View error, found after the merge


def test_the_member_lists_are_the_design_half_of_the_reviewed_classification():
    assert set(WHOLE_MEMBERS) == {"visibility", "axis", "deadlines", "shading", "timePresentation", "annotationPresentation",
                                  "backgroundDecoration", "progressFill", "annotationPlacement", "figureFormats", "heading"}
    assert {name: set(members) for name, members in SPLIT_MEMBERS.items()} == {
        "comparison": {"baselineMarks", "missingActualScope", "deltaUnit", "facets"},
        "rows": {"mode", "trackAllocation", "packing", "laneTable", "points", "items"}, "window": {"marginDays"},
        "grouping": {"presentation", "header", "tint"}, "colorEncoding": {"scale", "target"}}
