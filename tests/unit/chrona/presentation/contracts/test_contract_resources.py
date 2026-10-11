from copy import deepcopy
from dataclasses import fields
from pathlib import Path

import pytest
import yaml

from chrona.presentation.contracts import (
    ClosureIdentity,
    ContractError,
    PresentationResourceSource,
    ThemeContract,
    collect_presentation_contracts,
    parse_contract,
)
from chrona.presentation.contracts.resources import (
    ActualSetContract, ColorSchemeContract, LayoutProfileContract, ProfilePackageContract,
    ProjectContract, RenderContextContract, ReviewDetailProfileContract, SchemaContractError, SnapshotRefContract,
    SummaryProfileContract, UnsupportedResourceVersionError, ViewContract, ViewHeading, ViewLaneLabel, ViewLaneTable, ViewRowMode, _SCHEMAS,
)
from tests.support import synthetic_review as sr


ROOT = Path(__file__).resolve().parents[5]


def _theme():
    return {
        "version": "chrona/theme/v0.15", "kind": "theme", "id": "theme",
        "body": {"values": {}, "roles": {}, "colorBindings": {"text.fill": "text"}},
    }


def test_contract_is_schema_accepted_then_detached_and_immutable():
    value = _theme()
    contract = parse_contract(ClosureIdentity("theme", "theme", "r", "sha256:" + "a" * 64), value)
    assert isinstance(contract, ThemeContract)
    value["body"]["roles"]["text"] = {"fontFamily": "late"}
    assert "text" not in contract.theme_input["body"]["roles"]
    with pytest.raises(TypeError):
        contract.theme_input["body"]["roles"]["text"] = {}


def test_contract_rejects_schema_invalid_mandatory_resource():
    value = _theme()
    value["body"]["colorBindings"] = {}
    with pytest.raises(SchemaContractError, match="E_RESOURCE_SCHEMA") as error:
        parse_contract(ClosureIdentity("theme", "theme", "r", "sha256:" + "a" * 64), value)
    assert error.value.violation is not None
    assert (error.value.violation.resource_kind, error.value.violation.resource_identity) == ("theme", "theme")


def test_stale_string_version_has_a_typed_resource_local_diagnostic():
    value = _theme()
    value["version"] = "chrona/theme/v0.10"

    with pytest.raises(ContractError) as error:
        parse_contract(ClosureIdentity("theme", "theme", "r", "sha256:" + "a" * 64), value)

    diagnostic = error.value
    assert isinstance(diagnostic, UnsupportedResourceVersionError)
    assert diagnostic.diagnostic_id == "E_RESOURCE_VERSION_UNSUPPORTED"
    assert diagnostic.resource_kind == "theme"
    assert diagnostic.resource_id == "theme"
    assert diagnostic.found_version == "chrona/theme/v0.10"
    assert diagnostic.supported_versions == ("chrona/theme/v0.15", "chrona/theme/v0.16")
    assert diagnostic.source_ref == "/version"


@pytest.mark.parametrize("version", (
    "chrona/theme/v0.11", "chrona/theme/v0.12", "chrona/theme/v0.13", "chrona/theme/v0.14",
))
def test_retired_theme_versions_are_unsupported(version):
    value = _theme()
    value["version"] = version
    with pytest.raises(UnsupportedResourceVersionError) as error:
        parse_contract(ClosureIdentity("theme", "theme", "r", "sha256:" + "a" * 64), value)
    assert error.value.found_version == version
    assert error.value.supported_versions == ("chrona/theme/v0.15", "chrona/theme/v0.16")


def test_first_party_themes_and_derived_bases_use_the_current_contracts():
    from chrona.presentation.model.theme_inheritance import resolve_draft_theme
    from chrona.resources import safe_load

    paths = sorted((ROOT / "examples").glob("*/themes/*.yaml"))
    paths.extend(sorted((ROOT / "src/chrona/resources/presets/bundles").glob("*/theme.yaml")))
    assert paths
    for path in paths:
        source = safe_load(path.read_bytes())
        assert source["version"] in {"chrona/theme/v0.15", "chrona/theme/v0.16"}, path
        resolved = resolve_draft_theme(path) if source["version"] == "chrona/theme/v0.16" else source
        parse_contract(ClosureIdentity("theme", resolved["id"], "r", "sha256:" + "a" * 64), resolved)
        assert all(not isinstance(token, dict) or token.get("type") != "edge"
                   for token in source.get("body", {}).get("values", {}).values()), path
        assert all(not isinstance(role, dict) or "edge" not in role
                   for role in source.get("body", {}).get("roles", {}).values()), path


