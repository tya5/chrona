"""Locked file-transaction boundary for guided authoring mutations.

The coordinator treats prepared candidates and application results as opaque
values. It owns only canonical file identity, replay receipts, locking, CAS,
publication and process-crash recovery.
"""
from __future__ import annotations

from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import shutil
from typing import Any, Callable, Mapping

from chrona.core.store_address import Charset, StoreAddressError, check_store_address
from chrona.operational.resources import OperationalResourceError, canonical_bytes, content_identity, json_value
from chrona.resources import safe_load
from chrona.storage.file_lock import lock_file, unlock_file
from chrona.storage.file_transaction import PreparedFileMutation


_MARKER_VERSION = "chrona/authoring-file-transaction/v0.1"
_RECEIPT_VERSION = "chrona/authoring-command-replay/v0.1"


def read_authoring_workspace(path: Path) -> dict[str, Any]:
    """Read untyped workspace content for a use case or revision query."""
    return _load_workspace(_canonical_path(path))


def transact_authoring_command(
    path: Path,
    command: dict[str, Any],
    *,
    prepare: Callable[[Path, dict[str, Any]], PreparedFileMutation],
    reject: Callable[[str, str, str], dict[str, Any]],
    verify_receipt: Callable[[dict[str, Any], dict[str, Any], str, str], None],
) -> dict[str, Any]:
    """Replay or commit one validated authoring request under its workspace lock."""
    workspace, scope_identity = _canonical_workspace(path)
    command_id = command.get("commandId")
    if not isinstance(command_id, str) or not command_id:
        raise OperationalResourceError("E_AUTHORING_COMMAND_SCHEMA", "commandId must be a non-empty string")
    target_path = command.get("target", {}).get("path") if isinstance(command.get("target"), dict) else None
    with _aggregate_lock(workspace):
        pending = _recover_transaction(workspace, scope_identity, verify_receipt)
        current = _load_workspace(workspace)
        observed = content_identity(current)
        receipt = _read_receipt(workspace, scope_identity, command_id, verify_receipt)
        request = json_value(command)
        request_identity = content_identity(request)
        if receipt is not None:
            if receipt["requestIdentity"] != request_identity:
                return reject("E_AUTHORING_COMMAND_ID_REUSE", observed,
                              f"commandId {command_id!r} already identifies a different canonical request")
            if pending is not None and pending != command_id:
                return reject("E_AUTHORING_AGGREGATE_RECOVERY", observed,
                              "a committed transaction marker requires recovery before another command")
            return receipt["result"]
        if pending is not None:
            return reject("E_AUTHORING_AGGREGATE_RECOVERY", observed,
                          "a committed transaction marker requires recovery before a new command")
        if target_path != workspace.name:
            return reject("E_AUTHORING_TARGET_MISMATCH", observed,
                          f"target.path must name the canonical workspace filename {workspace.name!r}")

        if command.get("baseRevision") != observed:
            return reject("E_AUTHORING_BASE_REVISION", observed,
                          f"workspace revision expected {observed}; command declared {command.get('baseRevision')!r}")

        prepared = prepare(workspace, current)
        if not isinstance(prepared, PreparedFileMutation):
            raise TypeError("prepare must return PreparedFileMutation")
        if prepared.result_revision is None:
            if prepared.files:
                raise OperationalResourceError("E_AUTHORING_AGGREGATE_CANDIDATE",
                                               "a refused command must not contain candidate files")
            return prepared.result
        if not isinstance(prepared.result_revision, str) or not prepared.result_revision:
            raise OperationalResourceError("E_AUTHORING_AGGREGATE_CANDIDATE", "accepted candidate has no next revision identity")
        files, resource_directory = _validate_candidates(workspace, prepared.files)
        after = prepared.result_revision
        try:
            verify_receipt(request, prepared.result, observed, after)
        except (KeyError, TypeError, ValueError) as error:
            raise OperationalResourceError("E_AUTHORING_REPLAY_UNAVAILABLE",
                                           f"prepared accepted result cannot be verified: {error}") from error

        final_receipt = _receipt_path(workspace, scope_identity, command_id)
        receipt_directory = final_receipt.parent
        if final_receipt.exists() or final_receipt.is_symlink():
            raise OperationalResourceError("E_AUTHORING_REPLAY_UNAVAILABLE", "a receipt destination exists without a readable receipt")
        if resource_directory is not None and (workspace.parent / resource_directory).exists():
            return reject("E_AUTHORING_MATERIALIZE_COLLISION", observed,
                          f"destination directory {resource_directory!r} already exists")

        stage_name = _stage_name(command_id, scope_identity)
        stage = workspace.parent / stage_name
        marker = _transaction_marker(workspace)
        if stage.exists() or stage.is_symlink():
            raise OperationalResourceError("E_AUTHORING_AGGREGATE_RECOVERY", "a transaction staging path exists without a marker")
        receipt_value = {
            "version": _RECEIPT_VERSION,
            "commandId": command_id,
            "requestIdentity": request_identity,
            "workspaceIdentity": scope_identity,
            "beforeIdentity": observed,
            "afterIdentity": after,
            "request": request,
            "result": json_value(prepared.result),
        }
        receipt_bytes = canonical_bytes(receipt_value)
        receipt_relative = final_receipt.relative_to(workspace.parent).as_posix()
        owned = {name: _bytes_identity(payload) for name, payload in files.items() if name != workspace.name}
        owned[receipt_relative] = _bytes_identity(receipt_bytes)
        marker_value = {
            "version": _MARKER_VERSION,
            "workspaceIdentity": scope_identity,
            "beforeIdentity": observed,
            "afterIdentity": after,
            "commandId": command_id,
            "requestIdentity": request_identity,
            "stage": stage_name,
            "receipt": receipt_relative,
            "receiptIdentity": _bytes_identity(receipt_bytes),
            "resourceDirectory": resource_directory,
            "owned": owned,
        }
        _write_transaction_marker(marker, marker_value)
        committed = False
        try:
            stage.mkdir()
            for name, payload in files.items():
                destination = stage / PurePosixPath(name)
                destination.parent.mkdir(parents=True, exist_ok=True)
                _write_new_bytes(destination, payload)
            staged_receipt = stage / "receipt.json"
            _write_new_bytes(staged_receipt, receipt_bytes)

            if resource_directory is not None:
                target = workspace.parent / resource_directory
                if target.exists() or target.is_symlink():
                    raise FileExistsError(f"E_AUTHORING_MATERIALIZE_COLLISION: destination directory {resource_directory!r} already exists")
                (stage / resource_directory).rename(target)

            receipt_directory.mkdir(exist_ok=True)
            _ensure_private_directory("E_AUTHORING_REPLAY_UNAVAILABLE", receipt_directory)
            if final_receipt.exists() or final_receipt.is_symlink():
                raise OperationalResourceError("E_AUTHORING_REPLAY_UNAVAILABLE", "receipt destination appeared during publication")
            os.link(staged_receipt, final_receipt)

            if after != observed:
                if content_identity(_load_workspace(workspace)) != observed:
                    raise FileExistsError("E_AUTHORING_BASE_REVISION: workspace changed before publication")
                os.replace(stage / workspace.name, workspace)
            if content_identity(_load_workspace(workspace)) != after:
                raise OperationalResourceError("E_AUTHORING_AGGREGATE_RECOVERY", "published workspace does not match its prepared identity")
            committed = True
        except BaseException:
            if not committed:
                try:
                    pending = _recover_transaction(workspace, scope_identity, verify_receipt)
                except BaseException as recovery_error:
                    raise OperationalResourceError("E_AUTHORING_AGGREGATE_RECOVERY",
                                                   f"transaction failed and safe rollback is unavailable: {recovery_error}") from recovery_error
                # Recovery may have completed cleanup, so its pending marker signal is not
                # sufficient to recognize a commit. A matching durable receipt and the
                # prepared after-identity are the commit proof in either marker state.
                recovered_receipt = _read_receipt(workspace, scope_identity, command_id, verify_receipt)
                if recovered_receipt is not None and content_identity(_load_workspace(workspace)) == after:
                    return recovered_receipt["result"]
            raise

        # After the atomic workspace replacement (or receipt publication for a no-op), cleanup failure
        # cannot turn accepted work into a rejection. The marker is kept for the next locked caller.
        _cleanup_committed_marker(workspace, stage, marker, marker_value)
        return prepared.result


