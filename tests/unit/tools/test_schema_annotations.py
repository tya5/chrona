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
    schema = "description: Project document\ntype: object\noneOf: []\noneOf: []\noneOf: []\nanyOf:\n  - {description: Point form, type: object}\n  - {description: Span form, type: object}\n"
    schemas, inventory = _files(tmp_path, schema)

    with pytest.raises(SchemaAnnotationError, match="E_SCHEMA_ANNOTATION_EXAMPLE:project-v0.1.schema.yaml:/"):
        validate_annotations(schemas, inventory)


def test_annotation_lint_accepts_described_non_union_schema(tmp_path):
    schemas, inventory = _files(tmp_path, "description: Project document\ntype: object\nproperties:\n  project: {description: Project metadata, type: object}\n")

    validate_annotations(schemas, inventory)
