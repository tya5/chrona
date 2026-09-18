#!/usr/bin/env python3
"""Structural and local semantic checks for Federation v0.1 fixtures."""
from __future__ import annotations

from pathlib import Path
import sys
from datetime import date

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"
TRUSTED_REPOSITORIES = {"git+https://example.invalid/firmware.git"}


def load(path: Path):
    return yaml.safe_load(path.read_text())


def json_value(value):
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, list):
        return [json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    return value


def diagnostics(value: dict) -> set[str]:
    errors = set()
    namespaces = set()
    ids = set()
    for item in value.get("exports", []):
        if item.get("id") in ids:
            errors.add("FED-DUPLICATE-ID")
        ids.add(item.get("id"))
        namespace = item.get("presentation", {}).get("namespace")
        if namespace in namespaces:
            errors.add("FED-NAMESPACE-COLLISION")
        namespaces.add(namespace)
        revision = item.get("export", {}).get("revision", "")
        if not revision.startswith("git:") or len(revision) not in {44, 68}:
            errors.add("FED-REF-REVISION")
        if item.get("export", {}).get("repository") not in TRUSTED_REPOSITORIES:
            errors.add("FED-REPOSITORY-UNTRUSTED")
    return errors


def closure_diagnostics(here: Path, fixture: dict) -> set[str]:
    plan = load(here / fixture["plan"])
    available = [load(here / path) for path in fixture["availableExports"]]
    by_revision = {value["project"]["revision"]: value for value in available}
    actual = {item["id"]: item["export"]["revision"] for item in plan["exports"]}
    errors = set()
    if actual != fixture["expect"]["selected"]:
        errors.add("FED-CLOSURE-SELECTION")
    if any(revision not in by_revision for revision in actual.values()):
        errors.add("FED-EXPORT-UNAVAILABLE")
    if set(actual.values()) & set(fixture["expect"].get("ignored", {}).values()):
        errors.add("FED-UNPINNED-EXPORT-SELECTED")
    return errors


def main() -> int:
    here = Path(__file__).resolve().parent
    manifest = load(here / "conformance-v0.1.yaml")
    schemas = list(map(load, SCHEMAS.glob("*.schema.yaml")))
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas
    )
    failures = []
    for case in manifest["cases"]:
        if "closure" in case:
            actual = closure_diagnostics(here, load(here / case["closure"]))
            if actual:
                failures.append(f"{case['id']}: closure diagnostics {sorted(actual)}")
            continue
        value = json_value(load(here / case["resource"]))
        schema = load((here / case["schema"]).resolve())
        for error in Draft202012Validator(schema, registry=registry).iter_errors(value):
            failures.append(f"{case['id']}: {error.message}")
        actual = diagnostics(value)
        expected = set(case.get("expectDiagnostics", []))
        if actual != expected:
            failures.append(f"{case['id']}: diagnostics {sorted(actual)} != {sorted(expected)}")
    if failures:
        print("Federation conformance: FAIL", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        return 1
    print("Federation conformance: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
