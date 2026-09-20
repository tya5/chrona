from chrona.extensions.extension_registry import PackageRegistry
from chrona.extensions.package_lifecycle import lifecycle_summary


def test_lifecycle_summary_exposes_only_pinned_identity_and_diagnostics():
    manifest = {"packageId": "semiconductor", "version": "2.1.0", "source": {"provider": "registry", "identity": "approved"}, "contentIdentity": "sha256:semiconductor", "requires": {"projectFormats": ["timeline/v0.1"]}, "deprecated": True}
    reference = {key: manifest[key] for key in ("packageId", "version", "source", "contentIdentity")}
    result = PackageRegistry({("registry", "approved")}, [manifest]).resolve(reference, "timeline/v0.1")
    assert lifecycle_summary(result) == {"state": "verified", "packages": [{"packageId": "semiconductor", "version": "2.1.0", "source": {"provider": "registry", "identity": "approved"}, "contentIdentity": "sha256:semiconductor", "state": "deprecated"}], "diagnostics": []}


def test_lifecycle_summary_makes_rejection_visible_without_fallback():
    result = PackageRegistry(set(), []).resolve({"packageId": "missing", "version": "1.0.0", "source": {}, "contentIdentity": "sha256:missing"}, "timeline/v0.1")
    assert lifecycle_summary(result) == {"state": "rejected", "packages": [], "diagnostics": ["E_PACKAGE_MISSING"]}
