from pathlib import Path

import pytest

from tools.schema_inventory import SchemaInventoryError, validate_inventory


def _write(root: Path, text: str) -> tuple[Path, Path]:
    schemas = root / "schemas"; schemas.mkdir()
    (schemas / "project-v0.1.schema.yaml").write_text("{}")
    inventory = root / "inventory.yaml"; inventory.write_text(text)
    return schemas, inventory


def test_inventory_requires_exact_schema_coverage(tmp_path):
    schemas, inventory = _write(tmp_path, "version: chrona/schema-inventory/v0.1\nschemas: []\n")
    with pytest.raises(SchemaInventoryError, match="E_SCHEMA_INVENTORY_COVERAGE"):
        validate_inventory(schemas, inventory)


def test_transition_requires_successor_and_removal_slice(tmp_path):
    schemas, inventory = _write(tmp_path, """version: chrona/schema-inventory/v0.1
schemas:
  - file: project-v0.1.schema.yaml
    kind: project
    state: transitioning
    consumers: [src/chrona/core/validation.py]
""")
    with pytest.raises(SchemaInventoryError, match="E_SCHEMA_INVENTORY_TRANSITION"):
        validate_inventory(schemas, inventory)


def test_inventory_rejects_multiple_live_versions_for_one_kind(tmp_path):
    schemas, inventory = _write(tmp_path, """version: chrona/schema-inventory/v0.1
schemas:
  - file: project-v0.1.schema.yaml
    kind: project
    state: live
    consumers: [src/chrona/core/validation.py]
""")
    (schemas / "project-v0.2.schema.yaml").write_text("{}")
    inventory.write_text("""version: chrona/schema-inventory/v0.1
schemas:
  - file: project-v0.1.schema.yaml
    kind: project
    state: live
    consumers: [src/chrona/core/validation.py]
  - file: project-v0.2.schema.yaml
    kind: project
    state: live
    consumers: [conformance/validate_datetime_project.py]
""")
    with pytest.raises(SchemaInventoryError, match="E_SCHEMA_INVENTORY_DUPLICATE_LIVE"):
        validate_inventory(schemas, inventory)
