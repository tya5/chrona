from dataclasses import fields

import pytest

from chrona.presentation.contracts import ClosureIdentity, ContractError, ThemeContract, parse_contract
from chrona.presentation.contracts.resources import (
    ActualSetContract, ColorSchemeContract, LayoutProfileContract, ProfilePackageContract,
    ProjectContract, RenderContextContract, ReviewDetailProfileContract, SnapshotRefContract,
    SummaryProfileContract, ViewContract,
)


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


def test_resource_contracts_have_no_generic_document_or_body_escape_hatch():
    contracts = (
        ActualSetContract, ColorSchemeContract, LayoutProfileContract, ProfilePackageContract,
        ProjectContract, RenderContextContract, ReviewDetailProfileContract, SnapshotRefContract,
        SummaryProfileContract, ThemeContract, ViewContract,
    )
    assert all({field.name for field in fields(contract)}.isdisjoint({"body", "document"}) for contract in contracts)
