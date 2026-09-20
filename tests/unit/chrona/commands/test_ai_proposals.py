from copy import deepcopy

import yaml

from chrona.commands.ai_proposals import command_fingerprint, execute_ai_proposal
from chrona.storage.revision_store import MemoryRevisionStore


def _project():
    return {
        "version": "timeline/v0.1", "project": {"id": "p"},
        "extensions": [], "objects": {"gate": {"type": "milestone", "schedule": {"mode": "fixed", "at": "2026-10-01"}}}, "relations": [],
    }


def _proposal(base):
    return {
        "version": "chrona/ai-command-proposal/v0.1", "proposalId": "proposal-1",
        "actor": {"principal": "planner", "agentIdentity": "agent", "modelIdentity": "model-v1"}, "intent": "Rename gate",
        "proposedCommand": {"version": "chrona/command/v0.1", "commandId": "command-1", "type": "setTypedField", "target": {"kind": "project", "id": "p", "path": "project.yaml"}, "baseRevision": base, "payload": {"objectId": "gate", "field": "owner", "value": "fw"}},
    }


def _decision(proposal, decision="allow"):
    return {"version": "chrona/authorization-decision/v0.1", "proposalId": proposal["proposalId"], "commandFingerprint": command_fingerprint(proposal["proposedCommand"]), "principal": proposal["actor"]["principal"], "policyVersion": "policy-v1", "decision": decision}


def test_ai_proposal_executes_only_the_authorized_registered_command():
    store = MemoryRevisionStore(_project())
    proposal = _proposal(store.read().revision)
    result = execute_ai_proposal(store, proposal, _decision(proposal), {})
    assert result.status == "accepted"
    assert store.read().project["objects"]["gate"]["fields"]["owner"] == "fw"
    assert result.provenance["proposalId"] == "proposal-1"


def test_ai_proposal_rejects_denial_or_any_post_approval_change():
    store = MemoryRevisionStore(_project())
    proposal = _proposal(store.read().revision)
    denied = execute_ai_proposal(store, proposal, _decision(proposal, "deny"), {})
    assert denied.diagnostics == ("E_AUTHORIZATION_DENIED",)
    changed = deepcopy(proposal); changed["proposedCommand"]["payload"]["value"] = "other"
    rejected = execute_ai_proposal(store, changed, _decision(proposal), {})
    assert rejected.diagnostics == ("E_AUTHORIZATION_BINDING",)
    assert "fields" not in store.read().project["objects"]["gate"]
