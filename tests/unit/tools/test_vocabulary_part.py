"""The `vocabulary` schema part (I662-S2): registered and frozen, no inline copy of a shared vocabulary, subsets, and code twins."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterator

from jsonschema import Draft202012Validator
from referencing import Resource
import pytest
import yaml

from chrona.presentation.scene import visual_capabilities
from chrona.resources import SCHEMA_PARTS, schema_document, schema_registry, validator_for_schema
from tools.schema_inventory import definition_digest, load_inventory, validate_frozen_definitions, validate_inventory


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
SCHEMAS = ROOT / "schemas"
VOCABULARY = "vocabulary-v0.1.schema.yaml"
VOCABULARY_ID = "urn:chrona:vocabulary-v0.1"
ENTRIES = load_inventory(SCHEMAS / "schema-inventory-v0.1.yaml")
LIVE = tuple(entry["file"] for entry in ENTRIES if entry["state"] == "live")
PARTS = frozenset(SCHEMA_PARTS)


def _schema(name: str) -> dict[str, Any]:
    return yaml.safe_load((SCHEMAS / name).read_bytes())


def _defs() -> dict[str, Any]:
    return schema_document(VOCABULARY)["$defs"]


def _walk(node: Any, path: tuple[Any, ...] = ()) -> Iterator[tuple[tuple[Any, ...], Any]]:
    yield path, node
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _walk(value, path + (key,))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk(value, path + (index,))


def _pointer(path: tuple[Any, ...]) -> str:
    return "".join("/" + str(token).replace("~", "~0").replace("/", "~1") for token in path)


def _sites(name: str, definition: str) -> list[str]:
    target = f"{VOCABULARY_ID}#/$defs/{definition}"
    return [_pointer(path) for path, node in _walk(_schema(name)) if isinstance(node, dict) and node.get("$ref") == target]


def _site_validator(name: str, pointer: str) -> Draft202012Validator:
    schema = _schema(name)
    registry = schema_registry().with_resource(schema["$id"], Resource.from_contents(schema))
    return Draft202012Validator({"$ref": f"{schema['$id']}#{pointer}"}, registry=registry)


# --------------------------------------------------------------------------------------------
# Registration and freezing
# --------------------------------------------------------------------------------------------

def test_vocabulary_is_a_registered_live_part_with_frozen_digests():
    assert VOCABULARY in SCHEMA_PARTS
    entry = next(item for item in ENTRIES if item["file"] == VOCABULARY)
    assert entry["state"] == "live" and entry["kind"] == "schema-part-vocabulary"
    assert set(entry["frozenDefs"]) == set(_defs()), "every published definition of vocabulary-v0.1 is frozen"
    assert schema_document(VOCABULARY)["$id"] == VOCABULARY_ID
    assert {key for key in schema_document(VOCABULARY) if not key.startswith("$") and key not in {"title", "description"}} == set(), \
        "a part asserts nothing at its root"
    validate_frozen_definitions(SCHEMAS, ENTRIES)
    assert validate_inventory(SCHEMAS, SCHEMAS / "schema-inventory-v0.1.yaml", repo_root=ROOT)


def test_a_vocabulary_definition_is_an_untyped_enum_so_a_site_keeps_its_dereferenced_form():
    # A `type` here would add a keyword to every site that replaced an inline `enum`, and the S0 L1 fingerprint would differ.
    for name, definition in _defs().items():
        assert set(definition) - {"description", "examples"} == {"enum"}, name
        assert len(set(definition["enum"])) == len(definition["enum"]), name


# --------------------------------------------------------------------------------------------
# No live entry outside the parts spells out a vocabulary the part defines
# --------------------------------------------------------------------------------------------

# (file, pointer) of an `enum` that equals a definition of the part and is NOT the same concept, each with the reason.
DIFFERENT_CONCEPT: dict[tuple[str, str], str] = {}


def _enum_copies(name: str) -> set[tuple[str, str]]:
    enums = {json.dumps(definition["enum"]) for definition in _defs().values()}
    return {(name, _pointer(path)) for path, node in _walk(_schema(name))
            if isinstance(node, dict) and isinstance(node.get("enum"), list) and json.dumps(node["enum"]) in enums}


def test_no_live_entry_outside_the_parts_copies_a_shared_vocabulary():
    copies: set[tuple[str, str]] = set()
    for name in LIVE:
        if name not in PARTS:
            copies |= _enum_copies(name)
    assert copies == set(DIFFERENT_CONCEPT), sorted(copies ^ set(DIFFERENT_CONCEPT))


# --------------------------------------------------------------------------------------------
# visualProfile (S2a)
# --------------------------------------------------------------------------------------------

VISUAL_PROFILES = [
    "chrona-output/visual/v0.5-baseline", "chrona-output/visual/v0.6-svg", "chrona-output/visual/v0.6-png",
    "chrona-output/visual/v0.7-svg", "chrona-output/visual/v0.7-png",
]
VISUAL_PROFILE_SITES = {
    "render-context-v0.16.schema.yaml": "/properties/body/properties/target/properties/visualProfile",
    "presentation-preset-v0.1.schema.yaml": "/properties/body/properties/visualProfile/properties/preferred",
}


def test_visual_profile_enum_is_the_five_published_profiles_in_order():
    assert _defs()["visualProfile"]["enum"] == VISUAL_PROFILES


@pytest.mark.parametrize(("name", "pointer"), sorted(VISUAL_PROFILE_SITES.items()))
def test_each_visual_profile_site_references_the_definition_and_accepts_exactly_it(name, pointer):
    assert pointer in _sites(name, "visualProfile")
    validator = _site_validator(name, pointer)
    assert [value for value in VISUAL_PROFILES if not validator.is_valid(value)] == []
    for value in ("chrona-output/visual/v0.8-svg", "chrona-output/visual/v0.5-baseline ", "", None, 5):
        assert not validator.is_valid(value), value


def test_preset_library_references_the_visual_profile_for_its_preferred_profile():
    sites = _sites("preset-library-v0.2.schema.yaml", "visualProfile")
    assert len(sites) == 1 and sites[0].endswith("/properties/visualProfile/properties/preferred")


def test_visual_profile_code_twins_equal_the_schema_vocabulary():
    declared = set(_defs()["visualProfile"]["enum"])
    constants = {visual_capabilities.BASELINE_PROFILE, visual_capabilities.SVG_PROFILE, visual_capabilities.PNG_PROFILE,
                 visual_capabilities.SVG_ICON_PROFILE, visual_capabilities.PNG_ICON_PROFILE}
    assert constants == declared

    from chrona.app.cli import _add_draft_target_arguments
    command = argparse.ArgumentParser()
    _add_draft_target_arguments(command)
    choices = next(action.choices for action in command._actions if action.dest == "visual_profile")
    assert set(choices) == declared and len(choices) == len(declared)


def test_every_declared_visual_profile_resolves_for_a_target():
    # The profile is usable, not merely spelled: each one resolves for at least one target route.
    targets = ("svg", "png", "pdf", "typst", "tikz")
    for profile in _defs()["visualProfile"]["enum"]:
        resolved = []
        for target in targets:
            try:
                resolved.append(visual_capabilities.resolve_visual_profile(profile, target))
            except visual_capabilities.VisualCapabilityError:
                pass
        assert resolved, profile
