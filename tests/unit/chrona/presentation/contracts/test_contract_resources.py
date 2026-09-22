import pytest

from chrona.presentation.contracts import ClosureIdentity, ContractError, ThemeContract, parse_contract


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
    assert "text" not in contract.body["roles"]
    with pytest.raises(TypeError):
        contract.body["roles"]["text"] = {}


def test_contract_rejects_schema_invalid_mandatory_resource():
    value = _theme()
    value["body"]["colorBindings"] = {}
    with pytest.raises(ContractError, match="E_RESOURCE_SCHEMA"):
        parse_contract(ClosureIdentity("theme", "theme", "r", "sha256:" + "a" * 64), value)
