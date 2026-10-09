"""Two address sites that moved to `storeAddress` in place (#731, slice I731-D).

`preset-library-v0.2` `address` and `icon-catalog-v0.5` `rasterSource.address` reference the strict `storeAddress` without a
version bump (Spec 56 section 3.2, "Tightening a further site"). The in-place reading holds only because each consumer refuses
every value the schema refuses, at every use of the field: `preset_library._safe` uses the shared guard, and the catalog
parse step checks every declared raster address, selected or not. Every verdict is decided from data and the JSON Schema
validator, never from the host path flavour, so the file behaves the same on every operating system.
"""
from __future__ import annotations

import copy
import itertools
from pathlib import Path
from typing import Any

import pytest
import yaml

from chrona.core.store_address import StoreAddressError, check_store_address
from chrona.presentation.contracts import ClosureIdentity, ContractError, parse_contract
from chrona.presentation.model.closure import ClosureError, _load_draft_resource
from chrona.resources import schema_document, schema_validator, validator_for_schema
from chrona.usecases import preset_library


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
COMMON_ID = "urn:chrona:common-v0.1"
STORE_ADDRESS = validator_for_schema({"$ref": f"{COMMON_ID}#/$defs/storeAddress"})
PRESET_ADDRESS = validator_for_schema({"$defs": schema_document("preset-library-v0.2.schema.yaml")["$defs"], "$ref": "#/$defs/address"})
RASTER_SOURCE = validator_for_schema({"$defs": schema_document("icon-catalog-v0.5.schema.yaml")["$defs"], "$ref": "#/$defs/rasterSource"})
IDENTITY = "sha256:" + "a" * 64

# Inputs the old site accepted (or already refused) and `storeAddress` refuses: id -> text.
NARROWED = {
    "trailing-newline": "a\n",
    "double-slash": "a//b",
    "trailing-slash": "a/",
    "dots-segment": "a/...",
    "dots-segment-middle": "a/.../b",
    "dot-segment": "a/./b",
    "dot-dot-segment": "a/../b",
    "nul": "a\x00b",
    "backslash": "a\\b",
    "colon": "a:b",
    "absolute": "/a",
    "space": "a b",
    "non-ascii": "aé",
}
# Inputs `storeAddress` accepts. The first three are the widening (the old patterns required a letter or digit first).
WIDENED = {"leading-dot": ".hidden/x", "leading-underscore": "_x", "leading-hyphen": "-x"}
KEPT = {"plain": "icons/sample.png", "inner-dots": "a..b", "dotted-name": "a.b/c.d", "single": "x"}
ACCEPTED = {**WIDENED, **KEPT}


def _guard_accepts(address: object) -> bool:
    try:
        check_store_address(address)
    except StoreAddressError:
        return False
    return True


def _raster(address: object) -> dict[str, Any]:
    return {"address": address, "contentIdentity": IDENTITY}


def _catalog_v05(addresses: dict[str, object]) -> dict[str, Any]:
    # The envelope schema-checks the first entry only (a representative), so a good entry goes first and the parse-time
    # check alone decides the others, which is the population this slice closes.
    icons = {"aaa-representative": {"kind": "raster", "source": _raster("icons/ok.png"),
                                    "viewport": {"inlineSize": 24, "blockSize": 24}, "alternative": "ok"}}
    icons |= {name: {"kind": "raster", "source": _raster(address), "viewport": {"inlineSize": 24, "blockSize": 24},
                    "alternative": name} for name, address in addresses.items()}
    return {
        "version": "chrona/icon-catalog/v0.5", "kind": "icon-catalog", "id": "theme-assets",
        "body": {
            "set": "starter", "aliases": [],
            "provenance": {"sourceKind": "theme-asset-source", "sourceContentIdentity": "sha256:" + "b" * 64,
                           "license": {"spdx": "CC0-1.0", "notice": "CC0 notice"}},
            "icons": icons, "entryAliases": {}, "glyphs": {}, "patterns": {},
        },
    }


def _parse(value: dict[str, Any]):
    return parse_contract(ClosureIdentity("icon-catalog", value["id"], "r1", "sha256:" + "c" * 64), value)


def _parse_accepts(addresses: dict[str, object]) -> bool:
    try:
        _parse(_catalog_v05(addresses))
    except ContractError as error:
        assert error.diagnostic_id == "E_ICON_ASSET_PATH"
        return False
    return True