@pytest.mark.parametrize("target", ("value", "role"))
def test_current_theme_contract_rejects_the_retired_edge_declaration(target):
    value = _theme()
    if target == "value":
        value["body"]["values"]["legacy-edge"] = {"type": "edge", "value": {"side": "start", "size": 4}}
    else:
        value["body"]["roles"]["annotation-kind-accent"] = {"edge": "legacy-edge"}
    with pytest.raises(SchemaContractError):
        parse_contract(ClosureIdentity("theme", "theme", "r", "sha256:" + "a" * 64), value)


@pytest.mark.parametrize("kind", sorted({kind for kind, _version in _SCHEMAS}))
def test_unsupported_version_diagnostic_derives_supported_versions_from_schema_registry(kind):
    supported = tuple(sorted(version for registered_kind, version in _SCHEMAS if registered_kind == kind))
    value = {"kind": kind, "id": f"{kind}-resource", "version": "chrona/unsupported/v999", "body": {}}

    with pytest.raises(ContractError) as error:
        parse_contract(
            ClosureIdentity(kind, value["id"], "r", "sha256:" + "a" * 64), value,
        )

    assert error.value.diagnostic_id == "E_RESOURCE_VERSION_UNSUPPORTED"
    assert isinstance(error.value, UnsupportedResourceVersionError)
    assert error.value.resource_kind == kind
    assert error.value.resource_id == value["id"]
    assert error.value.supported_versions == supported


@pytest.mark.parametrize("version", ("missing", None, 42, True))
def test_missing_or_nonstring_version_is_not_reported_as_unsupported_version(version):
    value = _theme()
    if version == "missing":
        value.pop("version")
    else:
        value["version"] = version

    with pytest.raises(ContractError) as error:
        parse_contract(ClosureIdentity("theme", "theme", "r", "sha256:" + "a" * 64), value)

    assert error.value.diagnostic_id == "E_CLOSURE_KIND"
    assert error.value.diagnostic_id != "E_RESOURCE_VERSION_UNSUPPORTED"


def test_presentation_collector_continues_after_unsupported_version_to_report_sibling_schema_errors():
    view = yaml.safe_load((ROOT / "examples/controller-z/views/executive.yaml").read_text(encoding="utf-8"))
    theme = _theme()
    theme["id"] = "stale-theme"
    theme["version"] = "chrona/theme/v0.10"
    view["body"]["surface"] = "table-timelinez"

    result = collect_presentation_contracts((_source("theme", theme), _source("view", view)))

    assert [(item.code, item.resource_kind, item.resource_identity, item.pointer) for item in result.diagnostics] == [
        ("E_RESOURCE_VERSION_UNSUPPORTED", "theme", "stale-theme", "/version"),
        ("E_RESOURCE_SCHEMA", "view", "controller-z-executive", "/body/surface"),
    ]
    assert result.diagnostics[0].phase == "version"
    assert "chrona/theme/v0.10" in result.diagnostics[0].message
    assert "chrona/theme/v0.15" in result.diagnostics[0].message
    assert result.contracts == ()


def _source(kind, value):
    return PresentationResourceSource(
        ClosureIdentity(kind, value["id"], "draft", "sha256:" + "a" * 64), value,
    )


def test_presentation_collector_reports_all_independent_resource_schema_errors_in_declaration_order():
    view = yaml.safe_load((ROOT / "examples/controller-z/views/executive.yaml").read_text(encoding="utf-8"))
    theme = yaml.safe_load((ROOT / "examples/controller-z/themes/executive-light.yaml").read_text(encoding="utf-8"))
    view["body"]["surface"] = "table-timelinez"
    view["body"]["tableColumns"][0]["missing"] = "em-dashz"
    theme["body"]["values"]["text-weight"]["type"] = "fontWeightz"

    result = collect_presentation_contracts((_source("view", view), _source("theme", theme)))

    assert [(item.code, item.resource_kind, item.resource_identity, item.pointer, item.phase) for item in result.diagnostics] == [
        ("E_RESOURCE_SCHEMA", "view", "controller-z-executive", "/body/surface", "schema"),
        ("E_RESOURCE_SCHEMA", "view", "controller-z-executive", "/body/tableColumns/0/missing", "schema"),
        ("E_RESOURCE_SCHEMA", "theme", "executive-light", "/body/values/text-weight/type", "schema"),
    ]
    assert result.contracts == ()


