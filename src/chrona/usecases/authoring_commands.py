"""Typed guided-workspace command use case above the presentation-free CAS writer."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from chrona.presentation.contracts import ClosureIdentity, ContractError, parse_contract
from chrona.core.identity import content_identity


def parse_authoring_command(path: Path) -> dict[str, Any]:
    from chrona.resources import safe_load, schema_document
    from chrona.schema_diagnostics import explain_errors
    import jsonschema
    value = safe_load(path.read_text(encoding="utf-8"))
    schema = schema_document("authoring-command-v0.1.schema.yaml")
    if not isinstance(value, dict):
        raise ValueError("E_AUTHORING_COMMAND_SCHEMA: expected object")
    errors = tuple(jsonschema.Draft202012Validator(schema).iter_errors(value))
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
    workspace_path: Path, command: dict[str, Any], *, read_workspace: Any, cas_write: Any,
    cas_write_aggregate: Any | None = None,
) -> dict[str, Any]:
    """Validate source intent; persistence is injected by the outer application adapter."""
    current = read_workspace(workspace_path)
    base = content_identity(current)
    if command["target"]["path"] != workspace_path.name or command["baseRevision"] != base:
        return _rejected(command, "E_AUTHORING_BASE_REVISION", base)
    try:
        if command["type"] == "materializePresentationPreset":
            if cas_write_aggregate is None:
                raise ValueError("E_AUTHORING_AGGREGATE_WRITER")
            from chrona.usecases.authoring_materialization import materialization_candidate
            candidate, candidates = materialization_candidate(
                workspace_path, current, directory=command["payload"].get("directory", "presentation"),
            )
            result = cas_write_aggregate(workspace_path, base, candidates)
            if result is None:
                return _rejected(command, "E_AUTHORING_BASE_REVISION", base)
            return _accepted(command, base, result, reversible=False)
        candidate = deepcopy(current)
        _apply(candidate, command)
        parse_contract(ClosureIdentity("authoring-workspace", str(candidate["id"]), "draft", content_identity(candidate)), candidate)
        result = cas_write(workspace_path, base, candidate)
        if result is None:
            return _rejected(command, "E_AUTHORING_BASE_REVISION", base)
    except FileExistsError as error:
        return _rejected(command, str(error) if str(error).startswith("E_") else "E_AUTHORING_MATERIALIZE_COLLISION", base)
    except (KeyError, ContractError, ValueError) as error:
        code = getattr(error, "code", str(error))
        detail = getattr(error, "detail", "")
        return _rejected(command, code if code.startswith("E_") else "E_AUTHORING_COMMAND", base, detail=detail)
    return _accepted(command, base, result)


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
        raise ValueError("E_AUTHORING_COMMAND")


def _accepted(command: dict[str, Any], workspace: str, result: str, *, reversible: bool | None = None) -> dict[str, Any]:
    value = {
        "version": "chrona/authoring-command-result/v0.1", "status": "accepted",
        "commandId": command["commandId"], "commandBaseRevision": command["baseRevision"],
        "workspaceRevision": workspace, "resultRevision": result, "diagnostics": [],
    }
    return value if reversible is None else value | {"reversible": reversible}


def _rejected(command: dict[str, Any], code: str, base: str, *, detail: str = "") -> dict[str, Any]:
    diagnostic: dict[str, Any] = {"code": code}
    if detail:
        diagnostic["detail"] = detail
    if code == "E_AUTHORING_BASE_REVISION":
        diagnostic |= {
            "expectedRevision": base, "receivedRevision": command.get("baseRevision"),
            "detail": (f"workspace revision expected {base}; command declared "
                       f"{command.get('baseRevision')}; run `chrona workspace revision "
                       f"{command['target']['path']}` and retry"),
        }
    return {
        "version": "chrona/authoring-command-result/v0.1", "status": "rejected",
        "commandId": command.get("commandId"), "commandBaseRevision": command.get("baseRevision"),
        "workspaceRevision": base, "resultRevision": None, "diagnostics": [diagnostic],
    }
