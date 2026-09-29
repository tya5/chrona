"""Validate the explicit lifecycle inventory for packaged schema resources."""
from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
import re
from typing import Any

from chrona.resources import safe_load


SCHEMA_SUFFIXES = (".schema.yaml", ".schema.json")
STATES = frozenset({"live", "transitioning"})
EVOLUTION_BASELINE = {"view": (0, 28), "layout-profile": (0, 9), "project": (0, 7)}
_VERSION = re.compile(r"v(\d+)\.(\d+)")


class SchemaInventoryError(ValueError):
    """The checked-in schema inventory is incomplete or internally inconsistent."""


def _version_from_name(filename: str) -> tuple[int, int]:
    match = _VERSION.search(filename)
    if match is None:
        raise SchemaInventoryError(f"E_SCHEMA_EVOLUTION_VERSION:{filename}")
    return int(match[1]), int(match[2])


def _normalized_identity(schema: dict[str, Any], version: tuple[int, int]) -> dict[str, Any]:
    """Erase only the resource's own version metadata, not example content."""
    normalized = deepcopy(schema)
    token = f"v{version[0]}.{version[1]}"
    identity_values: set[str] = set()

    def replace(value: Any) -> Any:
        return re.sub(re.escape(token) + r"(?!\.\d|\d)", "<version>", value) if isinstance(value, str) else value

    for key in ("$id", "title"):
        if key in normalized:
            normalized[key] = replace(normalized[key])

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            properties = node.get("properties")
            if isinstance(properties, dict):
                version_property = properties.get("version")
                if isinstance(version_property, dict) and "const" in version_property:
                    if isinstance(version_property["const"], str):
                        identity_values.add(version_property["const"])
                    version_property["const"] = replace(version_property["const"])
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(normalized)
    examples = normalized.get("examples")
    if isinstance(examples, list):
        for example in examples:
            if (isinstance(example, dict) and isinstance(example.get("version"), str)
                    and example["version"] in identity_values):
                example["version"] = replace(example["version"])
    return normalized


def _additive_only_change(before: Any, after: Any) -> tuple[bool, str | None]:
    """Recognize an entirely optional-property insertion, or report ambiguity."""
    additions: list[tuple[str, dict[str, Any], str]] = []
    incompatible = False

    def compare(old: Any, new: Any, path: str, parent: dict[str, Any] | None = None) -> None:
        nonlocal incompatible
        if type(old) is not type(new):
            incompatible = True
        elif isinstance(old, dict):
            for key in sorted(old.keys() | new.keys()):
                child = f"{path}/{key}"
                if key not in old:
                    if parent is not None and path.endswith("/properties"):
                        additions.append((child, parent, key))
                    else:
                        incompatible = True
                elif key not in new:
                    incompatible = True
                else:
                    compare(old[key], new[key], child, old if key == "properties" else None)
        elif isinstance(old, list):
            if len(old) != len(new):
                incompatible = True
            else:
                for index, (left, right) in enumerate(zip(old, new)):
                    compare(left, right, f"{path}/{index}")
        elif old != new:
            incompatible = True

    compare(before, after, "")
    if incompatible or not additions:
        return False, None
    for path, owner, name in additions:
        if owner.get("type") != "object" or name in owner.get("required", ()):
            return False, path
        if any(key in owner for key in ("allOf", "anyOf", "oneOf", "if", "then", "else", "dependentRequired")):
            return False, path
    return True, None


