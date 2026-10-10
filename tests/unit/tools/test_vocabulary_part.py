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


def test_background_extent_is_shared_and_text_is_only_group_header_extension():
    expected = ["table", "timeline", "both"]
    assert _defs()["backgroundExtent"]["enum"] == expected
    layout = _schema("layout-profile-v0.10.schema.yaml")
    extents = layout["properties"]["reviewSurface"]["properties"]["backgroundExtents"]["properties"]
    vocabulary_ref = f"{VOCABULARY_ID}#/$defs/backgroundExtent"
    assert extents["rowBand"] == {"$ref": vocabulary_ref}
    assert extents["groupBand"] == {"$ref": vocabulary_ref}
    assert extents["groupHeaderBand"]["anyOf"] == [
        {"$ref": vocabulary_ref},
        {"description": "The measured group-header label interval, including declared leading inset, clamped to the table column.",
         "examples": ["text"], "const": "text"},
    ]

    for role in ("rowBand", "groupBand"):
        validator = _site_validator(
            "layout-profile-v0.10.schema.yaml",
            f"/properties/reviewSurface/properties/backgroundExtents/properties/{role}",
        )
        assert all(validator.is_valid(value) for value in expected)
        assert not validator.is_valid("text"), role

    validator = _site_validator("layout-profile-v0.10.schema.yaml", "/properties/reviewSurface/properties/backgroundExtents/properties/groupHeaderBand")
    assert all(validator.is_valid(value) for value in (*expected, "text"))
    assert not any(validator.is_valid(value) for value in ("Text", "table ", "none", None, 3))


# --------------------------------------------------------------------------------------------
# No live entry outside the parts spells out a vocabulary the part defines
# --------------------------------------------------------------------------------------------