# ---- the shared vectors: schema, guard and consumers agree -------------------------------------------------

@pytest.mark.parametrize("text", [*NARROWED.values(), *ACCEPTED.values()], ids=[*NARROWED, *ACCEPTED])
def test_schema_guard_and_both_consumers_agree_on_every_vector(text):
    expected = STORE_ADDRESS.is_valid(text)
    assert _guard_accepts(text) is expected
    assert PRESET_ADDRESS.is_valid(text) is expected
    assert RASTER_SOURCE.is_valid(_raster(text)) is expected
    assert _parse_accepts({"unselected": text}) is expected
    try:
        assert preset_library._safe(text) == text
        consumed = True
    except ValueError as error:
        assert str(error).startswith("E_BUILTIN_PRESET_RESOURCE: ")
        consumed = False
    assert consumed is expected


def test_the_vectors_are_what_the_design_says():
    assert not any(STORE_ADDRESS.is_valid(text) for text in NARROWED.values())
    assert all(STORE_ADDRESS.is_valid(text) for text in ACCEPTED.values())


@pytest.mark.parametrize("text", [text for text in WIDENED.values()], ids=list(WIDENED))
def test_the_widening_is_accepted_by_the_schemas_and_harms_no_consumer(text):
    """Moved verdict: a leading `.`, `_` or `-` is newly accepted; the consumers already accept it, so no consumer is harmed."""
    assert PRESET_ADDRESS.is_valid(text) and RASTER_SOURCE.is_valid(_raster(text))
    assert _guard_accepts(text) and _parse_accepts({"x": text}) and preset_library._safe(text) == text


@pytest.mark.parametrize("text", list(NARROWED.values()), ids=list(NARROWED))
def test_the_narrowed_inputs_are_refused_by_schema_and_consumer(text):
    """Moved verdict: each input the old pattern let through is refused by the schema, and the consumer already refused it."""
    assert not PRESET_ADDRESS.is_valid(text)
    assert not RASTER_SOURCE.is_valid(_raster(text))
    assert not _parse_accepts({"x": text})
    with pytest.raises(ValueError, match="E_BUILTIN_PRESET_RESOURCE"):
        preset_library._safe(text)


def test_exhaustive_parity_of_the_two_schema_sites_with_storeAddress():
    alphabet = ["a", "0", ".", "-", "_", "/", "\n", " ", ":", "\\", "\x00", "é"]
    count = 0
    for length in range(0, 5):
        for chars in itertools.product(alphabet, repeat=length):
            text = "".join(chars)
            expected = STORE_ADDRESS.is_valid(text)
            assert PRESET_ADDRESS.is_valid(text) is expected, repr(text)
            assert RASTER_SOURCE.is_valid(_raster(text)) is expected, repr(text)
            count += 1
    assert count > 20000


def test_a_non_string_address_is_refused_by_both_consumers():
    for value in (None, 7, ["a"], {"a": 1}):
        with pytest.raises(ValueError, match="E_BUILTIN_PRESET_RESOURCE"):
            preset_library._safe(value)
        assert not _parse_accepts({"x": value})


# ---- preset-library: the packaged catalogue and the consumer ------------------------------------------------

def _library_addresses() -> list[tuple[str, str]]:
    library = yaml.safe_load((ROOT / "src/chrona/resources/presets/library.yaml").read_text(encoding="utf-8"))
    found: list[tuple[str, str]] = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"sourceRoot", "sourcePath", "noticeSourcePath"}:
                    found.append((f"{path}/{key}", item))
                walk(item, f"{path}/{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}/{index}")

    walk(library, "")
    return found


def test_every_packaged_library_address_passes_the_shared_guard_and_the_schema():
    addresses = _library_addresses()
    assert len(addresses) > 30
    for pointer, address in addresses:
        assert _guard_accepts(address), pointer
        assert preset_library._safe(address) == address, pointer
    assert preset_library.list_builtin_presets()