def _canonical_workspace(path: Path) -> tuple[Path, str]:
    workspace = _canonical_path(path)
    if not workspace.is_file():
        raise OperationalResourceError("E_AUTHORING_WORKSPACE_SCHEMA", f"workspace {workspace.name!r} is not a regular file")
    identity = os.path.normcase(str(workspace))
    scope_identity = "sha256:" + sha256(identity.encode("utf-8")).hexdigest()
    return workspace, scope_identity


def _canonical_path(path: Path) -> Path:
    return path.resolve(strict=True)


def _receipt_directory(workspace: Path, scope_identity: str) -> Path:
    return workspace.parent / f".chrona-authoring-receipts-{scope_identity.removeprefix('sha256:')[:24]}"


def _receipt_path(workspace: Path, scope_identity: str, command_id: str) -> Path:
    command_digest = sha256(command_id.encode("utf-8")).hexdigest()
    return _receipt_directory(workspace, scope_identity) / f"{command_digest}.json"


def _stage_name(command_id: str, scope_identity: str) -> str:
    return ".chrona-authoring-stage-" + sha256(canonical_bytes([scope_identity, command_id])).hexdigest()


def _read_receipt(workspace: Path, scope_identity: str, command_id: str,
                  verify_receipt: Callable[[dict[str, Any], dict[str, Any], str, str], None]) -> dict[str, Any] | None:
    directory = _receipt_directory(workspace, scope_identity)
    if not directory.exists() and not directory.is_symlink():
        return None
    _ensure_private_directory("E_AUTHORING_REPLAY_UNAVAILABLE", directory)
    path = _receipt_path(workspace, scope_identity, command_id)
    if not path.exists() and not path.is_symlink():
        return None
    if path.is_symlink() or not path.is_file():
        raise OperationalResourceError("E_AUTHORING_REPLAY_UNAVAILABLE", "replay receipt path is not a regular file")
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError("receipt is not an object")
        required = {"version", "commandId", "requestIdentity", "workspaceIdentity", "beforeIdentity",
                    "afterIdentity", "request", "result"}
        if (set(value) != required or value["version"] != _RECEIPT_VERSION
                or value["commandId"] != command_id or value["workspaceIdentity"] != scope_identity
                or not isinstance(value["requestIdentity"], str)
                or not isinstance(value["beforeIdentity"], str)
                or not isinstance(value["afterIdentity"], str)
                or not isinstance(value["request"], dict) or not isinstance(value["result"], dict)
                or content_identity(value["request"]) != value["requestIdentity"]):
            raise ValueError("receipt identity fields are inconsistent")
        if value["request"].get("commandId") != command_id:
            raise ValueError("receipt request commandId disagrees with filename")
        if value["request"].get("target", {}).get("path") != workspace.name:
            raise ValueError("receipt target is outside its canonical workspace filename")
        try:
            verify_receipt(value["request"], value["result"], value["beforeIdentity"], value["afterIdentity"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"accepted result is invalid: {error}") from error
        return value
    except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError) as error:
        raise OperationalResourceError("E_AUTHORING_REPLAY_UNAVAILABLE",
                                       f"stored receipt for commandId {command_id!r} cannot be verified") from error


