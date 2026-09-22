from dataclasses import fields
from pathlib import Path

import pytest
import yaml

from chrona.presentation.contracts import ClosureIdentity, ContractError, ThemeContract, parse_contract
from chrona.presentation.contracts.resources import (
    ActualSetContract, ColorSchemeContract, LayoutProfileContract, ProfilePackageContract,
    ProjectContract, RenderContextContract, ReviewDetailProfileContract, SnapshotRefContract,
    SummaryProfileContract, ViewContract,
)


ROOT = Path(__file__).resolve().parents[5]


def _theme():
    return {
        "version": "chrona/theme/v0.2", "kind": "theme", "id": "theme",
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
    with pytest.raises(ContractError, match="E_RESOURCE_SCHEMA"):
        parse_contract(ClosureIdentity("theme", "theme", "r", "sha256:" + "a" * 64), value)


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
    view = yaml.safe_load((ROOT / "examples/aster-ssd/views/01-overview.yaml").read_text())
    summary = yaml.safe_load((ROOT / "examples/halcyon-1/profiles/summary.yaml").read_text())
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
    source = "\n".join(path.read_text() for path in (
        source_root / "usecases/render_review.py",
        source_root / "presentation/model/projection.py",
        source_root / "presentation/review/v05_content.py",
    ))
    assert "projection_input" not in source
    assert "summary_input" not in source
    assert "detail_input" not in source
