"""Immutable release-package assembly over output and acceptance manifests."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any

from .output import OutputResult


def _identity(value: Any) -> str:
    return "sha256:" + sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


@dataclass(frozen=True)
class ReleasePackageResult:
    package: dict[str, Any]
    artifact: str | None
    diagnostics: tuple[str, ...]


def create_release_package(acceptance: dict[str, Any], output: OutputResult) -> ReleasePackageResult:
    """Create a publishable package only for one fully accepted output closure."""
    output_manifest = output.manifest
    excluded = [entry["id"] for entry in acceptance.get("useCases", []) if entry.get("disposition") != "accepted"]
    evaluation = acceptance.get("inputClosure", {}).get("evaluationIdentity")
    target = acceptance.get("output", {})
    bindings_match = (
        evaluation == output_manifest.get("evaluationIdentity")
        and target.get("target") == output_manifest.get("target")
        and target.get("targetVersion") == output_manifest.get("targetVersion")
    )
    base = {
        "version": "chrona/release-package/v0.2",
        "releaseId": acceptance.get("releaseId", ""),
        "evaluationIdentity": evaluation,
        "output": {"target": target.get("target"), "targetVersion": target.get("targetVersion"), "manifestIdentity": _identity(output_manifest)},
        "acceptance": {"manifestIdentity": _identity(acceptance)},
    }
    if excluded or not bindings_match or output.artifact is None:
        diagnostics = ("E_RELEASE_ACCEPTANCE_INCOMPLETE",) if excluded else ("E_RELEASE_BINDING",)
        return ReleasePackageResult(base | {"status": "blocked", "artifact": {"contentIdentity": None}, "diagnostics": list(diagnostics)}, None, diagnostics)
    artifact_identity = _identity(output.artifact)
    return ReleasePackageResult(base | {"status": "published", "artifact": {"contentIdentity": artifact_identity}, "diagnostics": list(output.diagnostics)}, output.artifact, output.diagnostics)


def validate_release_package(package: dict[str, Any], acceptance: dict[str, Any], output: OutputResult) -> tuple[str, ...]:
    """Validate the package's exact closure binding without reparsing product state."""
    expected = create_release_package(acceptance, output).package
    for key in ("releaseId", "evaluationIdentity", "output", "acceptance", "artifact", "status"):
        if package.get(key) != expected.get(key):
            return ("E_RELEASE_BINDING",)
    if package.get("status") == "published" and output.artifact is None:
        return ("E_RELEASE_ARTIFACT",)
    return ()
