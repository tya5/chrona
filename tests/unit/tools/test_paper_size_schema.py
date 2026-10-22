from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from chrona.presentation.layout.paper_size import PAGE_SIZE_NAMES
from chrona.resources import schema_document, schema_validator
from tools.schema_inventory import definition_digest, load_inventory, validate_frozen_definitions


ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = ROOT / "schemas"
PROFILE = "layout-profile-v0.10.schema.yaml"
VOCABULARY = "vocabulary-v0.2.schema.yaml"


def test_layout_profile_page_size_is_optional_and_uses_shared_enum():
    schema = schema_document(PROFILE)
    page_size = schema["properties"]["pageSize"]
    assert page_size["$ref"] == "urn:chrona:vocabulary-v0.2#/$defs/pageSize"
    assert "enum" not in page_size

    profile = yaml.safe_load((ROOT / "tests/fixtures/layout-profiles/print-portrait.yaml").read_text())
    validator = schema_validator(PROFILE)
    assert validator.is_valid(profile), list(validator.iter_errors(profile))
    for name in PAGE_SIZE_NAMES:
        profile["pageSize"] = name
        assert validator.is_valid(profile), (name, list(validator.iter_errors(profile)))


@pytest.mark.parametrize("page_size", ["a4", "letter-portrait-extra", "poster-portrait", ""])
def test_layout_profile_rejects_unregistered_page_size(page_size):
    profile = yaml.safe_load((ROOT / "tests/fixtures/layout-profiles/print-portrait.yaml").read_text())
    profile["pageSize"] = page_size
    validator = schema_validator(PROFILE)
    assert not validator.is_valid(profile)


def test_page_size_schema_enum_matches_the_single_runtime_registry():
    definition = schema_document(VOCABULARY)["$defs"]["pageSize"]
    assert tuple(definition["enum"]) == PAGE_SIZE_NAMES


def test_vocabulary_inventory_freezes_the_new_page_size_definition():
    entries = load_inventory(SCHEMAS / "schema-inventory-v0.1.yaml")
    entry = next(item for item in entries if item["file"] == VOCABULARY)
    assert entry["frozenDefs"]["pageSize"] == definition_digest(
        schema_document(VOCABULARY)["$defs"]["pageSize"])
    validate_frozen_definitions(SCHEMAS, entries)