def validate_version_evolution(schema_root: Path, entries: tuple[dict[str, Any], ...]) -> None:
    """Guard future View/Layout Profile/Project bumps without rewriting history."""
    for entry in entries:
        kind, successor = entry.get("kind"), entry.get("successor")
        if kind not in EVOLUTION_BASELINE or not isinstance(successor, str):
            continue
        after_version = _version_from_name(successor)
        if after_version <= EVOLUTION_BASELINE[kind]:
            continue
        before_version = _version_from_name(entry["file"])
        before = safe_load((schema_root / entry["file"]).read_bytes())
        after = safe_load((schema_root / successor).read_bytes())
        if not isinstance(before, dict) or not isinstance(after, dict):
            raise SchemaInventoryError(f"E_SCHEMA_EVOLUTION_FORMAT:{entry['file']}:{successor}")
        additive_only, ambiguity = _additive_only_change(
            _normalized_identity(before, before_version),
            _normalized_identity(after, after_version),
        )
        if ambiguity:
            raise SchemaInventoryError(f"E_SCHEMA_EVOLUTION_UNSUPPORTED:{successor}:{ambiguity}")
        if additive_only:
            raise SchemaInventoryError(f"E_SCHEMA_ADDITIVE_BUMP:{entry['file']}:{successor}")


def schema_files(schema_root: Path) -> frozenset[str]:
    return frozenset(
        path.name for path in schema_root.iterdir()
        if path.is_file() and path.name.endswith(SCHEMA_SUFFIXES)
    )


def load_inventory(path: Path) -> tuple[dict[str, Any], ...]:
    value = safe_load(path.read_bytes())
    if not isinstance(value, dict) or value.get("version") != "chrona/schema-inventory/v0.1":
        raise SchemaInventoryError("E_SCHEMA_INVENTORY_FORMAT")
    entries = value.get("schemas")
    if not isinstance(entries, list):
        raise SchemaInventoryError("E_SCHEMA_INVENTORY_FORMAT")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise SchemaInventoryError("E_SCHEMA_INVENTORY_FORMAT")
        name, state = entry.get("file"), entry.get("state")
        if not isinstance(name, str) or not name.endswith(SCHEMA_SUFFIXES) or name in seen or state not in STATES:
            raise SchemaInventoryError("E_SCHEMA_INVENTORY_ENTRY")
        consumers = entry.get("consumers")
        if not isinstance(consumers, list) or not consumers or not all(isinstance(item, str) and item for item in consumers):
            raise SchemaInventoryError("E_SCHEMA_INVENTORY_CONSUMER")
        if state == "transitioning":
            if not all(isinstance(entry.get(key), str) and entry[key] for key in ("successor", "removalSlice")):
                raise SchemaInventoryError("E_SCHEMA_INVENTORY_TRANSITION")
        elif "successor" in entry or "removalSlice" in entry:
            raise SchemaInventoryError("E_SCHEMA_INVENTORY_LIVE")
        seen.add(name)
        normalized.append(entry)
    return tuple(normalized)


def validate_inventory(schema_root: Path, inventory_path: Path) -> tuple[dict[str, Any], ...]:
    entries = load_inventory(inventory_path)
    registered = {entry["file"] for entry in entries}
    actual = schema_files(schema_root)
    if actual != registered:
        missing, stale = sorted(actual - registered), sorted(registered - actual)
        raise SchemaInventoryError(f"E_SCHEMA_INVENTORY_COVERAGE:missing={missing};stale={stale}")
    live_by_kind: dict[str, list[str]] = {}
    for entry in entries:
        if entry["state"] == "live":
            kind = str(entry.get("kind", ""))
            if not kind:
                raise SchemaInventoryError("E_SCHEMA_INVENTORY_KIND")
            live_by_kind.setdefault(kind, []).append(entry["file"])
    duplicates = {kind: files for kind, files in live_by_kind.items() if len(files) > 1}
    if duplicates:
        raise SchemaInventoryError(f"E_SCHEMA_INVENTORY_DUPLICATE_LIVE:{duplicates}")
    validate_version_evolution(schema_root, entries)
    return entries


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schemas", type=Path, default=Path("schemas"))
    parser.add_argument("--inventory", type=Path, default=Path("schemas/schema-inventory-v0.1.yaml"))
    args = parser.parse_args()
    validate_inventory(args.schemas, args.inventory)


if __name__ == "__main__":
    main()
