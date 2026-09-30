from pathlib import Path

import pytest
import yaml

from tools.schema_inventory import (
    SchemaInventoryError, validate_inventory, validate_version_evolution,
)


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


def _live_root(root: Path, schema: dict) -> tuple[Path, Path]:
    schemas, inventory = _write(root, """version: chrona/schema-inventory/v0.1
schemas:
  - file: project-v0.1.schema.yaml
    kind: project
    state: live
    consumers: [src/chrona/core/validation.py]
""")
    (schemas / "project-v0.1.schema.yaml").write_text(yaml.safe_dump(schema))
    return schemas, inventory


@pytest.mark.parametrize("reference", [
    "urn:chrona:not-registered-v0.1#/$defs/x",   # a part missing from the registry
    "urn:chrona:presentation-resource-v0.1#/$defs/noSuchDefinition",  # registered, pointer nowhere
    "#/$defs/missing",                            # local pointer nowhere
])
def test_static_gate_rejects_an_unresolved_reference_without_any_document(tmp_path, reference):
    schemas, inventory = _live_root(tmp_path, {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "timeline/project-v0.1",
        "properties": {"a": {"$ref": reference}},
    })
    with pytest.raises(SchemaInventoryError, match="E_SCHEMA_REF_UNRESOLVED"):
        validate_inventory(schemas, inventory)


def test_static_gate_accepts_resolvable_local_and_part_references(tmp_path):
    schemas, inventory = _live_root(tmp_path, {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "timeline/project-v0.1",
        "$defs": {"x": {"type": "string"}},
        "properties": {"a": {"$ref": "#/$defs/x"}, "b": {"$ref": "urn:chrona:revision-store-resource-ref-v0.1"},
                       "c": {"$ref": "timeline/project-v0.1#/$defs/x"}},
    })
    validate_inventory(schemas, inventory)


def test_static_gate_ignores_transitioning_schemas(tmp_path):
    schemas, inventory = _live_root(tmp_path, {"properties": {"a": {"$ref": "urn:chrona:absent"}}})
    (schemas / "project-v0.2.schema.yaml").write_text("{}")
    inventory.write_text("""version: chrona/schema-inventory/v0.1
schemas:
  - {file: project-v0.1.schema.yaml, kind: project, state: transitioning, consumers: [x], successor: project-v0.2.schema.yaml, removalSlice: I1}
  - {file: project-v0.2.schema.yaml, kind: project, state: live, consumers: [x]}
""")
    validate_inventory(schemas, inventory)


def _evolution_pair(root: Path, *, old_version: str = "v0.28", new_version: str = "v0.29",
                    mutate=None, with_examples: bool = False):
    schemas = root / "schemas"
    schemas.mkdir()

    def document(version):
        schema = {
            "$id": f"https://chrona.dev/schemas/view-{version}.schema.yaml",
            "title": f"Chrona View {version}",
            "type": "object", "additionalProperties": False,
            "required": ["version", "body"],
            "properties": {
                "version": {"const": f"chrona/view/{version}"},
                "body": {"type": "object", "additionalProperties": False,
                         "required": ["existing"],
                         "properties": {"existing": {"type": "string"},
                                        "settings": {"type": "object", "properties":
                                                     {"original": {"type": "integer"}}}}},
            },
        }
        if with_examples:
            schema["examples"] = [{"version": f"chrona/view/{version}", "body": {"existing": "x"}}]
        return schema

    before, after = document(old_version), document(new_version)
    if mutate is not None:
        mutate(after)
    old_name = f"view-{old_version}.schema.yaml"
    new_name = f"view-{new_version}.schema.yaml"
    (schemas / old_name).write_text(yaml.safe_dump(before), encoding="utf-8")
    (schemas / new_name).write_text(yaml.safe_dump(after), encoding="utf-8")
    entries = ({"file": old_name, "kind": "view", "state": "transitioning",
                "successor": new_name, "consumers": ["test"], "removalSlice": "test"},
               {"file": new_name, "kind": "view", "state": "live", "consumers": ["test"]})
    return schemas, entries


def test_additive_optional_version_bump_fails_with_nested_and_multiple_fields(tmp_path):
    def add(schema):
        body = schema["properties"]["body"]["properties"]
        body["first"] = {"type": "string"}
        body["second"] = {"type": "object", "properties": {"nested": {"type": "integer"}}}

    schemas, entries = _evolution_pair(tmp_path, mutate=add)
    with pytest.raises(SchemaInventoryError, match="E_SCHEMA_ADDITIVE_BUMP"):
        validate_version_evolution(schemas, entries)


def test_nested_optional_bump_fails_through_registered_inventory_check(tmp_path):
    def add(schema):
        settings = schema["properties"]["body"]["properties"]["settings"]
        settings["properties"]["nested"] = {"type": "boolean"}

    schemas, entries = _evolution_pair(tmp_path, mutate=add)
    inventory = tmp_path / "inventory.yaml"
    inventory.write_text(yaml.safe_dump({"version": "chrona/schema-inventory/v0.1",
                                         "schemas": list(entries)}), encoding="utf-8")
    with pytest.raises(SchemaInventoryError, match="E_SCHEMA_ADDITIVE_BUMP"):
        validate_inventory(schemas, inventory)


def test_root_example_version_is_identity_but_other_example_changes_are_not(tmp_path):
    def add(schema):
        schema["properties"]["body"]["properties"]["optional"] = {"type": "string"}

    schemas, entries = _evolution_pair(tmp_path, mutate=add, with_examples=True)
    with pytest.raises(SchemaInventoryError, match="E_SCHEMA_ADDITIVE_BUMP"):
        validate_version_evolution(schemas, entries)
    path = schemas / entries[1]["file"]
    changed = yaml.safe_load(path.read_text())
    changed["examples"][0]["body"]["existing"] = "changed"
    path.write_text(yaml.safe_dump(changed), encoding="utf-8")
    validate_version_evolution(schemas, entries)


@pytest.mark.parametrize("mutate", [
    lambda schema: schema["properties"]["body"]["required"].append("optional"),
    lambda schema: schema["properties"]["body"]["properties"].pop("existing"),
    lambda schema: schema["properties"]["body"]["properties"]["existing"].update(type="integer"),
    lambda schema: schema["properties"]["body"]["properties"]["existing"].update(default="new"),
    lambda schema: schema["properties"]["body"].update(maxProperties=5),
])
def test_incompatible_transition_is_not_misclassified_as_additive(tmp_path, mutate):
    def change(schema):
        schema["properties"]["body"]["properties"]["optional"] = {"type": "string"}
        mutate(schema)

    schemas, entries = _evolution_pair(tmp_path, mutate=change)
    validate_version_evolution(schemas, entries)


def test_ambiguous_optional_property_fails_closed(tmp_path):
    def add(schema):
        body = schema["properties"]["body"]
        body["properties"]["optional"] = {"type": "string"}
        body["dependentRequired"] = {"existing": ["optional"]}

    schemas, entries = _evolution_pair(tmp_path, mutate=add)
    old_path = schemas / entries[0]["file"]
    before = yaml.safe_load(old_path.read_text())
    before["properties"]["body"]["dependentRequired"] = {"existing": ["optional"]}
    old_path.write_text(yaml.safe_dump(before), encoding="utf-8")
    with pytest.raises(SchemaInventoryError, match="E_SCHEMA_EVOLUTION_UNSUPPORTED"):
        validate_version_evolution(schemas, entries)


def test_published_historical_inventory_remains_valid():
    root = Path(__file__).resolve().parents[3]
    validate_inventory(root / "schemas", root / "schemas/schema-inventory-v0.1.yaml")
