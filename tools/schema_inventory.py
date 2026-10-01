"""Validate the explicit lifecycle inventory for packaged schema resources."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterator

from referencing import Registry, Resource
from referencing.exceptions import Unresolvable
from referencing.jsonschema import DRAFT202012

from chrona.resources import SCHEMA_PARTS, safe_load, schema_registry


SCHEMA_SUFFIXES = (".schema.yaml", ".schema.json")
STATES = frozenset({"live", "transitioning"})
EVOLUTION_BASELINE = {"view": (0, 28), "layout-profile": (0, 9), "project": (0, 7)}
_VERSION = re.compile(r"v(\d+)\.(\d+)")
_ANNOTATIONS = frozenset({"title", "description", "examples", "default", "deprecated", "readOnly", "writeOnly", "$comment"})
_SCHEMA_VALUED = frozenset({
    "items", "additionalProperties", "contains", "not", "if", "then", "else", "propertyNames",
    "unevaluatedItems", "unevaluatedProperties", "contentSchema",
})
_SCHEMA_LISTS = frozenset({"allOf", "anyOf", "oneOf", "prefixItems"})
_SCHEMA_MAPS = frozenset({"properties", "patternProperties", "dependentSchemas", "$defs"})
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
ROOT_DEFINITION = "#"


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


def _without_annotations(schema: Any) -> Any:
    """Drop annotation keywords from a schema, leaving property names and data values alone."""
    if not isinstance(schema, dict):
        return schema
    out: dict[str, Any] = {}
    for key, value in schema.items():
        if key in _ANNOTATIONS:
            continue
        if key in _SCHEMA_VALUED:
            out[key] = (
                [_without_annotations(item) for item in value] if isinstance(value, list) else _without_annotations(value)
            )
        elif key in _SCHEMA_LISTS and isinstance(value, list):
            out[key] = [_without_annotations(item) for item in value]
        elif key in _SCHEMA_MAPS and isinstance(value, dict):
            out[key] = {name: _without_annotations(item) for name, item in value.items()}
        else:
            out[key] = value
    return out


def definition_digest(definition: Any) -> str:
    """Canonical digest of one definition's meaning; annotations (wording) do not count."""
    text = json.dumps(_without_annotations(definition), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_frozen_definitions(schema_root: Path, entries: tuple[dict[str, Any], ...]) -> None:
    """Fail when a published part definition changed or vanished, or a part has no frozen digests.

    A part is frozen once published: changing or removing a definition is a new part version.
    Adding a definition is allowed, so only the digests the entry records are checked.
    """
    part_entries = {entry["file"]: entry for entry in entries if entry["file"] in SCHEMA_PARTS}
    for name in SCHEMA_PARTS:
        entry = part_entries.get(name)
        if entry is None or entry["state"] != "live" or not entry.get("frozenDefs"):
            raise SchemaInventoryError(f"E_SCHEMA_PART_UNFROZEN:{name}")
    for entry in entries:
        frozen = entry.get("frozenDefs")
        if frozen is None:
            continue
        if entry["file"] not in SCHEMA_PARTS:
            raise SchemaInventoryError(f"E_SCHEMA_INVENTORY_FROZEN_SCOPE:{entry['file']}")
        schema = safe_load((schema_root / entry["file"]).read_bytes())
        definitions = schema.get("$defs") if isinstance(schema, dict) else None
        for def_name, digest in frozen.items():
            # "#" freezes the whole document, for a part that is one schema with no `$defs`.
            target = schema if def_name == ROOT_DEFINITION else (definitions or {}).get(def_name)
            if not isinstance(target, dict):
                raise SchemaInventoryError(f"E_SCHEMA_PART_FROZEN:{entry['file']}:{def_name}:removed")
            if definition_digest(target) != digest:
                raise SchemaInventoryError(f"E_SCHEMA_PART_FROZEN:{entry['file']}:{def_name}:changed")


def _version_constants(schema: Any) -> Iterator[str]:
    """The document `version` strings a schema pins; a loader may select the schema by one of them."""
    if isinstance(schema, dict):
        version = (schema.get("properties") or {}).get("version") if isinstance(schema.get("properties"), dict) else None
        if isinstance(version, dict) and isinstance(version.get("const"), str):
            yield version["const"]
        for key, value in schema.items():
            if key != "properties":
                yield from _version_constants(value)
    elif isinstance(schema, list):
        for item in schema:
            yield from _version_constants(item)


def validate_consumers(repo_root: Path, schema_root: Path, entries: tuple[dict[str, Any], ...]) -> None:
    """Every consumer of a live entry exists and names the schema file, its kind, a version it pins, or a part it resolves."""
    part_ids: dict[str, str] = {}
    for name in SCHEMA_PARTS:
        part = safe_load((schema_root / name).read_bytes())
        if isinstance(part, dict) and isinstance(part.get("$id"), str):
            part_ids[part["$id"]] = name
    for entry in entries:
        if entry["state"] != "live":
            continue
        schema = safe_load((schema_root / entry["file"]).read_bytes())
        names = {entry["file"], entry["kind"], *_version_constants(schema)}
        for reference in _references(schema):
            part = part_ids.get(reference.partition("#")[0])
            if part is not None:
                names.add(part)
        for consumer in entry["consumers"]:
            path = repo_root / consumer
            if not path.is_file():
                raise SchemaInventoryError(f"E_SCHEMA_INVENTORY_CONSUMER_MISSING:{entry['file']}:{consumer}")
            text = path.read_text(encoding="utf-8")
            if not any(name in text for name in names):
                raise SchemaInventoryError(f"E_SCHEMA_INVENTORY_CONSUMER_STALE:{entry['file']}:{consumer}")


def _references(node: Any) -> Iterator[str]:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                yield value
            else:
                yield from _references(value)
    elif isinstance(node, list):
        for item in node:
            yield from _references(item)


def validate_schema_references(
    schema_root: Path, entries: tuple[dict[str, Any], ...], registry: Registry | None = None,
) -> None:
    """Resolve every `$ref` of every live schema against the part registry, without any input.

    A URN reference is otherwise looked up lazily, so an unregistered part would fail
    only for a document that reaches the reference.
    """
    registry = schema_registry() if registry is None else registry
    for entry in entries:
        if entry["state"] != "live":
            continue
        schema = safe_load((schema_root / entry["file"]).read_bytes())
        if not isinstance(schema, dict):
            continue
        base = schema.get("$id", "")
        base = base if isinstance(base, str) else ""
        resolver = registry.with_resource(base, Resource.from_contents(schema, default_specification=DRAFT202012)).resolver(base)
        for reference in _references(schema):
            try:
                resolver.lookup(reference)
            except Unresolvable as error:
                raise SchemaInventoryError(f"E_SCHEMA_REF_UNRESOLVED:{entry['file']}:{reference}") from error


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
        frozen = entry.get("frozenDefs")
        if frozen is not None and (
            state != "live" or not isinstance(frozen, dict) or not frozen
            or not all(isinstance(key, str) and isinstance(value, str) and _DIGEST.fullmatch(value) for key, value in frozen.items())
        ):
            raise SchemaInventoryError("E_SCHEMA_INVENTORY_FROZEN")
        seen.add(name)
        normalized.append(entry)
    return tuple(normalized)


def validate_inventory(
    schema_root: Path, inventory_path: Path, repo_root: Path | None = None,
) -> tuple[dict[str, Any], ...]:
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
    # A frozen part is never edited in place, so a new part version is published beside its
    # predecessor and both stay live while a transitioning schema or a reader still references
    # the old one (#710: `revision-store-resource-ref` v0.1 and v0.2). Only parts may coexist.
    duplicates = {kind: files for kind, files in live_by_kind.items()
                  if len(files) > 1 and not all(name in SCHEMA_PARTS for name in files)}
    if duplicates:
        raise SchemaInventoryError(f"E_SCHEMA_INVENTORY_DUPLICATE_LIVE:{duplicates}")
    validate_version_evolution(schema_root, entries)
    validate_schema_references(schema_root, entries)
    if all((schema_root / name).is_file() for name in SCHEMA_PARTS):
        validate_frozen_definitions(schema_root, entries)
    if repo_root is not None:
        validate_consumers(repo_root, schema_root, entries)
    return entries


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schemas", type=Path, default=Path("schemas"))
    parser.add_argument("--inventory", type=Path, default=Path("schemas/schema-inventory-v0.1.yaml"))
    args = parser.parse_args()
    validate_inventory(args.schemas, args.inventory, repo_root=args.schemas.resolve().parent)


if __name__ == "__main__":
    main()