# (file, pointer) of an `enum` that equals a definition of the part and is NOT the same concept, each with the reason.
DIFFERENT_CONCEPT: dict[tuple[str, str], str] = {
    ("view-v0.28.schema.yaml", "/allOf/1/properties/body/properties/tableColumns/items/properties/align"):
        "inline alignment of a table column's content inside its measured allocation, not an annotation's alignment along a side",
    ("layout-profile-v0.10.schema.yaml", "/$defs/guide/properties/at/oneOf/0"):
        "a named layout guide position along an axis, not an annotation's alignment along a side",
    ("layout-profile-v0.10.schema.yaml", "/$defs/slotHeading/properties/align"):
        "the inline position of a slot heading within its slot, not an annotation's alignment along a side",
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
    "render-context-v0.17.schema.yaml": "/properties/body/properties/target/properties/visualProfile",
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


def test_every_declared_value_reader_follows_a_part_reference_including_corpus_coverage():
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
    followed = _seen(corpus_coverage._schema_values, schema)
    assert followed >= wanted
    assert {item for item in followed if item[0] == ("provider",)}, "corpus coverage follows every part too (#715)"


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
    ("view-v0.28.schema.yaml", "monthLabelForm", 3),
    ("view-v0.28.schema.yaml", "quarterLabelForm", 3),
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
    assert every == set(FORMS), "the layout levels and the name-table form set cover the same forms"
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
    assert defs["viewGroupingBy"]["enum"] == ["objectType", "field", "hierarchy", "none"]
    assert defs["guidedViewGroupingBy"]["enum"] == ["objectType", "none"]


@pytest.mark.parametrize(("name", "definition", "count"), [
    (VIEW, "annotationPurpose", 1), (WORKSPACE, "annotationPurpose", 1),
    (VIEW, "annotationSide", 2), (WORKSPACE, "annotationSide", 1),
    (VIEW, "annotationAlignment", 1), (WORKSPACE, "annotationAlignment", 1),
    (VIEW, "annotationVisibilityMode", 2), (VIEW, "relationVisibilityMode", 1),
    (WORKSPACE, "guidedAnnotationVisibilityMode", 1), (WORKSPACE, "guidedRelationVisibilityMode", 1),
    (VIEW, "viewGroupingBy", 1), (WORKSPACE, "guidedViewGroupingBy", 1),
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
    ("guidedViewGroupingBy", "viewGroupingBy"),
])
def test_a_guided_override_subset_is_strictly_contained_in_the_view_vocabulary(subset, superset):
    small, large = _defs()[subset]["enum"], _defs()[superset]["enum"]
    assert set(small) < set(large), "a named subset is a proper subset: equal sets would need no second definition"
    assert [value for value in large if value in small] == small, "the subset keeps the superset's order"


def test_a_guided_override_cannot_select_the_semantic_annotation_mode():
    assert "semantic" in _defs()["annotationVisibilityMode"]["enum"]
    assert "semantic" not in _defs()["guidedAnnotationVisibilityMode"]["enum"]
    assert "critical" not in _defs()["guidedRelationVisibilityMode"]["enum"]


def test_a_guided_override_cannot_select_a_grouping_that_needs_a_field_or_a_depth():
    # View requires `field` and `missing` for `by: field` and `depth` and `rollup` for `by: hierarchy`; the guided
    # override carries only the dimension, so it offers only the two that need nothing more.
    assert {"field", "hierarchy"} <= set(_defs()["viewGroupingBy"]["enum"])
    assert not {"field", "hierarchy"} & set(_defs()["guidedViewGroupingBy"]["enum"])


def test_the_guided_workspace_accepts_no_visibility_value_the_view_rejects():
    view = _site_validator(VIEW, _sites(VIEW, "annotationVisibilityMode")[0])
    relations = _site_validator(VIEW, _sites(VIEW, "relationVisibilityMode")[0])
    for value in _defs()["guidedAnnotationVisibilityMode"]["enum"]:
        assert view.is_valid(value), value
    for value in _defs()["guidedRelationVisibilityMode"]["enum"]:
        assert relations.is_valid(value), value
    grouping = _site_validator(VIEW, _sites(VIEW, "viewGroupingBy")[0])
    for value in _defs()["guidedViewGroupingBy"]["enum"]:
        assert grouping.is_valid(value), value


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


# --------------------------------------------------------------------------------------------
# valueFormat and its two declared subsets (S2d)
# --------------------------------------------------------------------------------------------

SUMMARY = "summary-profile-v0.2.schema.yaml"
TABLE_FORMATS = ["text", "dateRange", "date", "signedDays"]
SUMMARY_FORMATS = ["text", "date", "count", "signedDays"]


def test_value_format_vocabulary_is_the_union_of_its_two_declared_subsets():
    defs = _defs()
    assert defs["tableColumnScalarFormat"]["enum"] == TABLE_FORMATS
    assert defs["summaryMetricFormat"]["enum"] == SUMMARY_FORMATS
    full = set(defs["valueFormat"]["enum"])
    assert set(TABLE_FORMATS) < full and set(SUMMARY_FORMATS) < full
    assert set(TABLE_FORMATS) | set(SUMMARY_FORMATS) == full, "the superset declares exactly the formats some context accepts"
    assert full - set(TABLE_FORMATS) == {"count"} and full - set(SUMMARY_FORMATS) == {"dateRange"}, \
        "the only difference between the contexts: a table has dateRange, a summary metric has count"


@pytest.mark.parametrize(("name", "definition"), [(VIEW, "tableColumnScalarFormat"), (SUMMARY, "summaryMetricFormat")])
def test_each_value_format_site_references_its_subset_and_accepts_exactly_it(name, definition):
    sites = _sites(name, definition)
    assert len(sites) == 1, sites
    validator = _site_validator(name, sites[0])
    allowed = _defs()[definition]["enum"]
    assert [value for value in allowed if not validator.is_valid(value)] == []
    for value in ("count", "dateRange", "signedDay", "Text", "", None, 3, {"kind": "presence"}):
        assert validator.is_valid(value) is (isinstance(value, str) and value in allowed), value
    other = {"tableColumnScalarFormat": "count", "summaryMetricFormat": "dateRange"}[definition]
    assert not validator.is_valid(other), f"{definition} must not accept the other context's format {other}"


def test_no_site_references_the_full_value_format():
    assert not any(_sites(name, "valueFormat") for name in LIVE if name not in PARTS)


def _literals(path: str) -> set[str]:
    import ast

    return {node.value for node in ast.walk(ast.parse((ROOT / path).read_text(encoding="utf-8"))) if isinstance(node, ast.Constant) and isinstance(node.value, str)}


def test_value_format_code_twins_equal_the_declared_subsets():
    import ast

    # The summary renderer rejects every formatter outside one set literal; it must be exactly the declared subset.
    tree = ast.parse((ROOT / "src/chrona/presentation/review/v05_content.py").read_text(encoding="utf-8"))
    sets = [{element.value for element in node.elts} for node in ast.walk(tree)
            if isinstance(node, ast.Set) and node.elts and all(isinstance(element, ast.Constant) and isinstance(element.value, str) for element in node.elts)]
    assert set(SUMMARY_FORMATS) in sets
    # The table formatter handles each declared scalar format by name.
    table = _literals("src/chrona/presentation/model/surface_content.py")
    assert set(TABLE_FORMATS) <= table


TABLE_FORMAT_PROBES = ["bogus", "", 5, None, [], {}, {"kind": "presence"}, {"kind": "presence", "whenTrue": "Yes"},
                       {"kind": "presence", "whenTrue": "Yes", "whenFalse": 3}, {"kind": "other", "whenTrue": "a", "whenFalse": "b"},
                       "count", "dateRange"]


def test_a_reference_in_the_table_format_union_changes_no_diagnostic():
    view = _schema(VIEW)
    pointer = next(_pointer(path) for path, node in _walk(view)
                   if path[-4:] == ("tableColumns", "items", "properties", "format") and isinstance(node, dict))
    rows = _union_explanations(VIEW, pointer, TABLE_FORMAT_PROBES)
    for value, adopted, twin in rows:
        assert adopted == twin, value
    assert any(row[1] != ("valid",) for row in rows) and any(row[1] == ("valid",) for row in _union_explanations(VIEW, pointer, ["text", "signedDays"]))


# --------------------------------------------------------------------------------------------
# dateEndpoint and anchorEndpoint (S2e)
# --------------------------------------------------------------------------------------------

PROJECT = "project-v0.7.schema.yaml"
DATE_ENDPOINTS = ["at", "start", "end"]
ANCHOR_ENDPOINTS = ["start", "end", "finish", "at", "body"]


def test_endpoint_vocabularies_are_the_published_values_in_order():
    assert _defs()["dateEndpoint"]["enum"] == DATE_ENDPOINTS
    assert _defs()["anchorEndpoint"]["enum"] == ANCHOR_ENDPOINTS


def test_the_two_endpoint_vocabularies_overlap_exactly_where_d4_says():
    # Design D4 / slice S4a: the span-end is `end` (canonical) and `finish` (alias) in a View anchor, `end` in a Project,
    # and `body` exists only on an anchor. S4a added `end` to the anchor vocabulary, so the Project vocabulary is a subset.
    date, anchor = set(DATE_ENDPOINTS), set(ANCHOR_ENDPOINTS)
    assert date <= anchor
    assert anchor - date == {"finish", "body"}


def test_end_widens_the_anchor_endpoint_to_a_superset_of_the_project_endpoints():
    assert [value for value in _defs()["dateEndpoint"]["enum"] if value not in _defs()["anchorEndpoint"]["enum"]] == []
    validator = _site_validator(VIEW, _sites(VIEW, "anchorEndpoint")[0])
    assert validator.is_valid("end") and validator.is_valid("finish")
    assert not validator.is_valid("End") and not validator.is_valid("finish ")


@pytest.mark.parametrize(("name", "definition", "count"), [(PROJECT, "dateEndpoint", 1), (VIEW, "anchorEndpoint", 1)])
def test_each_endpoint_site_references_its_definition_and_accepts_exactly_it(name, definition, count):
    sites = _sites(name, definition)
    assert len(sites) == count, sites
    validator = _site_validator(name, sites[0])
    allowed = _defs()[definition]["enum"]
    assert [value for value in allowed if not validator.is_valid(value)] == []
    for value in ("finish", "end", "body", "center", "At", "", None, 3):
        assert validator.is_valid(value) is (isinstance(value, str) and value in allowed), (definition, value)


def test_endpoint_code_twins_equal_the_schema_vocabulary():
    import ast

    from chrona.core.validation import _schedule_endpoints

    assert _schedule_endpoints({"mode": "fixed-point"}) | _schedule_endpoints({"mode": "span"}) == set(DATE_ENDPOINTS)
    tree = ast.parse((ROOT / "src/chrona/presentation/layout/annotations.py").read_text(encoding="utf-8"))
    sets = [{element.value for element in node.elts} for node in ast.walk(tree)
            if isinstance(node, ast.Set) and node.elts and all(isinstance(element, ast.Constant) and isinstance(element.value, str) for element in node.elts)]
    assert set(ANCHOR_ENDPOINTS) in sets, "the annotation resolver accepts exactly the declared anchor endpoints"


def test_the_declared_vocabulary_policy_still_reads_the_view_anchor_endpoint_through_the_reference():
    from tools.vocabulary_inventory import declared_values, load_policy

    entry = next(item for item in load_policy(ROOT / "conformance/declared-vocabulary-policy-v0.1.yaml")
                 if item.schema.endswith("view-v0.28.schema.yaml") and item.pointer.endswith("/anchor/properties/endpoint"))
    assert declared_values(ROOT, entry) == tuple(sorted(ANCHOR_ENDPOINTS))
    assert set(declared_values(ROOT, entry)) <= set(entry.accepted)
