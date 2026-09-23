from pathlib import Path

import pytest

from tools.schema_annotations import SchemaAnnotationError, validate_annotations


def _files(root: Path, schema: str) -> tuple[Path, Path]:
    schemas = root / "schemas"
    schemas.mkdir()
    (schemas / "project-v0.1.schema.yaml").write_text(schema)
    inventory = root / "inventory.yaml"
    inventory.write_text("version: chrona/schema-inventory/v0.1\nschemas:\n  - file: project-v0.1.schema.yaml\n    kind: project\n    state: live\n    consumers: [src/chrona/core/validation.py]\n")
    return schemas, inventory


def test_annotation_lint_names_missing_description(tmp_path):
    schemas, inventory = _files(tmp_path, "type: object\nproperties:\n  project: {type: object}\n")

    with pytest.raises(SchemaAnnotationError, match="E_SCHEMA_ANNOTATION_DESCRIPTION:project-v0.1.schema.yaml:/"):
        validate_annotations(schemas, inventory)


def test_annotation_lint_requires_union_examples(tmp_path):
    schema = "description: Project document\ntype: object\nanyOf:\n  - {description: Point form, type: object}\n  - {description: Span form, type: object}\n"
    schemas, inventory = _files(tmp_path, schema)

    with pytest.raises(SchemaAnnotationError, match="E_SCHEMA_ANNOTATION_EXAMPLE:project-v0.1.schema.yaml:/"):
        validate_annotations(schemas, inventory)


def test_annotation_lint_accepts_described_non_union_schema(tmp_path):
    schemas, inventory = _files(tmp_path, "description: Project document\ntype: object\nproperties:\n  project: {description: Project metadata, type: object}\n")

    validate_annotations(schemas, inventory)


def test_annotation_lint_does_not_treat_properties_map_as_a_schema_node(tmp_path):
    schemas, inventory = _files(
        tmp_path,
        "description: Project document\ntype: object\nproperties:\n  type: {description: Form selector, type: string}\n",
    )

    validate_annotations(schemas, inventory)


def test_annotation_lint_rejects_invalid_union_example(tmp_path):
    schema = "description: Project document\ntype: object\nexamples: [invalid]\nanyOf:\n  - {description: Integer form, type: integer}\n  - {description: Boolean form, type: boolean}\n"
    schemas, inventory = _files(tmp_path, schema)

    with pytest.raises(SchemaAnnotationError, match="E_SCHEMA_ANNOTATION_INVALID_EXAMPLE:project-v0.1.schema.yaml:/examples/0"):
        validate_annotations(schemas, inventory)


def test_annotation_lint_requires_a_conditional_form_example(tmp_path):
    schema = "description: Project document\ntype: object\nallOf:\n  - if: {properties: {mode: {const: fixed}}}\n    then: {required: [at]}\n"
    schemas, inventory = _files(tmp_path, schema)

    with pytest.raises(SchemaAnnotationError, match="E_SCHEMA_ANNOTATION_DESCRIPTION:project-v0.1.schema.yaml:/allOf/0"):
        validate_annotations(schemas, inventory)


def test_annotation_lint_requires_a_pattern_example(tmp_path):
    schemas, inventory = _files(
        tmp_path,
        "description: Project document\ntype: object\nproperties:\n  id: {description: Stable identifier, type: string, pattern: '^[a-z]+$'}\n",
    )

    with pytest.raises(SchemaAnnotationError, match="E_SCHEMA_ANNOTATION_EXAMPLE:project-v0.1.schema.yaml:/properties/id"):
        validate_annotations(schemas, inventory)
