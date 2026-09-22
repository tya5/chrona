"""Typed guided-workspace command use case above the presentation-free CAS writer."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from chrona.presentation.contracts import ClosureIdentity, ContractError, parse_contract


def parse_authoring_command(path: Path) -> dict[str, Any]:
    import yaml
    from chrona.resources import schema_resource
    import jsonschema
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    schema = yaml.safe_load(schema_resource("authoring-command-v0.1.schema.yaml").read_text())
    if not isinstance(value, dict) or next(jsonschema.Draft202012Validator(schema).iter_errors(value), None):
        raise ValueError("E_AUTHORING_COMMAND_SCHEMA")
    return value


def _identity(value: Any) -> str:
    return "sha256:" + sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def apply_authoring_command(
    workspace_path: Path, command: dict[str, Any], *, read_workspace: Any, cas_write: Any,
) -> dict[str, Any]:
    """Validate source intent; persistence is injected by the outer application adapter."""
    current = read_workspace(workspace_path)
    base = _identity(current)
    if command["target"]["path"] != workspace_path.name or command["baseRevision"] != base:
        return _rejected(command, "E_AUTHORING_BASE_REVISION", base)
    candidate = deepcopy(current)
    try:
        _apply(candidate, command)
        parse_contract(ClosureIdentity("authoring-workspace", str(candidate["id"]), "draft", _identity(candidate)), candidate)
    except (KeyError, ContractError, ValueError) as error:
        return _rejected(command, str(error) if str(error).startswith("E_") else "E_AUTHORING_COMMAND", base)
    result = cas_write(workspace_path, base, candidate)
    if result is None:
        return _rejected(command, "E_AUTHORING_BASE_REVISION", base)
    return {"status": "accepted", "commandId": command["commandId"], "baseRevision": base, "resultRevision": result, "diagnostics": []}


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


def _rejected(command: dict[str, Any], code: str, base: str) -> dict[str, Any]:
    return {"status": "rejected", "commandId": command.get("commandId"), "baseRevision": base, "resultRevision": None, "diagnostics": [{"code": code}]}
