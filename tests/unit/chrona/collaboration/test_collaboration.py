from chrona.collaboration.collaboration import AuditLog, resolve_merge_conflict, submit, replica_status
from chrona.storage.revision_store import MemoryRevisionStore


def test_stale_and_policy_are_explicit():
    store = MemoryRevisionStore({'version': 'timeline/v0.1', 'project': {'id': 'p'}, 'objects': {}, 'relations': []})
    base = store.read()
    store.write(base.revision, {'version': 'timeline/v0.1', 'project': {'id': 'p2'}, 'objects': {}, 'relations': []})
    command = {'commandId': 'x', 'baseRevision': base.revision, 'actor': {'principal': 'a'}, 'payload': {}}
    audit = AuditLog()
    assert submit(store, command, {'decision': 'deny'}, '2027', audit).diagnostic == 'E_AUTHORIZATION_DENIED'
    conflict = submit(store, command, {'decision': 'allow'}, '2027', audit).conflict
    assert conflict['kind'] == 'semantic' and len(audit.records()) == 2


def test_explicit_resolution_creates_revision_with_both_parents_and_audit():
    original = {'version': 'timeline/v0.1', 'project': {'id': 'old'}, 'objects': {}, 'relations': []}
    current = {'version': 'timeline/v0.1', 'project': {'id': 'new'}, 'objects': {}, 'relations': []}
    store = MemoryRevisionStore(original)
    base = store.read()
    current_snapshot = store.write(base.revision, current)
    audit = AuditLog()
    stale = {'commandId': 'stale', 'baseRevision': base.revision, 'actor': {'principal': 'planner'}, 'payload': {}}
    conflict = submit(store, stale, {'decision': 'allow'}, '2027', audit).conflict
    resolution = {'commandId': 'resolve', 'type': 'resolveMergeConflict', 'baseRevision': current_snapshot.revision,
                  'actor': {'principal': 'planner'}, 'payload': {'conflictId': conflict['id'], 'selected': 'left'}}
    result = resolve_merge_conflict(store, conflict, resolution, {'decision': 'allow'}, '2027', audit)
    assert result.status == 'accepted'
    assert store.read().parents == tuple(conflict['parents'])
    assert store.read().project == original
    assert audit.records()[-1].result_revision == result.revision


def test_replica_never_claims_unseen_tip():
    assert replica_status('r1', 'r2').diagnostic == 'I_REPLICA_BEHIND'
