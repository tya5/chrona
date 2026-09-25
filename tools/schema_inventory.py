"""Validate the explicit lifecycle inventory for packaged schema resources."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from chrona.resources import safe_load


SCHEMA_SUFFIXES = (".schema.yaml", ".schema.json")
STATES = frozenset({"live", "transitioning"})


class SchemaInventoryError(ValueError):
    """The checked-in schema inventory is incomplete or internally inconsistent."""


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
    return entries


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schemas", type=Path, default=Path("schemas"))
    parser.add_argument("--inventory", type=Path, default=Path("schemas/schema-inventory-v0.1.yaml"))
    args = parser.parse_args()
    validate_inventory(args.schemas, args.inventory)


if __name__ == "__main__":
    main()
