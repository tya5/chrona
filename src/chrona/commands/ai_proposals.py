"""AI Command proposals gated by an exact authorization decision."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any

from chrona.commands.commands import CommandResult, execute_set_typed_field


def command_fingerprint(command: dict[str, Any]) -> str:
    """Return the stable identity that an authorization decision approves."""
    payload = json.dumps(command, sort_keys=True, separators=(",", ":"), default=str).encode()
    return f"sha256:{sha256(payload).hexdigest()}"


@dataclass(frozen=True)
class AIProposalResult:
    status: str
    command: CommandResult | None
    diagnostics: tuple[str, ...]
    provenance: dict[str, str]


def execute_ai_proposal(
    store: Any,
    proposal: dict[str, Any],
    decision: dict[str, Any],
    package_manifests: dict[str, dict[str, Any]],
) -> AIProposalResult:
    """Authorize and execute one registered AI proposal without source rewriting."""
    command = proposal.get("proposedCommand", {})
    actor = proposal.get("actor", {})
    provenance = {
        "proposalId": str(proposal.get("proposalId", "")),
        "principal": str(actor.get("principal", "")),
        "policyVersion": str(decision.get("policyVersion", "")),
        "commandFingerprint": command_fingerprint(command),
    }
    if proposal.get("version") != "chrona/ai-command-proposal/v0.1" or decision.get("version") != "chrona/authorization-decision/v0.1":
        return AIProposalResult("rejected", None, ("E_AI_PROPOSAL_FORMAT",), provenance)
    if not provenance["proposalId"] or not provenance["principal"]:
        return AIProposalResult("rejected", None, ("E_AI_PROPOSAL_FORMAT",), provenance)
    if decision.get("proposalId") != proposal.get("proposalId") or decision.get("principal") != actor.get("principal"):
        return AIProposalResult("rejected", None, ("E_AUTHORIZATION_BINDING",), provenance)
    if decision.get("commandFingerprint") != provenance["commandFingerprint"]:
        return AIProposalResult("rejected", None, ("E_AUTHORIZATION_BINDING",), provenance)
    if decision.get("decision") != "allow":
        return AIProposalResult("rejected", None, ("E_AUTHORIZATION_DENIED",), provenance)
    if command.get("version") != "chrona/command/v0.1" or command.get("type") != "setTypedField" or command.get("target", {}).get("kind") != "project":
        return AIProposalResult("rejected", None, ("E_COMMAND_TYPE",), provenance)
    fields = command.get("payload", {})
    if not all(isinstance(fields.get(key), str) and fields[key] for key in ("objectId", "field")) or "value" not in fields:
        return AIProposalResult("rejected", None, ("E_COMMAND_FORMAT",), provenance)
    result = execute_set_typed_field(
        store, command.get("baseRevision", ""), package_manifests,
        fields["objectId"], fields["field"], fields["value"], command.get("commandId", ""),
    )
    return AIProposalResult(result.status, result, result.diagnostics, provenance)
