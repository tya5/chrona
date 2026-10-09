"""The `common` schema part (I662-S1c): frozen digests, no inline copies, parity, and probes."""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Iterator

from jsonschema import Draft202012Validator
from referencing import Resource
import pytest
import yaml

from chrona.presentation.icons import importer, normalizer
from chrona.resources import SCHEMA_PARTS, schema_document, schema_registry, validator_for_schema
from tools.schema_inventory import (
    ROOT_DEFINITION, SchemaInventoryError, definition_digest, load_inventory, validate_consumers,
    validate_frozen_definitions, validate_inventory,
)


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
SCHEMAS = ROOT / "schemas"
COMMON = "common-v0.1.schema.yaml"
COMMON_ID = "urn:chrona:common-v0.1"
ENTRIES = load_inventory(SCHEMAS / "schema-inventory-v0.1.yaml")
LIVE = tuple(entry["file"] for entry in ENTRIES if entry["state"] == "live")


def _schema(name: str) -> dict[str, Any]:
    return yaml.safe_load((SCHEMAS / name).read_bytes())


def _defs() -> dict[str, Any]:
    return schema_document(COMMON)["$defs"]


def _def_validator(name: str) -> Draft202012Validator:
    return validator_for_schema({"$ref": f"{COMMON_ID}#/$defs/{name}"})


def _anchor_neutral(pattern: str) -> str:
    """Treat `$` and the newline-proof `(?![\\s\\S])` as one anchor, so a parity check survives the T3 decision."""
    return pattern.replace("(?![\\s\\S])", "$")


# --------------------------------------------------------------------------------------------
# Frozen digests
# --------------------------------------------------------------------------------------------

def test_common_is_a_registered_live_part_with_frozen_digests():
    assert COMMON in SCHEMA_PARTS
    entry = next(item for item in ENTRIES if item["file"] == COMMON)
    assert entry["state"] == "live" and entry["kind"] == "schema-part-common"
    assert set(entry["frozenDefs"]) == set(_defs()), "every published definition of common-v0.1 is frozen"
    assert schema_document(COMMON)["$id"] == COMMON_ID
    assert {key for key in schema_document(COMMON) if not key.startswith("$") and key not in {"title", "description"}} == set(), \
        "a part asserts nothing at its root"
    assert validate_inventory(SCHEMAS, SCHEMAS / "schema-inventory-v0.1.yaml", repo_root=ROOT)


def test_every_part_has_frozen_digests_that_match_its_definitions():
    validate_frozen_definitions(SCHEMAS, ENTRIES)
    for name in SCHEMA_PARTS:
        assert next(item for item in ENTRIES if item["file"] == name)["frozenDefs"]


def _copy_schemas(tmp_path: Path) -> Path:
    root = tmp_path / "schemas"
    root.mkdir()
    for name in SCHEMA_PARTS:
        (root / name).write_bytes((SCHEMAS / name).read_bytes())
    return root


def _entries_with_frozen(name: str, frozen: dict[str, str]) -> tuple[dict[str, Any], ...]:
    return tuple({**entry, "frozenDefs": frozen} if entry["file"] == name else entry for entry in ENTRIES)


def test_changing_a_frozen_definition_fails_the_gate(tmp_path):
    root = _copy_schemas(tmp_path)
    schema = _schema(COMMON)
    schema["$defs"]["slug"]["pattern"] = "^[a-z][a-z0-9_-]*$"
    (root / COMMON).write_text(yaml.safe_dump(schema))

    with pytest.raises(SchemaInventoryError, match="E_SCHEMA_PART_FROZEN:common-v0.1.schema.yaml:slug:changed"):
        validate_frozen_definitions(root, ENTRIES)


def test_removing_a_frozen_definition_fails_the_gate(tmp_path):
    root = _copy_schemas(tmp_path)
    schema = _schema(COMMON)
    del schema["$defs"]["license"]
    (root / COMMON).write_text(yaml.safe_dump(schema))

    with pytest.raises(SchemaInventoryError, match="E_SCHEMA_PART_FROZEN:common-v0.1.schema.yaml:license:removed"):
        validate_frozen_definitions(root, ENTRIES)


