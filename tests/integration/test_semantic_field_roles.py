"""Role-bound Views consume Project meaning before geometry, never infer keys."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path

import pytest

from chrona.presentation.contracts import ClosureIdentity, parse_contract
from chrona.presentation.contracts.view_defaults import merge_view_defaults
from chrona.presentation.model.field_role_view import resolve_field_role_view
from chrona.presentation.model.info_diagnostics import UnboundFieldRole
from chrona.presentation.model.projection import build_review_projection
from chrona.presentation.model.surface_content import table_value
from chrona.usecases.render_review import RenderFailed
from chrona.usecases.draft_render import warning_payloads
from tests.support import synthetic_review as sr


def _source(*, roles=True):
    source = sr.with_calendar(sr.project({
        "a": sr.span("a", date(2026, 2, 1), 10, owner="engineering"),
        "b": sr.span("b", date(2026, 2, 5), 10, owner="operations"),
    }))
    source["objects"]["a"]["fields"]["stage"] = "Design"
    source["objects"]["b"]["fields"]["stage"] = "Build"
    if roles:
        source["fieldRoles"] = {"responsible": "owner", "phase": "stage"}
    return source


def _parts(mode="automatic"):
    parts = sr.bundle("executive-light")
    body = parts["view"]["body"]
    body["grouping"] = {"by": {"fieldRole": "responsible"}, "fallback": "objectType",
                        "missing": "Unassigned", "presentation": "band"}
    body.pop("hierarchyColumn", None)
    body["tableColumns"] = [
        {"id": "Task", "source": "title", "missing": "em-dash", "align": "start",
         "width": {"fr": 1}, "headerOrientation": "horizontal"},
        {"id": "Phase", "source": {"fieldRole": "phase"}, "missing": "em-dash", "align": "start",
         "width": "content", "headerOrientation": "horizontal"},
    ]
    body["rows"] = {"mode": mode}
    if mode == "lanes":
        del body["tableColumns"]
        body["rows"].update({"packing": ["explicit", "attached"], "laneTable": {
            "label": "group", "columns": [{"id": "Task", "source": "label"},
                                          {"id": "Phase", "source": {"fieldRole": "phase"}}]}})
    return parts


@pytest.mark.parametrize("mode", ["automatic", "lanes"])
def test_roles_group_by_entity_title_and_show_phase_without_project_field_names(tmp_path, mode):
    source, parts = _source(), _parts(mode)
    if mode == "automatic":
        parts["view"]["body"]["grouping"].update({"presentation": "header", "header": {"text": "{title}"}})
        parts["view"]["body"]["hierarchyColumn"] = "Task"
    originals = deepcopy((source, parts))

    rendered = sr.render(tmp_path, source, presentation=parts)

    texts = {item.text for item in rendered.surface.primitives if item.kind == "Text"}
    assert {"team engineering", "team operations", "phase", "design", "build"} <= {text.casefold() for text in texts}
    assert not any(isinstance(info, UnboundFieldRole) for info in rendered.info_diagnostics)
    assert (source, parts) == originals


@pytest.mark.parametrize("mode", ["automatic", "lanes"])
def test_unbound_roles_use_fallback_omit_phase_and_count_declarations_not_rows(tmp_path, mode):
    source, parts = _source(roles=False), _parts(mode)
    if mode == "lanes":
        parts["view"]["body"]["rows"]["laneTable"]["label"] = "lane"
    control = deepcopy(parts)
    control["view"]["body"]["grouping"] = {"by": "objectType", "presentation": "band"}
    if mode == "lanes":
        control["view"]["body"]["rows"]["laneTable"]["columns"].pop()
    else:
        control["view"]["body"]["tableColumns"].pop()

    (tmp_path / "role").mkdir()
    (tmp_path / "control").mkdir()
    rendered = sr.render(tmp_path / "role", source, presentation=parts)
    before = sr.render(tmp_path / "control", source, presentation=control)

    assert rendered.artifact.content == before.artifact.content
    assert not any(item.text == "Phase" for item in rendered.surface.primitives)
    info = {item.role: item for item in rendered.info_diagnostics if isinstance(item, UnboundFieldRole)}
    assert info["responsible"].count == 1
    assert info["phase"].count == 1
    assert info["phase"].code == "I_VIEW_FIELD_ROLE_UNBOUND"
    assert all("source/fieldRole" in path for path in info["phase"].source_refs)
    cli = {item["fieldRole"]: item for item in warning_payloads(rendered)
           if item["code"] == "I_VIEW_FIELD_ROLE_UNBOUND"}
    assert cli["phase"]["severity"] == "info" and cli["phase"]["count"] == 1
    assert cli["phase"]["sourceRefs"] == list(info["phase"].source_refs)


def test_declared_role_with_missing_item_value_keeps_the_column_missing_policy(tmp_path):
    source, parts = _source(), _parts()
    del source["objects"]["a"]["fields"]["stage"]

    rendered = sr.render(tmp_path, source, presentation=parts)

    texts = {item.text for item in rendered.surface.primitives if item.kind == "Text"}
    assert {"Phase", "Build", "—"} <= texts
    assert not any(isinstance(info, UnboundFieldRole) for info in rendered.info_diagnostics)


def test_omitting_every_column_is_an_explicit_view_failure(tmp_path):
    parts = _parts()
    parts["view"]["body"]["tableColumns"] = parts["view"]["body"]["tableColumns"][1:]

    with pytest.raises(RenderFailed) as error:
        sr.render(tmp_path, _source(roles=False), presentation=parts)

    assert error.value.code == "E_VIEW_TABLE_COLUMNS_EMPTY"


def test_hierarchy_column_cannot_silently_target_an_omitted_role_column(tmp_path):
    parts = _parts()
    body = parts["view"]["body"]
    body["grouping"]["presentation"] = "header"
    body["hierarchyColumn"] = "Phase"

    with pytest.raises(RenderFailed) as error:
        sr.render(tmp_path, _source(roles=False), presentation=parts)

    assert error.value.code == "E_VIEW_HIERARCHY_COLUMN_UNKNOWN"


def _typed_view(parts):
    return parse_contract(ClosureIdentity("view", parts["view"]["id"], "draft", "sha256:" + "a" * 64),
                          parts["view"]).view


@pytest.mark.parametrize("declared", [False, True])
def test_primary_color_icon_and_lane_key_sources_share_role_availability(declared):
    parts = _parts("lanes")
    body = parts["view"]["body"]
    body["rows"]["laneKeys"] = {"fieldRole": "responsible", "byObject": {"a": "one"}}
    body["colorEncoding"] = {"scale": "owner", "target": "planned", "source": {"fieldRole": "responsible"},
                             "domain": "firstAppearance"}
    body["visuals"] = [{"target": {"kind": "plot-label", "id": "a"},
                        "encoding": {"fieldRole": "responsible", "domain": {"engineering": "material:flag-outline-rounded"}}}]
    view = _typed_view(parts)

    resolved, info = resolve_field_role_view(view, _source(roles=declared))

    assert resolved.rows.lane_keys.by_object == {"a": "one"}
    if declared:
        assert resolved.grouping.field == "owner"
        assert resolved.color_encoding["source"] == {"field": "owner"}
        assert resolved.visuals[0].encoding["field"] == "owner"
        assert "fieldRole" not in resolved.visuals[0].encoding
        assert resolved.rows.lane_keys.field_role == "responsible"
        assert not info
    else:
        assert resolved.grouping.by == "objectType"
        assert resolved.color_encoding is None and resolved.visuals == ()
        assert resolved.rows.lane_keys.field_role is None
        finding = next(item for item in info if item.role == "responsible")
        assert finding.count == 4  # grouping, lane key, color, icon; not the number of items


def test_snapshot_role_values_use_the_snapshot_projects_own_mapping():
    primary = _source()
    snapshot = deepcopy(primary)
    snapshot["fieldRoles"]["phase"] = "historical_stage"
    for obj in snapshot["objects"].values():
        obj["fields"]["historical_stage"] = "Historical " + obj["fields"].pop("stage")
    parts = _parts()
    parts["view"]["body"]["comparison"].update(baseline="snapshot", baselineMarks="ghost")
    placements = {key: {"start": date(2026, 2, 1), "end": date(2026, 2, 20)} for key in primary["objects"]}

    projection = build_review_projection(primary, placements, _typed_view(parts), None,
                                        snapshot_project=snapshot, snapshot_placements=placements)

    primary_item = next(item for item in projection.rows[0].items if item.source_kind == "combined")
    snapshot_item = next(item for item in projection.rows[0].items if item.source_kind == "snapshot")
    assert table_value(primary_item, primary, {"fieldRole": "phase"}) == "Design"
    assert table_value(snapshot_item, primary, {"fieldRole": "phase"}) == "Historical Design"
    assert "stage" not in snapshot_item.fields
    assert snapshot_item.field_bindings != primary_item.field_bindings


def test_role_column_inherits_the_existing_field_column_style():
    parts = _parts()
    phase = parts["view"]["body"]["tableColumns"][1]
    for key in ("width", "align", "headerOrientation"):
        del phase[key]

    effective = merge_view_defaults(parts["view"], {"columnStyles": {"field": {
        "width": "content", "align": "start", "headerOrientation": "horizontal", "textRole": "secondary"}}})

    assert effective["body"]["tableColumns"][1] == {
        **phase, "width": "content", "align": "start", "headerOrientation": "horizontal", "textRole": "secondary"}


def test_none_fallback_disables_grouping_without_guessing_an_owner_field():
    parts = _parts()
    parts["view"]["body"]["grouping"]["fallback"] = "none"

    resolved, info = resolve_field_role_view(_typed_view(parts), _source(roles=False))

    assert resolved.grouping.by == "none" and resolved.grouping.field is None
    assert next(item for item in info if item.role == "responsible").count == 1


def test_role_color_and_icon_render_like_the_equivalent_explicit_field_sources(tmp_path):
    source, parts = _source(), _parts()
    parts["scheme"]["body"]["categories"].update({"role-a": "#1255AA", "role-b": "#AA5522"})
    parts["theme"]["body"]["colorScales"] = {"role-colors": {
        "slots": {"engineering": "role-a", "operations": "role-b"}}}
    body = parts["view"]["body"]
    body["colorEncoding"] = {"scale": "role-colors", "target": "planned", "source": {"fieldRole": "responsible"},
                             "domain": ["engineering", "operations"]}
    body["visuals"] = [{"target": {"kind": "plot-label", "id": "a"},
                        "encoding": {"fieldRole": "responsible", "domain": {"engineering": "material:flag-outline-rounded"}}}]
    control = deepcopy(parts)
    control["view"]["body"]["colorEncoding"]["source"] = {"field": "owner"}
    control["view"]["body"]["visuals"][0]["encoding"] = {
        "field": "owner", "domain": {"engineering": "material:flag-outline-rounded"}}
    catalog = Path(__file__).resolve().parents[2] / "src/chrona/resources/icons/material-symbols-outline-rounded-v2026-09-22.yaml"
    for name in ("role", "direct"):
        (tmp_path / name).mkdir()

    rendered = sr.render(tmp_path / "role", source, presentation=parts, icon_catalogs=(catalog,),
                         visual_profile="chrona-output/visual/v0.7-svg")
    direct = sr.render(tmp_path / "direct", source, presentation=control, icon_catalogs=(catalog,),
                       visual_profile="chrona-output/visual/v0.7-svg")

    assert rendered.artifact.content == direct.artifact.content
    assert any(item.kind == "Icon" for item in rendered.surface.primitives)
    planned_fills = {item.paint.fill for item in rendered.surface.primitives
                     if item.purpose == "planned" and item.paint is not None}
    assert {"#1255AA", "#AA5522"} <= planned_fills


def test_role_lane_key_combines_two_items_like_the_equivalent_explicit_field_key(tmp_path):
    source, parts = _source(), _parts("lanes")
    source["objects"]["b"]["fields"]["owner"] = "engineering"
    source["objects"]["b"]["schedule"].update(start="2026-02-15", end="2026-02-25")
    rows = parts["view"]["body"]["rows"]
    rows["laneKeys"] = {"fieldRole": "responsible"}
    rows["laneTable"].update(label="lane", count=True)
    control = deepcopy(parts)
    control["view"]["body"]["rows"]["laneKeys"] = {"field": "owner"}
    for name in ("role", "direct"):
        (tmp_path / name).mkdir()

    rendered = sr.render(tmp_path / "role", source, presentation=parts)
    direct = sr.render(tmp_path / "direct", source, presentation=control)

    assert rendered.artifact.content == direct.artifact.content
    assert any(item.table_column_id == "Items" and item.text == "2" for item in rendered.surface.primitives)