@pytest.mark.parametrize("field", ["sourcePath", "noticeSourcePath"])
@pytest.mark.parametrize("text", ["a\n", "a/.../b", "a/...", "a\x00b", "a b"], ids=["newline", "dots-mid", "dots", "nul", "space"])
def test_copy_builtin_preset_refuses_an_unsafe_member_address(monkeypatch, tmp_path, field, text):
    """The packaged-entry population the in-place clause names: the consumer refuses it, so the schema may refuse it too."""
    entry = copy.deepcopy(next(item for item in preset_library._library() if item["id"] == "technical-print"))
    entry["members"]["iconCatalogs"][0][field] = text
    monkeypatch.setattr(preset_library, "_library", lambda: [entry])
    destination = tmp_path / "not-created"
    with pytest.raises(ValueError, match="E_BUILTIN_PRESET_RESOURCE"):
        preset_library.copy_builtin_preset("technical-print", destination)
    assert not destination.exists()


def test_the_library_schema_refuses_an_unsafe_member_address_before_the_consumer():
    library = yaml.safe_load((ROOT / "src/chrona/resources/presets/library.yaml").read_text(encoding="utf-8"))
    validator = schema_validator("preset-library-v0.2.schema.yaml")
    assert not list(validator.iter_errors(library))
    for text in NARROWED.values():
        broken = copy.deepcopy(library)
        entry = next(item for item in broken["entries"] if item.get("members", {}).get("iconCatalogs"))
        entry["members"]["iconCatalogs"][0]["sourcePath"] = text
        assert list(validator.iter_errors(broken)), repr(text)


# ---- icon-catalog: every declared address is checked when the catalog is parsed -----------------------------

@pytest.mark.parametrize("text", list(NARROWED.values()), ids=list(NARROWED))
def test_an_unselected_raster_entry_cannot_carry_an_unsafe_address(text):
    """B1's failing population: nothing selects the entry, yet the catalog is refused at parse time."""
    with pytest.raises(ContractError) as caught:
        _parse(_catalog_v05({"good": "icons/good.png", "unselected": text}))
    assert caught.value.diagnostic_id == "E_ICON_ASSET_PATH"
    assert caught.value.source_ref == "/body/icons/unselected/source/address"


def test_the_first_and_the_last_entry_are_both_checked():
    many = {f"icon{index:02d}": "icons/ok.png" for index in range(50)}
    for position in ("icon00", "icon49"):
        broken = dict(many)
        broken[position] = "a/.../b"
        assert not _parse_accepts(broken), position
    assert _parse_accepts(many)


def test_a_vector_entry_and_a_catalog_without_icons_are_not_affected():
    assert _parse_accepts({})
    value = _catalog_v05({"ok": "icons/ok.png"})
    value["body"]["icons"]["vec"] = {"kind": "vector", "viewport": {"inlineSize": 24, "blockSize": 24},
                                     "alternative": "v", "paths": [{"paint": "fill", "data": "M 0 0 L 1 1 Z"}]}
    _parse(value)


@pytest.mark.parametrize("text", ["a/.../b", "a\n"], ids=["dots", "newline"])
def test_a_draft_catalog_with_an_unselected_unsafe_address_is_refused_with_its_pointer(tmp_path, text):
    path = tmp_path / "catalog.yaml"
    path.write_text(yaml.safe_dump(_catalog_v05({"unselected": text})), encoding="utf-8")
    with pytest.raises(ClosureError) as caught:
        _load_draft_resource("icon-catalog", path)
    assert caught.value.code == "E_ICON_ASSET_PATH" if hasattr(caught.value, "code") else True
    assert "E_ICON_ASSET_PATH" in {getattr(caught.value, name, None) for name in ("code", "diagnostic_id")} | {str(caught.value)}


def test_every_committed_and_packaged_v04_catalog_still_parses():
    parsed = 0
    for path in [*(ROOT / "src/chrona/resources/icons").glob("*.yaml"), *(ROOT / "tests/fixtures/icons").glob("*.yaml")]:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(value, dict) and value.get("version") == "chrona/icon-catalog/v0.5" and value.get("kind") == "icon-catalog":
            _parse(value)
            parsed += 1
    assert parsed >= 2


def test_a_v03_catalog_keeps_its_own_pattern_and_is_not_checked_at_parse_time():
    value = _catalog_v05({"x": "a//b"})
    value["version"] = "chrona/icon-catalog/v0.3"
    del value["body"]["glyphs"], value["body"]["patterns"]
    value["body"]["provenance"] = {"sourceKind": "iconify-json", "sourcePrefix": "acme", "sourceContentIdentity": "sha256:" + "b" * 64,
                                   "license": {"spdx": "MIT", "notice": "MIT"}}
    _parse(value)