def test_presentation_collector_runs_contract_semantics_only_after_resource_schema_acceptance():
    view = deepcopy(yaml.safe_load((ROOT / "examples/halcyon-1/views/06-flight-readiness.yaml").read_text(encoding="utf-8")))
    view["body"].pop("hierarchyColumn")

    result = collect_presentation_contracts((_source("view", view),))

    assert [(item.code, item.phase, item.pointer) for item in result.diagnostics] == [
        ("E_VIEW_HIERARCHY_COLUMN_REQUIRED", "contract", "/"),
    ]
    assert result.contracts == ()


def _view_contract(value):
    return parse_contract(ClosureIdentity("view", value["id"], "r", "sha256:" + "a" * 64), value)


def test_v028_heading_accepts_a_kicker_template_and_checks_its_closed_placeholder_grammar():
    value = sr.bundle("control-room-dark")["view"]
    value["version"] = "chrona/view/v0.28"
    value["body"]["heading"] = {
        "kicker": "Episode {asOf} · {project}",
        "title": "{project} board",
        "subtitle": "Calendar {calendar}",
        "dateForm": "day-month-year",
    }

    contract = _view_contract(value)

    assert contract.view.heading == ViewHeading(
        "{project} board", "Calendar {calendar}", "day-month-year", "Episode {asOf} · {project}")

    value["body"]["heading"]["kicker"] = "Episode {unknown}"
    with pytest.raises(ContractError, match="E_VIEW_HEADING_TEMPLATE"):
        _view_contract(value)

    value["body"]["heading"]["kicker"] = "Episode {project"
    with pytest.raises(ContractError, match="E_VIEW_HEADING_TEMPLATE"):
        _view_contract(value)


@pytest.mark.parametrize("kicker", ("", None, 7, True, [], {}))
def test_v028_heading_rejects_an_empty_null_or_nonstring_kicker(kicker):
    value = sr.bundle("control-room-dark")["view"]
    value["version"] = "chrona/view/v0.28"
    value["body"]["heading"] = {"kicker": kicker}

    with pytest.raises(SchemaContractError, match="E_RESOURCE_SCHEMA"):
        _view_contract(value)


def test_v028_slot_heading_text_is_detached_immutable_optional_caption_mapping():
    value = sr.bundle("control-room-dark")["view"]
    value["version"] = "chrona/view/v0.28"
    value["body"]["slotHeadingText"] = {"notes-panel": "Flight notes"}

    contract = _view_contract(value)
    assert contract.view.slot_heading_text == {"notes-panel": "Flight notes"}
    value["body"]["slotHeadingText"]["notes-panel"] = "Changed late"
    assert contract.view.slot_heading_text["notes-panel"] == "Flight notes"
    with pytest.raises(TypeError):
        contract.view.slot_heading_text["notes-panel"] = "Changed"

    value["body"]["slotHeadingText"] = {}
    assert _view_contract(value).view.slot_heading_text == {}


@pytest.mark.parametrize("wrap", ("allow", "forbid", None))
@pytest.mark.parametrize("site", ("heading", "laneTable", "column"))
def test_view_text_wrap_is_typed_once_with_runtime_defaults(wrap, site):
    value = sr.bundle("control-room-dark")["view"]
    value["body"]["heading"] = {"title": "{project}"}
    value["body"]["rows"]["laneTable"] = {"label": "group", "count": True}
    if site == "column":
        value["body"]["rows"] = {"mode": "automatic"}
        value["body"]["tableColumns"] = [{"id": "Task", "source": "title",
            "missing": "em-dash", "align": "start", "width": "content",
            "headerOrientation": "horizontal"}]
    targets = (value["body"]["heading"],) if site == "heading" else (
        value["body"]["rows"]["laneTable"],) if site == "laneTable" else value["body"]["tableColumns"]
    for target in targets:
        target.pop("text", None)
        if wrap is not None:
            target["text"] = {"wrap": wrap}
    view = _view_contract(value).view
    expected = wrap or "forbid"
    typed = (view.heading,) if site == "heading" else (view.rows.lane_table,) if site == "laneTable" else view.table_columns
    assert all(item.text_wrap == expected for item in typed)


