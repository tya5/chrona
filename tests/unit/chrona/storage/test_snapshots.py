from chrona.storage.revision_store import MemoryRevisionStore
from chrona.storage.snapshots import LocalBaselineRegistry, MemorySnapshotStore, capture_baseline_v02, capture_snapshot
import chrona.storage.publication as publication


def _project():
    return {"version": "timeline/v0.7", "project": {"id": "controller"}, "objects": {}, "relations": []}


def _reference(snapshot):
    return {"id": "controller", "kind": "project", "store": {"provider": "local", "identity": "project-store"}, "address": "project.yaml", "revision": {"token": snapshot.revision}, "contentIdentity": snapshot.content_identity}


def _assert_diagnostic(result, code, *operands):
    assert result.status == "rejected"
    assert len(result.diagnostics) == 1
    diagnostic = result.diagnostics[0]
    assert diagnostic.startswith(f"{code}: ")
    for operand in operands:
        assert operand in diagnostic


def test_capture_publishes_only_an_immutable_project_reference():
    project_store = MemoryRevisionStore(_project())
    project = project_store.read()
    snapshot_store = MemorySnapshotStore("presentation-store")
    result = capture_snapshot(project_store, project.revision, _reference(project), "baseline-q2", snapshot_store)
    assert result.status == "accepted"
    assert result.snapshot_ref["body"]["project"] == _reference(project)
    assert snapshot_store.read("baseline-q2") == result.snapshot_ref
    assert project_store.read().project == _project()


def test_capture_rejects_stale_or_identity_mismatched_or_duplicate_publication():
    project_store = MemoryRevisionStore(_project())
    project = project_store.read()
    snapshot_store = MemorySnapshotStore("presentation-store")
    conflict = capture_snapshot(project_store, "expected-revision-q2", _reference(project), "baseline-q2", snapshot_store)
    _assert_diagnostic(conflict, "E_CONFLICT", "baseline-q2", "expected-revision-q2", project.revision)
    bad = _reference(project) | {"contentIdentity": "sha256:identity-from-reference"}
    mismatch = capture_snapshot(project_store, project.revision, bad, "baseline-q2", snapshot_store)
    _assert_diagnostic(mismatch, "E_CONTENT_IDENTITY", "baseline-q2", "controller", "sha256:identity-from-reference", project.content_identity)
    assert capture_snapshot(project_store, project.revision, _reference(project), "baseline-q2", snapshot_store).status == "accepted"
    duplicate = capture_snapshot(project_store, project.revision, _reference(project), "baseline-q2", snapshot_store)
    _assert_diagnostic(duplicate, "E_SNAPSHOT_EXISTS", "baseline-q2", "controller")


def test_capture_store_reference_diagnostic_names_snapshot_and_bad_reference():
    project_store = MemoryRevisionStore(_project())
    project = project_store.read()
    snapshot_store = MemorySnapshotStore("presentation-store")

    wrong_kind = _reference(project) | {"id": "foreign-project", "kind": "icon-catalog"}
    result = capture_snapshot(project_store, project.revision, wrong_kind, "baseline-q2", snapshot_store)
    _assert_diagnostic(result, "E_STORE_REFERENCE", "baseline-q2", "foreign-project", "icon-catalog")

    wrong_id = _reference(project) | {"id": "foreign-project"}
    result = capture_snapshot(project_store, project.revision, wrong_id, "baseline-q3", snapshot_store)
    _assert_diagnostic(result, "E_STORE_REFERENCE", "baseline-q3", "foreign-project", "controller")

    missing_address = _reference(project) | {"address": ""}
    result = capture_snapshot(project_store, project.revision, missing_address, "baseline-q4", snapshot_store)
    _assert_diagnostic(result, "E_STORE_REFERENCE", "baseline-q4", "controller", "address present=False")


def test_v02_capture_is_append_only_and_registry_reference_is_verifiable(tmp_path):
    project_store = MemoryRevisionStore(_project())
    project = project_store.read()
    registry = LocalBaselineRegistry(tmp_path, "baselines")
    result = capture_baseline_v02(project_store, project.revision, _reference(project), "q2", registry)
    assert result.status == "accepted"
    assert registry.read(result.snapshot_ref)
    duplicate = capture_baseline_v02(project_store, project.revision, _reference(project), "q2", registry)
    _assert_diagnostic(duplicate, "E_BASELINE_EXISTS", "q2", "controller")

    unsafe_root = tmp_path / "unsafe"
    unsafe_id = capture_baseline_v02(project_store, project.revision, _reference(project), "../q3", LocalBaselineRegistry(unsafe_root, "baselines"))
    _assert_diagnostic(unsafe_id, "E_BASELINE_EXISTS", "../q3", "safe Store segment", "controller")
    assert not unsafe_root.exists()


def test_v02_capture_does_not_require_hard_link_support(tmp_path, monkeypatch):
    monkeypatch.setattr(publication.os, "link", lambda *_args: (_ for _ in ()).throw(OSError("unsupported")))
    project_store = MemoryRevisionStore(_project())
    result = capture_baseline_v02(project_store, project_store.read().revision, _reference(project_store.read()), "q2", LocalBaselineRegistry(tmp_path, "baselines"))
    assert result.status == "accepted"


def test_v02_capture_rejects_stale_or_mismatched_project_reference(tmp_path):
    project_store = MemoryRevisionStore(_project())
    project = project_store.read()
    registry = LocalBaselineRegistry(tmp_path, "baselines")
    conflict = capture_baseline_v02(project_store, "expected-revision-q2", _reference(project), "q2", registry)
    _assert_diagnostic(conflict, "E_CONFLICT", "q2", "expected-revision-q2", project.revision)
    mismatch = capture_baseline_v02(project_store, project.revision, _reference(project) | {"id": "foreign-project"}, "q2", registry)
    _assert_diagnostic(mismatch, "E_BASELINE_REFERENCE", "q2", "controller", "foreign-project", project.revision, project.content_identity)
    bad_identity = capture_baseline_v02(
        project_store, project.revision,
        _reference(project) | {"contentIdentity": "sha256:baseline-reference-identity"},
        "q3", registry,
    )
    _assert_diagnostic(bad_identity, "E_BASELINE_REFERENCE", "q3", "sha256:baseline-reference-identity", project.content_identity)


def test_capture_accepts_revision_only_reference_and_publishes_computed_identity(tmp_path):
    project_store = MemoryRevisionStore(_project())
    project = project_store.read()
    revision_only = _reference(project) | {"contentIdentity": None}
    revision_only.pop("contentIdentity")
    snapshot = capture_snapshot(project_store, project.revision, revision_only, "baseline-q2", MemorySnapshotStore("presentation-store"))
    assert snapshot.status == "accepted"
    assert snapshot.snapshot_ref["body"]["project"]["contentIdentity"] == project.content_identity

    baseline = capture_baseline_v02(project_store, project.revision, revision_only, "q2", LocalBaselineRegistry(tmp_path, "baselines"))
    assert baseline.status == "accepted"
    assert baseline.snapshot_ref["contentIdentity"].startswith("sha256:")
    assert set(baseline.snapshot_ref) == {"id", "kind", "store", "address", "revision", "contentIdentity"}