def _validate_candidates(workspace: Path, candidates: Mapping[str, bytes]) -> tuple[dict[str, bytes], str | None]:
    if not isinstance(candidates, Mapping) or workspace.name not in candidates:
        raise OperationalResourceError("E_AUTHORING_AGGREGATE_CANDIDATE",
                                       f"prepared mutation must include workspace {workspace.name!r}")
    files: dict[str, bytes] = {}
    for name, payload in candidates.items():
        if not isinstance(name, str) or not isinstance(payload, bytes):
            raise OperationalResourceError("E_AUTHORING_AGGREGATE_CANDIDATE", "candidate file names and bytes are required")
        charset: Charset = "file-name" if name == workspace.name else "address"
        try:
            check_store_address(name, charset=charset)
        except StoreAddressError as error:
            raise OperationalResourceError("E_AUTHORING_AGGREGATE_PATH", f"candidate path {name!r} is unsafe") from error
        if name != workspace.name and len(PurePosixPath(name).parts) < 2:
            raise OperationalResourceError("E_AUTHORING_AGGREGATE_PATH", "non-workspace outputs must be nested under a resource directory")
        files[name] = payload
    resources = [name for name in files if name != workspace.name]
    if not resources:
        return files, None
    top_levels = {PurePosixPath(name).parts[0] for name in resources}
    if len(top_levels) != 1 or any(len(PurePosixPath(name).parts) < 2 for name in resources):
        raise OperationalResourceError("E_AUTHORING_AGGREGATE_PATH", "resource outputs must share one nested directory")
    return files, next(iter(top_levels))


