from chrona.commands.actual_commands import (
    MemoryActualStore,
    redo_actual_command,
    resolve_actual_observation,
    undo_actual_command,
)


def _actual_set():
    return {
        "version": "chrona/presentation/v0.1",
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
