from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import yaml

from chrona.commands import execute_set_typed_field, set_typed_field
from chrona.loader import schedule_snapshot, validate_snapshot
from chrona.revision_store import LocalSnapshotReader, MemoryRevisionStore
from chrona.scheduler import schedule
from chrona.validation import validate_project

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "timeline-design" / "docs" / "fixtures"


def _manifest():
    return {"implementation-delivery": yaml.safe_load((FIXTURES / "implementation-delivery-profile-v0.1.yaml").read_text())}


def _roadmap():
    project = yaml.safe_load((FIXTURES / "implementation-delivery-roadmap-v0.1.yaml").read_text())
    project.pop("expectedPlacements")
    return project


def test_resolved_delivery_profile_validates_and_schedules_through_core():
    project = _roadmap()
    assert validate_project(project, package_manifests=_manifest()) == []
    assert schedule(project, package_manifests=_manifest()).ok


def test_invalid_state_is_rejected_without_changing_project():
    project = _roadmap()
    original = deepcopy(project)
    result = set_typed_field(project, _manifest(), "idp-4", "workflowState", "done")
    assert result.status == "rejected"
    assert result.diagnostics == ("IDP-STATE-001",)
    assert project == original


def test_valid_typed_field_command_returns_a_new_candidate_only():
    project = _roadmap()
    result = set_typed_field(project, _manifest(), "idp-4", "workflowState", "active")
    assert result.status == "accepted"
    assert result.project is not project
    assert result.project["objects"]["idp-4"]["fields"]["workflowState"] == "active"
    assert project["objects"]["idp-4"]["fields"]["workflowState"] == "planned"


def test_typed_field_command_uses_cas_and_creates_immutable_snapshot():
    store = MemoryRevisionStore(_roadmap())
    base = store.read()
    result = execute_set_typed_field(store, base.revision, _manifest(), "idp-4", "workflowState", "active")
    assert result.status == "accepted"
    assert result.result_revision and result.result_revision != base.revision
    assert store.read().project["objects"]["idp-4"]["fields"]["workflowState"] == "active"
    conflict = execute_set_typed_field(store, base.revision, _manifest(), "idp-4", "workflowState", "blocked")
    assert conflict.status == "rejected"
    assert conflict.diagnostics == ("E_CONFLICT",)


def test_local_snapshot_reader_resolves_pinned_package_reference(tmp_path):
    manifest_bytes = (FIXTURES / "implementation-delivery-profile-v0.1.yaml").read_bytes()
    snapshot = tmp_path / "snapshot-1" / "packages"
    snapshot.mkdir(parents=True)
    (snapshot / "implementation-delivery.yaml").write_bytes(manifest_bytes)
    project = _roadmap()
    project["extensions"] = [{"packageId": "implementation-delivery", "resource": {
        "id": "implementation-delivery", "kind": "profile-package",
        "store": {"provider": "local", "identity": "chrona-test"},
        "address": "packages/implementation-delivery.yaml", "revision": {"token": "snapshot-1"},
        "contentIdentity": f"sha256:{sha256(manifest_bytes).hexdigest()}",
    }}]
    reader = LocalSnapshotReader(tmp_path, "chrona-test")
    assert validate_project(project, package_reader=reader) == []
    assert schedule(project, package_reader=reader).ok
    project["extensions"][0]["resource"]["contentIdentity"] = "sha256:" + "0" * 64
    assert {item.id for item in validate_project(project, package_reader=reader)} == {"E_CONTENT_IDENTITY", "IDP-PROFILE-006"}


def test_snapshot_loader_evaluates_only_pinned_project_and_package_bytes(tmp_path):
    manifest_bytes = (FIXTURES / "implementation-delivery-profile-v0.1.yaml").read_bytes()
    project = _roadmap()
    project["extensions"] = [{"packageId": "implementation-delivery", "resource": {
        "id": "implementation-delivery", "kind": "profile-package",
        "store": {"provider": "local", "identity": "chrona-test"},
        "address": "packages/implementation-delivery.yaml", "revision": {"token": "snapshot-2"},
        "contentIdentity": f"sha256:{sha256(manifest_bytes).hexdigest()}",
    }}]
    project_bytes = yaml.safe_dump(project, sort_keys=True).encode()
    snapshot = tmp_path / "snapshot-2"
    (snapshot / "packages").mkdir(parents=True)
    (snapshot / "packages" / "implementation-delivery.yaml").write_bytes(manifest_bytes)
    (snapshot / "project.yaml").write_bytes(project_bytes)
    reference = {
        "id": "chrona-delivery-roadmap", "kind": "project",
        "store": {"provider": "local", "identity": "chrona-test"}, "address": "project.yaml",
        "revision": {"token": "snapshot-2"}, "contentIdentity": f"sha256:{sha256(project_bytes).hexdigest()}",
    }
    reader = LocalSnapshotReader(tmp_path, "chrona-test")
    assert validate_snapshot(reference, reader) == []
    first = schedule_snapshot(reference, reader)
    second = schedule_snapshot(reference, reader)
    assert first.ok and second.ok and first.placements == second.placements
    draft = reference | {"revision": {"token": "Draft"}}
    try:
        schedule_snapshot(draft, reader)
    except Exception as error:
        assert getattr(error, "diagnostic_id") == "E_IMMUTABLE_SNAPSHOT_REQUIRED"
    else:
        raise AssertionError("Draft reference was evaluated")
