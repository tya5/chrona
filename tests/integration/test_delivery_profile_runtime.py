from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import yaml

from chrona.storage.loader import schedule_snapshot, validate_snapshot
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.scheduling.scheduler import schedule
from chrona.core.validation import validate_project
from chrona.extensions.profiles import resolve_profile_diagnostics, validate_profiles

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
FIXTURES = ROOT / "conformance"


def _manifest():
    return {"implementation-delivery": yaml.safe_load((FIXTURES / "implementation-delivery-profile-v0.1.yaml").read_text())}


def _roadmap():
    project = yaml.safe_load((FIXTURES / "implementation-delivery-roadmap-v0.1.yaml").read_text())
    project.pop("expectedPlacements")
    return project


def test_resolved_delivery_profile_validates_and_schedules_through_core():
    project = _roadmap()
    diagnostics = validate_profiles(project, _manifest())
    assert validate_project(project, extension_diagnostics=diagnostics) == []
    assert schedule(project, extension_diagnostics=diagnostics).ok


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
    diagnostics = resolve_profile_diagnostics(project, reader)
    assert validate_project(project, extension_diagnostics=diagnostics) == []
    assert schedule(project, extension_diagnostics=diagnostics).ok
    project["extensions"][0]["resource"]["contentIdentity"] = "sha256:" + "0" * 64
    diagnostics = resolve_profile_diagnostics(project, reader)
    assert {item.id for item in validate_project(project, extension_diagnostics=diagnostics)} == {"E_CONTENT_IDENTITY", "IDP-PROFILE-006"}


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
