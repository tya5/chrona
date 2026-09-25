from dataclasses import fields
from pathlib import Path

import pytest
import yaml

from chrona.presentation.contracts import ClosureIdentity, ContractError, ThemeContract, parse_contract
from chrona.presentation.contracts.resources import (
    ActualSetContract, ColorSchemeContract, LayoutProfileContract, ProfilePackageContract,
    ProjectContract, RenderContextContract, ReviewDetailProfileContract, SchemaContractError, SnapshotRefContract,
    SummaryProfileContract, ViewContract,
)


ROOT = Path(__file__).resolve().parents[5]


def _theme():
    return {
        "version": "chrona/theme/v0.10", "kind": "theme", "id": "theme",
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


def _view_contract(value):
    return parse_contract(ClosureIdentity("view", value["id"], "r", "sha256:" + "a" * 64), value)


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
    assert contract.view.row_decoration == "alternate-rows"


def test_v17_axis_tiers_have_one_role_and_unit_valid_label_forms():
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
    invalid_grid_label["body"]["axis"]["tiers"][1]["label"] = {"form": "year-quarter", "align": "center", "overflow": "diagnose"}
    with pytest.raises(SchemaContractError, match="E_RESOURCE_SCHEMA"):
        _view_contract(invalid_grid_label)


def test_v17_auto_axis_is_labels_only_and_declares_its_candidate_forms():
    value = yaml.safe_load((ROOT / "examples/halcyon-1/views/01-mission-brief.yaml").read_text(encoding="utf-8"))
    value["body"]["axis"]["tiers"] = [{
        "unit": "auto", "every": 1, "role": "labels",
        "label": {"forms": {"month": "short-month", "quarter": "year-quarter"}, "align": "start", "overflow": "thin-with-record"},
    }]
    assert isinstance(_view_contract(value), ViewContract)

    invalid = yaml.safe_load((ROOT / "examples/halcyon-1/views/01-mission-brief.yaml").read_text(encoding="utf-8"))
    invalid["body"]["axis"]["tiers"] = [{"unit": "auto", "every": 1, "role": "grid-major"}]
    with pytest.raises(SchemaContractError, match="E_RESOURCE_SCHEMA"):
        _view_contract(invalid)


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
