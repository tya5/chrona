from chrona.commands.actual_commands import (
    MemoryActualStore,
    LocalActualStore,
    apply_actual_intake_batch,
    redo_actual_command,
    resolve_actual_observation,
    undo_actual_command,
)


def _actual_set_v02():
    return {"version": "chrona/actual-set/v0.2", "kind": "actual-set", "id": "supplier-observed", "body": {"observations": []}}


def _batch(records):
    return {"source": {"system": "supplier", "contentIdentity": "sha256:" + "a" * 64}, "records": records}


def _actual_set():
    return {
        "version": "chrona/actual-set/v0.1",
        "kind": "actual-set",
        "id": "supplier-observed",
        "body": {
            "observations": [
                {
                    "id": "supplier:42",
                    "sequence": 1,
                    "externalIdentity": {"system": "supplier", "key": 42},
                    "alignment": "unmatched",
                    "actual": {"finish": "2026-04-20"},
                }
            ]
        },
    }


def test_explicit_actual_resolution_is_cas_bound_and_preserves_provenance():
    store = MemoryActualStore(_actual_set())
    base, _ = store.read()
    result = resolve_actual_observation(store, base, "supplier:42", "firmware", {"firmware"})
    assert result.status == "accepted"
    assert result.provenance == {"externalIdentity": {"system": "supplier", "key": 42}}
    observation = result.actual_set["body"]["observations"][0]
    assert observation["projectObjectId"] == "firmware"
    assert "externalIdentity" not in observation and "alignment" not in observation


def test_actual_resolution_rejects_stale_unknown_or_non_unmatched_observation():
    store = MemoryActualStore(_actual_set())
    base, _ = store.read()
    assert resolve_actual_observation(store, "actual:old", "supplier:42", "firmware", {"firmware"}).diagnostics == ("E_CONFLICT",)
    assert resolve_actual_observation(store, base, "supplier:42", "unknown", {"firmware"}).diagnostics == ("E_REFERENCE",)
    accepted = resolve_actual_observation(store, base, "supplier:42", "firmware", {"firmware"})
    assert accepted.status == "accepted"
    assert resolve_actual_observation(store, accepted.result_revision, "supplier:42", "firmware", {"firmware"}).diagnostics == ("E_ACTUAL_ALIGNMENT",)


def test_actual_undo_redo_create_new_revisions_without_rewriting_history():
    store = MemoryActualStore(_actual_set())
    base, original = store.read()
    accepted = resolve_actual_observation(store, base, "supplier:42", "firmware", {"firmware"}, command_id="resolve-42")
    undone = undo_actual_command(store, accepted.result_revision, "resolve-42")
    assert undone.status == "accepted"
    assert undone.result_revision != base
    assert undone.actual_set == original
    redone = redo_actual_command(store, undone.result_revision, "resolve-42")
    assert redone.status == "accepted"
    assert redone.result_revision not in {base, accepted.result_revision, undone.result_revision}
    assert redone.actual_set == accepted.actual_set


def test_intake_is_atomic_and_replay_safe_with_explicit_unmatched_records():
    store = MemoryActualStore(_actual_set_v02())
    base, _ = store.read()
    batch = _batch([
        {"externalKey": "FW-42", "projectObjectId": "firmware", "actual": {"finish": "2026-04-18"}},
        {"externalKey": "HW-19", "projectObjectId": "unknown", "actual": {"finish": "2026-04-20"}},
    ])
    accepted = apply_actual_intake_batch(store, base, batch, {"firmware"})
    assert accepted.status == "accepted" and accepted.dispositions == ("inserted", "inserted")
    observations = accepted.actual_set["body"]["observations"]
    assert observations[0]["projectObjectId"] == "firmware"
    assert observations[1]["alignment"] == "unmatched"
    assert observations[0]["sourceContentIdentity"] == batch["source"]["contentIdentity"]
    replay = apply_actual_intake_batch(store, accepted.result_revision, batch, {"firmware"})
    assert replay.status == "accepted" and replay.dispositions == ("alreadyPresent", "alreadyPresent")
    assert replay.result_revision == accepted.result_revision


def test_intake_rejects_duplicate_or_conflicting_records_without_partial_write():
    store = MemoryActualStore(_actual_set_v02())
    base, original = store.read()
    duplicate = _batch([{ "externalKey": "x", "actual": {"finish": "2026-04-18"}}, {"externalKey": "x", "actual": {"finish": "2026-04-19"}}])
    assert apply_actual_intake_batch(store, base, duplicate, set()).diagnostics == ("E_INTAKE_DUPLICATE_KEY",)
    accepted = apply_actual_intake_batch(store, base, _batch([{ "externalKey": "x", "actual": {"finish": "2026-04-18"}}]), set())
    conflict = _batch([{ "externalKey": "x", "actual": {"finish": "2026-04-19"}}])
    rejected = apply_actual_intake_batch(store, accepted.result_revision, conflict, set())
    assert rejected.diagnostics == ("E_ACTUAL_EXTERNAL_CONFLICT",)
    assert store.read()[1] == accepted.actual_set and original != accepted.actual_set


def test_resolution_keeps_v02_external_provenance_for_future_deduplication():
    store = MemoryActualStore(_actual_set_v02())
    base, _ = store.read()
    intake = apply_actual_intake_batch(store, base, _batch([{ "externalKey": "x", "actual": {"finish": "2026-04-18"}}]), set())
    resolved = resolve_actual_observation(store, intake.result_revision, "supplier:x", "firmware", {"firmware"})
    observation = resolved.actual_set["body"]["observations"][0]
    assert observation["externalIdentity"] == {"system": "supplier", "key": "x"}
    assert observation["sourceContentIdentity"] == "sha256:" + "a" * 64
    assert "alignment" not in observation and observation["projectObjectId"] == "firmware"


def test_local_actual_store_publishes_new_immutable_token_and_reopens(tmp_path):
    store = LocalActualStore(tmp_path, _actual_set_v02())
    base, _ = store.read()
    accepted = apply_actual_intake_batch(store, base, _batch([{ "externalKey": "x", "actual": {"finish": "2026-04-18"}}]), set())
    assert accepted.status == "accepted" and accepted.result_revision != base
    reopened = LocalActualStore(tmp_path, _actual_set_v02())
    assert reopened.read()[0] == accepted.result_revision
    assert (tmp_path / accepted.result_revision / "actuals" / "supplier-observed.yaml").is_file()
