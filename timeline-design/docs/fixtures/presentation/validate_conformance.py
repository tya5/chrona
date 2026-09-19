#!/usr/bin/env python3
"""Structural reference runner for Presentation v0.1 conformance fixtures."""
from __future__ import annotations

from pathlib import Path
import sys
from datetime import date
from hashlib import sha256
from pathlib import PurePosixPath
import subprocess

import yaml
from jsonschema import Draft202012Validator, RefResolver


ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"
REPOSITORY_ROOT = ROOT.parents[1]


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


def resolve_revision_ref(ref: dict) -> tuple[dict | None, list[str]]:
    """Load one canonical reference from its declared Git revision."""
    errors = []
    path_text = ref.get("path", "")
    path = PurePosixPath(path_text)
    if not path_text or path.is_absolute() or any(part in {".", ".."} for part in path.parts):
        return None, ["PRES-REF-PATH"]
    revision = ref.get("revision", "")
    if not revision.startswith("git:"):
        return None, ["PRES-REF-REVISION"]
    git_revision = revision.removeprefix("git:")
    try:
        result = subprocess.run(
            ["git", "-C", str(REPOSITORY_ROOT), "show", f"{git_revision}:{path_text}"],
            check=True, capture_output=True,
        )
    except subprocess.CalledProcessError:
        return None, ["PRES-REF-REVISION"]
    expected = ref.get("contentIdentity", "").removeprefix("sha256:")
    if sha256(result.stdout).hexdigest() != expected:
        errors.append("PRES-REF-CONTENT")
    try:
        value = json_value(yaml.safe_load(result.stdout))
    except yaml.YAMLError:
        return None, errors + ["PRES-REF-REVISION"]
    expected_kind = ref.get("kind")
    expected_id = ref.get("id")
    if expected_kind == "project":
        actual_id = value.get("project", {}).get("id")
        actual_kind = "project"
    else:
        actual_id = value.get("id")
        actual_kind = value.get("kind")
    if actual_kind != expected_kind or actual_id != expected_id:
        errors.append("PRES-REF-IDENTITY")
    return value, errors


def delta_diagnostics(resource: dict, expected: dict) -> list[str]:
    errors = []
    if resource.get("replaceScope") != expected.get("replaceScope"):
        errors.append("PRES-SCENE-DELTA-SCOPE")
    if resource.get("replaceScope") is None and resource.get("reason") != "actual-observation-change":
        errors.append("PRES-SCENE-DELTA-SCOPE")
    if resource.get("replaceScope") == "scene" and resource.get("reason") not in {"viewport-reflow", "scale-change"}:
        errors.append("PRES-SCENE-DELTA-SCOPE")
    if resource.get("targetGeneration", 0) <= resource.get("baseGeneration", 0):
        errors.append("RUNTIME-GENERATION-ORDER")
    allowed = set(expected.get("allowedSceneIds", []))
    if allowed and resource.get("replaceScope") is None:
        for operation in resource.get("operations", []):
            scene_id = operation.get("sceneId")
            if scene_id and scene_id not in allowed:
                errors.append("PRES-SCENE-DELTA-IMPACT")
    return errors