@pytest.mark.parametrize("site", ("heading", "laneTable", "column"))
@pytest.mark.parametrize("text", ({}, {"wrap": "auto"}, {"wrap": "allow", "extra": True},
                                  {"wrap": True}, None, "allow"))
def test_view_text_wrap_sites_share_the_closed_schema(site, text):
    value = sr.bundle("control-room-dark")["view"]
    value["body"]["heading"] = {"title": "{project}"}
    value["body"]["rows"]["laneTable"] = {"label": "group"}
    if site == "column":
        value["body"]["rows"] = {"mode": "automatic"}
        value["body"]["tableColumns"] = [{"id": "Task", "source": "title",
            "missing": "em-dash", "align": "start", "width": "content",
            "headerOrientation": "horizontal"}]
    target = (value["body"]["heading"] if site == "heading" else
              value["body"]["rows"]["laneTable"] if site == "laneTable" else
              value["body"]["tableColumns"][0])
    target["text"] = text
    with pytest.raises(SchemaContractError, match="E_RESOURCE_SCHEMA"):
        _view_contract(value)


@pytest.mark.parametrize("captions", ({"": "Notes"}, {"notes": ""}, {"notes": None}, {"notes": 7}, {"notes": "bad\ncaption"}))
def test_v028_slot_heading_text_schema_rejects_invalid_keys_or_caption_values(captions):
    value = sr.bundle("control-room-dark")["view"]
    value["version"] = "chrona/view/v0.28"
    value["body"]["slotHeadingText"] = captions

    with pytest.raises(SchemaContractError, match="E_RESOURCE_SCHEMA"):
        _view_contract(value)


def test_v16_table_intent_contract_rejects_ambiguous_hierarchy_column():
    automatic = yaml.safe_load((ROOT / "examples/halcyon-1/views/06-flight-readiness.yaml").read_text(encoding="utf-8"))
    automatic["body"].pop("hierarchyColumn")
    with pytest.raises(ContractError, match="E_VIEW_HIERARCHY_COLUMN_REQUIRED"):
        _view_contract(automatic)

    automatic = yaml.safe_load((ROOT / "examples/halcyon-1/views/06-flight-readiness.yaml").read_text(encoding="utf-8"))
    automatic["body"]["hierarchyColumn"] = "missing"
    with pytest.raises(ContractError, match="E_VIEW_HIERARCHY_COLUMN_UNKNOWN"):
        _view_contract(automatic)

    flat = yaml.safe_load((ROOT / "examples/aster-ssd/views/01-overview.yaml").read_text(encoding="utf-8"))
    flat["body"]["hierarchyColumn"] = flat["body"]["tableColumns"][0]["id"]
    with pytest.raises(ContractError, match="E_VIEW_HIERARCHY_COLUMN_UNEXPECTED"):
        _view_contract(flat)


def test_v16_table_intent_contract_rejects_duplicate_columns_and_keeps_explicit_nesting_typed():
    value = yaml.safe_load((ROOT / "examples/halcyon-1/views/06-flight-readiness.yaml").read_text(encoding="utf-8"))
    duplicate = dict(value["body"]["tableColumns"][0])
    duplicate["source"] = "id"
    value["body"]["tableColumns"].append(duplicate)
    with pytest.raises(ContractError, match="E_VIEW_TABLE_COLUMN_DUPLICATE"):
        _view_contract(value)

    explicit = yaml.safe_load((ROOT / "examples/aster-ssd/views/01-overview.yaml").read_text(encoding="utf-8"))
    body = explicit["body"]
    for name in ("selection", "grouping", "ordering"):
        body.pop(name)
    body["rows"] = {"mode": "explicit", "items": [
        {"id": "parent", "depth": 0, "items": [{"id": "primary", "source": {"kind": "primary", "object": "board"}}]},
        {"id": "child", "depth": 1, "parentRow": "parent", "items": [{"id": "actual", "source": {"kind": "actual", "object": "ftl"}}]},
    ]}
    body["hierarchyColumn"] = body["tableColumns"][0]["id"]
    contract = _view_contract(explicit)
    assert contract.view.hierarchy_column == "Work package / gate"
    assert contract.view.background_decoration == ("alternate", "none")


