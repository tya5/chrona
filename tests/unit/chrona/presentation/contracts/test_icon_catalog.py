from hashlib import sha256
from types import SimpleNamespace

import pytest

from chrona.presentation.contracts import ClosureIdentity, SchemaContractError, parse_contract, validate_icon_catalog_entry
from chrona.presentation.contracts.resources import _compact_commands
from chrona.presentation.model.closure import ClosureError, _selected_catalog_entries


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
    assert contract.entry_names == ("risk",)
    validate_icon_catalog_entry(contract, "risk")


def test_icon_catalog_decodes_only_canonical_compact_geometry():
    value = _catalog()
    value["body"]["icons"] = {"check": {"kind": "vector", "viewport": {"inlineSize": 24, "blockSize": 24},
                                           "alternative": "Check", "paths": [{"paint": "fill", "data": "M 0 0 L 24 24 Z"}]}}
    contract = parse_contract(ClosureIdentity("icon-catalog", "acme-icons", "r1", "sha256:" + "c" * 64), value)
    validate_icon_catalog_entry(contract, "check")
    assert _compact_commands(contract.raw_icons["check"]["paths"][0]["data"])


@pytest.mark.parametrize("data", ("m 0 0", "M 0 0 C 1 2 3 4 5 6", "M 0 0 L 1e3 2", "L 0 0"))
def test_icon_catalog_rejects_noncanonical_compact_geometry(data):
    value = _catalog()
    value["body"]["icons"] = {"check": {"kind": "vector", "viewport": {"inlineSize": 24, "blockSize": 24},
                                           "alternative": "Check", "paths": [{"paint": "fill", "data": data}]}}
    contract = parse_contract(ClosureIdentity("icon-catalog", "acme-icons", "r1", "sha256:" + "c" * 64), value)
    with pytest.raises(ValueError, match="E_ICON_CATALOG_GEOMETRY"):
        _compact_commands(contract.raw_icons["check"]["paths"][0]["data"])


@pytest.mark.parametrize("source", ("../risk.svg", "https://example.test/risk.svg", "/risk.svg"))
def test_icon_catalog_rejects_unsafe_asset_address(source):
    with pytest.raises(SchemaContractError):
        parse_contract(ClosureIdentity("icon-catalog", "acme-icons", "r1", "sha256:" + "a" * 64), _catalog(source))


def test_icon_catalog_rejects_an_alias_without_a_canonical_target():
    value = _catalog()
    value["body"]["entryAliases"] = {"warning": "absent"}

    with pytest.raises(SchemaContractError):
        parse_contract(ClosureIdentity("icon-catalog", "acme-icons", "r1", "sha256:" + "a" * 64), value)


def test_catalog_expands_only_selected_entries_and_reports_selected_schema_errors():
    value = _catalog()
    value["body"]["icons"] = {
        "good": {"kind": "vector", "viewport": {"inlineSize": 24, "blockSize": 24},
                 "alternative": "Good", "paths": [{"paint": "fill", "data": "M 0 0 L 24 24 Z"}]},
        "bad": {"kind": "vector"},
    }
    catalog = parse_contract(ClosureIdentity("icon-catalog", "acme-icons", "r1", "sha256:" + "c" * 64), value)
    selected_good = SimpleNamespace(view=SimpleNamespace(visuals=(SimpleNamespace(ref="acme:good", encoding=None),)))
    assert _selected_catalog_entries(catalog, selected_good)[0].name == "good"

    selected_bad = SimpleNamespace(view=SimpleNamespace(visuals=(SimpleNamespace(ref="acme:bad", encoding=None),)))
    with pytest.raises(ClosureError, match="E_ICON_CATALOG_SCHEMA") as error:
        _selected_catalog_entries(catalog, selected_bad)
    assert error.value.source_ref == "/body/icons/bad"
