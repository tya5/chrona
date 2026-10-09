from hashlib import sha256
from types import SimpleNamespace

import jsonschema
import pytest

from chrona.presentation.contracts import ClosureIdentity, SchemaContractError, parse_contract, validate_icon_catalog_entry
from chrona.presentation.contracts.resources import UnsupportedResourceVersionError, _compact_commands
from chrona.presentation.model.closure import ClosureError, _selected_catalog_entries
from chrona.resources import schema_document, validator_for_schema


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


def _catalog_v05():
    return {
        "version": "chrona/icon-catalog/v0.5", "kind": "icon-catalog", "id": "theme-assets",
        "body": {
            "set": "starter", "aliases": [],
            "provenance": {"sourceKind": "theme-asset-source", "sourceContentIdentity": "sha256:" + "b" * 64,
                           "license": {"spdx": "CC0-1.0", "notice": "CC0 notice"}},
            "icons": {}, "entryAliases": {},
            "glyphs": {"pin": {"viewport": {"inlineSize": 24, "blockSize": 24},
                                "parts": [{"paint": "fill", "data": "M 12 0 L 24 12 Q 12 24 0 12 Z"}]}},
            "patterns": {"dots": {"tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
                                   "densityBasisPoints": 1250,
                                   "primitives": [{"kind": "circle", "cx": 2, "cy": 2, "radius": 1}] }},
        },
    }


def test_icon_catalog_contract_keeps_set_name_and_closed_raster_source():
    value = _catalog()
    contract = parse_contract(ClosureIdentity("icon-catalog", "acme-icons", "r1", "sha256:" + sha256(b"x").hexdigest()), value)
    assert contract.set_name == "acme"
    assert contract.entry_names == ("risk",)
    validate_icon_catalog_entry(contract, "risk")
    with pytest.raises(ValueError, match="E_ICON_CATALOG_SCHEMA") as error:
        validate_icon_catalog_entry(contract, "poster")
    assert "catalog='acme-icons', icon='poster'" in error.value.detail
    assert "expected selected canonical entry" in error.value.detail


def test_icon_catalog_v05_accepts_glyph_and_pattern_only_catalogues():
    value = _catalog_v05()
    contract = parse_contract(ClosureIdentity("icon-catalog", "theme-assets", "r1", "sha256:" + "c" * 64), value)
    assert contract.version == "chrona/icon-catalog/v0.5"
    assert contract.entry_names == ()
    assert tuple(contract.raw_glyphs) == ("pin",)
    assert tuple(contract.raw_patterns) == ("dots",)


@pytest.mark.parametrize("mutate", [
    lambda value: value["body"]["patterns"]["dots"].update(densityBasisPoints=0),
    lambda value: value["body"]["patterns"]["dots"]["primitives"].append(
        {"kind": "arc", "cx": 1, "cy": 1, "radius": 1, "startAngle": 0, "endAngle": 90, "strokeWidth": 1}),
    lambda value: value["body"]["glyphs"]["pin"].update(parts=[{"paint": "fill", "data": "M 0 0 Z"}] * 33),
])
def test_icon_catalog_v05_rejects_invalid_density_raw_arc_and_part_limit(mutate):
    value = _catalog_v05()
    mutate(value)
    with pytest.raises(SchemaContractError):
        parse_contract(ClosureIdentity("icon-catalog", "theme-assets", "r1", "sha256:" + "c" * 64), value)


def test_retired_asset_catalog_v04_is_not_reinterpreted():
    value = _catalog_v05()
    value["version"] = "chrona/icon-catalog/v0.4"
    with pytest.raises(UnsupportedResourceVersionError) as error:
        parse_contract(ClosureIdentity("icon-catalog", "theme-assets", "r1", "sha256:" + "c" * 64), value)
    assert error.value.diagnostic_id == "E_RESOURCE_VERSION_UNSUPPORTED"
    assert error.value.source_ref == "/version"
    assert error.value.supported_versions == ("chrona/icon-catalog/v0.3", "chrona/icon-catalog/v0.5")


def test_theme_asset_source_schema_accepts_one_kind_and_requires_declared_density():
    schema = schema_document("theme-asset-source-v0.2.schema.yaml")
    source = {
        "version": "chrona/theme-asset-source/v0.2", "kind": "theme-asset-source", "id": "local-assets",
        "body": {"set": "local", "aliases": [], "license": {"spdx": "MIT", "notice": "MIT notice"},
                 "glyphs": {}, "patterns": {"hatch": {
                     "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0, "densityBasisPoints": 1250,
                     "primitives": [{"kind": "rect", "x": 0, "y": 0, "inlineSize": 8, "blockSize": 1}],
                 }}},
    }
    validator_for_schema(schema).validate(source)
    del source["body"]["patterns"]["hatch"]["densityBasisPoints"]
    with pytest.raises(jsonschema.ValidationError):
        validator_for_schema(schema).validate(source)


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
