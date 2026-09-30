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
DIFFERENT_CONCEPT: dict[tuple[str, str], str] = {
    ("view-v0.28.schema.yaml", "/allOf/1/properties/body/properties/tableColumns/items/properties/align"):
        "inline alignment of a table column's content inside its measured allocation, not an annotation's alignment along a side",
    ("layout-profile-v0.9.schema.yaml", "/$defs/guide/properties/at/oneOf/0"):
        "a named layout guide position along an axis, not an annotation's alignment along a side",
}


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



# --------------------------------------------------------------------------------------------
# The readers that list a kind's finite vocabulary still see what moved into the part (review F2)
# --------------------------------------------------------------------------------------------

def _seen(reader: Any, schema: Any) -> set[tuple[tuple[str, ...], str]]:
    return {(path, json.dumps(value)) for path, value in reader(schema)}


@pytest.mark.parametrize("kind", ["view", "layout-profile", "theme", "color-scheme"])
def test_presentation_coverage_sees_the_same_vocabulary_as_the_inlined_schema(kind):
    # The walk follows `$ref` into a part, so a value that moved is still listed: its output equals the fully inlined twin.
    from chrona.resources import dereferenced_schema
    from tools.presentation_coverage import _integer_minimums, _schema_values, live_schemas

    schemas = live_schemas(ROOT)
    name = next(entry["file"] for entry in ENTRIES if entry["state"] == "live" and entry["kind"] == kind)
    inlined = dereferenced_schema(name)
    assert _seen(_schema_values, schemas[kind]) == _seen(_schema_values, inlined)
    assert set(_integer_minimums(schemas[kind])) == set(_integer_minimums(inlined))


def test_the_readers_follow_a_vocabulary_reference_but_corpus_coverage_leaves_other_parts_alone():
    from tools import corpus_coverage, presentation_coverage

    schema = {"$id": "urn:test", "type": "object", "properties": {
        "profile": {"$ref": f"{VOCABULARY_ID}#/$defs/visualProfile"},
        "provider": {"$ref": "urn:chrona:revision-store-resource-ref-v0.1#/properties/store/properties/provider"},
        "local": {"$ref": "#/$defs/mode"}},
        "$defs": {"mode": {"enum": ["a", "b"]}}}
    wanted = {(("profile",), json.dumps(value)) for value in VISUAL_PROFILES} | {(("local",), '"a"'), (("local",), '"b"')}
    everything = _seen(presentation_coverage._schema_values, presentation_coverage.with_parts(schema, presentation_coverage.schema_parts(ROOT)))
    assert everything >= wanted
    assert {item for item in everything if item[0] == ("provider",)}, "presentation coverage follows every part"
    vocabulary_only = _seen(corpus_coverage._schema_values, schema)
    assert vocabulary_only >= wanted
    assert not {item for item in vocabulary_only if item[0] == ("provider",)}, "corpus coverage follows vocabulary parts only"


def test_vocabulary_inventory_reads_a_declared_value_through_a_part_reference(tmp_path):
    from tools.vocabulary_inventory import VocabularyEntry, VocabularyInventoryError, declared_values

    (tmp_path / "schemas").mkdir()
    (tmp_path / "schemas" / "site.schema.yaml").write_text(yaml.safe_dump({
        "$id": "urn:test-site", "properties": {"profile": {"description": "x", "$ref": f"{VOCABULARY_ID}#/$defs/visualProfile"},
                                                "broken": {"$ref": "urn:chrona:missing-v9#/$defs/nope"}}}), encoding="utf-8")
    entry = VocabularyEntry("schemas/site.schema.yaml", "/properties/profile", "test", "finite", tuple(VISUAL_PROFILES))
    assert declared_values(tmp_path, entry) == tuple(sorted(VISUAL_PROFILES))
    with pytest.raises(VocabularyInventoryError, match="E_VOCABULARY_REFERENCE"):
        declared_values(tmp_path, VocabularyEntry("schemas/site.schema.yaml", "/properties/broken", "test", "finite", ("x",)))


def test_every_declared_vocabulary_policy_value_is_read_from_the_dereferenced_schema():
    from chrona.resources import dereferenced_schema
    from tools.vocabulary_inventory import declared_values, load_policy

    for entry in load_policy(ROOT / "conformance/declared-vocabulary-policy-v0.1.yaml"):
        node: Any = dereferenced_schema(Path(entry.schema).name)
        for token in entry.pointer[1:].split("/"):
            node = node[int(token)] if isinstance(node, list) else node[token.replace("~1", "/").replace("~0", "~")]
        expected = (node["const"],) if "const" in node else tuple(node["enum"])
        assert declared_values(ROOT, entry) == tuple(sorted(expected)), entry.identity


