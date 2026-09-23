"""Lint author-facing JSON Schema annotations in the live schema inventory."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Iterator

import yaml

from tools.schema_inventory import validate_inventory


class SchemaAnnotationError(ValueError):
    """A live schema lacks a required author-facing annotation."""


def annotation_paths(value: Any, path: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], dict[str, Any]]]:
    """Yield reachable authored choice nodes, excluding bare reference wrappers."""
    if not isinstance(value, dict):
        if isinstance(value, list):
            for index, item in enumerate(value):
                yield from annotation_paths(item, (*path, str(index)))
        return
    authored = any(key in value for key in ("type", "properties", "required", "enum", "const", "oneOf", "anyOf", "pattern", "items"))
    if authored and not (set(value) <= {"$ref", "description"}):
        yield path, value
    for key, item in value.items():
        if key in {"$schema", "$id", "title", "description", "examples", "default", "if", "then", "else", "allOf", "not"}:
            continue
        yield from annotation_paths(item, (*path, str(key)))


def pointer(path: tuple[str, ...]) -> str:
    return "/" + "/".join(part.replace("~", "~0").replace("/", "~1") for part in path) if path else "/"


def validate_annotations(schema_root: Path, inventory_path: Path) -> None:
    for entry in validate_inventory(schema_root, inventory_path):
        if entry["state"] != "live":
            continue
        schema = yaml.safe_load((schema_root / entry["file"]).read_text(encoding="utf-8"))
        for path, node in annotation_paths(schema):
            description = node.get("description")
            if not isinstance(description, str) or not description.strip():
                raise SchemaAnnotationError(f"E_SCHEMA_ANNOTATION_DESCRIPTION:{entry['file']}:{pointer(path)}")
            if any(key in node for key in ("oneOf", "anyOf")):
                examples = node.get("examples")
                if not isinstance(examples, list) or not examples:
                    raise SchemaAnnotationError(f"E_SCHEMA_ANNOTATION_EXAMPLE:{entry['file']}:{pointer(path)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schemas", type=Path, default=Path("schemas"))
    parser.add_argument("--inventory", type=Path, default=Path("schemas/schema-inventory-v0.1.yaml"))
    args = parser.parse_args()
    validate_annotations(args.schemas, args.inventory)


if __name__ == "__main__":
    main()