def test_boolean_comparison_columns_require_a_complete_typed_presence_presentation():
    value = yaml.safe_load((ROOT / "examples/halcyon-1/views/04-tvac-slip.yaml").read_text(encoding="utf-8"))
    column = {"id": "Obs", "source": {"comparisonFacet": "missingActual"},
              "format": {"kind": "presence", "whenTrue": "Missing", "whenFalse": "Recorded"},
              "missing": "em-dash", "align": "center", "width": "content",
              "headerOrientation": "horizontal"}
    value["body"]["tableColumns"].append(column)
    contract = _view_contract(value)
    assert contract.view.table_columns[-1].format.when_true == "Missing"
    column["format"] = "text"
    with pytest.raises(ContractError, match="E_VIEW_BOOLEAN_PRESENTATION"):
        _view_contract(value)


def test_v18_axis_tiers_have_one_role_and_unit_valid_label_forms():
    value = yaml.safe_load((ROOT / "examples/halcyon-1/views/01-mission-brief.yaml").read_text(encoding="utf-8"))
    assert isinstance(_view_contract(value), ViewContract)

    invalid_role = yaml.safe_load((ROOT / "examples/halcyon-1/views/01-mission-brief.yaml").read_text(encoding="utf-8"))
    invalid_role["body"]["axis"]["tiers"][0]["roles"] = ["band", "grid-major"]
    invalid_role["body"]["axis"]["tiers"][0].pop("role")
    with pytest.raises(SchemaContractError, match="E_RESOURCE_SCHEMA"):
        _view_contract(invalid_role)

    invalid_form = yaml.safe_load((ROOT / "examples/halcyon-1/views/01-mission-brief.yaml").read_text(encoding="utf-8"))
    invalid_form["body"]["axis"]["tiers"][2]["label"]["form"] = "year"
    with pytest.raises(SchemaContractError, match="E_RESOURCE_SCHEMA"):
        _view_contract(invalid_form)

    invalid_grid_label = yaml.safe_load((ROOT / "examples/halcyon-1/views/01-mission-brief.yaml").read_text(encoding="utf-8"))
    invalid_grid_label["body"]["axis"]["tiers"][1]["label"] = {"form": "year-quarter", "align": "center", "overflow": "visible-overflow"}
    with pytest.raises(SchemaContractError, match="E_RESOURCE_SCHEMA"):
        _view_contract(invalid_grid_label)


def test_v18_auto_axis_is_labels_only_and_declares_its_candidate_forms():
    value = yaml.safe_load((ROOT / "examples/halcyon-1/views/01-mission-brief.yaml").read_text(encoding="utf-8"))
    value["body"]["axis"]["tiers"] = [{
        "unit": "auto", "every": 1, "role": "labels",
        "label": {"forms": {"month": "short-month", "quarter": "year-quarter"}, "align": "start", "overflow": "thin-with-record", "orientation": "horizontal"},
    }]
    assert isinstance(_view_contract(value), ViewContract)

    invalid = yaml.safe_load((ROOT / "examples/halcyon-1/views/01-mission-brief.yaml").read_text(encoding="utf-8"))
    invalid["body"]["axis"]["tiers"] = [{"unit": "auto", "every": 1, "role": "grid-major"}]
    with pytest.raises(SchemaContractError, match="E_RESOURCE_SCHEMA"):
        _view_contract(invalid)


def test_v18_detaches_closed_orientation_intent_for_layout():
    value = yaml.safe_load((ROOT / "examples/halcyon-1/views/06-flight-readiness.yaml").read_text(encoding="utf-8"))
    value["body"]["tableColumns"][0]["headerOrientation"] = "rotate-cw"
    contract = _view_contract(value)
    assert contract.view.table_columns[0].header_orientation == "rotate-cw"


