"""Read-only resolution of pinned Federation exports."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class FederationResult:
    status: str
    exports: dict[str, dict[str, Any]]
    diagnostics: tuple[str, ...]


def resolve_federation(
    plan: dict[str, Any],
    available_exports: Iterable[dict[str, Any]],
    trusted_repositories: set[str],
) -> FederationResult:
    """Select only exports pinned by a parent plan, without any write capability."""
    by_revision = {item.get("project", {}).get("revision"): item for item in available_exports}
    diagnostics: list[str] = []
    namespaces: set[str] = set()
    resolved: dict[str, dict[str, Any]] = {}
    for item in plan.get("exports", []):
        name = item.get("id", "")
        export = item.get("export", {})
        namespace = item.get("presentation", {}).get("namespace")
        if namespace in namespaces:
            diagnostics.append("FED-NAMESPACE-COLLISION")
            continue
        namespaces.add(namespace)
        if export.get("repository") not in trusted_repositories:
            diagnostics.append("FED-REPOSITORY-UNTRUSTED")
            continue
        revision = export.get("revision")
        available = by_revision.get(revision)
        if available is None:
            diagnostics.append("FED-EXPORT-UNAVAILABLE")
            continue
        if available.get("id") != export.get("id") or available.get("kind") != export.get("kind"):
            diagnostics.append("FED-EXPORT-MISMATCH")
            continue
        resolved[name] = deepcopy(available)
    if diagnostics:
        return FederationResult("rejected", {}, tuple(sorted(set(diagnostics))))
    return FederationResult("resolved", resolved, ())
