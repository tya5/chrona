#!/usr/bin/env python3
"""Structural and local semantic checks for Federation v0.1 fixtures."""
from __future__ import annotations

from pathlib import Path
import sys
from datetime import date

import yaml
from jsonschema import Draft202012Validator, RefResolver


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


def main() -> int:
    here = Path(__file__).resolve().parent
    manifest = load(here / "conformance-v0.1.yaml")
    store = {schema["$id"]: schema for schema in map(load, SCHEMAS.glob("*.schema.yaml"))}
    failures = []
    for case in manifest["cases"]:
        value = json_value(load(here / case["resource"]))
        schema = load((here / case["schema"]).resolve())
        resolver = RefResolver.from_schema(schema, store=store)
        for error in Draft202012Validator(schema, resolver=resolver).iter_errors(value):
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
