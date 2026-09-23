from hashlib import sha256

import pytest

from chrona.presentation.contracts import ClosureIdentity, SchemaContractError, parse_contract


def _catalog(source: str = "assets/risk.svg"):
    return {
        "version": "chrona/icon-catalog/v0.1", "kind": "icon-catalog", "id": "acme-icons",
        "body": {"icons": {"acme.risk": {
            "kind": "vector", "source": {"address": source, "contentIdentity": "sha256:" + "a" * 64},
            "viewport": {"inlineSize": 24, "blockSize": 24}, "alternative": "Risk",
        }}},
    }


def test_icon_catalog_contract_keeps_namespaced_identity_and_closed_source():
    value = _catalog()
    contract = parse_contract(ClosureIdentity("icon-catalog", "acme-icons", "r1", "sha256:" + sha256(b"x").hexdigest()), value)
    assert contract.entries[0].id == "acme.risk"
    assert contract.entries[0].source.address == "assets/risk.svg"


@pytest.mark.parametrize("source", ("../risk.svg", "https://example.test/risk.svg", "/risk.svg"))
def test_icon_catalog_rejects_unsafe_asset_address(source):
    with pytest.raises(SchemaContractError):
        parse_contract(ClosureIdentity("icon-catalog", "acme-icons", "r1", "sha256:" + "a" * 64), _catalog(source))