def test_wording_and_new_definitions_do_not_change_a_frozen_digest(tmp_path):
    root = _copy_schemas(tmp_path)
    schema = _schema(COMMON)
    schema["$defs"]["slug"]["description"] = "Reworded."
    schema["$defs"]["slug"]["examples"] = ["other"]
    schema["$defs"]["addedLater"] = {"type": "string"}
    (root / COMMON).write_text(yaml.safe_dump(schema))

    validate_frozen_definitions(root, ENTRIES)


def test_a_property_named_like_an_annotation_still_counts_in_the_digest():
    left = {"type": "object", "properties": {"description": {"type": "string"}}}
    right = {"type": "object", "properties": {"description": {"type": "integer"}}}
    assert definition_digest(left) != definition_digest(right)


def test_a_part_without_recorded_digests_fails_the_gate():
    stripped = tuple({key: value for key, value in entry.items() if key != "frozenDefs"} if entry["file"] == COMMON else entry
                     for entry in ENTRIES)
    with pytest.raises(SchemaInventoryError, match="E_SCHEMA_PART_UNFROZEN:common-v0.1.schema.yaml"):
        validate_frozen_definitions(SCHEMAS, stripped)


def test_frozen_defs_are_only_legal_on_a_part():
    with pytest.raises(SchemaInventoryError, match="E_SCHEMA_INVENTORY_FROZEN_SCOPE:project-v0.7.schema.yaml"):
        validate_frozen_definitions(
            SCHEMAS, _entries_with_frozen("project-v0.7.schema.yaml", {"date": definition_digest({})}),
        )


def test_the_whole_document_of_a_part_without_defs_is_frozen():
    entry = next(item for item in ENTRIES if item["file"] == "revision-store-resource-ref-v0.1.schema.yaml")
    assert set(entry["frozenDefs"]) == {ROOT_DEFINITION}


# --------------------------------------------------------------------------------------------
# Consumers of live entries
# --------------------------------------------------------------------------------------------

def test_every_consumer_of_a_live_entry_names_its_schema():
    validate_consumers(ROOT, SCHEMAS, ENTRIES)


def test_a_consumer_that_never_mentions_the_schema_fails_the_gate():
    broken = tuple({**entry, "consumers": ["src/chrona/schema_diagnostics.py"]} if entry["file"] == "project-v0.7.schema.yaml" else entry
                   for entry in ENTRIES)
    with pytest.raises(SchemaInventoryError, match="E_SCHEMA_INVENTORY_CONSUMER_STALE:project-v0.7.schema.yaml"):
        validate_consumers(ROOT, SCHEMAS, broken)
    missing = tuple({**entry, "consumers": ["src/chrona/absent.py"]} if entry["file"] == "project-v0.7.schema.yaml" else entry
                    for entry in ENTRIES)
    with pytest.raises(SchemaInventoryError, match="E_SCHEMA_INVENTORY_CONSUMER_MISSING:project-v0.7.schema.yaml"):
        validate_consumers(ROOT, SCHEMAS, missing)


# --------------------------------------------------------------------------------------------
# No inline copy of a shared pattern in a live entry (design D8)
# --------------------------------------------------------------------------------------------

# Live entries that keep a copy on purpose, each with the reason and the slice that removes it. Empty since I662 row 1 closed.
DEFERRED_FILES: dict[str, str] = {}
# (file, pointer) copies inside adopting schemas, each with the reason. Empty: the nullable `resultRevision` adopted `sha256IdentityOrNull`.
DEFERRED_COPIES: dict[tuple[str, str], str] = {}
PARTS_AND_DEFERRED = set(SCHEMA_PARTS) | set(DEFERRED_FILES)


def _pointer(path: tuple[Any, ...]) -> str:
    return "".join("/" + str(token).replace("~", "~0").replace("/", "~1") for token in path)