def semantic_errors(path: Path, resource: dict) -> list[str]:
    errors = []
    kind = resource.get("kind")
    body = resource.get("body", {})
    if kind == "snapshot-ref" and not str(body.get("project", {}).get("revision", "")).startswith(("git:", "store:")):
        errors.append("PRES-SNAPSHOT-REVISION")
    if kind == "snapshot-ref":
        project, ref_errors = resolve_revision_ref(body.get("project", {}))
        errors.extend(ref_errors)
        if project and project.get("project", {}).get("id") != body["project"].get("id"):
            errors.append("PRES-PROJECT-COMPATIBILITY")
    if kind == "actual-set":
        sequences_by_subject = {}
        for observation in body.get("observations", []):
            external = observation.get("externalIdentity")
            resolved = observation.get("projectObjectId")
            if bool(external) == bool(resolved):
                errors.append("PRES-ACTUAL-ALIGNMENT")
            if external and observation.get("alignment") != "unmatched":
                errors.append("PRES-ACTUAL-ALIGNMENT")
            subject = resolved
            if not subject and external:
                subject = f"external:{external.get('system')}:{external.get('key')}"
            sequence = observation.get("sequence")
            if subject and sequence in sequences_by_subject.setdefault(subject, set()):
                errors.append("VIEW-OBSERVATION-SEQUENCE")
            if subject:
                sequences_by_subject[subject].add(sequence)
    if kind == "theme":
        values = dict(body.get("values", {}))
        roles = dict(body.get("roles", {}))
        parent = body.get("extends")
        if parent:
            inherited, ref_errors = resolve_revision_ref(parent)
            errors.extend(ref_errors)
            if inherited and inherited.get("kind") == "theme":
                parent_body = inherited.get("body", {})
                inherited_values = dict(parent_body.get("values", {}))
                inherited_values.update(values)
                values = inherited_values
                inherited_roles = dict(parent_body.get("roles", {}))
                inherited_roles.update(roles)
                roles = inherited_roles
            else:
                errors.append("THEME-INHERITANCE-INVALID")
        for bindings in roles.values():
            for token_name in bindings.values():
                if token_name not in values:
                    errors.append("THEME-UNDEFINED-TOKEN")
    if kind == "render-context":
        target = body.get("target", {})
        if not target.get("kind") or not isinstance(target.get("capabilities"), list):
            errors.append("PRES-TARGET-CAPABILITY")
            return errors
        def load_ref(name: str):
            ref = body.get(name)
            if not ref:
                return None
            value, ref_errors = resolve_revision_ref(ref)
            errors.extend(ref_errors)
            return value
        view = load_ref("view")
        actual_ref = body.get("inputs", {}).get("actual")
        if view:
            comparison = view.get("body", {}).get("comparison", {})
            if comparison.get("actual") == "required" and not actual_ref:
                errors.append("PRES-VIEW-ACTUAL-REQUIRED")
            for annotation in view.get("body", {}).get("annotations", []):
                if annotation.get("purpose") == "explanatory-arrow" and "marker" not in target["capabilities"]:
                    errors.append("PRES-TARGET-CAPABILITY")
            if view.get("body", {}).get("visibility", {}).get("labels") and "text-alternative" not in target["capabilities"]:
                errors.append("PRES-TARGET-CAPABILITY")
        if actual_ref:
            actual, actual_errors = resolve_revision_ref(actual_ref)
            project, project_errors = resolve_revision_ref(body["project"])
            errors.extend(actual_errors)
            errors.extend(project_errors)
            if not actual or not project:
                return errors
            project_ids = set(project.get("objects", {}))
            for observation in actual.get("body", {}).get("observations", []):
                resolved = observation.get("projectObjectId")
                if resolved and resolved not in project_ids:
                    errors.append("PRES-ACTUAL-ALIGNMENT")
        snapshot_ref = body.get("inputs", {}).get("snapshot")
        if snapshot_ref:
            snapshot, snapshot_errors = resolve_revision_ref(snapshot_ref)
            errors.extend(snapshot_errors)
            if not snapshot:
                return errors
            revision = snapshot.get("body", {}).get("project", {}).get("revision")
            if not str(revision).startswith(("git:", "store:")):
                errors.append("PRES-SNAPSHOT-REVISION")
            if snapshot.get("body", {}).get("project", {}).get("id") != body["project"].get("id"):
                errors.append("PRES-PROJECT-COMPATIBILITY")
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
            errors = list(Draft202012Validator(schema, resolver=resolver).iter_errors(resource))
            if case.get("expectSchemaError"):
                if not errors:
                    failures.append(f"{case['id']}: expected schema rejection")
            else:
                failures.extend(f"{case['id']}: {error.message}" for error in errors)
        if "expect" in case:
            expected_delta = set(case.get("expectDeltaDiagnostics", []))
            actual_delta = set(delta_diagnostics(resource, case["expect"]))
            if actual_delta != expected_delta:
                failures.append(f"{case['id']}: delta diagnostics {sorted(actual_delta)} != {sorted(expected_delta)}")
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