# --------------------------------------------------------------------------------------------
# monthLabelForm and quarterLabelForm (S2b)
# --------------------------------------------------------------------------------------------

MONTH_FORMS = ["short-month", "long-month", "numeric-month", "short-month-year", "long-month-year", "numeric-year-month"]
QUARTER_FORMS = ["quarter", "year-quarter", "quarter-year"]


def test_month_and_quarter_label_forms_are_the_published_forms_in_order():
    assert _defs()["monthLabelForm"]["enum"] == MONTH_FORMS
    assert _defs()["quarterLabelForm"]["enum"] == QUARTER_FORMS


@pytest.mark.parametrize(("name", "definition", "count"), [
    ("view-v0.28.schema.yaml", "monthLabelForm", 2),
    ("view-v0.28.schema.yaml", "quarterLabelForm", 2),
    ("axis-name-tables-v0.1.schema.yaml", "monthLabelForm", 2),
])
def test_each_axis_label_form_site_references_the_definition_and_accepts_exactly_it(name, definition, count):
    sites = _sites(name, definition)
    assert len(sites) == count, sites
    allowed = _defs()[definition]["enum"]
    for pointer in sites:
        validator = _site_validator(name, pointer)
        assert [value for value in allowed if not validator.is_valid(value)] == [], pointer
        for value in ("year", "iso-week", "Short-Month", "short-month ", "", None, 3):
            assert not validator.is_valid(value) or value in allowed, (pointer, value)


def test_axis_label_form_code_twins_equal_the_schema_vocabulary():
    from chrona.presentation.layout.axis import _FORMS_BY_LEVEL
    from chrona.presentation.model.axis_names import FORMS, MONTH_FORMS as MODEL_MONTH_FORMS

    assert list(MODEL_MONTH_FORMS) == _defs()["monthLabelForm"]["enum"]
    assert _FORMS_BY_LEVEL["month"] == frozenset(_defs()["monthLabelForm"]["enum"])
    assert _FORMS_BY_LEVEL["quarter"] == frozenset(_defs()["quarterLabelForm"]["enum"])
    every = set().union(*_FORMS_BY_LEVEL.values())
    assert every == set(FORMS), "the layout levels and the name-table form set cover the same 13 forms"
    catalog = _schema("axis-name-tables-v0.1.schema.yaml")
    assert set(catalog["$defs"]["table"]["properties"]["templates"]["required"]) == set(FORMS)


# --------------------------------------------------------------------------------------------
# annotationPurpose / Side / Alignment and the visibility-mode subsets (S2c)
# --------------------------------------------------------------------------------------------

PURPOSES = ["callout", "highlight", "note", "explanatory-arrow"]
SIDES = ["above", "below", "start", "end"]
ALIGNMENTS = ["start", "center", "end"]
VIEW = "view-v0.28.schema.yaml"
WORKSPACE = "authoring-workspace-v0.1.schema.yaml"


def test_annotation_vocabulary_is_the_published_values_in_order():
    defs = _defs()
    assert defs["annotationPurpose"]["enum"] == PURPOSES
    assert defs["annotationSide"]["enum"] == SIDES
    assert defs["annotationAlignment"]["enum"] == ALIGNMENTS
    assert defs["annotationVisibilityMode"]["enum"] == ["none", "semantic", "presentation", "all"]
    assert defs["relationVisibilityMode"]["enum"] == ["none", "semantic", "critical", "all"]
    assert defs["guidedAnnotationVisibilityMode"]["enum"] == ["none", "presentation", "all"]
    assert defs["guidedRelationVisibilityMode"]["enum"] == ["none", "semantic"]


@pytest.mark.parametrize(("name", "definition", "count"), [
    (VIEW, "annotationPurpose", 1), (WORKSPACE, "annotationPurpose", 1),
    (VIEW, "annotationSide", 2), (WORKSPACE, "annotationSide", 1),
    (VIEW, "annotationAlignment", 1), (WORKSPACE, "annotationAlignment", 1),
    (VIEW, "annotationVisibilityMode", 2), (VIEW, "relationVisibilityMode", 1),
    (WORKSPACE, "guidedAnnotationVisibilityMode", 1), (WORKSPACE, "guidedRelationVisibilityMode", 1),
])
def test_each_annotation_vocabulary_site_references_the_definition_and_accepts_exactly_it(name, definition, count):
    sites = _sites(name, definition)
    assert len(sites) == count, sites
    allowed = _defs()[definition]["enum"]
    for pointer in sites:
        validator = _site_validator(name, pointer)
        assert [value for value in allowed if not validator.is_valid(value)] == [], pointer
        for value in ("inside", "rail", "auto", "Callout", "above ", "", None, 3, ["above"]):
            assert validator.is_valid(value) is (value in allowed if isinstance(value, str) else False), (pointer, value)