def _walk(node: Any, path: tuple[Any, ...] = ()) -> Iterator[tuple[tuple[Any, ...], Any]]:
    yield path, node
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _walk(value, path + (key,))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk(value, path + (index,))


def _copies(name: str) -> set[tuple[str, str]]:
    """Places in one schema that spell out a pattern or shape `common` already defines."""
    patterns = {definition["pattern"] for definition in _defs().values() if "pattern" in definition}
    structural = {definition_digest(_defs()["fractionalTrack"])}
    found: set[tuple[str, str]] = set()
    for path, node in _walk(_schema(name)):
        if not isinstance(node, dict):
            continue
        if isinstance(node.get("pattern"), str) and node["pattern"] in patterns:
            found.add((name, _pointer(path)))
        elif "required" in node and definition_digest(node) in structural:
            found.add((name, _pointer(path)))
    return found


def test_no_live_entry_outside_the_parts_copies_a_shared_definition():
    copies: set[tuple[str, str]] = set()
    for name in LIVE:
        if name not in PARTS_AND_DEFERRED:
            copies |= _copies(name)
    assert copies == set(DEFERRED_COPIES), sorted(copies ^ set(DEFERRED_COPIES))


def test_deferred_files_and_copies_still_hold_what_they_claim():
    for name in DEFERRED_FILES:
        assert name in LIVE
        assert _copies(name), f"{name} no longer copies a shared definition: drop it from DEFERRED_FILES"
    for name, pointer in DEFERRED_COPIES:
        assert (name, pointer) in _copies(name)


# --------------------------------------------------------------------------------------------
# Parity of `common` with the two frozen parts, and with Python twins
# --------------------------------------------------------------------------------------------

def _pattern_at(name: str, pointer: str) -> str:
    node: Any = _schema(name)
    for token in pointer.split("/")[1:]:
        node = node[token]
    return node["pattern"]


@pytest.mark.parametrize(("part", "pointer", "definition"), [
    ("presentation-resource-v0.1.schema.yaml", "/$defs/resourceRef/properties/path", "safeRelativePath"),
    ("presentation-resource-v0.1.schema.yaml", "/$defs/projectRef/properties/path", "safeRelativePath"),
    ("presentation-resource-v0.1.schema.yaml", "/$defs/resourceRef/properties/revision", "gitRevision"),
    ("presentation-resource-v0.1.schema.yaml", "/$defs/projectRef/properties/revision", "gitRevision"),
    ("presentation-resource-v0.1.schema.yaml", "/$defs/resourceRef/properties/contentIdentity", "sha256Identity"),
    ("presentation-resource-v0.1.schema.yaml", "/$defs/projectRef/properties/contentIdentity", "sha256Identity"),
    ("revision-store-resource-ref-v0.1.schema.yaml", "/properties/address", "relativeAddress"),
    ("revision-store-resource-ref-v0.1.schema.yaml", "/properties/revision/properties/token", "revisionToken"),
    ("revision-store-resource-ref-v0.1.schema.yaml", "/properties/contentIdentity", "sha256Identity"),
])
def test_frozen_parts_spell_the_same_patterns_as_common_except_the_anchor(part, pointer, definition):
    assert _anchor_neutral(_pattern_at(part, pointer)) == _anchor_neutral(_defs()[definition]["pattern"])


def test_the_three_portable_name_copies_in_python_equal_the_common_definition():
    expected = _anchor_neutral(_defs()["portableName"]["pattern"])
    assert _anchor_neutral(importer._THEME_ASSET_NAME.pattern) == expected
    assert _anchor_neutral(normalizer._ASSET_NAME.pattern) == expected
    # The third copy is a local in `_icon_catalog_envelope`, so read it from the source.
    source = (ROOT / "src/chrona/presentation/contracts/resources.py").read_text(encoding="utf-8")
    function = next(node for node in ast.walk(ast.parse(source))
                    if isinstance(node, ast.FunctionDef) and node.name == "_icon_catalog_envelope")
    compiled = [call.args[0].value for call in ast.walk(function)
                if isinstance(call, ast.Call) and getattr(call.func, "attr", "") == "compile"
                and call.args and isinstance(call.args[0], ast.Constant)]
    assert [_anchor_neutral(pattern) for pattern in compiled] == [expected]