@pytest.mark.parametrize(
    ("kind", "path", "mutate"),
    (
        ("theme", "examples/halcyon-1/themes/briefing.yaml",
         lambda value: value["body"]["values"]["arrow"].update({"value": "circle"})),
        ("render-context", "examples/halcyon-1/contexts/01-mission-brief.yaml",
         lambda value: value["body"]["environment"].update({"locale": "en-GB"})),
        ("view", "examples/aster-ssd/views/01-overview.yaml",
         lambda value: value["body"].update({"annotations": [{"id": "note", "purpose": "note", "anchor": {"kind": "object", "id": "firmware", "endpoint": "body"}, "placement": {"side": "above", "alignment": "center"}, "text": "missing facet"}]})),
    ),
)
def test_declared_vocabulary_is_rejected_at_its_resource_boundary(kind, path, mutate):
    value = yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))
    mutate(value)

    with pytest.raises(SchemaContractError, match="E_RESOURCE_SCHEMA"):
        parse_contract(ClosureIdentity(kind, value["id"], "r", "sha256:" + "a" * 64), value)


@pytest.mark.parametrize(
    ("kind", "path", "mutate", "expected_pointer"),
    (
        ("view", "examples/aster-ssd/views/01-overview.yaml",
         lambda value: value["body"]["tableColumns"][0].update({"source": {"comparisonFacet": "invalid"}}),
         "/body/tableColumns/0/source"),
        ("theme", "examples/aster-ssd/themes/executive-light.yaml",
         lambda value: value["body"]["colorBindings"].update({"text.fill": "invalid"}),
         "/body/colorBindings/text.fill"),
        ("layout-profile", "examples/halcyon-1/layouts/briefing.yaml",
         lambda value: value["relationRouting"].update({"maxBends": "invalid"}),
         "/relationRouting/maxBends"),
    ),
)
def test_contract_schema_errors_report_the_nested_failing_pointer(kind, path, mutate, expected_pointer):
    value = yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))
    mutate(value)

    with pytest.raises(SchemaContractError) as error:
        parse_contract(ClosureIdentity(kind, value["id"], "r", "sha256:" + "a" * 64), value)

    assert error.value.kind == kind
    assert error.value.source_ref == expected_pointer
    if kind == "theme":
        assert "expected one permitted form" in str(error.value)


def test_summary_subtree_scope_is_limited_to_a_typed_object_planned_source():
    identity = ClosureIdentity("summary-profile", "summary", "r", "sha256:" + "a" * 64)
    value = {
        "version": "chrona/summary-profile/v0.1", "kind": "summary-profile", "id": "summary",
        "body": {"panels": [{"id": "completion", "metrics": {
            "planned": {"source": {"object": "programme", "facet": "planned"},
                        "scope": "subtree", "format": "date"},
        }}]},
    }
    assert isinstance(parse_contract(identity, value), SummaryProfileContract)
    value["body"]["panels"][0]["metrics"]["planned"]["source"] = "planned.nextPoint"
    with pytest.raises(ContractError, match="E_RESOURCE_SCHEMA"):
        parse_contract(identity, value)


def test_summary_scenario_source_is_closed_to_id_or_title():
    identity = ClosureIdentity("summary-profile", "summary", "r", "sha256:" + "a" * 64)
    value = {
        "version": "chrona/summary-profile/v0.1", "kind": "summary-profile", "id": "summary",
        "body": {"panels": [{"id": "scenario", "metrics": {
            "hypothesis": {"source": {"scenario": "title"}, "format": "text"},
        }}]},
    }
    assert isinstance(parse_contract(identity, value), SummaryProfileContract)
    value["body"]["panels"][0]["metrics"]["hypothesis"]["source"] = {"scenario": "unknown"}
    with pytest.raises(ContractError, match="E_RESOURCE_SCHEMA"):
        parse_contract(identity, value)