def _write_transaction_marker(path: Path, value: Mapping[str, Any]) -> None:
    _ensure_not_symlink("E_AUTHORING_AGGREGATE_RECOVERY", path)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, sort_keys=True, separators=(",", ":"))
        handle.flush()
        os.fsync(handle.fileno())


def _recover_transaction(workspace: Path, scope_identity: str,
                         verify_receipt: Callable[[dict[str, Any], dict[str, Any], str, str], None]) -> str | None:
    marker = _transaction_marker(workspace)
    if not marker.exists() and not marker.is_symlink():
        return None
    if marker.is_symlink() or not marker.is_file():
        raise OperationalResourceError("E_AUTHORING_AGGREGATE_RECOVERY", f"transaction marker {marker.name!r} is not a regular file")
    try:
        value = json.loads(marker.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("marker is not an object")
        if value.get("version") != _MARKER_VERSION:
            return _recover_legacy_marker(workspace, marker, value)
        expected_keys = {"version", "workspaceIdentity", "beforeIdentity", "afterIdentity", "commandId",
                         "requestIdentity", "stage", "receipt", "receiptIdentity", "resourceDirectory", "owned"}
        if set(value) != expected_keys or value["workspaceIdentity"] != scope_identity:
            raise ValueError("marker identity or shape is invalid")
        command_id = value["commandId"]
        if not isinstance(command_id, str) or not command_id:
            raise ValueError("marker commandId is invalid")
        before, after = value["beforeIdentity"], value["afterIdentity"]
        if not isinstance(before, str) or not isinstance(after, str):
            raise ValueError("marker workspace identities are invalid")
        stage_name = value["stage"]
        if stage_name != _stage_name(command_id, scope_identity):
            raise ValueError("marker staging path does not match command identity")
        if not isinstance(value["owned"], dict) or not isinstance(value["receiptIdentity"], str):
            raise ValueError("marker output ownership is invalid")
        resource_directory = value["resourceDirectory"]
        if resource_directory is not None and (
            not isinstance(resource_directory, str)
            or not _safe_relative_output(resource_directory)
            or len(PurePosixPath(resource_directory).parts) != 1
        ):
            raise ValueError("marker resource directory is unsafe")
        receipt_path = _receipt_path(workspace, scope_identity, command_id)
        receipt_relative = receipt_path.relative_to(workspace.parent).as_posix()
        if value["receipt"] != receipt_relative or value["owned"].get(receipt_relative) != value["receiptIdentity"]:
            raise ValueError("marker receipt path or identity is inconsistent")
        for name, identity in value["owned"].items():
            if not isinstance(name, str) or not isinstance(identity, str) or not _safe_relative_output(name):
                raise ValueError("marker owns an unsafe path")
        resource_names = set(value["owned"]) - {receipt_relative}
        if (resource_directory is None) != (not resource_names) or any(
            not name.startswith(resource_directory + "/") for name in resource_names
        ):
            raise ValueError("marker resource paths disagree with their directory")
        observed = content_identity(_load_workspace(workspace))
        receipt_exists = receipt_path.exists() or receipt_path.is_symlink()
        receipt_valid = _owned_file_matches(receipt_path, value["receiptIdentity"]) if receipt_exists else False

        committed = False
        if before == after and observed == before:
            if receipt_exists:
                if not receipt_valid:
                    raise ValueError("no-op receipt does not match its transaction marker")
                _verify_marker_receipt(workspace, scope_identity, command_id, value, verify_receipt)
                if not _resources_match(workspace, value):
                    raise ValueError("no-op resource outputs do not match marker identities")
                committed = True
            else:
                _rollback_owned_outputs(workspace, value)
                _remove_stage(workspace, stage_name, value)
                marker.unlink()
                return None
        elif observed == after:
            if not receipt_exists or not receipt_valid:
                raise ValueError("committed workspace has no matching durable receipt")
            if not _resources_match(workspace, value):
                raise ValueError("committed resource outputs do not match marker identities")
            _verify_marker_receipt(workspace, scope_identity, command_id, value, verify_receipt)
            committed = True
        elif observed == before:
            _rollback_owned_outputs(workspace, value)
            _remove_stage(workspace, stage_name, value)
            marker.unlink()
            return None
        else:
            raise ValueError("workspace matches neither transaction before nor after identity")

        if committed:
            try:
                _remove_stage(workspace, stage_name, value)
                marker.unlink()
            except (OSError, ValueError):
                return command_id
            return None
        raise ValueError("transaction state cannot be classified")
    except OperationalResourceError:
        raise
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        raise OperationalResourceError("E_AUTHORING_AGGREGATE_RECOVERY",
                                       f"transaction marker {marker.name!r} cannot be safely recovered") from error


def _recover_legacy_marker(workspace: Path, marker: Path, value: dict[str, Any]) -> None:
    """Rollback only the exact pre-receipt marker shape when its old state is proven."""
    try:
        if set(value) != {"workspaceIdentity", "directory", "resources"}:
            raise ValueError("legacy marker shape is not recognized")
        expected, directory, resources = value["workspaceIdentity"], value["directory"], value["resources"]
        if not isinstance(expected, str) or not isinstance(directory, str) or not _safe_relative_output(directory):
            raise ValueError("legacy marker identity/path is invalid")
        if len(PurePosixPath(directory).parts) != 1 or not isinstance(resources, dict):
            raise ValueError("legacy marker output set is invalid")
        if content_identity(_load_workspace(workspace)) != expected:
            raise ValueError("legacy marker cannot prove whether the workspace committed")
        target = workspace.parent / directory
        if target.exists() or target.is_symlink():
            expected_paths = set()
            for name, identity in resources.items():
                if not isinstance(name, str) or not isinstance(identity, str) or not _safe_relative_output(name):
                    raise ValueError("legacy marker owns an unsafe path")
                expected_paths.add(name)
            if not _tree_matches(workspace.parent, target, {name: resources[name] for name in expected_paths}):
                raise ValueError("legacy aggregate outputs are not exactly marker-owned")
            shutil.rmtree(target)
        marker.unlink()
        return None
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise OperationalResourceError("E_AUTHORING_AGGREGATE_RECOVERY",
                                       f"legacy transaction marker {marker.name!r} cannot be safely recovered") from error


def _verify_marker_receipt(workspace: Path, scope_identity: str, command_id: str,
                           marker: Mapping[str, Any],
                           verify_receipt: Callable[[dict[str, Any], dict[str, Any], str, str], None]) -> None:
    receipt = _read_receipt(workspace, scope_identity, command_id, verify_receipt)
    if (receipt is None or receipt["requestIdentity"] != marker["requestIdentity"]
            or receipt["beforeIdentity"] != marker["beforeIdentity"]
            or receipt["afterIdentity"] != marker["afterIdentity"]):
        raise ValueError("receipt identities disagree with transaction marker")


def _rollback_owned_outputs(workspace: Path, marker: Mapping[str, Any]) -> None:
    owned = marker["owned"]
    receipt = workspace.parent / PurePosixPath(marker["receipt"])
    resource_files = {name: identity for name, identity in owned.items() if name != marker["receipt"]}
    directory = marker["resourceDirectory"]
    if directory is not None:
        target = workspace.parent / directory
        if target.exists() or target.is_symlink():
            if not _tree_matches(workspace.parent, target, resource_files):
                raise ValueError("published resource directory contains unowned or modified files")
            shutil.rmtree(target)
    elif resource_files:
        raise ValueError("marker lists resources without a resource directory")
    if receipt.exists() or receipt.is_symlink():
        if not _owned_file_matches(receipt, marker["receiptIdentity"]):
            raise ValueError("published receipt does not match marker identity")
        receipt.unlink()


def _resources_match(workspace: Path, marker: Mapping[str, Any]) -> bool:
    directory = marker["resourceDirectory"]
    expected = {name: identity for name, identity in marker["owned"].items() if name != marker["receipt"]}
    if directory is None:
        return not expected
    target = workspace.parent / directory
    return _tree_matches(workspace.parent, target, expected)


def _tree_matches(root: Path, target: Path, expected: Mapping[str, str]) -> bool:
    if target.is_symlink() or not target.is_dir():
        return False
    actual: dict[str, str] = {}
    for path in target.rglob("*"):
        if path.is_symlink():
            return False
        if path.is_file():
            actual[path.relative_to(root).as_posix()] = _bytes_identity(path.read_bytes())
        elif not path.is_dir():
            return False
    return actual == dict(expected)


def _owned_file_matches(path: Path, identity: str) -> bool:
    return not path.is_symlink() and path.is_file() and _bytes_identity(path.read_bytes()) == identity


def _remove_stage(workspace: Path, name: str, marker: Mapping[str, Any]) -> None:
    if name != _stage_name_from_path(name) or "/" in name or "\\" in name:
        raise ValueError("transaction stage path is unsafe")
    stage = workspace.parent / name
    if stage.is_symlink():
        raise ValueError("transaction stage path is a symlink")
    if stage.exists():
        if not stage.is_dir():
            raise ValueError("transaction stage path is not a directory")
        _validate_stage_contents(stage, workspace, marker)
        shutil.rmtree(stage)


def _validate_stage_contents(stage: Path, workspace: Path, marker: Mapping[str, Any]) -> None:
    resource_directory = marker["resourceDirectory"]
    owned = marker["owned"]
    expected_files = {"receipt.json"}
    if resource_directory is not None:
        expected_files.update(name[len(resource_directory) + 1:]
                              for name in owned if name != marker["receipt"]
                              and name.startswith(resource_directory + "/"))
        expected_files = {"receipt.json", *(f"{resource_directory}/{name}" for name in expected_files if name != "receipt.json")}
    expected_files.add(workspace.name)
    expected_directories = {
        "/".join(PurePosixPath(name).parts[:index])
        for name in expected_files
        for index in range(1, len(PurePosixPath(name).parts))
    }
    actual_files: set[str] = set()
    actual_directories: set[str] = set()
    for path in stage.rglob("*"):
        relative = path.relative_to(stage).as_posix()
        if path.is_symlink():
            raise ValueError("transaction stage contains a symlink")
        if path.is_dir():
            actual_directories.add(relative)
        elif path.is_file():
            actual_files.add(relative)
        else:
            raise ValueError("transaction stage contains a non-file entry")
    if not actual_files <= expected_files or not actual_directories <= expected_directories:
        raise ValueError("transaction stage contains unowned entries")
    for relative in actual_files:
        path = stage / PurePosixPath(relative)
        if relative == workspace.name:
            if content_identity(_load_workspace(path)) != marker["afterIdentity"]:
                raise ValueError("staged workspace does not match the transaction identity")
        elif relative == "receipt.json":
            if not _owned_file_matches(path, marker["receiptIdentity"]):
                raise ValueError("staged receipt does not match the transaction identity")
        else:
            output = f"{resource_directory}/{relative.split('/', 1)[1]}"
            if output not in owned or not _owned_file_matches(path, owned[output]):
                raise ValueError("staged resource does not match the transaction identity")


def _stage_name_from_path(name: str) -> str:
    return name if name.startswith(".chrona-authoring-stage-") else ""


def _cleanup_committed_marker(workspace: Path, stage: Path, marker: Path,
                              marker_value: Mapping[str, Any]) -> None:
    try:
        if stage.exists():
            _remove_stage(workspace, stage.name, marker_value)
        marker.unlink()
    except (OSError, ValueError):
        # The marker plus verified receipt is the recovery authority; publication already committed.
        return


def _ensure_private_directory(code: str, path: Path) -> None:
    if path.is_symlink() or not path.is_dir():
        raise OperationalResourceError(code, f"private transaction directory {path.name!r} is not a real directory")


def _ensure_not_symlink(code: str, path: Path) -> None:
    if path.is_symlink():
        raise OperationalResourceError(code, f"transaction path {path.name!r} is a symlink")


def _safe_relative_output(name: str) -> bool:
    try:
        check_store_address(name, charset="address")
    except StoreAddressError:
        return False
    return True


def _write_new_bytes(path: Path, payload: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


@contextmanager
def _aggregate_lock(path: Path):
    # Resolve before selecting this sibling so symlink/case aliases share one OS lock.
    path = _canonical_path(path)
    lock = path.with_name(f".{path.name}.authoring.lock")
    _ensure_not_symlink("E_AUTHORING_LOCK_UNAVAILABLE", lock)
    with lock.open("a+b") as handle:
        _lock_file(handle, workspace_path=path, lock_path=lock)
        try:
            yield
        finally:
            _unlock_file(handle)


def _lock_file(handle: Any, *, workspace_path: Path | None = None, lock_path: Path | None = None) -> None:
    """Acquire the one-byte advisory aggregate lock on the active platform."""
    import errno

    try:
        lock_file(handle)
    except OSError as error:
        if os.name != "nt" or error.errno not in {errno.EACCES, errno.EAGAIN}:
            raise
        workspace = workspace_path if workspace_path is not None else "<unknown workspace>"
        lock = lock_path if lock_path is not None else "<unknown lock>"
        raise OperationalResourceError(
            "E_AUTHORING_LOCK_TIMEOUT",
            f"timed out acquiring authoring aggregate lock {lock} for workspace {workspace}; "
            "wait for the active authoring command to finish and retry",
        ) from error


def _unlock_file(handle: Any) -> None:
    unlock_file(handle)


def _transaction_marker(path: Path) -> Path:
    return path.with_name(f".{path.name}.authoring-transaction.json")


def _load_workspace(path: Path) -> dict[str, Any]:
    value = safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise OperationalResourceError("E_AUTHORING_WORKSPACE_SCHEMA",
                                       f"workspace {path.name!r} must be a mapping, not {type(value).__name__}")
    return value


def _bytes_identity(payload: bytes) -> str:
    return "sha256:" + sha256(payload).hexdigest()