def test_the_adopted_portable_name_sites_use_the_common_definition():
    for name in ("icon-catalog-v0.5.schema.yaml", "theme-asset-source-v0.2.schema.yaml"):
        assert _schema(name)["$defs"]["name"]["$ref"] == f"{COMMON_ID}#/$defs/portableName"
    assert _defs()["portableName"]["pattern"] == importer._THEME_ASSET_NAME.pattern


# --------------------------------------------------------------------------------------------
# One probe per definition
# --------------------------------------------------------------------------------------------

DIGEST = "sha256:" + "0" * 64
GIT = "git:" + "a" * 40

# name -> (accepted, rejected)
PROBES: dict[str, tuple[list[Any], list[Any]]] = {
    "sha256Identity": ([DIGEST, "sha256:" + "abcdef0123456789" * 4], ["", "sha256:abc", "SHA256:" + "0" * 64, "sha256:" + "A" * 64, "sha256:" + "0" * 65, 5, None]),
    "sha256IdentityOrNull": ([DIGEST, "sha256:" + "abcdef0123456789" * 4, None], ["", "sha256:abc", "SHA256:" + "0" * 64, "sha256:" + "A" * 64, "sha256:" + "0" * 65, 5, [], {}]),
    "isoDate": (["2026-09-30", "0001-01-01"], ["", "2026-9-30", "20260930", "2026/09/30", "2026-09-30T00:00", " 2026-09-30", 20260930, None]),
    "safeRelativePath": (["a", "views/overview.yaml", "A0._-/b", "a..b"], ["", "/abs", "../x", "a/../b", "a/..", "a/./b", ".hidden", "a b", "a\\b", "a\x00b", "é", 5]),
    "relativeAddress": (["resources/project.yaml", "a b", "a\\b", "é", ".hidden", "a..b"], ["", "/abs", "../x", "a/../b", "a/..", "./a", "a/./b"]),
    "relativeAddressDotTolerant": (["a", "a/./b", "./a", "a b", "é"], ["", "/abs", "../x", "a/../b", "a/.."]),
    "storeAddress": (["a", "a/b/c.yaml", "resources/project.yaml", ".hidden", "a..b", "a./b", "A_b-c.0/d"],
                     ["", ".", "..", "...", "./a", "a/./b", "a/../b", "../x", "a/...", "a//b", "a/", "/x", "C:/x", "C:x", "\\\\server\\share\\x",
                      "a\\b", "a\x00b", "a\nb", "a\n", "\na", "a:b", "a b", "\u00e9", "a\x7fb", "a\tb", 5, None]),
    "fileName": (["a", "plan.yaml", "計画.yaml", "my plan.yaml", "a..b", ".hidden"], ["", ".", "..", "a/b", "a\\b", "a\nb", "a\n", "a\x00b", "\t", "a\x7f", 5]),
    "identifier": (["x", "Work package / gate", "作業ストリーム", "Δ", "#", "supplier:FW-42", " padded "], ["", "a\nb", "a\n", "\x00", "a\tb", "\x7f", 5]),
    "slug": (["a", "controller-z", "a1-b2"], ["", "A", "1a", "a_b", "a b", "-a", "a.b", 5]),
    "portableName": (["a", "0a", "A_b-c"], ["", "_a", "-a", "a b", "a.b", "é", 5]),
    "gitRevision": ([GIT, "git:" + "F" * 64, "git:" + "0Aa1" * 10], ["", "git:" + "a" * 39, "git:" + "a" * 65, "git:xyz", "Git:" + "a" * 40, "a" * 40, 5]),
    "revisionToken": (["main", "v1.2", "a:b/c", "é"], ["", " ", "a b", "a\tb", 5]),
    "fractionalTrack": ([{"fr": 1}, {"fr": 0.5}, {"fr": 1000000}], [{}, {"fr": 0}, {"fr": -1}, {"fr": 1000001}, {"fr": "1"}, {"fr": 1, "x": 1}, "1fr", 1]),
    "license": ([{"spdx": "MIT", "notice": "n"}], [{}, {"spdx": "MIT"}, {"notice": "n"}, {"spdx": "", "notice": "n"}, {"spdx": "MIT", "notice": ""}, {"spdx": "MIT", "notice": "n", "x": 1}, "MIT"]),
    "literalCaption": (["Notes", "作業計画", "a" * 80], ["", "a" * 81, "bad\ncaption", "bad\x00caption", 5, None]),
}