def test_summary_panel_arrangement_defaults_to_stack_and_accepts_inline():
    identity = ClosureIdentity("summary-profile", "summary", "r", "sha256:" + "a" * 64)
    value = {
        "version": "chrona/summary-profile/v0.1", "kind": "summary-profile", "id": "summary",
        "body": {"panels": [{"id": "countdown", "metrics": {"days": "count.selected"}}]},
    }

    contract = parse_contract(identity, value)
    assert contract.summary.panels[0].arrangement == "stack"

    value["body"]["panels"][0]["arrangement"] = "inline"
    contract = parse_contract(identity, value)
    assert contract.summary.panels[0].arrangement == "inline"

    value["body"]["panels"][0]["arrangement"] = "diagonal"
    with pytest.raises(SchemaContractError, match="E_RESOURCE_SCHEMA"):
        parse_contract(identity, value)


def test_resource_contracts_have_no_generic_document_or_body_escape_hatch():
    contracts = (
        ActualSetContract, ColorSchemeContract, LayoutProfileContract, ProfilePackageContract,
        ProjectContract, RenderContextContract, ReviewDetailProfileContract, SnapshotRefContract,
        SummaryProfileContract, ThemeContract, ViewContract,
    )
    assert all({field.name for field in fields(contract)}.isdisjoint({"body", "document"}) for contract in contracts)


def test_live_closed_resources_become_named_presentation_records():
    view = yaml.safe_load((ROOT / "examples/aster-ssd/views/01-overview.yaml").read_text(encoding="utf-8"))
    summary = yaml.safe_load((ROOT / "examples/halcyon-1/profiles/summary.yaml").read_text(encoding="utf-8"))
    view_contract = parse_contract(ClosureIdentity("view", view["id"], "r", "sha256:" + "a" * 64), view)
    summary_contract = parse_contract(ClosureIdentity("summary-profile", summary["id"], "r", "sha256:" + "a" * 64), summary)

    assert isinstance(view_contract, ViewContract)
    assert view_contract.view.rows.mode == "automatic"
    assert all(column.id and column.missing for column in view_contract.view.table_columns)
    assert isinstance(view_contract.view.visibility.labels, bool)
    assert isinstance(summary_contract, SummaryProfileContract)
    assert summary_contract.summary.panels[0].metrics


def test_v028_lane_contract_normalizes_typed_intent():
    value = yaml.safe_load((ROOT / "examples/halcyon-1/views/02-programme-board.yaml").read_text(encoding="utf-8"))
    body = value["body"]
    body.pop("tableColumns", None)
    body["rows"] = {"mode": "lanes", "laneTable": {"label": "group", "count": True}}
    body["visibility"]["labels"] = {
        "placement": "plot", "content": ["title", "finishDelta"],
        "side": "auto", "overflow": "suppress",
    }
    contract = parse_contract(
        ClosureIdentity("view", value["id"], "r", "sha256:" + "a" * 64), value,
    )
    assert isinstance(contract, ViewContract)
    assert contract.view.rows.mode is ViewRowMode.LANES
    assert contract.view.rows.lane_table == ViewLaneTable(ViewLaneLabel.GROUP, True)



def test_v028_lane_contract_parses_packing_defaults_and_explicit_keys():
    value = yaml.safe_load((ROOT / "examples/halcyon-1/views/02-programme-board.yaml").read_text(encoding="utf-8"))
    value["version"] = "chrona/view/v0.28"
    body = value["body"]
    body.pop("tableColumns", None)
    body["rows"] = {"mode": "lanes", "laneTable": {"label": "group"}}
    body["visibility"]["labels"] = {"placement": "plot"}
    identity = ClosureIdentity("view", value["id"], "r", "sha256:" + "a" * 64)
    contract = parse_contract(identity, value)
    assert contract.view.rows.packing == ("explicit", "attached")
    assert contract.view.rows.lane_keys is None

    body["rows"]["packing"] = ["explicit", "attached", "chain"]
    body["rows"]["laneKeys"] = {"field": "lane", "byObject": {"item-1": "alpha"}}
    contract = parse_contract(identity, value)
    assert contract.view.rows.packing == ("explicit", "attached", "chain")
    assert contract.view.rows.lane_keys.field == "lane"
    assert contract.view.rows.lane_keys.by_object == {"item-1": "alpha"}
    with pytest.raises(TypeError, match="immutable"):
        contract.view.rows.lane_keys.by_object["item-2"] = "beta"


