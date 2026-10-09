"""The one schema loader: registry, validator factory, bundled and dereferenced forms."""
import ast
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

import chrona.resources as resources
from chrona.resources import (
    SCHEMA_PARTS, bundled_schema, dereferenced_schema, schema_document, schema_registry, schema_validator,
    validator_for_schema,
)

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
FACTORY = ROOT / "src" / "chrona" / "resources" / "__init__.py"
# The S0 equivalence gate is independent of the loader on purpose: a loader bug
# must not be able to hide itself from the gate that checks the loader.
INDEPENDENT = (ROOT / "tools" / "schema_equivalence.py",)
PART_REFERENCE_SCHEMAS = ("view-v0.28.schema.yaml", "command-request-v0.3.schema.yaml", "icon-catalog-v0.5.schema.yaml")


def _contains_part_reference(node) -> bool:
    if isinstance(node, dict):
        return any((key == "$ref" and isinstance(value, str) and value.startswith("urn:chrona:"))
                   or _contains_part_reference(value) for key, value in node.items())
    if isinstance(node, list):
        return any(_contains_part_reference(item) for item in node)
    return False


@pytest.fixture
def fresh_registry():
    schema_registry.cache_clear()
    yield
    schema_registry.cache_clear()


def test_registry_holds_exactly_the_listed_parts():
    registry = schema_registry()
    assert set(registry) == {schema_document(name)["$id"] for name in SCHEMA_PARTS}
    assert all(uri.startswith("urn:chrona:") for uri in registry)


def test_a_missing_part_raises_at_the_gate_not_at_a_document(monkeypatch, fresh_registry):
    monkeypatch.setattr(resources, "SCHEMA_PARTS", (*SCHEMA_PARTS, "no-such-part-v0.1.schema.yaml"))
    with pytest.raises(Exception):
        schema_registry()


def test_validator_is_cached_by_name_and_shares_the_registry():
    assert schema_validator("view-v0.28.schema.yaml") is schema_validator("view-v0.28.schema.yaml")
    assert schema_validator("view-v0.28.schema.yaml") is not schema_validator("project-v0.7.schema.yaml")
    project = schema_document("project-v0.7.schema.yaml")
    assert validator_for_schema(project).schema == project


@pytest.mark.parametrize("name", PART_REFERENCE_SCHEMAS)
def test_factory_evaluates_a_referenced_part_without_unresolvable(name):
    assert _contains_part_reference(schema_document(name))
    tuple(schema_validator(name).iter_errors({}))


@pytest.mark.parametrize("name", PART_REFERENCE_SCHEMAS)
def test_bundled_form_validates_with_a_bare_validator_and_agrees_with_the_factory(name):
    bundled = bundled_schema(name)
    Draft202012Validator.check_schema(bundled)
    bare = Draft202012Validator(bundled)
    for document in ({}, {"version": "x"}, {"version": "chrona/view/v0.28", "kind": "view", "id": "a", "body": {}}):
        assert ({(tuple(e.absolute_path), e.validator) for e in bare.iter_errors(document)}
                == {(tuple(e.absolute_path), e.validator) for e in schema_validator(name).iter_errors(document)})
    assert {schema_document(part)["$id"] for part in SCHEMA_PARTS} & set(bundled["$defs"])


def test_bundled_form_does_not_mutate_the_cached_schema():
    before = dict(schema_document("view-v0.28.schema.yaml"))
    bundled_schema("view-v0.28.schema.yaml")["$defs"].clear()
    assert dict(schema_document("view-v0.28.schema.yaml")) == before


@pytest.mark.parametrize("name", PART_REFERENCE_SCHEMAS)
def test_dereferenced_form_has_no_part_reference(name):
    assert not _contains_part_reference(dereferenced_schema(name))


def test_schema_without_a_part_reference_is_unchanged_by_either_form():
    assert dereferenced_schema("store-config-v0.1.schema.yaml") == schema_document("store-config-v0.1.schema.yaml")
    assert bundled_schema("store-config-v0.1.schema.yaml") == schema_document("store-config-v0.1.schema.yaml")


def _validator_constructions(path: Path) -> list[int]:
    return [node.lineno for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
            if isinstance(node, ast.Call)
            and (getattr(node.func, "id", None) == "Draft202012Validator"
                 or getattr(node.func, "attr", None) == "Draft202012Validator")]


def test_only_the_factory_constructs_a_validator():
    offenders = [f"{path.relative_to(ROOT)}:{line}"
                 for directory in ("src", "tools", "conformance")
                 for path in sorted((ROOT / directory).rglob("*.py")) if path != FACTORY and path not in INDEPENDENT
                 for line in _validator_constructions(path)]
    assert offenders == []
    assert _validator_constructions(FACTORY), "the factory is expected to hold the construction"


def test_guard_detects_a_construction(tmp_path):
    sample = tmp_path / "sample.py"
    sample.write_text("import jsonschema\njsonschema.Draft202012Validator({})\n")
    assert _validator_constructions(sample) == [2]