# Accepted today by the byte-exact `$` anchor, `\d`, or the shape-only date. Not endorsed: a later slice
# (T2/T3, decided by the owner) flips each of these, and then moves the string to PROBES' rejected list.
ACCEPTED_TODAY: dict[str, list[str]] = {
    "sha256Identity": [DIGEST + "\n"],
    "sha256IdentityOrNull": [DIGEST + "\n"],
    "isoDate": ["2026-13-45", "2026-02-30", "0000-00-00", "２０２６-09-30", "2026-09-30\n"],
    "safeRelativePath": ["a.yaml\n"],
    "relativeAddress": ["a\nb", "a\x00b", "a\\b"],
    "relativeAddressDotTolerant": ["a\n", "a\\b", "a\x00b"],
    "slug": ["a\n"],
    "portableName": ["a\n"],
    "gitRevision": [GIT + "\n"],
    "revisionToken": ["main\n"],
}


def test_every_definition_has_a_probe_row():
    assert set(PROBES) == set(_defs())


@pytest.mark.parametrize("name", sorted(PROBES))
def test_definition_accepts_and_rejects_the_probe_values(name):
    validator = _def_validator(name)
    accepted, rejected = PROBES[name]
    assert [value for value in accepted if not validator.is_valid(value)] == []
    assert [value for value in rejected if validator.is_valid(value)] == []


@pytest.mark.parametrize("name", sorted(ACCEPTED_TODAY))
def test_definition_keeps_todays_laxness_until_the_decided_tightening(name):
    validator = _def_validator(name)
    assert [value for value in ACCEPTED_TODAY[name] if not validator.is_valid(value)] == []


def test_new_definitions_are_newline_proof_from_the_start():
    for name in ("fileName", "identifier", "storeAddress"):
        assert not _def_validator(name).is_valid("a\n")


def test_definitions_that_name_an_existing_pattern_are_byte_exact_to_it():
    # These are the exact strings the live schemas carried before S1c (copied from the frozen parts and from git history).
    assert _defs()["sha256Identity"]["pattern"] == _pattern_at("presentation-resource-v0.1.schema.yaml", "/$defs/resourceRef/properties/contentIdentity")
    assert _defs()["safeRelativePath"]["pattern"] == _pattern_at("presentation-resource-v0.1.schema.yaml", "/$defs/resourceRef/properties/path")
    assert _defs()["gitRevision"]["pattern"] == _pattern_at("presentation-resource-v0.1.schema.yaml", "/$defs/resourceRef/properties/revision")
    assert _defs()["relativeAddress"]["pattern"] == _pattern_at("revision-store-resource-ref-v0.1.schema.yaml", "/properties/address")
    assert _defs()["revisionToken"]["pattern"] == _pattern_at("revision-store-resource-ref-v0.1.schema.yaml", "/properties/revision/properties/token")
    assert _defs()["isoDate"]["pattern"] == r"^\d{4}-\d{2}-\d{2}$"
    assert _defs()["slug"]["pattern"] == "^[a-z][a-z0-9-]*$"
    assert _defs()["portableName"]["pattern"] == "^[A-Za-z0-9][A-Za-z0-9_-]*$"
    assert _defs()["relativeAddressDotTolerant"]["pattern"] == r"^(?!/)(?!.*(?:^|/)\.\.(?:/|$)).+$"


# --------------------------------------------------------------------------------------------
# One probe per adopting kind (every adopted site of every live schema)
# --------------------------------------------------------------------------------------------

