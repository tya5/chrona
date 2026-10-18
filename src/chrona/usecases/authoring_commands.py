"""Typed guided-workspace command preparation above the transaction port."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from chrona.core.identity import content_identity
from chrona.presentation.contracts import ClosureIdentity, ContractError, parse_contract
from chrona.storage.file_transaction import PreparedFileMutation


def parse_authoring_command(path: Path) -> dict[str, Any]:
    from chrona.resources import safe_load, schema_validator
    from chrona.schema_diagnostics import explain_errors
    value = safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("E_AUTHORING_COMMAND_SCHEMA: expected object")
    errors = tuple(schema_validator("authoring-command-v0.1.schema.yaml").iter_errors(value))
    if errors:
        violation = explain_errors(
            errors, resource_kind="authoring-command", resource_identity=value.get("commandId") if isinstance(value.get("commandId"), str) else None,
        )
        raise ValueError(f"E_AUTHORING_COMMAND_SCHEMA: {violation.pointer}: {violation.message}")
    return value


def workspace_revision(workspace_path: Path, *, read_workspace: Any) -> str:
    """Return the one local CAS precondition for a validated workspace."""
    return content_identity(read_workspace(workspace_path))


def apply_authoring_command(
    workspace_path: Path, command: dict[str, Any], *, transact: Any,
) -> dict[str, Any]:
    """Prepare source intent and delegate all canonical publication to Engine."""
    def prepare(canonical_path: Path, current: dict[str, Any]) -> PreparedFileMutation:
        return prepare_authoring_command(canonical_path, current, command)

    def reject(code: str, observed_identity: str, detail: str = "") -> dict[str, Any]:
        return _rejected(command, code, observed_identity, detail=detail)

    return transact(
        workspace_path, command, prepare=prepare, reject=reject,
        verify_receipt=verify_authoring_receipt,
    )


def prepare_authoring_command(
    canonical_path: Path, current: dict[str, Any], command: dict[str, Any],
) -> PreparedFileMutation:
    """Return complete validated bytes and exact result without canonical writes."""
    base = content_identity(current)
    if command["target"]["path"] != canonical_path.name:
        return _prepared_rejection(command, "E_AUTHORING_TARGET_MISMATCH", base,
                                   detail=f"target path must name canonical workspace {canonical_path.name!r}")
    if command["baseRevision"] != base:
        return _prepared_rejection(command, "E_AUTHORING_BASE_REVISION", base)
    try:
        if command["type"] == "materializePresentationPreset":
            from chrona.usecases.authoring_materialization import materialization_candidate
            explicit, files = materialization_candidate(
                canonical_path, current, directory=command["payload"].get("directory", "presentation"),
            )
            next_revision = content_identity(explicit)
            result = _accepted(command, base, next_revision, reversible=False)
            return PreparedFileMutation(files=files, result_revision=next_revision, result=result)

        candidate = deepcopy(current)
        _apply(candidate, command)
        parse_contract(ClosureIdentity("authoring-workspace", str(candidate["id"]), "draft", content_identity(candidate)), candidate)
        payload = yaml.safe_dump(candidate, allow_unicode=True, sort_keys=False).encode("utf-8")
        next_revision = content_identity(candidate)
        result = _accepted(command, base, next_revision)
        return PreparedFileMutation(files={canonical_path.name: payload}, result_revision=next_revision, result=result)
    except FileExistsError as error:
        message = str(error)
        if message.startswith("E_"):
            return _prepared_rejection(command, message, base)
        return _prepared_rejection(command, "E_AUTHORING_MATERIALIZE_COLLISION", base, detail=message)
    except (KeyError, ContractError, ValueError) as error:
        code = getattr(error, "code", str(error))
        detail = getattr(error, "detail", "")
        return _prepared_rejection(command, code if code.startswith("E_") else "E_AUTHORING_COMMAND", base, detail=detail)


def verify_authoring_receipt(
    request: dict[str, Any], result: dict[str, Any], before_identity: str, after_identity: str,
) -> None:
    """Validate persisted replay data before Engine returns it as authoritative."""
    from chrona.resources import schema_validator

    request_errors = tuple(schema_validator("authoring-command-v0.1.schema.yaml").iter_errors(request))
    result_errors = tuple(schema_validator("authoring-command-result-v0.1.schema.yaml").iter_errors(result))
    if request_errors or result_errors:
        raise ValueError("E_AUTHORING_REPLAY_UNAVAILABLE: retained request or result violates its schema")
    if (
        result["status"] != "accepted"
        or result["commandId"] != request["commandId"]
        or result["commandBaseRevision"] != request["baseRevision"]
        or result["workspaceRevision"] != before_identity
        or result["resultRevision"] != after_identity
    ):
        raise ValueError("E_AUTHORING_REPLAY_UNAVAILABLE: retained result identities do not match the accepted request")


def _apply(candidate: dict[str, Any], command: dict[str, Any]) -> None:
    body, payload, command_type = candidate["body"], command["payload"], command["type"]
    if command_type == "setWorkspaceTask":
        task, tasks = payload["task"], body["project"]["tasks"]
        index = next((i for i, item in enumerate(tasks) if item["id"] == task["id"]), None)
        tasks.append(task) if index is None else tasks.__setitem__(index, task)
    elif command_type == "setWorkspaceActual":
        actual, actuals = payload["actual"], body.setdefault("actuals", [])
        index = next((i for i, item in enumerate(actuals) if item["taskId"] == actual["taskId"]), None)
        actuals.append(actual) if index is None else actuals.__setitem__(index, actual)
    elif command_type == "selectPresentationPreset":
        body["presentation"]["binding"]["preset"] = payload["preset"]
    elif command_type == "setPresentationOverride":
        body["presentation"]["binding"]["overrides"] = payload["overrides"]
    else:
        raise ValueError(f"E_AUTHORING_COMMAND: unsupported command type {command_type!r}")


def _accepted(command: dict[str, Any], workspace: str, result: str, *, reversible: bool | None = None) -> dict[str, Any]:
    value = {
        "version": "chrona/authoring-command-result/v0.1", "status": "accepted",
        "commandId": command["commandId"], "commandBaseRevision": command["baseRevision"],
        "workspaceRevision": workspace, "resultRevision": result, "diagnostics": [],
    }
    return value if reversible is None else value | {"reversible": reversible}


def _prepared_rejection(command: dict[str, Any], code: str, base: str, *, detail: str = "") -> PreparedFileMutation:
    result = _rejected(command, code, base, detail=detail)
    return PreparedFileMutation(files={}, result_revision=None, result=result)


def _rejected(command: dict[str, Any], code: str, base: str, detail: str = "") -> dict[str, Any]:
    code, _, inline_detail = code.partition(":")
    detail = detail or inline_detail.strip()
    diagnostic: dict[str, Any] = {"code": code}
    if detail:
        diagnostic["detail"] = detail
    if code == "E_AUTHORING_BASE_REVISION":
        diagnostic |= {
            "expectedRevision": base, "receivedRevision": command.get("baseRevision"),
            "detail": (f"workspace revision expected {base}; command declared "
                       f"{command.get('baseRevision')}; query workspace_revision for "
                       f"{command['target']['path']!r} and retry"),
        }
    return {
        "version": "chrona/authoring-command-result/v0.1", "status": "rejected",
        "commandId": command.get("commandId"), "commandBaseRevision": command.get("baseRevision"),
        "workspaceRevision": base, "resultRevision": None, "diagnostics": [diagnostic],
    }