@pytest.mark.parametrize("labels", [
    {"placement": "table", "content": ["title"]},
    {"placement": "plot", "content": ["finishDelta"]},
    {"placement": "plot", "overflow": "visible-overflow"},
    False,
])
def test_v028_lane_requires_plot_name_and_terminal_suppression(labels):
    value = yaml.safe_load((ROOT / "examples/halcyon-1/views/02-programme-board.yaml").read_text(encoding="utf-8"))
    value["version"] = "chrona/view/v0.28"
    body = value["body"]
    body.pop("tableColumns", None)
    body["rows"] = {"mode": "lanes", "laneTable": {"label": "group"}}
    body["visibility"]["labels"] = labels
    with pytest.raises(SchemaContractError, match="E_RESOURCE_SCHEMA"):
        parse_contract(ClosureIdentity("view", value["id"], "r", "sha256:" + "a" * 64), value)


def test_v028_lane_accepts_inside_declared_fallback_and_non_lane_still_requires_side_and_content():
    value = yaml.safe_load((ROOT / "examples/halcyon-1/views/02-programme-board.yaml").read_text(encoding="utf-8"))
    value["version"] = "chrona/view/v0.28"
    body = value["body"]
    body.pop("tableColumns", None)
    body["rows"] = {"mode": "lanes", "laneTable": {"label": "group"}}
    body["visibility"]["labels"] = {"placement": "plot", "content": ["title"], "side": "inside"}
    body["visibility"]["fallback"] = {"labels": ["inside", "end", "suppress"]}
    identity = ClosureIdentity("view", value["id"], "r", "sha256:" + "a" * 64)
    assert parse_contract(identity, value).view.visibility.labels["side"] == "inside"

    body["rows"] = {"mode": "automatic"}
    body["visibility"]["labels"] = {"placement": "plot"}
    with pytest.raises(SchemaContractError, match="E_RESOURCE_SCHEMA"):
        parse_contract(identity, value)


def test_downstream_presentation_code_has_no_raw_contract_input_escape_hatch():
    source_root = ROOT / "src/chrona"
    source = "\n".join(path.read_text(encoding="utf-8") for path in (
        source_root / "usecases/render_review.py",
        source_root / "presentation/model/projection.py",
        source_root / "presentation/review/v05_content.py",
    ))
    assert "projection_input" not in source
    assert "summary_input" not in source
    assert "detail_input" not in source


def _detail_of(value) -> str:
    with pytest.raises(ContractError) as raised:
        _view_contract(value)
    return raised.value.detail


def test_view_contract_errors_name_the_column_or_id_at_fault():
    """#829: every ambiguity the typed View refuses says which column, id or setting it found."""
    halcyon = ROOT / "examples/halcyon-1/views/06-flight-readiness.yaml"
    value = yaml.safe_load(halcyon.read_text(encoding="utf-8"))
    value["body"].pop("hierarchyColumn")
    assert "hierarchyColumn must name a table column" in _detail_of(value)

    value = yaml.safe_load(halcyon.read_text(encoding="utf-8"))
    value["body"]["hierarchyColumn"] = "missing"
    assert "'missing'" in _detail_of(value)

    flat = yaml.safe_load((ROOT / "examples/aster-ssd/views/01-overview.yaml").read_text(encoding="utf-8"))
    flat["body"]["hierarchyColumn"] = flat["body"]["tableColumns"][0]["id"]
    assert repr(flat["body"]["hierarchyColumn"]) in _detail_of(flat)

    value = yaml.safe_load(halcyon.read_text(encoding="utf-8"))
    duplicate = dict(value["body"]["tableColumns"][0])
    duplicate["source"] = "id"
    value["body"]["tableColumns"].append(duplicate)
    assert repr(duplicate["id"]) in _detail_of(value)

    value = yaml.safe_load((ROOT / "examples/halcyon-1/views/04-tvac-slip.yaml").read_text(encoding="utf-8"))
    value["body"]["tableColumns"].append({
        "id": "Obs", "source": {"comparisonFacet": "missingActual"}, "format": "text", "missing": "em-dash",
        "align": "center", "width": "content", "headerOrientation": "horizontal"})
    assert "'Obs'" in _detail_of(value)
