from pathlib import Path

import pytest

from tools.validate_schema_references import SchemaReferenceError, validate_specifications


def _root(tmp_path: Path, text: str) -> tuple[Path, Path, Path]:
    schemas = tmp_path / "schemas"; schemas.mkdir()
    (schemas / "project.schema.yaml").write_text("properties:\n  version: {const: timeline/v0.7}\n")
    inventory = tmp_path / "inventory.yaml"
    inventory.write_text("version: chrona/schema-inventory/v0.1\nschemas:\n  - file: project.schema.yaml\n    kind: project\n    state: live\n    consumers: [src/chrona/core/validation.py]\n")
    specs = tmp_path / "specs"; specs.mkdir(); (specs / "01.md").write_text(text)
    return specs, schemas, inventory


def test_current_reference_must_be_live(tmp_path):
    specs, schemas, inventory = _root(tmp_path, "# chrona-contract: current\nversion: timeline/v0.7\n")
    validate_specifications(specs, schemas, inventory)


def test_current_reference_accepts_version_in_composed_root(tmp_path):
    specs, schemas, inventory = _root(tmp_path, "# chrona-contract: current\nversion: chrona/style/v0.2\n")
    (schemas / "project.schema.yaml").write_text(
        "allOf:\n"
        "  - type: object\n"
        "  - allOf:\n"
        "      - properties:\n"
        "          version: {const: chrona/style/v0.2}\n"
    )
    validate_specifications(specs, schemas, inventory)


def test_version_in_nested_resource_is_not_a_root_contract(tmp_path):
    specs, schemas, inventory = _root(tmp_path, "# chrona-contract: current\nversion: nested/v0.1\n")
    (schemas / "project.schema.yaml").write_text(
        "$defs:\n  nested:\n    properties:\n      version: {const: nested/v0.1}\n"
    )
    with pytest.raises(SchemaReferenceError, match="E_SCHEMA_REFERENCE_STALE"):
        validate_specifications(specs, schemas, inventory)


def test_unclassified_reference_is_rejected(tmp_path):
    specs, schemas, inventory = _root(tmp_path, "version: timeline/v0.7\n")
    with pytest.raises(SchemaReferenceError, match="E_SCHEMA_REFERENCE_UNCLASSIFIED"):
        validate_specifications(specs, schemas, inventory)


def test_stale_current_reference_is_rejected(tmp_path):
    specs, schemas, inventory = _root(tmp_path, "# chrona-contract: current\nversion: timeline/v0.5\n")
    with pytest.raises(SchemaReferenceError, match="E_SCHEMA_REFERENCE_STALE"):
        validate_specifications(specs, schemas, inventory)
