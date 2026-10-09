"""The `graphics` schema part (I662-S3): registered and frozen, no inline copy of its shapes, the Scene sibling, and site parity."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from jsonschema import Draft202012Validator
from referencing import Resource
import pytest
import yaml

from chrona.resources import SCHEMA_PARTS, schema_document, schema_registry, validator_for_schema
from tools.schema_inventory import definition_digest, load_inventory, validate_frozen_definitions, validate_inventory


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
SCHEMAS = ROOT / "schemas"
GRAPHICS = "graphics-v0.1.schema.yaml"
GRAPHICS_ID = "urn:chrona:graphics-v0.1"
COMMON_ID = "urn:chrona:common-v0.1"
CATALOG = "icon-catalog-v0.5.schema.yaml"
SOURCE = "theme-asset-source-v0.2.schema.yaml"
SCENE = "scene-v0.7.schema.yaml"
ENTRIES = load_inventory(SCHEMAS / "schema-inventory-v0.1.yaml")
LIVE = tuple(entry["file"] for entry in ENTRIES if entry["state"] == "live")
PARTS = frozenset(SCHEMA_PARTS)


def _schema(name: str) -> dict[str, Any]:
    return yaml.safe_load((SCHEMAS / name).read_bytes())


def _defs() -> dict[str, Any]:
    return schema_document(GRAPHICS)["$defs"]


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


def _sites(name: str, definition: str, part: str = GRAPHICS_ID) -> list[str]:
    target = f"{part}#/$defs/{definition}"
    return [_pointer(path) for path, node in _walk(_schema(name)) if isinstance(node, dict) and node.get("$ref") == target]


def _site_validator(name: str, pointer: str, *, schema: dict[str, Any] | None = None) -> Draft202012Validator:
    schema = schema or _schema(name)
    registry = schema_registry().with_resource(schema["$id"], Resource.from_contents(schema))
    return Draft202012Validator({"$ref": f"{schema['$id']}#{pointer}"}, registry=registry)


def _definition_validator(name: str) -> Draft202012Validator:
    return validator_for_schema({"$ref": f"{GRAPHICS_ID}#/$defs/{name}"})


# --------------------------------------------------------------------------------------------
# Registration and freezing
# --------------------------------------------------------------------------------------------

def test_graphics_is_a_registered_live_part_with_frozen_digests():
    assert GRAPHICS in SCHEMA_PARTS
    entry = next(item for item in ENTRIES if item["file"] == GRAPHICS)
    assert entry["state"] == "live" and entry["kind"] == "schema-part-graphics"
    assert set(entry["frozenDefs"]) == set(_defs()), "every published definition of graphics-v0.1 is frozen"
    assert schema_document(GRAPHICS)["$id"] == GRAPHICS_ID
    assert {key for key in schema_document(GRAPHICS) if not key.startswith("$") and key not in {"title", "description"}} == set(), \
        "a part asserts nothing at its root"
    validate_frozen_definitions(SCHEMAS, ENTRIES)
    assert validate_inventory(SCHEMAS, SCHEMAS / "schema-inventory-v0.1.yaml", repo_root=ROOT)


def test_a_graphics_enum_is_untyped_so_a_site_keeps_its_dereferenced_form():
    # A `type` would add a keyword to every site that replaced an inline `enum`, and the S0 L1 fingerprint would differ.
    for name in ("paintMode", "lineCap", "lineJoin"):
        assert set(_defs()[name]) - {"description", "examples"} == {"enum"}, name


def test_the_shared_defs_carry_the_asset_bounds_that_scene_leaves_open():
    defs = _defs()
    assert defs["viewport"]["properties"]["inlineSize"]["maximum"] == 4096
    assert defs["tile"]["properties"]["blockSize"]["maximum"] == 256
    assert defs["circlePrimitive"]["properties"]["radius"]["maximum"] == 128
    assert defs["circlePrimitive"]["properties"]["cx"]["maximum"] == 256
    assert defs["rectanglePrimitive"]["properties"]["x"]["maximum"] == 256


# --------------------------------------------------------------------------------------------
# Adopted sites
# --------------------------------------------------------------------------------------------

THEME = "theme-v0.15.schema.yaml"
# definition -> {file: number of sites}
ADOPTION: dict[str, dict[str, int]] = {
    "viewport": {CATALOG: 2, SOURCE: 1},
    "tile": {CATALOG: 1, SOURCE: 1},
    "tileAngle": {CATALOG: 1, SOURCE: 1, SCENE: 1, THEME: 1},
    "densityBasisPoints": {CATALOG: 1, SOURCE: 1, SCENE: 1},
    # The frozen predecessor is reused through its coordinate/radius properties.
    "circlePrimitive": {},
    "patternCirclePrimitive": {CATALOG: 1, SOURCE: 1},
    "rectanglePrimitive": {CATALOG: 1, SOURCE: 1},
    "paintMode": {CATALOG: 3, SOURCE: 1, SCENE: 2},
    "lineCap": {CATALOG: 3, SOURCE: 1, SCENE: 1},
    "lineJoin": {CATALOG: 3, SOURCE: 1, SCENE: 1},
    "strokePaintRequiresStrokeFields": {CATALOG: 3, SOURCE: 1, SCENE: 1},
    "fillPaintForbidsStrokeFields": {CATALOG: 3, SOURCE: 1, SCENE: 1},
}


def test_every_graphics_definition_is_used_and_the_adoption_table_is_complete():
    assert set(ADOPTION) == set(_defs())


@pytest.mark.parametrize(("definition", "counts"), sorted(ADOPTION.items()))
def test_each_graphics_definition_is_referenced_where_the_adoption_table_says(definition, counts):
    for name, count in counts.items():
        assert len(_sites(name, definition)) == count, (name, definition, _sites(name, definition))


# Valid and invalid values per definition. Each adopted site must agree with its definition on all of them.
TILE = {"inlineSize": 8, "blockSize": 8}
PROBES: dict[str, tuple[list[Any], list[Any]]] = {
    "viewport": ([{"inlineSize": 1, "blockSize": 4096}, {"inlineSize": 24, "blockSize": 24}],
                 [{}, {"inlineSize": 0, "blockSize": 1}, {"inlineSize": 1, "blockSize": 4097}, {"inlineSize": 1.5, "blockSize": 1},
                  {"inlineSize": 1}, {"inlineSize": 1, "blockSize": 1, "x": 1}, 5, None]),
    "tile": ([TILE, {"inlineSize": 1, "blockSize": 256}, {"inlineSize": 1.5, "blockSize": 2.5}],
             [{}, {"inlineSize": 0.5, "blockSize": 8}, {"inlineSize": 8, "blockSize": 257}, {"inlineSize": 8}, {**TILE, "x": 1}, 5]),
    "tileAngle": ([0, 45, 359.99], [-1, 360, "0", None]),
    "densityBasisPoints": ([1, 2500, 10000], [0, 10001, 1.5, "1", None]),
    "circlePrimitive": ([{"kind": "circle", "cx": 0, "cy": 256, "radius": 128}, {"kind": "circle", "cx": 4.5, "cy": 4, "radius": 0.5}],
                        [{"kind": "circle", "cx": -1, "cy": 0, "radius": 1}, {"kind": "circle", "cx": 257, "cy": 0, "radius": 1},
                         {"kind": "circle", "cx": 0, "cy": 0, "radius": 0}, {"kind": "circle", "cx": 0, "cy": 0, "radius": 129},
                         {"kind": "rect", "cx": 0, "cy": 0, "radius": 1}, {"kind": "circle", "cx": 0, "cy": 0},
                         {"kind": "circle", "cx": 0, "cy": 0, "radius": 1, "x": 1}, 5]),
    "rectanglePrimitive": ([{"kind": "rect", "x": 0, "y": 256, "inlineSize": 256, "blockSize": 1}],
                           [{"kind": "rect", "x": -1, "y": 0, "inlineSize": 1, "blockSize": 1}, {"kind": "rect", "x": 257, "y": 0, "inlineSize": 1, "blockSize": 1},
                            {"kind": "rect", "x": 0, "y": 0, "inlineSize": 0, "blockSize": 1}, {"kind": "rect", "x": 0, "y": 0, "inlineSize": 257, "blockSize": 1},
                            {"kind": "circle", "x": 0, "y": 0, "inlineSize": 1, "blockSize": 1}, {"kind": "rect", "x": 0, "y": 0, "inlineSize": 1},
                            {"kind": "rect", "x": 0, "y": 0, "inlineSize": 1, "blockSize": 1, "r": 1}, None]),
    "paintMode": (["fill", "stroke"], ["", "Fill", "both", "fill ", None, 1, ["fill"]]),
    "lineCap": (["butt", "round", "square"], ["", "Round", "miter", "round ", None, 1]),
    "lineJoin": (["miter", "round", "bevel"], ["", "Miter", "butt", "round ", None, 1]),
    "strokePaintRequiresStrokeFields": (
        [{"paint": "stroke", "strokeWidth": 1, "lineCap": "round", "lineJoin": "round"}, {"paint": "fill"}, {}, {"paint": "other"}],
        [{"paint": "stroke"}, {"paint": "stroke", "strokeWidth": 1}, {"paint": "stroke", "strokeWidth": 1, "lineCap": "round"},
         {"paint": "stroke", "lineCap": "round", "lineJoin": "round"}]),
    "fillPaintForbidsStrokeFields": (
        [{"paint": "fill"}, {"paint": "stroke", "strokeWidth": 1}, {}, {"strokeWidth": 1}],
        [{"paint": "fill", "strokeWidth": 1}, {"paint": "fill", "lineCap": "round"}, {"paint": "fill", "lineJoin": "bevel"}]),
}


PROBES["patternCirclePrimitive"] = (
    [*PROBES["circlePrimitive"][0],
     {"kind": "circle", "cx": 4, "cy": 4, "radius": 3, "fillChannel": "substrate", "strokeWidth": 0.8},
     {"kind": "circle", "cx": 4, "cy": 4, "radius": 3, "fillChannel": "none", "strokeWidth": 0.125}],
    [*PROBES["circlePrimitive"][1],
     {"kind": "circle", "cx": 4, "cy": 4, "radius": 3, "fillChannel": "none"},
     {"kind": "circle", "cx": 4, "cy": 4, "radius": 3, "fillChannel": "red"},
     {"kind": "circle", "cx": 4, "cy": 4, "radius": 3, "strokeWidth": 0},
     {"kind": "circle", "cx": 4, "cy": 4, "radius": 3, "strokeWidth": 16.01}],
)


def test_pattern_circle_reuses_frozen_coordinates_and_scene_reuses_new_fields():
    for field in ("cx", "cy", "radius"):
        assert _defs()["patternCirclePrimitive"]["properties"][field]["$ref"] == f"#/$defs/circlePrimitive/properties/{field}"
    circle = _scene_defs()["catalogPatternPrimitive"]["oneOf"][0]
    for field in ("fillChannel", "strokeWidth"):
        assert circle["properties"][field]["$ref"] == f"{GRAPHICS_ID}#/$defs/patternCirclePrimitive/properties/{field}"


def test_every_definition_has_a_probe_row():
    assert set(PROBES) == set(_defs())


@pytest.mark.parametrize("name", sorted(PROBES))
def test_definition_accepts_and_rejects_the_probe_values(name):
    validator = _definition_validator(name)
    accepted, rejected = PROBES[name]
    assert [value for value in accepted if not validator.is_valid(value)] == []
    assert [value for value in rejected if validator.is_valid(value)] == []


# The rule definitions constrain an object's own fields and say nothing about the rest of it, so a site-level probe for them is
# the whole object of a path. `ADOPTION` is the authority on where each one is used; this checks every site of one of them.
RULE_DEFINITIONS = {"strokePaintRequiresStrokeFields", "fillPaintForbidsStrokeFields"}


@pytest.mark.parametrize(("definition", "counts"), sorted((key, value) for key, value in ADOPTION.items() if key not in RULE_DEFINITIONS))
def test_every_adopted_site_accepts_and_rejects_like_its_definition(definition, counts):
    accepted, rejected = PROBES[definition]
    for name in counts:
        for pointer in _sites(name, definition):
            validator = _site_validator(name, pointer)
            assert [value for value in accepted if not validator.is_valid(value)] == [], (name, pointer)
            assert [value for value in rejected if validator.is_valid(value)] == [], (name, pointer)


def test_the_license_sites_use_the_common_definition_and_keep_the_probe_matrix():
    sites = {CATALOG: "/allOf/1/properties/body/properties/provenance/properties/license",
             SOURCE: "/properties/body/properties/license"}
    for name, pointer in sites.items():
        assert _sites(name, "license", COMMON_ID) == [pointer]
        validator = _site_validator(name, pointer)
        assert validator.is_valid({"spdx": "MIT", "notice": "n"})
        for bad in ({}, {"spdx": "MIT"}, {"notice": "n"}, {"spdx": "", "notice": "n"}, {"spdx": "MIT", "notice": ""},
                    {"spdx": "MIT", "notice": "n", "x": 1}, "MIT", None):
            assert not validator.is_valid(bad), (name, bad)


# --------------------------------------------------------------------------------------------
# No live entry outside the parts spells out a graphics shape (design D8)
# --------------------------------------------------------------------------------------------

# (file, pointer) of a node that equals a graphics definition structurally and is deliberately not a reference, each with the reason.
DIFFERENT_CONCEPT: dict[tuple[str, str], str] = {
    **{("layout-profile-v0.10.schema.yaml", f"/$defs/cell/properties/{field}"):
       "a 1..10000 grid cell index or span, not a pattern coverage in basis points"
       for field in ("column", "columnSpan", "row", "rowSpan")},
}


def _shape_copies(name: str) -> set[tuple[str, str]]:
    """(file, pointer) of every node of one schema whose structure equals a graphics definition."""
    digests = {definition_digest(definition) for definition in _defs().values()}
    return {(name, _pointer(path)) for path, node in _walk(_schema(name))
            if isinstance(node, dict) and ("enum" in node or "type" in node or "if" in node) and definition_digest(node) in digests}


def test_no_live_entry_outside_the_parts_copies_a_graphics_definition():
    copies: set[tuple[str, str]] = set()
    for name in LIVE:
        if name not in PARTS:
            copies |= _shape_copies(name)
    assert copies == set(DIFFERENT_CONCEPT), sorted(copies ^ set(DIFFERENT_CONCEPT))


# --------------------------------------------------------------------------------------------
# Scene is a sibling of the catalog geometry, not a reference to the bounded definitions
# --------------------------------------------------------------------------------------------

def _scene_defs() -> dict[str, Any]:
    return _schema(SCENE)["$defs"]


def _scene_validator(definition: str) -> Draft202012Validator:
    # Only `$defs` of the Scene schema: its root would add its own envelope rules.
    return validator_for_schema({"$id": "urn:test:scene-wrapper", "$defs": _scene_defs(), "$ref": f"#/$defs/{definition}"})


def _catalog_primitive_validator() -> Draft202012Validator:
    return validator_for_schema({"$id": "urn:test:catalog-wrapper", "$defs": _schema(CATALOG)["$defs"], "$ref": "#/$defs/patternPrimitive"})


def _kinds(oneof: list[dict[str, Any]], definitions: dict[str, Any]) -> set[str]:
    kinds: set[str] = set()
    for branch in oneof:
        if "$ref" in branch:
            ref = branch["$ref"]
            target = (_defs() if ref.startswith(GRAPHICS_ID) else definitions)[ref.rpartition("/")[2]]
            kinds.add(target["properties"]["kind"]["const"])
        else:
            kinds.add(branch["properties"]["kind"]["const"])
    return kinds


def test_scene_circle_and_rectangle_stay_unbounded_siblings():
    scene_circle = {"kind": "circle", "cx": 1000, "cy": -5, "radius": 500}
    scene_rect = {"kind": "rect", "x": -10, "y": 1000, "inlineSize": 5000, "blockSize": 0.01}
    scene = _scene_validator("catalogPatternPrimitive")
    assert scene.is_valid(scene_circle) and scene.is_valid(scene_rect)
    strict = _catalog_primitive_validator()
    assert not strict.is_valid(scene_circle) and not strict.is_valid(scene_rect), "the catalog bounds are the asset bounds"
    # A reference would have tightened Scene: the two branches are not references.
    for branch in _scene_defs()["catalogPatternPrimitive"]["oneOf"]:
        assert "$ref" not in branch
    assert not _sites(SCENE, "circlePrimitive") and not _sites(SCENE, "rectanglePrimitive")
    assert not _sites(SCENE, "viewport") and not _sites(SCENE, "tile")


def test_every_valid_catalog_primitive_is_valid_scene_geometry_and_the_kind_sets_are_equal():
    scene = _scene_validator("catalogPatternPrimitive")
    catalog = _catalog_primitive_validator()
    valid = [*PROBES["patternCirclePrimitive"][0], *PROBES["rectanglePrimitive"][0],
             {"kind": "path", "paint": "fill", "commands": [{"kind": "move", "points": [0, 0]}, {"kind": "line", "points": [4, 4]}, {"kind": "close", "points": []}]},
             {"kind": "path", "paint": "stroke", "strokeWidth": 1, "lineCap": "round", "lineJoin": "bevel",
              "commands": [{"kind": "move", "points": [0, 0]}, {"kind": "quadratic", "points": [1, 1, 2, 2]}]}]
    for value in valid:
        assert catalog.is_valid(value), value
        assert scene.is_valid(value), value
    catalog_kinds = _kinds(_schema(CATALOG)["$defs"]["patternPrimitive"]["oneOf"], _schema(CATALOG)["$defs"])
    scene_kinds = _kinds(_scene_defs()["catalogPatternPrimitive"]["oneOf"], _scene_defs())
    assert catalog_kinds == scene_kinds == {"circle", "rect", "path"}
    command_kinds = _schema(CATALOG)["$defs"]["pathCommand"]["properties"]["kind"]["enum"]
    assert set(command_kinds) == set(_scene_defs()["catalogPatternCommand"]["properties"]["kind"]["enum"])


def test_scene_shares_the_bound_free_definitions_only():
    # Enums, the angle, the density and the stroke rules carry no bound that Scene leaves open, so Scene references them.
    shared = {definition for definition, counts in ADOPTION.items() if SCENE in counts}
    assert shared == {"tileAngle", "densityBasisPoints", "paintMode", "lineCap", "lineJoin",
                      "strokePaintRequiresStrokeFields", "fillPaintForbidsStrokeFields"}


# --------------------------------------------------------------------------------------------
# A reference changes no diagnostic: every reducer says what the inlined twin says
# --------------------------------------------------------------------------------------------

def _load(path: str) -> dict[str, Any]:
    return yaml.safe_load((ROOT / path).read_bytes())


def _set(document: Any, pointer: tuple[Any, ...], value: Any) -> Any:
    clone = json.loads(json.dumps(document))
    node = clone
    for token in pointer[:-1]:
        node = node[token]
    node[pointer[-1]] = value
    return clone


def _explanations(schema: dict[str, Any], document: Any) -> tuple[Any, ...]:
    from chrona.schema_diagnostics import explain_all_errors, explain_errors

    errors = list(validator_for_schema(schema).iter_errors(document))
    return ("valid",) if not errors else (explain_errors(errors), explain_all_errors(errors))


STROKE = {"paint": "stroke", "strokeWidth": 1, "lineCap": "round", "lineJoin": "round"}
BAD_VIEWPORTS = [{}, {"inlineSize": 0, "blockSize": 1}, {"inlineSize": 1, "blockSize": 4097}, {"inlineSize": 1.5, "blockSize": 1}, {"inlineSize": 1}, 5]
BAD_TILES = [{}, {"inlineSize": 0.5, "blockSize": 8}, {"inlineSize": 8, "blockSize": 257}, {"inlineSize": 8}, 5]
BAD_PRIMITIVES = [{"kind": "star"}, {"kind": "circle"}, {"kind": "circle", "cx": 0, "cy": 0, "radius": 129}, {"kind": "circle", "cx": -1, "cy": 0, "radius": 1},
                  {"kind": "rect", "x": 0, "y": 0, "inlineSize": 0, "blockSize": 1}, {"kind": "rect", "x": 0, "y": 0, "inlineSize": 1}, {"x": 1}, 5, None]
GOOD_PRIMITIVES = [{"kind": "circle", "cx": 4, "cy": 4, "radius": 1}, {"kind": "rect", "x": 0, "y": 0, "inlineSize": 8, "blockSize": 1}]
BAD_LICENSES = [{}, {"spdx": "MIT"}, {"spdx": "", "notice": "n"}, {"spdx": "MIT", "notice": "n", "x": 1}, "MIT"]


def _source_cases() -> list[Any]:
    base = _load("tests/fixtures/icons/theme-assets-valid.yaml")
    part = ("body", "glyphs", "pin", "parts", 0)
    pattern = ("body", "patterns", "dither-12-5")
    cases: list[Any] = [base]
    cases += [_set(base, ("body", "glyphs", "pin", "viewport"), value) for value in BAD_VIEWPORTS]
    cases += [_set(base, pattern + ("tile",), value) for value in BAD_TILES]
    cases += [_set(base, pattern + ("angle",), value) for value in (-1, 360, "0")]
    cases += [_set(base, pattern + ("densityBasisPoints",), value) for value in (0, 10001, 1.5)]
    cases += [_set(base, pattern + ("primitives", 0), value) for value in (*BAD_PRIMITIVES, *GOOD_PRIMITIVES)]
    cases += [_set(base, ("body", "license"), value) for value in BAD_LICENSES]
    cases += [_set(base, part, {"d": "M 0 0", **value}) for value in (
        STROKE, {"paint": "stroke"}, {"paint": "stroke", "strokeWidth": 1}, {"paint": "fill", "lineCap": "round"}, {"paint": "fill", "strokeWidth": 1},
        {**STROKE, "lineCap": "rounded"}, {**STROKE, "lineJoin": "x"}, {"paint": "both"}, {"paint": "fill"})]
    return cases


def _catalog_cases() -> list[Any]:
    base = _load("tests/fixtures/icons/theme-assets-valid.normalized-v0.5.yaml")
    pattern = ("body", "patterns", "dither-12-5")
    cases: list[Any] = [base]
    cases += [_set(base, ("body", "glyphs", "pin", "viewport"), value) for value in BAD_VIEWPORTS]
    cases += [_set(base, pattern + ("tile",), value) for value in BAD_TILES]
    cases += [_set(base, pattern + ("angle",), value) for value in (-1, 360, "0")]
    cases += [_set(base, pattern + ("densityBasisPoints",), value) for value in (0, 10001, 1.5)]
    cases += [_set(base, pattern + ("primitives", 0), value) for value in (*BAD_PRIMITIVES, *GOOD_PRIMITIVES)]
    cases += [_set(base, ("body", "provenance", "license"), value) for value in BAD_LICENSES]
    commands = [{"kind": "move", "points": [0, 0]}]
    cases += [_set(base, pattern + ("primitives", 0), {"kind": "path", "commands": commands, **value}) for value in (
        STROKE, {"paint": "stroke"}, {"paint": "stroke", "strokeWidth": 1}, {"paint": "fill", "lineCap": "round"}, {"paint": "fill", "strokeWidth": 1},
        {**STROKE, "lineCap": "rounded"}, {"paint": "both"}, {"paint": "fill"})]
    cases += [_set(base, ("body", "glyphs", "pin", "parts", 0), {"data": "M 0 0", **value}) for value in (
        STROKE, {"paint": "stroke"}, {"paint": "fill", "lineJoin": "bevel"}, {"paint": "both"}, {"paint": "fill"})]
    return cases


@pytest.mark.parametrize(("name", "cases"), [(SOURCE, _source_cases), (CATALOG, _catalog_cases)])
def test_a_graphics_reference_changes_no_diagnostic_of_an_asset_document(name, cases):
    from chrona.resources import dereferenced_schema

    twin = dict(dereferenced_schema(name))
    adopted = _schema(name)
    documents = cases()
    verdicts = {_explanations(adopted, document)[0] == "valid" for document in documents}
    assert verdicts == {True, False}, "the matrix holds both valid and invalid documents"
    for document in documents:
        assert _explanations(adopted, document) == _explanations(twin, document), json.dumps(document)[:200]


def test_a_graphics_reference_changes_no_diagnostic_of_a_scene_pattern():
    from chrona.resources import dereferenced_schema

    adopted_defs = _scene_defs()
    twin_defs = dereferenced_schema(SCENE)["$defs"]
    path = {"kind": "path", "commands": [{"kind": "move", "points": [0, 0]}]}
    sites = {"catalogPatternPrimitive": [*BAD_PRIMITIVES, *GOOD_PRIMITIVES,
                                          {**path, "paint": "stroke"}, {**path, "paint": "fill", "strokeWidth": 1},
                                          {**path, "paint": "both"}, {**path, **STROKE}],
             "lineCap": ["butt", "round", "x", None], "lineJoin": ["miter", "bevel", "y", None],
             "markerPaintMode": ["fill", "stroke", "both", None], "patternAngle": [0, 359, 360, -1, "0"],
             "strokeFinish": [{"lineCap": "round", "lineJoin": "round", "fidelity": "required"},
                              {"lineCap": "x", "lineJoin": "round", "fidelity": "required"}]}
    for definition, values in sites.items():
        for value in values:
            adopted = {"$id": "urn:test:scene-adopted", "$defs": adopted_defs, "$ref": f"#/$defs/{definition}"}
            twin = {"$id": "urn:test:scene-twin", "$defs": twin_defs, "$ref": f"#/$defs/{definition}"}
            assert _explanations(adopted, value) == _explanations(twin, value), (definition, value)
