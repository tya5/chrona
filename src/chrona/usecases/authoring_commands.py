"""Typed guided-workspace command preparation above the transaction port."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from chrona.core.identity import content_identity
from chrona.presentation.contracts import (
    ClosureIdentity, ContractError, SchemaContractError, explain_schema_errors, parse_contract,
)
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
        if command["type"] == "selectPresentationPreset":
            _check_preset_identity(canonical_path.parent, command["payload"]["preset"])
        identity = ClosureIdentity("authoring-workspace", str(candidate["id"]), "draft", content_identity(candidate))
        try:
            parse_contract(identity, candidate)
        except SchemaContractError as error:
            details = _override_violations(command, identity, candidate)
            if not details:
                raise
            return PreparedFileMutation(files={}, result_revision=None,
                                        result=_rejected(command, error.diagnostic_id, base, details=details))
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


def _check_preset_identity(root: Path, selector: dict[str, Any]) -> None:
    """Refuse a binding whose id/version differ from the preset file it names.

    Render requires the bound id and version to equal the preset's own identity, so
    a binding that fails here could never render.  A path that does not exist yet is
    left to the render-time resolver, as before.
    """
    from chrona.core.store_address import StoreAddressError, resolve_store_address
    from chrona.resources import safe_load
    try:
        path = resolve_store_address(root, str(selector["path"]))
    except StoreAddressError:
        return
    if not path.is_file():
        return
    try:
        document = safe_load(path.read_text(encoding="utf-8"))
        actual_id = str(document["id"])
        actual_version = str(document["body"]["package"]["version"])
    except (OSError, KeyError, TypeError, ValueError, yaml.YAMLError) as error:
        raise ValueError(f"E_AUTHORING_PRESET_SCHEMA: {selector['path']!r} is not a readable presentation preset") from error
    if str(selector["id"]) != actual_id or str(selector["version"]) != actual_version:
        raise ValueError(
            f"E_AUTHORING_PRESET_IDENTITY: binding id/version={selector['id']!r}/{selector['version']!r}, but "
            f"{selector['path']!r} is preset {actual_id!r}/{actual_version!r}; to use another builtin preset create a "
            "workspace with create_workspace, or point the binding at a copied preset directory whose id and version match")


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


_OVERRIDES_IN_WORKSPACE = "/body/presentation/binding/overrides"
_MAX_VIOLATIONS = 8


def _override_violations(command: dict[str, Any], identity: ClosureIdentity, candidate: dict[str, Any]) -> list[str]:
    """Each schema violation of a ``setPresentationOverride`` payload as ``<command pointer>: <message>`` (#1892 row 5).

    The workspace schema reports a bad override as one union failure at ``/body/presentation``; the discriminator
    selects the guided branch, so the violation names the node inside ``payload.overrides`` and what it may hold.
    A violation outside the overrides is not this command's input, so it is not translated.
    """
    from chrona.schema_diagnostics import violation_node, violation_sentence
    if command["type"] != "setPresentationOverride":
        return []
    details: list[str] = []
    for violation in explain_schema_errors(identity, candidate, select_branches=True):
        node = violation_node(violation)
        if node != _OVERRIDES_IN_WORKSPACE and not node.startswith(_OVERRIDES_IN_WORKSPACE + "/"):
            return []
        details.append(f"/payload/overrides{node[len(_OVERRIDES_IN_WORKSPACE):]}: {violation_sentence(violation)}")
    return details[:_MAX_VIOLATIONS]


def _rejected(command: dict[str, Any], code: str, base: str, detail: str = "",
              details: list[str] | None = None) -> dict[str, Any]:
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
    rows = [{"code": code, "detail": item} for item in details] if details else [diagnostic]
    return {
        "version": "chrona/authoring-command-result/v0.1", "status": "rejected",
        "commandId": command.get("commandId"), "commandBaseRevision": command.get("baseRevision"),
        "workspaceRevision": base, "resultRevision": None, "diagnostics": rows,
    }