@pytest.mark.parametrize(("subset", "superset"), [
    ("guidedAnnotationVisibilityMode", "annotationVisibilityMode"),
    ("guidedRelationVisibilityMode", "relationVisibilityMode"),
])
def test_a_guided_override_subset_is_strictly_contained_in_the_view_vocabulary(subset, superset):
    small, large = _defs()[subset]["enum"], _defs()[superset]["enum"]
    assert set(small) < set(large), "a named subset is a proper subset: equal sets would need no second definition"
    assert [value for value in large if value in small] == small, "the subset keeps the superset's order"


def test_a_guided_override_cannot_select_the_semantic_annotation_mode():
    assert "semantic" in _defs()["annotationVisibilityMode"]["enum"]
    assert "semantic" not in _defs()["guidedAnnotationVisibilityMode"]["enum"]
    assert "critical" not in _defs()["guidedRelationVisibilityMode"]["enum"]


def test_the_guided_workspace_accepts_no_visibility_value_the_view_rejects():
    view = _site_validator(VIEW, _sites(VIEW, "annotationVisibilityMode")[0])
    relations = _site_validator(VIEW, _sites(VIEW, "relationVisibilityMode")[0])
    for value in _defs()["guidedAnnotationVisibilityMode"]["enum"]:
        assert view.is_valid(value), value
    for value in _defs()["guidedRelationVisibilityMode"]["enum"]:
        assert relations.is_valid(value), value


def test_view_and_workspace_annotation_enums_are_one_definition():
    # B2: the two schemas share the exact purpose, side and alignment vocabulary through one definition each.
    for definition in ("annotationPurpose", "annotationSide", "annotationAlignment"):
        assert _sites(VIEW, definition) and _sites(WORKSPACE, definition), definition


def test_annotation_side_is_one_concept_for_a_rung_and_an_adjacent_search():
    # `legacy_candidate` expands a rung side into an adjacent search on the same side, so both sites share the definition.
    from chrona.presentation.model.placement_candidates import _parse_search, legacy_candidate

    for side in SIDES:
        assert legacy_candidate(side, "note").search.side == side
        assert _parse_search({"kind": "adjacent", "side": side}).side == side
    for side in ("inside", "rail", "auto", ""):
        with pytest.raises(ValueError, match="E_PRESENTATION_CANDIDATE_INVALID"):
            _parse_search({"kind": "adjacent", "side": side})


def _union_explanations(name: str, pointer: str, values: list[Any]) -> list[Any]:
    from chrona.resources import dereferenced_schema
    from chrona.schema_diagnostics import explain_all_errors, explain_errors

    schema = _schema(name)
    registry = schema_registry().with_resource(schema["$id"], Resource.from_contents(schema))
    adopted = Draft202012Validator({"$ref": f"{schema['$id']}#{pointer}"}, registry=registry)
    twin_schema = dereferenced_schema(name)
    twin = Draft202012Validator({"$ref": f"{twin_schema['$id']}#{pointer}"},
                                registry=schema_registry().with_resource(twin_schema["$id"], Resource.from_contents(twin_schema)))
    rows = []
    for value in values:
        outcomes = []
        for validator in (adopted, twin):
            errors = list(validator.iter_errors(value))
            outcomes.append(("valid",) if not errors else (explain_errors(errors), explain_all_errors(errors)))
        rows.append((value, outcomes[0], outcomes[1]))
    return rows


def _view_pointer(*tail: str) -> str:
    view = _schema(VIEW)
    found = [pointer for pointer in (_pointer(path) for path, node in _walk(view)
                                      if isinstance(node, dict) and "visibility" in node.get("properties", {}))]
    assert found
    return found[0] + "/properties/visibility/properties/" + "/properties/".join(tail)


VISIBILITY_PROBES = ["bogus", "", 5, None, [], {}, {"mode": "all"}, {"mode": "bogus", "marker": "none"}, {"mode": "all", "marker": "x"},
                     {"mode": "all", "marker": "numbered", "extra": 1}, "critical", "semantic", "presentation",
                     {"mode": "critical", "overflow": "suppress"}, {"mode": "all", "overflow": "suppress"}]


@pytest.mark.parametrize("field", ["annotations", "relations"])
def test_a_reference_in_the_visibility_union_changes_no_diagnostic(field):
    # `_union_forms` reads a branch's `required`; an enum branch has none, so a `$ref` enum branch must explain exactly as the
    # inline enum did. The fully inlined twin is the inline form.
    for value, adopted, twin in _union_explanations(VIEW, _view_pointer(field), VISIBILITY_PROBES):
        assert adopted == twin, value
    assert any(row[1] != ("valid",) for row in _union_explanations(VIEW, _view_pointer(field), VISIBILITY_PROBES))
