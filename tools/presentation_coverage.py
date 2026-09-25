#!/usr/bin/env python3
"""Generate non-gating presentation vocabulary and realized-slot evidence."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
import tempfile
from typing import Any, Iterable, Mapping

import yaml


class PresentationCoverageError(ValueError):
    """Declared presentation evidence cannot be used for coverage."""


KINDS = ("view", "layout-profile", "theme", "color-scheme")


@dataclass(frozen=True)
class Slide:
    identifier: str
    root: Path
    resources: tuple[tuple[str, Path, Mapping[str, Any]], ...]
    scene: Path


@dataclass(frozen=True, order=True)
class Value:
    kind: str
    path: tuple[str, ...]
    value: str


def _load(path: Path) -> Mapping[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise PresentationCoverageError(f"E_PRESENTATION_COVERAGE_LOAD:{path}") from error
    if not isinstance(value, Mapping):
        raise PresentationCoverageError(f"E_PRESENTATION_COVERAGE_DOCUMENT:{path}")
    return value


def _inside(root: Path, address: object) -> Path:
    if not isinstance(address, str) or not address:
        raise PresentationCoverageError("E_PRESENTATION_COVERAGE_REFERENCE")
    path = (root / address).resolve()
    if root.resolve() not in path.parents or not path.is_file():
        raise PresentationCoverageError(f"E_PRESENTATION_COVERAGE_REFERENCE:{address}")
    return path


def discover(root: Path) -> tuple[Slide, ...]:
    """Return every declared slide with its presentation closure and Scene."""
    result: list[Slide] = []
    for manifest_path in sorted((root / "examples").glob("*/manifest.yaml")):
        manifest, example = _load(manifest_path), manifest_path.parent.resolve()
        if manifest.get("role") != "regression-corpus" or not isinstance(manifest.get("id"), str):
            raise PresentationCoverageError(f"E_PRESENTATION_COVERAGE_MANIFEST:{manifest_path}")
        default = manifest.get("context")
        for item in manifest.get("slides", ()):
            if not isinstance(item, Mapping) or not isinstance(item.get("id"), str):
                raise PresentationCoverageError(f"E_PRESENTATION_COVERAGE_MANIFEST:{manifest_path}")
            context = _load(_inside(example, item.get("context", default)))
            body = context.get("body")
            if not isinstance(body, Mapping):
                raise PresentationCoverageError(f"E_PRESENTATION_COVERAGE_CONTEXT:{item['id']}")
            resources = []
            for key, kind in (("view", "view"), ("layout", "layout-profile"),
                              ("theme", "theme"), ("colorScheme", "color-scheme")):
                ref = body.get(key)
                if not isinstance(ref, Mapping) or ref.get("kind") != kind:
                    raise PresentationCoverageError(f"E_PRESENTATION_COVERAGE_CONTEXT:{item['id']}:{key}")
                resources.append((kind, _inside(example, ref.get("address")), _load(_inside(example, ref.get("address")))))
            scene = _inside(example, item.get("expectedScene"))
            result.append(Slide(f"{manifest['id']}/{item['id']}", example, tuple(resources), scene))
    return tuple(result)


def _pointer(schema: Mapping[str, Any], reference: str) -> Mapping[str, Any] | None:
    if not reference.startswith("#/"):
        return None
    value: Any = schema
    for part in reference[2:].split("/"):
        value = value.get(part.replace("~1", "/").replace("~0", "~")) if isinstance(value, Mapping) else None
    return value if isinstance(value, Mapping) else None


def _schema_values(schema: Mapping[str, Any], node: Mapping[str, Any] | None = None,
                   path: tuple[str, ...] = (), seen: frozenset[str] = frozenset()) -> Iterable[tuple[tuple[str, ...], Any]]:
    node = schema if node is None else node
    reference = node.get("$ref")
    if isinstance(reference, str) and reference not in seen:
        target = _pointer(schema, reference)
        if target is not None:
            yield from _schema_values(schema, target, path, seen | {reference})
    if "const" in node:
        yield path, node["const"]
    if isinstance(node.get("enum"), list):
        yield from ((path, value) for value in node["enum"])
    for key, child in (node.get("properties") or {}).items():
        if isinstance(key, str) and isinstance(child, Mapping):
            yield from _schema_values(schema, child, path + (key,), seen)
    for key, component in (("additionalProperties", "*"), ("items", "[]")):
        child = node.get(key)
        if isinstance(child, Mapping):
                yield from _schema_values(schema, child, path + (component,), seen)
    for key in ("allOf", "anyOf", "oneOf", "prefixItems"):
        for child in node.get(key, ()):
            if isinstance(child, Mapping):
                yield from _schema_values(schema, child, path, seen)
    # Conditional schemas retain their enclosing instance path.  Treating
    # ``then`` as an unrelated schema is what previously hid finite values in
    # Theme token ``value`` objects.
    for key in ("if", "then", "else", "not", "contains"):
        child = node.get(key)
        if isinstance(child, Mapping):
            yield from _schema_values(schema, child, path, seen)
    for child in (node.get("patternProperties") or {}).values():
        if isinstance(child, Mapping):
            yield from _schema_values(schema, child, path + ("*",), seen)
    for child in (node.get("dependentSchemas") or {}).values():
        if isinstance(child, Mapping):
            yield from _schema_values(schema, child, path, seen)


def _values_at(value: Any, path: tuple[str, ...]) -> Iterable[Any]:
    if not path:
        yield value
    elif path[0] == "*" and isinstance(value, Mapping):
        for item in value.values(): yield from _values_at(item, path[1:])
    elif path[0] == "[]" and isinstance(value, list):
        for item in value: yield from _values_at(item, path[1:])
    elif isinstance(value, Mapping) and path[0] in value:
        yield from _values_at(value[path[0]], path[1:])


def live_schemas(root: Path) -> dict[str, Mapping[str, Any]]:
    inventory = _load(root / "schemas/schema-inventory-v0.1.yaml")
    result: dict[str, Mapping[str, Any]] = {}
    for entry in inventory.get("schemas", ()):
        if isinstance(entry, Mapping) and entry.get("state") == "live" and entry.get("kind") in KINDS:
            kind, filename = entry["kind"], entry.get("file")
            if kind in result or not isinstance(filename, str):
                raise PresentationCoverageError("E_PRESENTATION_COVERAGE_SCHEMA")
            result[kind] = _load(root / "schemas" / filename)
    if set(result) != set(KINDS):
        raise PresentationCoverageError("E_PRESENTATION_COVERAGE_SCHEMA")
    return result


def vocabulary(root: Path) -> tuple[Value, ...]:
    return _vocabulary(live_schemas(root))


def _vocabulary(schemas: Mapping[str, Mapping[str, Any]]) -> tuple[Value, ...]:
    rows: set[Value] = set()
    for kind, schema in schemas.items():
        for path, value in _schema_values(schema):
            if isinstance(value, (str, int, float, bool)) or value is None:
                rows.add(Value(kind, path, json.dumps(value, ensure_ascii=False, sort_keys=True)))
    return tuple(sorted(rows))


def _schema_version(schema: Mapping[str, Any]) -> str:
    versions = {value for path, value in _schema_values(schema) if path == ("version",) and isinstance(value, str)}
    if len(versions) != 1:
        raise PresentationCoverageError("E_PRESENTATION_COVERAGE_SCHEMA")
    return versions.pop()


def _validate_resource_versions(slides: Iterable[Slide], schemas: Mapping[str, Mapping[str, Any]]) -> None:
    """Reject corpus evidence that is not governed by the selected live contract."""
    expected = {kind: _schema_version(schema) for kind, schema in schemas.items()}
    for slide in slides:
        for kind, path, document in slide.resources:
            if document.get("version") != expected[kind]:
                raise PresentationCoverageError(
                    f"E_PRESENTATION_COVERAGE_VERSION:{slide.identifier}:{kind}:{path}"
                )


def _scene_slots(path: Path) -> tuple[set[str], set[str]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PresentationCoverageError(f"E_PRESENTATION_COVERAGE_SCENE:{path}") from error
    if document.get("version") != "chrona/scene/v0.2" or document.get("kind") != "scene":
        raise PresentationCoverageError(f"E_PRESENTATION_COVERAGE_SCENE:{path}")
    placed, realized = set(), set()
    for surface in document.get("surfaces", ()):
        if not isinstance(surface, Mapping):
            raise PresentationCoverageError(f"E_PRESENTATION_COVERAGE_SCENE:{path}")
        slots = {item.get("id"): item.get("source") for item in surface.get("slots", ()) if isinstance(item, Mapping)}
        if None in slots:
            raise PresentationCoverageError(f"E_PRESENTATION_COVERAGE_SCENE:{path}")
        placed.update(str(source) for source in slots.values())
        for primitive in surface.get("primitives", ()):
            if not isinstance(primitive, Mapping) or primitive.get("slotId") not in slots:
                raise PresentationCoverageError(f"E_PRESENTATION_COVERAGE_SCENE:{path}")
            realized.add(str(slots[primitive["slotId"]]))
    return placed, realized


def _declared_slots(document: Mapping[str, Any]) -> set[str]:
    """Return Layout-declared slot sources without interpreting placement."""
    result: set[str] = set()
    def walk(value: Any) -> None:
        if isinstance(value, Mapping):
            if value.get("kind") == "slot" and isinstance(value.get("source"), str):
                result.add(value["source"])
            for item in value.values(): walk(item)
        elif isinstance(value, list):
            for item in value: walk(item)
    walk(document)
    return result


def _label(path: tuple[str, ...]) -> str:
    return ".".join(path).replace(".[]", "[]")


def render(root: Path) -> str:
    slides, schemas = discover(root), live_schemas(root)
    _validate_resource_versions(slides, schemas)
    rows = _vocabulary(schemas)
    lines = ["# Presentation vocabulary coverage", "", "Generated by `tools/presentation_coverage.py`; this is a non-gating curation selector, not render validation.", "",
             "## Evidence inputs", "", "- Scene contract: `chrona/scene/v0.2`", "- Corpus slides: " + str(len(slides)),
             "- Live schemas: " + ", ".join(f"`{kind}` = `{_schema_version(schemas[kind])}`" for kind in sorted(schemas)),
             "- Scene artifacts:"]
    lines.extend(f"  - `{slide.scene.relative_to(root)}`" for slide in slides)
    lines.extend(["", "## Finite live-schema vocabulary", "", "| Contract | Schema path | Value | Declared slides |", "| --- | --- | --- | --- |"])
    uncovered = []
    for row in rows:
        evidence = [slide.identifier for slide in slides if any(kind == row.kind and json.loads(row.value) in _values_at(document, row.path) for kind, _path, document in slide.resources)]
        if not evidence: uncovered.append(row)
        lines.append(f"| {row.kind} | `{_label(row.path)}` | `{row.value}` | {', '.join(evidence) or '—'} |")
    lines.extend(["", "## Uncovered presentation vocabulary", ""])
    lines.extend(f"- {row.kind} `{_label(row.path)}` = `{row.value}`" for row in uncovered)
    if not uncovered: lines.append("None.")
    evidence = {state: {} for state in ("declared", "placed", "realized")}
    for slide in slides:
        layout = next(document for kind, _path, document in slide.resources if kind == "layout-profile")
        for value in _declared_slots(layout): evidence["declared"].setdefault(value, []).append(slide.identifier)
        for state, values in zip(("placed", "realized"), _scene_slots(slide.scene), strict=True):
            for value in values: evidence[state].setdefault(value, []).append(slide.identifier)
    sources = sorted(set().union(*(set(value) for value in evidence.values())))
    lines.extend(["", "## Layout slot evidence", "", "| Slot source | Declared | Placed | Realized |", "| --- | --- | --- | --- |"])
    for source in sources:
        lines.append("| `" + source + "` | " + " | ".join(", ".join(evidence[state].get(source, ())) or "—" for state in ("declared", "placed", "realized")) + " |")
    lines.extend(["", "## Declared but never realized slot sources", ""])
    missing = [source for source in sources if evidence["declared"].get(source) and not evidence["realized"].get(source)]
    lines.extend(f"- `{source}`" for source in missing)
    if not missing: lines.append("None.")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--root", type=Path, default=Path(".")); parser.add_argument("--output", type=Path, default=Path("docs/gallery/presentation-coverage.md")); parser.add_argument("--check", action="store_true")
    args = parser.parse_args(); root = args.root.resolve(); output = args.output if args.output.is_absolute() else root / args.output; content = render(root)
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != content: raise SystemExit("E_PRESENTATION_COVERAGE_STALE")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    # Evidence is committed bytes, so generation must not inherit the host
    # platform's newline translation (notably CRLF on Windows).
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=output.parent, delete=False) as temporary:
        temporary.write(content); temporary_path = Path(temporary.name)
    temporary_path.replace(output)


if __name__ == "__main__": main()