ADOPTERS = frozenset({
    "actual-intake-batch-v0.2.schema.yaml", "actual-set-v0.3.schema.yaml", "authoring-command-result-v0.1.schema.yaml",
    "authoring-command-v0.1.schema.yaml", "authoring-workspace-v0.1.schema.yaml", "automation-result-v0.2.schema.yaml",
    "command-request-v0.3.schema.yaml", "example-registry-v0.1.schema.yaml", "icon-catalog-v0.5.schema.yaml",
    "layout-profile-v0.10.schema.yaml", "presentation-materialization-receipt-v0.1.schema.yaml", "presentation-preset-v0.1.schema.yaml",
    "preset-library-v0.2.schema.yaml", "profile-v0.3.schema.yaml", "project-v0.7.schema.yaml",
    "render-context-v0.17.schema.yaml", "scene-v0.7.schema.yaml", "theme-asset-source-v0.2.schema.yaml",
    "theme-v0.16.schema.yaml", "view-v0.28.schema.yaml",
})


# Parts published after `common` that reference it: a part may name another part's definition, and each is
# frozen with that reference in its digest. The parts published before it must still reference nothing.
PARTS_REFERENCING_COMMON: dict[str, set[str]] = {"revision-store-resource-ref-v0.2.schema.yaml": {"storeAddress"}}


# Adopted sites that add a local rule beside the `$ref`: the registry stores `snapshots/<id>.yaml`, so the id is one segment.
SEGMENT_SITES = {("command-request-v0.3.schema.yaml", "/allOf/4/then/properties/payload/properties/snapshotId")}


def _adopted_sites(name: str) -> list[tuple[str, str]]:
    return [(_pointer(path), node["$ref"].partition("#/$defs/")[2]) for path, node in _walk(_schema(name))
            if isinstance(node, dict) and isinstance(node.get("$ref"), str) and node["$ref"].startswith(COMMON_ID + "#/$defs/")]


def test_the_adopting_kinds_are_exactly_the_planned_ones():
    adopters = {name for name in LIVE if name not in SCHEMA_PARTS and _adopted_sites(name)}
    assert adopters == ADOPTERS
    for name in SCHEMA_PARTS:
        if name in PARTS_REFERENCING_COMMON:
            assert {definition for _, definition in _adopted_sites(name)} == PARTS_REFERENCING_COMMON[name]
        else:
            assert not _adopted_sites(name), f"{name} is frozen and must not reference common"


@pytest.mark.parametrize("name", sorted(ADOPTERS))
def test_every_adopted_site_accepts_and_rejects_like_its_definition(name):
    schema = _schema(name)
    registry = schema_registry().with_resource(schema["$id"], Resource.from_contents(schema))
    sites = _adopted_sites(name)
    assert sites
    for pointer, definition in sites:
        accepted, rejected = PROBES[definition]
        validator = Draft202012Validator({"$ref": f"{schema['$id']}#{pointer}"}, registry=registry)
        if (name, pointer) in SEGMENT_SITES:  # a site that narrows the definition to one segment: the extra rule is its own sibling
            assert [value for value in accepted if "/" not in value and not validator.is_valid(value)] == [], (name, pointer)
            assert [value for value in accepted if "/" in value and validator.is_valid(value)] == [], (name, pointer)
            assert [value for value in rejected if validator.is_valid(value)] == [], (name, pointer)
            continue
        assert [value for value in accepted if not validator.is_valid(value)] == [], (name, pointer)
        assert [value for value in rejected if validator.is_valid(value)] == [], (name, pointer)
        assert [value for value in ACCEPTED_TODAY.get(definition, []) if not validator.is_valid(value)] == [], (name, pointer)


def test_adopted_sites_keep_their_local_extras():
    # A `$ref` site keeps its own siblings: the path fields stay non-empty.
    schema = _schema("authoring-workspace-v0.1.schema.yaml")
    assert schema["$defs"]["preset"]["properties"]["path"]["minLength"] == 1
    assert schema["$defs"]["localReference"]["properties"]["path"]["minLength"] == 1


