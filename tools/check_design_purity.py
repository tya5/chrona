#!/usr/bin/env python3
"""Audit presentation design resources for lexical Project-specific content.

This is a read-only candidate finder, not a semantic dependency proof.  It
checks only Theme, Layout and presentation-profile resources; the View and
Context are the explicit Project-to-design connections and are not audited.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

import yaml

from chrona.presentation.model.theme_inheritance import (
    ThemeInheritanceError,
    is_derived_theme,
    theme_base_reference,
)
from chrona.presentation.contracts.resources import RENDER_CONTEXT_VERSIONS, _SCHEMAS
from chrona.resources import safe_load
from chrona.usecases.deck_context import load_deck_manifest, select_deck_context
from chrona.usecases.failure_report import StableFailure
from chrona.usecases import materialize


_COLLECTIONS = (
    "objects", "entities", "calendars", "periods", "scenarios",
    "relations", "annotations",
)
_WORDING_FIELDS = frozenset({"title", "label", "description", "text"})
_DESIGN_TEXT_FIELDS = frozenset({
    "title", "label", "description", "text", "heading", "kicker", "subtitle",
    "caption", "secondary", "header", "footer", "placeholder",
})
_PLACEHOLDER = re.compile(
    r"(?<!\{)\{(?:project|asOf|calendar|ordinal|title|secondary|label|subject|subjectId"
    r")(?:\|[A-Za-z][A-Za-z0-9_-]*)?\}(?!\})"
)
_IDENTIFIER_BOUNDARY = r"[\w-]"
_SUPPORTED_DESIGN_VERSIONS = {
    kind: frozenset(version for resource_kind, version in _SCHEMAS if resource_kind == kind)
    for kind in ("theme", "layout-profile", "summary-profile", "review-detail-profile")
}


class DesignPurityError(ValueError):
    """An input, reference, or identity error prevents a complete audit."""


@dataclass(frozen=True)
class ProjectFact:
    kind: str
    value: str
    pointer: str


def _pointer(parent: str, token: object) -> str:
    rendered = str(token).replace("~", "~0").replace("/", "~1")
    return f"{parent}/{rendered}"


def _normal(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _literal_segments(value: str) -> tuple[str, ...]:
    """Remove only known, unescaped template slots; escaped braces stay literal."""
    return (_PLACEHOLDER.sub(" ", value),)


def _phrase_occurs(phrase: str, candidate: str) -> bool:
    phrase, candidate = _normal(phrase), _normal(candidate)
    if not phrase or not candidate:
        return False
    # Phrases are contiguous, with word-like boundaries.  Hyphen and underscore
    # remain identifier characters so a short id cannot match a longer id.
    pattern = re.compile(
        rf"(?<!{_IDENTIFIER_BOUNDARY}){re.escape(phrase)}(?!{_IDENTIFIER_BOUNDARY})",
        re.UNICODE,
    )
    return pattern.search(candidate) is not None


def _project_facts(project: object) -> tuple[ProjectFact, ...]:
    if not isinstance(project, Mapping):
        raise DesignPurityError("E_DESIGN_PURITY_PROJECT: Project must be a mapping")
    facts: list[ProjectFact] = []
    identity = project.get("project")
    project_id = identity.get("id") if isinstance(identity, Mapping) else None
    if not isinstance(project_id, str) or not project_id:
        raise DesignPurityError("E_DESIGN_PURITY_PROJECT: missing Project id")
    if not isinstance(project.get("version"), str) or ("project", project["version"]) not in _SCHEMAS:
        raise DesignPurityError(f"E_DESIGN_PURITY_UNSUPPORTED: Project version {project.get('version')!r}")
    facts.append(ProjectFact("identifier", project_id, "/project/id"))

    for collection in _COLLECTIONS:
        value = project.get(collection)
        base = f"/{collection}"
        if isinstance(value, Mapping):
            for key in value:
                if isinstance(key, str) and key:
                    facts.append(ProjectFact("identifier", key, _pointer(base, key)))
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for index, item in enumerate(value):
                if isinstance(item, Mapping):
                    item_id = item.get("id")
                    if isinstance(item_id, str) and item_id:
                        facts.append(ProjectFact("identifier", item_id, f"{base}/{index}/id"))

    def wording(node: object, path: str) -> None:
        if isinstance(node, Mapping):
            for key, value in node.items():
                child = _pointer(path, key)
                if key in _WORDING_FIELDS and isinstance(value, str) and value.strip():
                    facts.append(ProjectFact("wording", value, child))
                wording(value, child)
        elif isinstance(node, Sequence) and not isinstance(node, (str, bytes, bytearray)):
            for index, value in enumerate(node):
                wording(value, f"{path}/{index}")

    wording(project, "")
    unique = {(fact.kind, fact.value, fact.pointer): fact for fact in facts}
    return tuple(sorted(unique.values(), key=lambda fact: (fact.pointer, fact.kind, fact.value)))


def _connection_identifier(pointer: str) -> bool:
    parts = pointer.split("/")
    # Summary metric source.object is the only design field that names a
    # Project object directly; its other lexical collisions remain candidates.
    return len(parts) >= 3 and parts[-2:] == ["source", "object"]


def _user_facing_text(parent: Mapping[str, Any], key: object) -> bool:
    """Whether this resource value is authored text, rather than a token name/value."""
    if key == "value" and parent.get("type") == "text":
        return True
    return isinstance(key, str) and key in _DESIGN_TEXT_FIELDS


def _matches(text: str, facts: tuple[ProjectFact, ...], pointer: str,
             location: str, resource_kind: str | None, *,
             user_facing_text: bool = False) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for segment in _literal_segments(text):
        for fact in facts:
            if fact.kind == "identifier":
                connection = (resource_kind == "summary-profile" and location == "value"
                              and _connection_identifier(pointer))
                typed = (connection and fact.pointer.startswith("/objects/")
                         and text == fact.value)
                if not connection and not (location == "value" and user_facing_text):
                    continue
                if not _phrase_occurs(fact.value, segment):
                    continue
                match_class = "typed-connection-identifier" if typed else "identifier-candidate"
            else:
                if not _phrase_occurs(fact.value, segment):
                    continue
                match_class = "wording-candidate"
            result.append({
                "pointer": pointer,
                "project_fact": f"{fact.kind}:{fact.pointer}",
                "match": fact.value,
                "match_class": match_class,
                "location": location,
            })
    deduplicated = {tuple(sorted(item.items())): item for item in result}
    return list(deduplicated.values())


def _scan_design(resource_name: str, value: object,
                 facts: tuple[ProjectFact, ...]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    resource_kind = value.get("kind") if isinstance(value, Mapping) else None

    def visit(node: object, pointer: str) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                child_pointer = _pointer(pointer, key)
                # Resource envelope identity/version are schema metadata, not design content.
                if not pointer and key in {"version", "kind", "id"}:
                    continue
                if isinstance(key, str):
                    findings.extend({"resource": resource_name, **item}
                                    for item in _matches(key, facts, child_pointer, "key", resource_kind))
                if isinstance(child, str):
                    findings.extend({"resource": resource_name, **item}
                                    for item in _matches(
                                        child, facts, child_pointer, "value", resource_kind,
                                        user_facing_text=_user_facing_text(node, key)))
                else:
                    visit(child, child_pointer)
        elif isinstance(node, Sequence) and not isinstance(node, (str, bytes, bytearray)):
            for index, child in enumerate(node):
                visit(child, f"{pointer}/{index}")
        elif isinstance(node, str):
            findings.extend({"resource": resource_name, **item}
                            for item in _matches(node, facts, pointer, "value", resource_kind))

    visit(value, "")
    return findings


def _load_yaml(payload: bytes, label: str) -> Any:
    try:
        return safe_load(payload)
    except (yaml.YAMLError, UnicodeDecodeError) as error:
        raise DesignPurityError(f"E_DESIGN_PURITY_YAML:{label}:{error}") from error


def _reference_key(reference: Mapping[str, Any]) -> tuple[str, str, str]:
    store = reference.get("store")
    if not isinstance(store, Mapping):
        raise DesignPurityError("E_DESIGN_PURITY_REFERENCE: missing Store declaration")
    provider, identity, address = store.get("provider"), store.get("identity"), reference.get("address")
    if not all(isinstance(item, str) and item for item in (provider, identity, address)):
        raise DesignPurityError("E_DESIGN_PURITY_REFERENCE: incomplete Store/address")
    return provider, identity, address


def _reference_label(reference: Mapping[str, Any]) -> str:
    provider, identity, address = _reference_key(reference)
    return f"{provider}:{identity}/{address}"


def _read_reference(example: Path, reference: dict[str, Any], stores: Mapping[str, Path] | None) -> bytes:
    try:
        return materialize.read_materializer_reference(example, reference, stores)
    except Exception as error:
        raise DesignPurityError(f"E_DESIGN_PURITY_REFERENCE:{_reference_label(reference)}:{error}") from error


def _stores(example: Path, declared: object) -> dict[str, Path]:
    try:
        result = materialize.materializer_store_roots(example, declared)
    except Exception as error:
        raise DesignPurityError(f"E_DESIGN_PURITY_STORES:{error}") from error
    if not isinstance(result, Mapping):
        raise DesignPurityError("E_DESIGN_PURITY_STORES: Store resolver returned a non-mapping")
    return dict(result)


def _inside(root: Path, address: str) -> Path:
    result = (root / address).resolve()
    if root.resolve() not in (result, *result.parents):
        raise DesignPurityError(f"E_DESIGN_PURITY_CONTEXT_PATH:{address}")
    return result


def _resource_reference(context: Mapping[str, Any], key: str,
                        kind: str | None = None) -> dict[str, Any]:
    body = context.get("body")
    reference = body.get(key) if isinstance(body, Mapping) else None
    if not isinstance(reference, dict):
        raise DesignPurityError(f"E_DESIGN_PURITY_CONTEXT: missing body.{key} reference")
    if kind is not None and reference.get("kind") != kind:
        raise DesignPurityError(f"E_DESIGN_PURITY_CONTEXT: body.{key} must reference {kind}")
    _reference_key(reference)
    return reference


def _validate_design_version(value: Mapping[str, Any], expected: str, label: str) -> None:
    version = value.get("version")
    if not isinstance(version, str) or version not in _SUPPORTED_DESIGN_VERSIONS.get(expected, frozenset()):
        raise DesignPurityError(f"E_DESIGN_PURITY_UNSUPPORTED:{label}:{expected}:{version!r}")
    declared_kind = value.get("kind")
    if ((expected in {"theme", "summary-profile"} and declared_kind != expected)
            or (declared_kind is not None and declared_kind != expected)):
        raise DesignPurityError(f"E_DESIGN_PURITY_RESOURCE:{label}: expected {expected}")
    if not isinstance(value.get("id"), str) or not value["id"]:
        raise DesignPurityError(f"E_DESIGN_PURITY_IDENTITY:{label}: missing resource id")


def _input_reference(context: Mapping[str, Any], key: str,
                     kind: str) -> dict[str, Any] | None:
    body = context.get("body")
    inputs = body.get("inputs") if isinstance(body, Mapping) else None
    reference = inputs.get(key) if isinstance(inputs, Mapping) else None
    if reference is None:
        return None
    if not isinstance(reference, dict) or reference.get("kind") != kind:
        raise DesignPurityError(f"E_DESIGN_PURITY_CONTEXT: body.inputs.{key} must reference {kind}")
    _reference_key(reference)
    return reference


def _scan_context(example: Path, context: Mapping[str, Any], context_label: str,
                  stores: Mapping[str, Path], *,
                  errors: list[str] | None = None) -> list[dict[str, str]]:
    if not isinstance(context, Mapping) or not isinstance(context.get("body"), Mapping):
        raise DesignPurityError(f"E_DESIGN_PURITY_CONTEXT:{context_label}")
    if context.get("kind") != "render-context" or context.get("version") not in RENDER_CONTEXT_VERSIONS:
        raise DesignPurityError(f"E_DESIGN_PURITY_UNSUPPORTED_CONTEXT:{context_label}")
    project_ref = _resource_reference(context, "project", "project")
    project = _load_yaml(_read_reference(example, project_ref, stores), _reference_label(project_ref))
    facts = _project_facts(project)
    if project["project"]["id"] != project_ref.get("id"):
        raise DesignPurityError(f"E_DESIGN_PURITY_IDENTITY:{_reference_label(project_ref)}: Project id differs from reference")
    findings: list[dict[str, str]] = []
    def scan_reference(reference: dict[str, Any], expected: str,
                       stack: tuple[tuple[str, str, str], ...] = ()) -> None:
        label = _reference_label(reference)
        key = _reference_key(reference)
        if key in stack:
            raise DesignPurityError(f"E_DESIGN_PURITY_THEME_CYCLE:{label}")
        payload = _read_reference(example, reference, stores)
        value = _load_yaml(payload, label)
        if not isinstance(value, Mapping):
            raise DesignPurityError(f"E_DESIGN_PURITY_RESOURCE:{label}: expected mapping")
        _validate_design_version(value, expected, label)
        if value["id"] != reference.get("id"):
            raise DesignPurityError(f"E_DESIGN_PURITY_IDENTITY:{label}: resource id differs from reference")
        findings.extend(_scan_design(label, value, facts))
        if expected == "theme" and is_derived_theme(value):
            try:
                base = theme_base_reference(reference, dict(value))
            except ThemeInheritanceError as error:
                raise DesignPurityError(f"E_DESIGN_PURITY_THEME_BASE:{label}:{error}") from error
            scan_reference(base, "theme", (*stack, key))

    for key, kind, optional in (("theme", "theme", False), ("layout", "layout-profile", False),
                                ("summaryProfile", "summary-profile", True),
                                ("detailProfile", "review-detail-profile", True)):
        try:
            reference = (_input_reference(context, key, kind) if optional
                         else _resource_reference(context, key, kind))
            if reference is not None:
                scan_reference(reference, kind)
        except (DesignPurityError, StableFailure, OSError, ValueError) as error:
            if errors is None:
                raise
            errors.append(f"{context_label}:{error}")
    return [{**finding, "project": _reference_label(project_ref),
             "context": context_label} for finding in findings]


def _batch(examples_root: Path, *, errors: list[str] | None = None) -> list[dict[str, str]]:
    if not examples_root.is_dir():
        raise DesignPurityError(f"E_DESIGN_PURITY_EXAMPLES_ROOT:{examples_root}")
    manifests = sorted(examples_root.glob("*/manifest.yaml"))
    if not manifests:
        raise DesignPurityError(f"E_DESIGN_PURITY_EMPTY:{examples_root}")
    findings: list[dict[str, str]] = []
    for manifest_path in manifests:
        example = manifest_path.parent.resolve()
        try:
            manifest_source = load_deck_manifest(manifest_path)
            manifest = manifest_source.document
            if not isinstance(manifest, Mapping) or not isinstance(manifest.get("slides"), list) or not manifest["slides"]:
                raise DesignPurityError(f"E_DESIGN_PURITY_MANIFEST:{manifest_path}")
            stores = _stores(example, manifest.get("stores"))
        except (DesignPurityError, OSError, ValueError) as error:
            if errors is None:
                raise
            errors.append(f"{manifest_path}:{error}")
            continue
        for slide_index, slide in enumerate(manifest["slides"]):
            try:
                if not isinstance(slide, Mapping):
                    raise DesignPurityError(f"E_DESIGN_PURITY_MANIFEST:{manifest_path}:slides/{slide_index}")
                selected = select_deck_context(manifest_path, manifest_source, slide["id"])
                if selected.source_path is not None:
                    context_label = selected.source_path.relative_to(manifest_path.parents[1]).as_posix()
                else:
                    context_label = f"{manifest_path.relative_to(examples_root.parent).as_posix()}#slide={selected.slide_id}"
                findings.extend(_scan_context(example, selected.document, context_label, stores, errors=errors))
            except (DesignPurityError, StableFailure, OSError, ValueError) as error:
                if errors is None:
                    raise
                errors.append(f"{manifest_path}:slides/{slide_index}:{error}")
    return findings


def audit(project: object, resources: Sequence[tuple[str, object]], *,
          project_label: str = "explicit-project") -> list[dict[str, str]]:
    """Return stable candidate findings for explicit Project/design inputs."""
    if not resources:
        raise DesignPurityError("E_DESIGN_PURITY_EMPTY: no design resources were supplied")
    facts = _project_facts(project)
    findings = [{**finding, "project": project_label} for name, resource in resources
                for finding in _scan_design(name, resource, facts)]
    return _sort_findings(findings)


def _sort_findings(findings: Sequence[dict[str, str]]) -> list[dict[str, str]]:
    unique = {tuple(sorted(item.items())): item for item in findings}
    return sorted(unique.values(), key=lambda item: (
        item.get("resource", ""), item.get("pointer", ""),
        item.get("project_fact", ""), item.get("match_class", ""),
        item.get("location", ""), item.get("match", ""),
        item.get("project", ""), item.get("context", ""),
    ))


def _explicit(project_path: Path, resource_paths: Sequence[Path]) -> list[dict[str, str]]:
    project = _load_yaml(project_path.read_bytes(), project_path.as_posix())
    _project_facts(project)  # fail closed before examining resources
    resources = []
    for path in resource_paths:
        value = _load_yaml(path.read_bytes(), path.as_posix())
        if not isinstance(value, Mapping):
            raise DesignPurityError(f"E_DESIGN_PURITY_RESOURCE:{path}: expected mapping")
        if value.get("kind") is not None and value["kind"] not in tuple(_SUPPORTED_DESIGN_VERSIONS):
            raise DesignPurityError(f"E_DESIGN_PURITY_RESOURCE:{path}: connection/non-design kind")
        version = value.get("version")
        if not isinstance(version, str):
            raise DesignPurityError(f"E_DESIGN_PURITY_UNSUPPORTED:{path}:{version!r}")
        expected = next((kind for kind, versions in _SUPPORTED_DESIGN_VERSIONS.items()
                         if version in versions), None)
        if expected is None:
            raise DesignPurityError(f"E_DESIGN_PURITY_UNSUPPORTED:{path}:{version!r}")
        _validate_design_version(value, expected, path.as_posix())
        resources.append((path.as_posix(), value))
    return audit(project, resources, project_label=project_path.as_posix())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path)
    parser.add_argument("--resource", type=Path, action="append", default=[])
    parser.add_argument("--examples-root", type=Path)
    parser.add_argument("--report-only", action="store_true",
                        help="emit findings without failing solely because of lexical candidates")
    args = parser.parse_args(argv)
    explicit = args.project is not None or bool(args.resource)
    if explicit == (args.examples_root is not None) or (explicit and (args.project is None or not args.resource)):
        parser.error("choose --examples-root OR both --project and at least one --resource")
    errors: list[str] = []
    try:
        findings = (_explicit(args.project, args.resource) if explicit
                    else _sort_findings(_batch(args.examples_root, errors=errors)))
    except (DesignPurityError, OSError, ValueError) as error:
        findings, errors = [], [str(error)]
    payload = {"errors": sorted(errors), "findings": _sort_findings(findings),
               "counts": {"findings": len(findings),
                          "resourcesWithFindings": len({item["resource"] for item in findings}),
                          "contextsWithFindings": len({item["context"] for item in findings if "context" in item})}}
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    if errors:
        return 2
    return 1 if findings and not args.report_only else 0


if __name__ == "__main__":
    raise SystemExit(main())
