"""Actual command operand detail survives projection to operational result rows."""

from chrona.commands.actual_commands import (
    MemoryActualStore,
    apply_actual_intake_batch,
    resolve_actual_observation,
)
from chrona.operational.resources import diagnostic_row


def _actual_set():
    return {
        "version": "chrona/actual-set/v0.3",
        "kind": "actual-set",
        "id": "observed",
        "body": {"observations": [{
            "id": "supplier:42",
            "sequence": 1,
            "externalIdentity": {"system": "supplier", "key": "42"},
            "sourceContentIdentity": "sha256:old",
            "alignment": "unmatched",
            "actual": {"finish": "2026-04-20"},
        }]},
    }


def _batch(records):
    return {"source": {"system": "supplier", "contentIdentity": "sha256:new"}, "records": records}


def _row(result):
    assert result.status == "rejected" and len(result.diagnostics) == 1
    return diagnostic_row(result.diagnostics[0])


def test_actual_rejection_operands_reach_result_row_messages():
    store = MemoryActualStore(_actual_set())
    base, _ = store.read()
    cases = [
        (apply_actual_intake_batch(store, base, _batch([{"externalKey": "bad", "actual": {}}]), set()),
         "E_INTAKE_SCHEMA", "records[0].actual"),
        (apply_actual_intake_batch(store, base, _batch([
            {"externalKey": "duplicate-key", "actual": {"finish": "2026-04-18"}},
            {"externalKey": "duplicate-key", "actual": {"finish": "2026-04-19"}},
        ]), set()), "E_INTAKE_DUPLICATE_KEY", "duplicate-key"),
        (apply_actual_intake_batch(store, base, _batch([
            {"externalKey": "42", "actual": {"finish": "2026-04-21"}},
        ]), set()), "E_ACTUAL_EXTERNAL_CONFLICT", "external key '42'"),
        (resolve_actual_observation(store, base, "supplier:42", "missing-object", set()),
         "E_REFERENCE", "projectObjectId 'missing-object'"),
        (resolve_actual_observation(store, base, "missing-observation", "object", {"object"}),
         "E_REFERENCE", "missing-observation"),
        (resolve_actual_observation(
            MemoryActualStore(_actual_set() | {"body": {"observations": [{
                **_actual_set()["body"]["observations"][0], "alignment": "aligned"} ]}}),
            "actual:0", "supplier:42", "object", {"object"}),
         "E_ACTUAL_ALIGNMENT", "supplier:42"),
        (apply_actual_intake_batch(store, "actual:stale", _batch([]), set()),
         "E_CONFLICT", "base revision 'actual:stale'"),
    ]

    for result, expected_code, expected_detail in cases:
        row = _row(result)
        assert row["code"] == expected_code
        assert expected_detail in row["message"]
