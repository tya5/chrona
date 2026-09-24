#!/usr/bin/env python3
"""Generate the non-gating semantic-register corpus coverage report."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
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


def _load(path: Path) -> Mapping[str, Any]:
    try:
        value = safe_load(path.read_bytes())
    except (OSError, ValueError) as error:
        raise CorpusCoverageError(f"E_CORPUS_COVERAGE_LOAD:{path}") from error
    if not isinstance(value, Mapping):
        raise CorpusCoverageError(f"E_CORPUS_COVERAGE_DOCUMENT:{path}")
    return value


def discover(root: Path) -> tuple[CorpusProject, ...]:
    """Discover only manifests and project-scoped declared resource locations."""
    result: list[CorpusProject] = []
    for manifest_path in sorted((root / "examples").glob("*/manifest.yaml")):
        manifest = _load(manifest_path)
        identifier = manifest.get("id")
        if manifest.get("role") != "regression-corpus" or not isinstance(identifier, str):
            raise CorpusCoverageError(f"E_CORPUS_COVERAGE_MANIFEST:{manifest_path.relative_to(root)}")
        project_root = manifest_path.parent
        paths = [project_root / "project.yaml"]
        paths.extend(sorted((project_root / "snapshots").glob("*.yaml")))
        paths.extend(sorted((project_root / "extensions").glob("*.yaml")))
        actual = project_root / "actual.yaml"
        if actual.is_file():
            paths.append(actual)
        resources: list[tuple[str, Path, Mapping[str, Any]]] = []
        for path in paths:
            if not path.is_file():
                raise CorpusCoverageError(f"E_CORPUS_COVERAGE_RESOURCE:{path.relative_to(root)}")
            kind = "project" if path.name == "project.yaml" else ("actual" if path.name == "actual.yaml" else
                    ("snapshot" if path.parent.name == "snapshots" else "extension"))
            resources.append((kind, path, _load(path)))
        result.append(CorpusProject(identifier, project_root, tuple(resources)))
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
        if kind == "project":
            objects = value.get("objects", {})
            if isinstance(objects, Mapping):
                yield from (item for item in objects.values() if isinstance(item, Mapping))


def _project_probe(project: CorpusProject, condition: Callable[[Mapping[str, Any]], bool]) -> tuple[Path, ...]:
    return tuple(path for kind, path, _ in project.resources if kind == "project" and any(condition(item) for item in _project_objects(project)))


def _actual_probe(project: CorpusProject, condition: Callable[[Mapping[str, Any]], bool]) -> tuple[Path, ...]:
    return _resource_paths(project, "actual", lambda item: isinstance(item.get("actual"), Mapping) and condition(item["actual"]))


PROBES = (
    Probe("Project", "deadline", lambda p: _project_probe(p, lambda o: "deadline" in o)),
    Probe("Project", "constraints", lambda p: _project_probe(p, lambda o: isinstance(o.get("schedule"), Mapping) and "constraints" in o["schedule"])),
    Probe("Project", "negative-lag", lambda p: _project_probe(p, lambda o: False)),
    Probe("Project", "hierarchy", lambda p: _project_probe(p, lambda o: "parent" in o or "wbsCode" in o)),
    Probe("Project", "scenario-relation-edit", lambda p: _resource_paths(p, "project", lambda x: "remove" in x or "add" in x)),
    Probe("Actual", "point-observation", lambda p: _actual_probe(p, lambda a: "at" in a)),
    Probe("Actual", "in-flight-observation", lambda p: _actual_probe(p, lambda a: "start" in a and "progress" in a and "finish" not in a)),
    Probe("Actual", "progress", lambda p: _actual_probe(p, lambda a: "progress" in a)),
    Probe("Snapshot", "pinned-snapshot", lambda p: tuple(path for kind, path, _ in p.resources if kind == "snapshot")),
    Probe("Extension", "declared-profile-package", lambda p: tuple(path for kind, path, _ in p.resources if kind == "extension")),
    Probe("Extension", "typed-field", lambda p: _resource_paths(p, "extension", lambda x: "fields" in x)),
)


def _negative_lag(project: CorpusProject) -> tuple[Path, ...]:
    return tuple(path for kind, path, value in project.resources if kind == "project" and any(
        isinstance(item, Mapping) and (
            isinstance(item.get("lag"), str) and item["lag"].startswith("-")
            or isinstance(item.get("lag"), Mapping) and isinstance(item["lag"].get("value"), str)
            and item["lag"]["value"].startswith("-"))
        for item in _walk(value)))


PROBES = tuple(Probe(probe.contract, probe.identifier, _negative_lag) if probe.identifier == "negative-lag" else probe for probe in PROBES)


def render(root: Path) -> str:
    projects = discover(root)
    lines = ["# Corpus coverage", "", "Generated by `tools/corpus_coverage.py`; this is a curation backlog, not a CI coverage gate.", "",
             "## Semantic-register evidence", "", "| Contract | Probe | " + " | ".join(project.identifier for project in projects) + " |",
             "| --- | --- | " + " | ".join("---" for _ in projects) + " |"]
    for probe in PROBES:
        cells = []
        for project in projects:
            paths = probe.predicate(project)
            cells.append(", ".join(path.relative_to(root).as_posix() for path in paths) if paths else "—")
        lines.append(f"| {probe.contract} | `{probe.identifier}` | " + " | ".join(cells) + " |")
    uncovered = [probe.identifier for probe in PROBES if not any(probe.predicate(project) for project in projects)]
    lines.extend(["", "## Uncovered register probes", "", ", ".join(f"`{item}`" for item in uncovered) if uncovered else "None.", ""])
    return "\n".join(lines)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=Path("docs/examples/corpus-coverage.md"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve(); output = args.output if args.output.is_absolute() else root / args.output
    content = render(root)
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != content:
            raise SystemExit("E_CORPUS_COVERAGE_STALE")
        return
    write(output, content)


if __name__ == "__main__":
    main()
