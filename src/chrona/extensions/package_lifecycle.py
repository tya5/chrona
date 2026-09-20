"""Read-only profile lifecycle presentation from verified registry results."""
from __future__ import annotations
from typing import Any

from chrona.extensions.extension_registry import PackageResolution


def lifecycle_summary(result: PackageResolution) -> dict[str, Any]:
    """Expose pinned package identities and diagnostics without changing the closure."""
    packages = [
        {
            "packageId": manifest["packageId"],
            "version": manifest["version"],
            "source": dict(manifest["source"]),
            "contentIdentity": manifest["contentIdentity"],
            "state": "deprecated" if manifest.get("deprecated") else result.state,
        }
        for manifest in result.manifests
    ]
    return {"state": result.state, "packages": packages, "diagnostics": list(result.diagnostics)}
