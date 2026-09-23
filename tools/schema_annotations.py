"""Lint author-facing JSON Schema annotations in the live schema inventory."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Iterator

import yaml
from jsonschema import Draft202012Validator

from tools.schema_inventory import validate_inventory


class SchemaAnnotationError(ValueError):
    """A live schema lacks a required author-facing annotation."""


def annotation_paths(value: Any, path: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], dict[str, Any]]]:
    """Yield authorable schema nodes, never schema-map container dictionaries."""
    if not isinstance(value, dict):
        return
    authored = any(key in value for key in ("type", "properties", "required", "enum", "const", "oneOf", "anyOf", "pattern", "items"))
    if authored and not (set(value) <= {"$ref", "description"}):
        yield path, value

    for key in ("properties", "patternProperties", "$defs", "definitions", "dependentSchemas"):
        children = value.get(key)
        if isinstance(children, dict):
            for name, child in children.items():
                yield from annotation_paths(child, (*path, key, str(name)))

    for key in ("items", "additionalProperties", "contains"):
        child = value.get(key)
        if isinstance(child, dict):
            yield from annotation_paths(child, (*path, key))
        elif isinstance(child, list):
            for index, item in enumerate(child):
                yield from annotation_paths(item, (*path, key, str(index)))

    for key in ("oneOf", "anyOf"):
        children = value.get(key)
        if isinstance(children, list):
            for index, child in enumerate(children):
                yield from annotation_paths(child, (*path, key, str(index)))


def pointer(path: tuple[str, ...]) -> str:
    return "/" + "/".join(part.replace("~", "~0").replace("/", "~1") for part in path) if path else "/"


def validate_annotations(schema_root: Path, inventory_path: Path) -> None:
    for entry in validate_inventory(schema_root, inventory_path):
        if entry["state"] != "live":
            continue
        schema = yaml.safe_load((schema_root / entry["file"]).read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        for path, node in annotation_paths(schema):
            description = node.get("description")
            if not isinstance(description, str) or not description.strip():
                raise SchemaAnnotationError(f"E_SCHEMA_ANNOTATION_DESCRIPTION:{entry['file']}:{pointer(path)}")
            if any(key in node for key in ("oneOf", "anyOf")):
                examples = node.get("examples")
                if not isinstance(examples, list) or not examples:
                    raise SchemaAnnotationError(f"E_SCHEMA_ANNOTATION_EXAMPLE:{entry['file']}:{pointer(path)}")
                for index, example in enumerate(examples):
                    if list(validator.descend(example, node)):
                        example_path = f"{pointer(path).rstrip('/')}/examples/{index}"
                        raise SchemaAnnotationError(
                            f"E_SCHEMA_ANNOTATION_INVALID_EXAMPLE:{entry['file']}:{example_path}"
                        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schemas", type=Path, default=Path("schemas"))
    parser.add_argument("--inventory", type=Path, default=Path("schemas/schema-inventory-v0.1.yaml"))
    args = parser.parse_args()
    validate_annotations(args.schemas, args.inventory)


if __name__ == "__main__":
    main()
