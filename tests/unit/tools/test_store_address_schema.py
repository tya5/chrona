"""The strict `storeAddress` definition and the `revision-store-resource-ref` v0.2 part (#710, row 1, slice S-A).

Every verdict here is decided from data and the JSON Schema validator, never from the host path
flavour, so the file behaves the same on every operating system.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
import pytest
import yaml

from chrona.core.store_address import StoreAddressError, check_store_address
from chrona.resources import SCHEMA_PARTS, schema_document, validator_for_schema
from tools.schema_inventory import load_inventory, validate_inventory


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
SCHEMAS = ROOT / "schemas"
COMMON_ID = "urn:chrona:common-v0.1"
PART_V1, PART_V2 = "revision-store-resource-ref-v0.1.schema.yaml", "revision-store-resource-ref-v0.2.schema.yaml"
ENTRIES = load_inventory(SCHEMAS / "schema-inventory-v0.1.yaml")


def _def(name: str) -> Draft202012Validator:
    return validator_for_schema({"$ref": f"{COMMON_ID}#/$defs/{name}"})


STORE_ADDRESS = _def("storeAddress")


def _guard_accepts(address: object) -> bool:
    try:
        check_store_address(address)
    except StoreAddressError:
        return False
    return True


# Owner row 1 and design D5: every input the strict definition refuses.  The second column is the
# verdict of the loose `relativeAddress` definition that `layout-profile` v0.9 and
# `revision-store-resource-ref` v0.1 use today (True = the predecessor accepted it, so the bump
# deliberately narrows it); an input the predecessor already refused is listed to prove it stays refused.
REJECTED_BY_STORE_ADDRESS: dict[str, tuple[str, bool]] = {
    "nul": ("a\x00b", True),
    "backslash": ("a\\b", True),
    "embedded-newline": ("a\nb", True),
    "trailing-newline": ("a\n", True),
    "leading-newline": ("\na", False),
    "dot-segment-leading": ("./a", False),
    "dot-segment-inner": ("a/./b", False),
    "empty-segment": ("a//b", True),
    "trailing-slash": ("a/", True),
    "windows-drive-absolute": ("C:/x", True),
    "windows-drive-relative": ("C:x", True),
    "unc": ("\\\\server\\share\\x", True),
    "colon-in-segment": ("a:b", True),
    "all-dot-segment": ("a/...", True),
    "all-dot-address": ("...", True),
    "dot-dot": ("..", False),
    "dot": (".", False),
    "traversal": ("../x", False),
    "inner-traversal": ("a/../b", False),
    "absolute": ("/x", False),
    "space": ("a b", True),
    "non-ascii": ("é", True),
    "delete-character": ("a\x7fb", True),
    "tab": ("a\tb", True),
    "empty": ("", False),
}
ACCEPTED_BY_STORE_ADDRESS = (
    "a", "a/b/c.yaml", "resources/project.yaml", "snapshots/baseline-2027-06.yaml", ".hidden", "a..b", "a./b", "a/..b",
    "A_b-c.0/d",
)
NOT_A_STRING = (None, 5, 1.5, True, [], {}, ["a"])


def test_store_address_is_a_frozen_definition_of_the_common_part():
    entry = next(item for item in ENTRIES if item["file"] == "common-v0.1.schema.yaml")
    assert "storeAddress" in entry["frozenDefs"]
    definition = schema_document("common-v0.1.schema.yaml")["$defs"]["storeAddress"]
    assert definition["type"] == "string"
    assert validate_inventory(SCHEMAS, SCHEMAS / "schema-inventory-v0.1.yaml", repo_root=ROOT)


@pytest.mark.parametrize(("label", "value"), [(label, item[0]) for label, item in REJECTED_BY_STORE_ADDRESS.items()])
def test_store_address_refuses_each_listed_input(label, value):
    assert not STORE_ADDRESS.is_valid(value), label


@pytest.mark.parametrize("value", ACCEPTED_BY_STORE_ADDRESS)
def test_store_address_accepts_a_legitimate_address(value):
    assert STORE_ADDRESS.is_valid(value)


@pytest.mark.parametrize("value", NOT_A_STRING)
def test_store_address_refuses_a_non_string(value):
    assert not STORE_ADDRESS.is_valid(value)


@pytest.mark.parametrize(("label", "value", "predecessor_accepted"),
                         [(label, *item) for label, item in REJECTED_BY_STORE_ADDRESS.items()])
def test_the_loose_predecessor_verdict_of_each_listed_input_is_recorded(label, value, predecessor_accepted):
    """Both results, so a reviewer sees which refusals are a narrowing (the predecessor accepted it)."""
    assert _def("relativeAddress").is_valid(value) is predecessor_accepted, label


def test_the_frozen_loose_definitions_keep_todays_laxness():
    """`relativeAddress*` stay in `common-v0.1` for the transitioning predecessors: they are not edited."""
    accepted = [value for value, was in REJECTED_BY_STORE_ADDRESS.values() if was]
    assert accepted, "the table must list narrowed inputs"
    assert all(_def("relativeAddress").is_valid(value) for value in accepted)


def test_every_committed_and_packaged_structured_address_matches_the_definition():
    """Owner row 4, now checked against the schema definition itself: only the named negative fixture is refused."""
    negative_fixtures = {"conformance/revision-store/invalid-address.yaml"}
    roots = ("examples", "conformance", "src/chrona/resources", "docs/examples", "packages")
    seen: list[tuple[str, str]] = []
    refused: list[tuple[str, str]] = []

    def visit(value: Any, where: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "address" and isinstance(item, str):
                    seen.append((where, item))
                    if not STORE_ADDRESS.is_valid(item):
                        refused.append((where, item))
                else:
                    visit(item, where)
        elif isinstance(value, list):
            for item in value:
                visit(item, where)

    for root in roots:
        for path in sorted((ROOT / root).rglob("*")):
            if path.suffix not in {".yaml", ".yml", ".json"} or not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            if "address" not in text:
                continue
            documents = [json.loads(text)] if path.suffix == ".json" else list(yaml.safe_load_all(text))
            for document in documents:
                visit(document, path.relative_to(ROOT).as_posix())
    assert len(seen) > 300, "the survey must actually find the committed addresses"
    assert {where for where, _ in refused} == negative_fixtures, refused
    assert all(_guard_accepts(address) for _, address in seen if (_, address) not in refused), "the code guard is never stricter than a survey address"


def test_the_schema_never_accepts_what_the_code_guard_refuses():
    """The definition is at least as strict as `check_store_address` on every short string over a hostile alphabet."""
    alphabet = ["a", "0", ".", "-", "_", "/", "\n", " ", ":", "\\", "\x00", "é"]
    weaker = [text for length in range(0, 5) for tuple_ in itertools.product(alphabet, repeat=length)
              if STORE_ADDRESS.is_valid(text := "".join(tuple_)) and not _guard_accepts(text)]
    assert weaker == []


def test_the_closed_character_set_is_the_whole_grammar():
    """One character outside `[A-Za-z0-9._-]` (or a separator in the wrong place) anywhere is refused."""
    for extra in (" ", "\u00e9", ":", "\\", "\x00", "\n", "/", "+", "@", "%", "~", "#"):
        assert not STORE_ADDRESS.is_valid(f"a{extra}"), extra
        assert not STORE_ADDRESS.is_valid(f"{extra}a"), extra
        assert STORE_ADDRESS.is_valid(f"a{extra}b") is (extra == "/"), extra


# --------------------------------------------------------------------------------------------
# revision-store-resource-ref v0.2
# --------------------------------------------------------------------------------------------

def _reference(address: Any) -> dict[str, Any]:
    return {"id": "project", "kind": "project", "store": {"provider": "local", "identity": "local"},
            "address": address, "revision": {"token": "main"}}


def _part(name: str) -> Draft202012Validator:
    return validator_for_schema(schema_document(name))


def test_v0_2_is_a_registered_live_part_beside_v0_1():
    assert PART_V1 in SCHEMA_PARTS and PART_V2 in SCHEMA_PARTS
    entries = {item["file"]: item for item in ENTRIES}
    assert entries[PART_V1]["state"] == entries[PART_V2]["state"] == "live"
    assert entries[PART_V1]["kind"] == entries[PART_V2]["kind"] == "revision-store-resource-reference"
    assert set(entries[PART_V2]["frozenDefs"]) == {"#"}
    assert schema_document(PART_V2)["$id"] == "urn:chrona:revision-store-resource-ref-v0.2"


def test_v0_2_differs_from_v0_1_only_in_identity_and_the_address_site():
    before, after = yaml.safe_load((SCHEMAS / PART_V1).read_bytes()), yaml.safe_load((SCHEMAS / PART_V2).read_bytes())
    for document in (before, after):
        for key in ("$id", "title", "description"):
            document.pop(key)
    address = after["properties"].pop("address")
    assert address["$ref"] == f"{COMMON_ID}#/$defs/storeAddress"
    assert set(address) == {"description", "examples", "$ref"}, "the site is the reference and its own annotations, nothing else"
    before["properties"].pop("address")
    assert before == after


@pytest.mark.parametrize(("label", "value"), [(label, item[0]) for label, item in REJECTED_BY_STORE_ADDRESS.items()])
def test_v0_2_refuses_each_listed_address_and_v0_1_keeps_its_verdict(label, value):
    v1_accepts = REJECTED_BY_STORE_ADDRESS[label][1]
    assert _part(PART_V1).is_valid(_reference(value)) is v1_accepts, label
    assert not _part(PART_V2).is_valid(_reference(value)), label


@pytest.mark.parametrize("value", ACCEPTED_BY_STORE_ADDRESS)
def test_v0_2_accepts_what_v0_1_accepts_for_a_legitimate_address(value):
    assert _part(PART_V1).is_valid(_reference(value))
    assert _part(PART_V2).is_valid(_reference(value))


def test_v0_2_keeps_every_other_v0_1_rule():
    document = _reference("a/b.yaml")
    for broken in ({"id": ""}, {"kind": ""}, {"store": {"provider": "ftp", "identity": "x"}}, {"revision": {"token": "a b"}},
                   {"contentIdentity": "sha256:abc"}, {"extra": 1}):
        assert not _part(PART_V1).is_valid({**document, **broken}), broken
        assert not _part(PART_V2).is_valid({**document, **broken}), broken
    assert _part(PART_V2).is_valid({**document, "contentIdentity": "sha256:" + "0" * 64, "projectId": "p"})
