from hashlib import sha256

import pytest

from chrona.presentation.contracts import ClosureIdentity, ContractError, SchemaContractError, parse_contract


def _catalog(source: str = "assets/risk.png"):
    return {
        "version": "chrona/icon-catalog/v0.3", "kind": "icon-catalog", "id": "acme-icons",
        "body": {"set": "acme", "aliases": ["acme-ui"],
                 "provenance": {"sourceKind": "iconify-json", "sourcePrefix": "acme", "sourceContentIdentity": "sha256:" + "b" * 64, "license": {"spdx": "MIT", "notice": "MIT"}},
                 "entryAliases": {}, "icons": {"risk": {
            "kind": "raster", "source": {"address": source, "contentIdentity": "sha256:" + "a" * 64},
            "viewport": {"inlineSize": 24, "blockSize": 24}, "alternative": "Risk",
        }}},
    }


def test_icon_catalog_contract_keeps_set_name_and_closed_raster_source():
    value = _catalog()
    contract = parse_contract(ClosureIdentity("icon-catalog", "acme-icons", "r1", "sha256:" + sha256(b"x").hexdigest()), value)
    assert contract.set_name == "acme"
    assert contract.entries[0].name == "risk"
    assert contract.entries[0].source.address == "assets/risk.png"


def test_icon_catalog_decodes_only_canonical_compact_geometry():
    value = _catalog()
    value["body"]["icons"] = {"check": {"kind": "vector", "viewport": {"inlineSize": 24, "blockSize": 24},
                                           "alternative": "Check", "paths": [{"paint": "fill", "data": "M 0 0 L 24 24 Z"}]}}
    contract = parse_contract(ClosureIdentity("icon-catalog", "acme-icons", "r1", "sha256:" + "c" * 64), value)
    assert [command["kind"] for command in contract.entries[0].paths[0].commands] == ["move", "line", "close"]


@pytest.mark.parametrize("data", ("m 0 0", "M 0 0 C 1 2 3 4 5 6", "M 0 0 L 1e3 2", "L 0 0"))
def test_icon_catalog_rejects_noncanonical_compact_geometry(data):
    value = _catalog()
    value["body"]["icons"] = {"check": {"kind": "vector", "viewport": {"inlineSize": 24, "blockSize": 24},
                                           "alternative": "Check", "paths": [{"paint": "fill", "data": data}]}}
    with pytest.raises(ContractError, match="E_ICON_CATALOG_GEOMETRY"):
        parse_contract(ClosureIdentity("icon-catalog", "acme-icons", "r1", "sha256:" + "c" * 64), value)


@pytest.mark.parametrize("source", ("../risk.svg", "https://example.test/risk.svg", "/risk.svg"))
def test_icon_catalog_rejects_unsafe_asset_address(source):
    with pytest.raises(SchemaContractError):
        parse_contract(ClosureIdentity("icon-catalog", "acme-icons", "r1", "sha256:" + "a" * 64), _catalog(source))