def test_the_nullable_result_revision_keeps_its_shape_through_the_nullable_definition():
    result = _schema("authoring-command-result-v0.1.schema.yaml")
    assert result["properties"]["resultRevision"]["$ref"] == f"{COMMON_ID}#/$defs/sha256IdentityOrNull"
    nullable, strict = _defs()["sha256IdentityOrNull"], _defs()["sha256Identity"]
    assert nullable["type"] == [strict["type"], "null"] and nullable["pattern"] == strict["pattern"]


# --------------------------------------------------------------------------------------------
# S1f: layout-profile adoption keeps every diagnostic of a bad track size
# --------------------------------------------------------------------------------------------

BAD_TRACK_SIZES = [{"fr": 0}, {"fr": "x"}, {"fr": -1}, {"fr": 2000000}, {"fr": 1, "extra": 1}, {"zz": 1}, {}, 5, "bad", None, [],
                   {"fixed": -1}, {"fitContent": "a"}, {"fr": None}, True, {"fr": 1, "fixed": 2}]
GOOD_TRACK_SIZES = [{"fr": 1}, {"fr": 0.5}, "content", {"fixed": 24}]


def _layout_with_grid(track: Any, where: str) -> dict[str, Any]:
    document = yaml.safe_load((ROOT / "conformance/layout-profile-intent-v0.2.yaml").read_text(encoding="utf-8"))
    slot = document["root"]["children"][0]
    grid = {"id": "g", "kind": "grid", "inlineSize": "fill", "blockSize": "fill", "columnTracks": [{"fr": 1}], "rowTracks": ["content"],
            "gap": 0, "padding": 0, "alignItems": "start", "justifyContent": "start", "children": [slot]}
    grid[where] = [track] if where.endswith("Tracks") else track
    document["root"] = grid
    return document


def _explanations(schema: dict[str, Any], document: dict[str, Any]) -> tuple[Any, ...]:
    from chrona.schema_diagnostics import explain_all_errors, explain_errors

    errors = list(validator_for_schema(schema).iter_errors(document))
    if not errors:
        return ("valid",)
    return (explain_errors(errors), explain_all_errors(errors))


@pytest.mark.parametrize("where", ["columnTracks", "rowTracks", "inlineSize"])
def test_layout_profile_fractional_track_reference_changes_no_diagnostic(where):
    # `_union_forms` reads a branch's `required`, so a `$ref` union branch can change a union message (the View `width`
    # branches stay inline for that reason). The size union of layout-profile is reached only beneath the `root` union, whose own
    # message wins, and `explain_all_errors` flattens to leaves; this proves both reducers equal an inline twin.
    adopted = _schema("layout-profile-v0.10.schema.yaml")
    branch = adopted["$defs"]["simpleSize"]["oneOf"][1]
    assert branch["$ref"] == f"{COMMON_ID}#/$defs/fractionalTrack"
    twin = _schema("layout-profile-v0.10.schema.yaml")
    twin["$defs"]["simpleSize"]["oneOf"][1] = {key: value for key, value in _defs()["fractionalTrack"].items() if key != "examples"}
    for value in (*BAD_TRACK_SIZES, *GOOD_TRACK_SIZES):
        document = _layout_with_grid(value, where)
        assert _explanations(adopted, document) == _explanations(twin, document), value
    assert _explanations(adopted, _layout_with_grid({"fr": 1}, where)) == ("valid",)
    assert _explanations(adopted, _layout_with_grid({"fr": 0}, where)) != ("valid",)


# --------------------------------------------------------------------------------------------
# Row 1 closure: authoring-command and its result adopt the shared definitions and keep every diagnostic
# --------------------------------------------------------------------------------------------

def _command(**changes: Any) -> dict[str, Any]:
    document = {"version": "chrona/authoring-command/v0.1", "commandId": "c", "type": "setWorkspaceTask",
                "target": {"kind": "authoring-workspace", "path": "workspace.yaml"}, "baseRevision": DIGEST,
                "payload": {"task": {"id": "t", "title": "T", "planned": {"start": "2026-01-01", "finish": "2026-01-02"}}}}
    return {**document, **changes}


