"""Pinned declarative extension-package closure resolution for M8."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PackageResolution:
    state: str
    manifests: tuple[dict[str, Any], ...]
    diagnostics: tuple[str, ...]


class PackageRegistry:
    def __init__(self, trusted_sources: set[tuple[str, str]], manifests: list[dict[str, Any]]):
        self.trusted_sources = trusted_sources
        self.manifests = {(item.get("packageId"), item.get("version")): item for item in manifests}

    def resolve(self, reference: dict[str, Any], project_format: str) -> PackageResolution:
        closure: list[dict[str, Any]] = []
        visiting: set[tuple[str, str]] = set()
        resolved: set[tuple[str, str]] = set()

        def visit(ref: dict[str, Any]) -> str | None:
            key = (ref.get("packageId"), ref.get("version"))
            if key in visiting:
                return "E_PACKAGE_DEPENDENCY_CYCLE"
            if key in resolved:
                return None
            manifest = self.manifests.get(key)
            if manifest is None:
                return "E_PACKAGE_MISSING"
            source = manifest.get("source", {})
            if (source.get("provider"), source.get("identity")) not in self.trusted_sources:
                return "E_PACKAGE_UNTRUSTED"
            if ref.get("contentIdentity") != manifest.get("contentIdentity"):
                return "E_CONTENT_IDENTITY"
            if "executableEntry" in manifest or "code" in manifest:
                return "E_PACKAGE_EXECUTABLE_CONTENT"
            formats = manifest.get("requires", {}).get("projectFormats", [project_format])
            if project_format not in formats:
                return "E_PACKAGE_INCOMPATIBLE"
            visiting.add(key)
            for dependency in sorted(manifest.get("dependencies", []), key=lambda item: (item.get("packageId", ""), item.get("version", ""))):
                diagnostic = visit(dependency)
                if diagnostic:
                    return diagnostic
            visiting.remove(key)
            resolved.add(key)
            closure.append(manifest)
            return None

        diagnostic = visit(reference)
        return PackageResolution("verified" if not diagnostic else "rejected", tuple(closure), () if not diagnostic else (diagnostic,))


def resolve_evaluation_packages(registry: PackageRegistry, references: list[dict[str, Any]], project_format: str) -> tuple[dict[str, dict[str, Any]], tuple[str, ...]]:
    """Resolve explicit lifecycle references before Core/profile evaluation."""
    manifests: dict[str, dict[str, Any]] = {}
    diagnostics: list[str] = []
    for reference in references:
        result = registry.resolve(reference, project_format)
        diagnostics.extend(result.diagnostics)
        for manifest in result.manifests:
            existing = manifests.get(manifest["packageId"])
            if existing and existing.get("contentIdentity") != manifest.get("contentIdentity"):
                diagnostics.append("E_PACKAGE_DUPLICATE_IDENTITY")
            else:
                manifests[manifest["packageId"]] = manifest
    return manifests, tuple(sorted(set(diagnostics)))
