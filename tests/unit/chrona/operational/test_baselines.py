from hashlib import sha256
import yaml

from chrona.operational.baselines import compare_baseline


class Reader:
    def __init__(self, values): self.values = values
    def read(self, reference): return self.values[reference["address"]]


def _reference(address, kind, identifier, payload):
    return {"id": identifier, "kind": kind, "store": {"provider": "local", "identity": "test"}, "address": address, "revision": {"token": "r-" + address}, "contentIdentity": "sha256:" + sha256(payload).hexdigest()}


def _project(identifier, objects):
    return {"version": "timeline/v0.7", "project": {"id": identifier}, "extensions": [], "objects": objects, "relations": []}


def test_baseline_comparison_verifies_both_closures_and_returns_machine_result():
    before = _project("p", {})
    after = _project("p", {"gate": {"type": "milestone", "schedule": {"mode": "fixed-point", "at": "2026-10-01"}}})
    before_bytes, after_bytes = yaml.safe_dump(before).encode(), yaml.safe_dump(after).encode()
    before_ref = _reference("before.yaml", "project", "p", before_bytes)
    candidate_ref = _reference("after.yaml", "project", "p", after_bytes)
    baseline = {"version": "chrona/snapshot-ref/v0.2", "kind": "snapshot-ref", "id": "q2", "body": {"project": before_ref}}
    baseline_bytes = yaml.safe_dump(baseline).encode()
    baseline_ref = _reference("snapshots/q2.yaml", "snapshot-ref", "q2", baseline_bytes)
    reader = Reader({"before.yaml": before_bytes, "after.yaml": after_bytes, "snapshots/q2.yaml": baseline_bytes})
    result = compare_baseline(reader, baseline_ref, reader, candidate_ref)
    assert result["status"] == "accepted"
    assert result["comparison"]["changes"] == [{"kind": "object", "id": "gate", "change": "added"}]


def test_baseline_comparison_rejects_invalid_immutable_closure():
    bad = {"id": "q2", "kind": "snapshot-ref", "store": {"provider": "local", "identity": "test"}, "address": "missing.yaml", "revision": {"token": "r"}, "contentIdentity": "sha256:" + "a" * 64}
    candidate = bad | {"id": "p", "kind": "project"}
    result = compare_baseline(Reader({}), bad, Reader({}), candidate)
    assert result["status"] == "rejected"
    assert result["diagnostics"][0]["code"] == "E_BASELINE_REFERENCE"
