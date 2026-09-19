from copy import deepcopy
from pathlib import Path

import yaml

from chrona.federation import FederationTrustPolicy, resolve_federation, resolve_federation_v2


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "timeline-design" / "docs" / "fixtures" / "federation"
TRUSTED = {"git+https://example.invalid/firmware.git"}


def _load(name):
    return yaml.safe_load((FIXTURES / name).read_text())


def test_federation_selects_only_the_parent_pinned_export_and_repin_changes_it():
    available = [_load("firmware-program.yaml"), _load("firmware-program-next.yaml")]
    original = deepcopy(available)
    before = resolve_federation(_load("program-federation.yaml"), available, TRUSTED)
    after = resolve_federation(_load("program-federation-repinned.yaml"), available, TRUSTED)
    assert before.status == after.status == "resolved"
    assert before.exports["firmware"]["project"]["revision"].endswith("1111111111111111111111111111111111111111")
    assert after.exports["firmware"]["project"]["revision"].endswith("3333333333333333333333333333333333333333")
    assert available == original
    before.exports["firmware"]["project"]["id"] = "cannot-mutate-child"
    assert available == original


def test_federation_rejects_untrusted_and_unavailable_exports():
    available = [_load("firmware-program.yaml")]
    untrusted = resolve_federation(_load("invalid-untrusted-repository.yaml"), available, TRUSTED)
    assert untrusted.diagnostics == ("FED-REPOSITORY-UNTRUSTED",)
    unavailable = resolve_federation(_load("program-federation-repinned.yaml"), available, TRUSTED)
    assert unavailable.diagnostics == ("FED-EXPORT-UNAVAILABLE",)
    collision = resolve_federation(_load("invalid-namespace-collision.yaml"), available, TRUSTED)
    assert collision.diagnostics == ("FED-NAMESPACE-COLLISION",)


def test_v2_federation_trusts_store_identity_and_exact_pin_only():
    plan = _load("program-federation-v0.2.yaml")
    reference = plan["exports"][0]["export"]
    export = _load("firmware-program.yaml")
    export["project"]["id"] = "firmware"
    policy = FederationTrustPolicy(frozenset({("content", "firmware-release-key-1")}))
    resolved = resolve_federation_v2(plan, [(reference, export)], policy)
    assert resolved.status == "resolved"
    rejected = resolve_federation_v2(plan, [(reference, export)], FederationTrustPolicy(frozenset()))
    assert rejected.diagnostics == ("FED-STORE-UNTRUSTED",)
