#!/usr/bin/env python3
"""Generate the non-gating semantic-register corpus coverage report."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import tempfile
from typing import Any, Callable, Iterable, Mapping

from chrona.resources import safe_load


class CorpusCoverageError(ValueError):
    """Declared corpus evidence cannot be read as coverage input."""


@dataclass(frozen=True)
class CorpusProject:
    identifier: str
    root: Path
    resources: tuple[tuple[str, Path, Mapping[str, Any]], ...]


@dataclass(frozen=True)
class Probe:
    contract: str
    identifier: str
    predicate: Callable[[CorpusProject], tuple[Path, ...]]


@dataclass(frozen=True, order=True)
class VocabularyValue:
    contract: str
    path: tuple[str, ...]
    value: str


SCHEMA_SOURCES = (
    ("Project", "project", "project-v0.6.schema.yaml"),
    ("Actual set", "actual", "actual-set-v0.2.schema.yaml"),
    ("Snapshot reference", "snapshot", "snapshot-ref-v0.2.schema.yaml"),
    ("Profile package", "extension", "profile-v0.2.schema.yaml"),
)


def _load(path: Path) -> Mapping[str, Any]:
    try:
        value = safe_load(path.read_bytes())
    except (OSError, ValueError) as error:
        raise CorpusCoverageError(f"E_CORPUS_COVERAGE_LOAD:{path}") from error
    if not isinstance(value, Mapping):
        raise CorpusCoverageError(f"E_CORPUS_COVERAGE_DOCUMENT:{path}")
    return value


def _declared_path(project_root: Path, address: Any) -> Path:
    if not isinstance(address, str) or not address:
        raise CorpusCoverageError(f"E_CORPUS_COVERAGE_REFERENCE:{project_root}")
    path = (project_root / address).resolve()
    if project_root.resolve() not in path.parents or not path.is_file():
        raise CorpusCoverageError(f"E_CORPUS_COVERAGE_RESOURCE:{address}")
    return path


def _context_paths(project_root: Path, manifest: Mapping[str, Any]) -> tuple[Path, ...]:
    default, slides = manifest.get("context"), manifest.get("slides")
    if not isinstance(default, str) or not isinstance(slides, list):
        raise CorpusCoverageError(f"E_CORPUS_COVERAGE_MANIFEST:{project_root / 'manifest.yaml'}")
    addresses = {default}
    for slide in slides:
        if not isinstance(slide, Mapping) or not isinstance(slide.get("context", default), str):
            raise CorpusCoverageError(f"E_CORPUS_COVERAGE_MANIFEST:{project_root / 'manifest.yaml'}")
        addresses.add(slide.get("context", default))
    return tuple(_declared_path(project_root, address) for address in sorted(addresses))


def _reference_address(value: Mapping[str, Any], key: str) -> str | None:
    candidate = value.get(key)
    if not isinstance(candidate, Mapping):
        return None
    address = candidate.get("address")
    return address if isinstance(address, str) else None


def discover(root: Path) -> tuple[CorpusProject, ...]:
    """Discover resources named by a corpus manifest, Context, or Project."""
    result: list[CorpusProject] = []
    for manifest_path in sorted((root / "examples").glob("*/manifest.yaml")):
        manifest = _load(manifest_path)
        identifier = manifest.get("id")
        if manifest.get("role") != "regression-corpus" or not isinstance(identifier, str):
            raise CorpusCoverageError(f"E_CORPUS_COVERAGE_MANIFEST:{manifest_path.relative_to(root)}")
        project_root, project_path = manifest_path.parent, manifest_path.parent / "project.yaml"
        project = _load(project_path)
        declared: dict[Path, str] = {project_path.resolve(): "project"}
        for context_path in _context_paths(project_root, manifest):
            context = _load(context_path)
            body = context.get("body")
            inputs = body.get("inputs", {}) if isinstance(body, Mapping) else None
            if not isinstance(inputs, Mapping):
                raise CorpusCoverageError(f"E_CORPUS_COVERAGE_CONTEXT:{context_path.relative_to(root)}")
            for key, kind in (("actual", "actual"), ("snapshot", "snapshot")):
                address = _reference_address(inputs, key)
                if address is not None:
                    declared[_declared_path(project_root, address)] = kind
        extensions = project.get("extensions", [])
        if not isinstance(extensions, list):
            raise CorpusCoverageError(f"E_CORPUS_COVERAGE_EXTENSIONS:{project_path.relative_to(root)}")
        for extension in extensions:
            if not isinstance(extension, Mapping) or not isinstance(extension.get("resource"), Mapping):
                raise CorpusCoverageError(f"E_CORPUS_COVERAGE_EXTENSIONS:{project_path.relative_to(root)}")
            address = _reference_address(extension, "resource")
            if address is not None:
                declared[_declared_path(project_root, address)] = "extension"
        result.append(CorpusProject(identifier, project_root, tuple(
            (kind, path, _load(path)) for path, kind in sorted(declared.items()))))
    return tuple(result)


def _walk(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def _resource_paths(project: CorpusProject, kind: str, condition: Callable[[Mapping[str, Any]], bool]) -> tuple[Path, ...]:
    return tuple(path for resource_kind, path, value in project.resources
                 if resource_kind == kind and any(condition(item) for item in _walk(value)))


def _project_objects(project: CorpusProject) -> Iterable[Mapping[str, Any]]:
    for kind, _path, value in project.resources:
        if kind == "project" and isinstance(value.get("objects"), Mapping):
            yield from (item for item in value["objects"].values() if isinstance(item, Mapping))


def _project_probe(project: CorpusProject, condition: Callable[[Mapping[str, Any]], bool]) -> tuple[Path, ...]:
    return tuple(path for kind, path, _ in project.resources if kind == "project" and any(condition(item) for item in _project_objects(project)))


def _actual_probe(project: CorpusProject, condition: Callable[[Mapping[str, Any]], bool]) -> tuple[Path, ...]:
    return _resource_paths(project, "actual", lambda item: isinstance(item.get("actual"), Mapping) and condition(item["actual"]))


def _negative_lag(project: CorpusProject) -> tuple[Path, ...]:
    return tuple(path for kind, path, value in project.resources if kind == "project" and any(
        isinstance(item, Mapping) and (isinstance(item.get("lag"), str) and item["lag"].startswith("-")
        or isinstance(item.get("lag"), Mapping) and isinstance(item["lag"].get("value"), str) and item["lag"]["value"].startswith("-"))
        for item in _walk(value)))


PROBES = (
    Probe("Project", "deadline", lambda p: _project_probe(p, lambda o: "deadline" in o)),
    Probe("Project", "constraints", lambda p: _project_probe(p, lambda o: isinstance(o.get("schedule"), Mapping) and "constraints" in o["schedule"])),
    Probe("Project", "negative-lag", _negative_lag),
    Probe("Project", "hierarchy", lambda p: _project_probe(p, lambda o: "parent" in o or "wbsCode" in o)),
    Probe("Project", "scenario-relation-edit", lambda p: _resource_paths(p, "project", lambda x: "remove" in x or "add" in x)),
    Probe("Actual", "point-observation", lambda p: _actual_probe(p, lambda a: "at" in a)),
    Probe("Actual", "in-flight-observation", lambda p: _actual_probe(p, lambda a: "start" in a and "progress" in a and "finish" not in a)),
    Probe("Actual", "progress", lambda p: _actual_probe(p, lambda a: "progress" in a)),
    Probe("Snapshot", "pinned-snapshot", lambda p: tuple(path for kind, path, _ in p.resources if kind == "snapshot")),
    Probe("Extension", "declared-profile-package", lambda p: tuple(path for kind, path, _ in p.resources if kind == "extension")),
    Probe("Extension", "typed-field", lambda p: _resource_paths(p, "extension", lambda x: "fields" in x)),
)


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
    properties = node.get("properties")
    if isinstance(properties, Mapping):
        for key, child in properties.items():
            if isinstance(key, str) and isinstance(child, Mapping):
                yield from _schema_values(schema, child, path + (key,), seen)
    additional, items = node.get("additionalProperties"), node.get("items")
    if isinstance(additional, Mapping):
        yield from _schema_values(schema, additional, path + ("*",), seen)
    if isinstance(items, Mapping):
        yield from _schema_values(schema, items, path + ("[]",), seen)
    for keyword in ("allOf", "anyOf", "oneOf"):
        if isinstance(node.get(keyword), list):
            for branch in node[keyword]:
                if isinstance(branch, Mapping):
                    yield from _schema_values(schema, branch, path, seen)


def _values_at(value: Any, path: tuple[str, ...]) -> Iterable[Any]:
    if not path:
        yield value
    elif path[0] == "*" and isinstance(value, Mapping):
        for item in value.values(): yield from _values_at(item, path[1:])
    elif path[0] == "[]" and isinstance(value, list):
        for item in value: yield from _values_at(item, path[1:])
    elif isinstance(value, Mapping) and path[0] in value:
        yield from _values_at(value[path[0]], path[1:])


def vocabulary(root: Path) -> tuple[VocabularyValue, ...]:
    rows: set[VocabularyValue] = set()
    for contract, _kind, filename in SCHEMA_SOURCES:
        for path, value in _schema_values(_load(root / "schemas" / filename)):
            if isinstance(value, (str, int, float, bool)) or value is None:
                rows.add(VocabularyValue(contract, path, json.dumps(value, ensure_ascii=False, sort_keys=True)))
    return tuple(sorted(rows))


def _vocabulary_evidence(project: CorpusProject, row: VocabularyValue) -> tuple[Path, ...]:
    kind = next(kind for contract, kind, _ in SCHEMA_SOURCES if contract == row.contract)
    expected = json.loads(row.value)
    return tuple(path for resource_kind, path, document in project.resources if resource_kind == kind
                 and any(value == expected for value in _values_at(document, row.path)))


def _path_label(path: tuple[str, ...]) -> str:
    return ".".join(path).replace(".[]", "[]")


def render(root: Path) -> str:
    projects = discover(root)
    lines = ["# Corpus coverage", "", "Generated by `tools/corpus_coverage.py`; this is a curation backlog, not a CI coverage gate.", "",
             "## Semantic-register evidence", "", "| Contract | Probe | " + " | ".join(p.identifier for p in projects) + " |",
             "| --- | --- | " + " | ".join("---" for _ in projects) + " |"]
    for probe in PROBES:
        cells = [", ".join(path.relative_to(root).as_posix() for path in probe.predicate(project)) or "—" for project in projects]
        lines.append(f"| {probe.contract} | `{probe.identifier}` | " + " | ".join(cells) + " |")
    uncovered = [probe.identifier for probe in PROBES if not any(probe.predicate(project) for project in projects)]
    lines.extend(["", "## Uncovered register probes", "", ", ".join(f"`{item}`" for item in uncovered) if uncovered else "None.", "",
                  "## Finite-schema vocabulary", "", "Direct `enum` and `const` values from the Project, Actual Set, Snapshot Reference, and Profile Package source schemas. Open maps and non-direct conditional inference are intentionally excluded.", "",
                  "| Contract | Schema path | Value | " + " | ".join(p.identifier for p in projects) + " |",
                  "| --- | --- | --- | " + " | ".join("---" for _ in projects) + " |"])
    uncovered_rows: list[VocabularyValue] = []
    for row in vocabulary(root):
        evidence = [_vocabulary_evidence(project, row) for project in projects]
        if not any(evidence): uncovered_rows.append(row)
        cells = [", ".join(path.relative_to(root).as_posix() for path in paths) or "—" for paths in evidence]
        lines.append(f"| {row.contract} | `{_path_label(row.path)}` | `{row.value}` | " + " | ".join(cells) + " |")
    lines.extend(["", "## Uncovered schema vocabulary", ""])
    lines.extend(f"- {row.contract} `{_path_label(row.path)}` = `{row.value}`" for row in uncovered_rows)
    if not uncovered_rows: lines.append("None.")
    lines.append("")
    return "\n".join(lines)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(".")); parser.add_argument("--output", type=Path, default=Path("docs/examples/corpus-coverage.md")); parser.add_argument("--check", action="store_true")
    args = parser.parse_args(); root = args.root.resolve(); output = args.output if args.output.is_absolute() else root / args.output
    content = render(root)
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != content: raise SystemExit("E_CORPUS_COVERAGE_STALE")
        return
    write(output, content)


if __name__ == "__main__": main()
