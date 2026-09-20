from chrona.storage.revision_store import MemoryRevisionStore
from chrona.storage.snapshots import MemorySnapshotStore, capture_snapshot


def _project():
    return {"version": "timeline/v0.1", "project": {"id": "controller"}, "objects": {}, "relations": []}


def _reference(snapshot):
    return {"id": "controller", "kind": "project", "store": {"provider": "local", "identity": "project-store"}, "address": "project.yaml", "revision": {"token": snapshot.revision}, "contentIdentity": snapshot.content_identity}


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
    assert capture_snapshot(project_store, "old", _reference(project), "baseline-q2", snapshot_store).diagnostics == ("E_CONFLICT",)
    bad = _reference(project) | {"contentIdentity": "sha256:bad"}
    assert capture_snapshot(project_store, project.revision, bad, "baseline-q2", snapshot_store).diagnostics == ("E_CONTENT_IDENTITY",)
    assert capture_snapshot(project_store, project.revision, _reference(project), "baseline-q2", snapshot_store).status == "accepted"
    assert capture_snapshot(project_store, project.revision, _reference(project), "baseline-q2", snapshot_store).diagnostics == ("E_SNAPSHOT_EXISTS",)
