"""Closed CAS commands for the guided workspace source facade."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from chrona.operational.resources import OperationalResourceError, content_identity, parse_document
from chrona.presentation.contracts import ClosureIdentity, ContractError, parse_contract


def apply_authoring_command(workspace_path: Path, command: dict[str, Any]) -> dict[str, Any]:
    """Apply one validated Stage-1/2 command atomically, or write nothing."""
    current = _load_workspace(workspace_path)
    current_identity = content_identity(current)
    if command["target"]["path"] != workspace_path.name or command["baseRevision"] != current_identity:
        return _rejected(command, "E_AUTHORING_BASE_REVISION", current_identity)
    candidate = deepcopy(current)
    try:
        _apply(candidate, command)
        parse_contract(ClosureIdentity("authoring-workspace", str(candidate["id"]), "draft", content_identity(candidate)), candidate)
    except (KeyError, ContractError, ValueError) as error:
        return _rejected(command, str(error) if str(error).startswith("E_") else "E_AUTHORING_COMMAND", current_identity)
    try:
        _atomic_yaml_write(workspace_path, candidate, current_identity)
    except FileExistsError:
        return _rejected(command, "E_AUTHORING_BASE_REVISION", current_identity)
    return {"status": "accepted", "commandId": command["commandId"], "baseRevision": current_identity,
            "resultRevision": content_identity(candidate), "diagnostics": []}


def parse_authoring_command(path: Path) -> dict[str, Any]:
    return parse_document(path.read_text(encoding="utf-8"), "authoring-command-v0.1.schema.yaml")


def _load_workspace(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise OperationalResourceError("E_AUTHORING_WORKSPACE_SCHEMA")
    return value


def _apply(candidate: dict[str, Any], command: dict[str, Any]) -> None:
    body = candidate["body"]
    command_type = command["type"]
    payload = command["payload"]
    if command_type == "setWorkspaceTask":
        task = payload["task"]
        tasks = body["project"]["tasks"]
        index = next((index for index, item in enumerate(tasks) if item["id"] == task["id"]), None)
        if index is None:
            tasks.append(task)
        else:
            tasks[index] = task
    elif command_type == "setWorkspaceActual":
        actual = payload["actual"]
        actuals = body.setdefault("actuals", [])
        index = next((index for index, item in enumerate(actuals) if item["taskId"] == actual["taskId"]), None)
        if index is None:
            actuals.append(actual)
        else:
            actuals[index] = actual
    elif command_type == "selectPresentationPreset":
        body["presentation"]["binding"]["preset"] = payload["preset"]
    elif command_type == "setPresentationOverride":
        body["presentation"]["binding"]["overrides"] = payload["overrides"]
    else:  # schema should make this unreachable
        raise ValueError("E_AUTHORING_COMMAND")


def _atomic_yaml_write(path: Path, candidate: dict[str, Any], expected_identity: str) -> None:
    if content_identity(_load_workspace(path)) != expected_identity:
        raise FileExistsError
    temporary = path.with_name(f".{path.name}.authoring.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            yaml.safe_dump(candidate, handle, sort_keys=False)
            handle.flush()
        if content_identity(_load_workspace(path)) != expected_identity:
            raise FileExistsError
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _rejected(command: dict[str, Any], code: str, base: str) -> dict[str, Any]:
    return {"status": "rejected", "commandId": command.get("commandId"), "baseRevision": base,
            "resultRevision": None, "diagnostics": [{"code": code}]}
