#!/usr/bin/env python3
"""Structural reference runner for Presentation v0.1 conformance fixtures."""
from __future__ import annotations

from pathlib import Path
import sys
from datetime import date

import yaml
from jsonschema import Draft202012Validator, RefResolver


ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"


def load_yaml(path: Path):
    with path.open() as handle:
        return yaml.safe_load(handle)


def json_value(value):
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, list):
        return [json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    return value


def schema_store():
    store = {}
    for path in SCHEMAS.glob("*.schema.yaml"):
        schema = load_yaml(path)
        store[schema["$id"]] = schema
    return store


def assert_delta(case_id: str, resource: dict, expected: dict) -> list[str]:
    errors = []
    if resource.get("replaceScope") != expected.get("replaceScope"):
        errors.append(f"{case_id}: replaceScope mismatch")
    if resource.get("replaceScope") is None and resource.get("reason") != "actual-observation-change":
        errors.append(f"{case_id}: local delta needs actual-observation-change reason")
    if resource.get("replaceScope") == "scene" and resource.get("reason") not in {"viewport-reflow", "scale-change"}:
        errors.append(f"{case_id}: global delta needs declared global reason")
    return errors


def semantic_errors(path: Path, resource: dict) -> list[str]:
    errors = []
    kind = resource.get("kind")
    body = resource.get("body", {})
    if kind == "snapshot-ref" and not str(body.get("project", {}).get("revision", "")).startswith(("git:", "store:")):
        errors.append("PRES-SNAPSHOT-REVISION")
    if kind == "actual-set":
        for observation in body.get("observations", []):
            external = observation.get("externalIdentity")
            resolved = observation.get("projectObjectId")
            if bool(external) == bool(resolved):
                errors.append("PRES-ACTUAL-ALIGNMENT")
            if external and observation.get("alignment") != "unmatched":
                errors.append("PRES-ACTUAL-ALIGNMENT")
    if kind == "render-context":
        target = body.get("target", {})
        if not target.get("kind") or not isinstance(target.get("capabilities"), list):
            errors.append("PRES-TARGET-CAPABILITY")
    return errors


def main() -> int:
    manifest_path = Path(__file__).with_name("conformance-v0.1.yaml")
    manifest = load_yaml(manifest_path)
    store = schema_store()
    failures = []
    for case in manifest["cases"]:
        resource = json_value(load_yaml(manifest_path.parent / case["resource"]))
        if "schema" in case:
            schema_path = (manifest_path.parent / case["schema"]).resolve()
            schema = load_yaml(schema_path)
            resolver = RefResolver.from_schema(schema, store=store)
            errors = Draft202012Validator(schema, resolver=resolver).iter_errors(resource)
            failures.extend(f"{case['id']}: {error.message}" for error in errors)
        if "expect" in case:
            failures.extend(assert_delta(case["id"], resource, case["expect"]))
        expected_diagnostics = set(case.get("expectDiagnostics", []))
        actual_diagnostics = set(semantic_errors(manifest_path.parent / case["resource"], resource))
        if actual_diagnostics != expected_diagnostics:
            failures.append(f"{case['id']}: diagnostics {sorted(actual_diagnostics)} != {sorted(expected_diagnostics)}")
    if failures:
        print("Presentation conformance: FAIL", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        return 1
    print("Presentation conformance: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
