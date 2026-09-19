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


@dataclass(frozen=True)
class FederationTrustPolicy:
    """Allow-list trust boundary for provider-neutral Federation references."""

    allowed_sources: frozenset[tuple[str, str]]

    def accepts(self, reference: dict[str, Any]) -> bool:
        store = reference.get("store", {})
        return (store.get("provider"), store.get("identity")) in self.allowed_sources


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


def resolve_federation_v2(
    plan: dict[str, Any],
    available_exports: Iterable[tuple[dict[str, Any], dict[str, Any]]],
    trust: FederationTrustPolicy,
) -> FederationResult:
    """Resolve only exact, trusted v0.2 references; never select a latest export."""
    available = {
        (reference.get("revision", {}).get("token"), reference.get("contentIdentity")): body
        for reference, body in available_exports
    }
    resolved: dict[str, dict[str, Any]] = {}
    namespaces: set[str] = set()
    diagnostics: list[str] = []
    for entry in plan.get("exports", []):
        reference = entry.get("export", {})
        namespace = entry.get("presentation", {}).get("namespace")
        if namespace in namespaces:
            diagnostics.append("FED-NAMESPACE-COLLISION")
            continue
        namespaces.add(namespace)
        if not trust.accepts(reference):
            diagnostics.append("FED-STORE-UNTRUSTED")
            continue
        body = available.get((reference.get("revision", {}).get("token"), reference.get("contentIdentity")))
        if body is None:
            diagnostics.append("FED-EXPORT-UNAVAILABLE")
            continue
        if body.get("id") != reference.get("id") or body.get("kind") != "timeline-export" or body.get("project", {}).get("id") != reference.get("projectId"):
            diagnostics.append("FED-EXPORT-MISMATCH")
            continue
        resolved[entry["id"]] = deepcopy(body)
    if diagnostics:
        return FederationResult("rejected", {}, tuple(sorted(set(diagnostics))))
    return FederationResult("resolved", resolved, ())


def execute_federation_command(
    store: Any,
    command: dict[str, Any],
    available_exports: Iterable[tuple[dict[str, Any], dict[str, Any]]],
    trust: FederationTrustPolicy,
) -> FederationResult:
    """Execute only parent-side v0.2 pin/unpin through the Store CAS boundary."""
    snapshot = store.read()
    if command.get("version") != "chrona/federation-command/v0.2" or command.get("target", {}).get("kind") != "federation-plan":
        return FederationResult("rejected", {}, ("FED-COMMAND-SHAPE",))
    if command.get("baseRevision", {}).get("token") != snapshot.revision:
        return FederationResult("rejected", {}, ("E_CONFLICT",))
    candidate = deepcopy(snapshot.project)
    payload = command.get("payload", {})
    federation_id = payload.get("federationId")
    entries = candidate.get("exports", [])
    index = next((i for i, entry in enumerate(entries) if entry.get("id") == federation_id), None)
    if command.get("type") == "pinFederatedExport":
        if not federation_id or not isinstance(payload.get("export"), dict) or not isinstance(payload.get("presentation"), dict):
            return FederationResult("rejected", {}, ("FED-COMMAND-SHAPE",))
        entry = {"id": federation_id, "export": deepcopy(payload["export"]), "presentation": deepcopy(payload["presentation"])}
        if index is None:
            entries.append(entry)
        else:
            entries[index] = entry
        checked = resolve_federation_v2(candidate, available_exports, trust)
        if checked.status != "resolved":
            return checked
    elif command.get("type") == "unpinFederatedExport":
        if index is None:
            return FederationResult("rejected", {}, ("FED-EXPORT-UNAVAILABLE",))
        entries.pop(index)
    else:
        return FederationResult("rejected", {}, ("FED-COMMAND-SHAPE",))
    persisted = store.write(snapshot.revision, candidate)
    if persisted is None:
        return FederationResult("rejected", {}, ("E_CONFLICT",))
    return FederationResult("accepted", {"plan": persisted.project, "resultRevision": persisted.revision}, ())