def _result(**changes: Any) -> dict[str, Any]:
    document = {"version": "chrona/authoring-command-result/v0.1", "status": "accepted", "commandId": "c",
                "commandBaseRevision": DIGEST, "workspaceRevision": DIGEST, "resultRevision": DIGEST, "diagnostics": []}
    return {**document, **changes}


def _planned(start: Any, finish: Any) -> dict[str, Any]:
    return {"task": {"id": "t", "title": "T", "planned": {"start": start, "finish": finish}}}


def _observed(start: Any, finish: Any) -> dict[str, Any]:
    return {"actual": {"taskId": "t", "actual": {"start": start, "finish": finish}}}


def _command_documents() -> list[dict[str, Any]]:
    documents = [_command()]
    documents += [_command(baseRevision=value) for value in ("", "sha256:abc", DIGEST.upper(), DIGEST + "0", 5, None, DIGEST + "\n")]
    for start, finish in (("2026-9-1", "2026-01-02"), ("2026-01-01", "tomorrow"), (5, "2026-01-02"), ("2026-02-30", "2026-13-45"), ("2026-01-01\n", "2026-01-02")):
        documents.append(_command(payload=_planned(start, finish)))
    for start, finish in (("2026-01-01", "2026-01-02"), ("x", "2026-01-02"), ("2026-01-01", None), ("２０２６-01-01", "2026-01-02")):
        documents.append(_command(type="setWorkspaceActual", payload=_observed(start, finish)))
    return documents


def _result_documents() -> list[dict[str, Any]]:
    rejected = {"status": "rejected", "diagnostics": [{"code": "E_X"}]}
    documents = [_result(), _result(resultRevision=None, **rejected), _result(**rejected)]
    documents += [_result(resultRevision=value) for value in ("", "sha256:abc", DIGEST.upper(), 5, None, [], DIGEST + "\n")]
    documents += [_result(resultRevision=value, **rejected) for value in (DIGEST, "bad", None)]
    return documents


@pytest.mark.parametrize(("name", "documents"), [("authoring-command-v0.1.schema.yaml", _command_documents),
                                                 ("authoring-command-result-v0.1.schema.yaml", _result_documents)])
def test_adopting_the_shared_definitions_changes_no_diagnostic_of_an_authoring_document(name, documents):
    from chrona.resources import dereferenced_schema

    adopted, twin = _schema(name), dict(dereferenced_schema(name))
    cases = documents()
    assert {_explanations(adopted, case) == ("valid",) for case in cases} == {True, False}
    for case in cases:
        assert _explanations(adopted, case) == _explanations(twin, case), case


def test_authoring_command_keeps_no_inline_copy_of_a_common_definition():
    assert not _copies("authoring-command-v0.1.schema.yaml")
    assert not _copies("authoring-command-result-v0.1.schema.yaml")
    sites = {definition for _, definition in _adopted_sites("authoring-command-v0.1.schema.yaml")}
    assert {"sha256Identity", "isoDate", "fileName", "safeRelativePath"} <= sites


# --------------------------------------------------------------------------------------------
# schemas/README.md mirrors the live inventory entries (I662-S6)
# --------------------------------------------------------------------------------------------

def test_the_readme_table_mirrors_the_live_inventory_entries():
    lines = (SCHEMAS / "README.md").read_text(encoding="utf-8").splitlines()
    start = lines.index("| Kind | Live schema |") + 2
    rows = []
    for line in lines[start:]:
        if not line.startswith("|"):
            break
        kind, file = (cell.strip() for cell in line.strip("|").split("|"))
        rows.append((kind, file))
    live = [(entry["kind"], entry["file"]) for entry in ENTRIES if entry["state"] == "live"]
    assert sorted(rows) == sorted(live)
    assert len(rows) == len(set(rows)), "a live schema is listed once"
