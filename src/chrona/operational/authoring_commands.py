"""Presentation-free compare-and-set persistence for authoring workspace bytes."""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Mapping

import yaml

from chrona.operational.resources import OperationalResourceError, content_identity
from chrona.yaml_codec import safe_load


def read_authoring_workspace(path: Path) -> dict[str, Any]:
    """Read untyped source bytes for an application use case to validate."""
    return _load_workspace(path)


def cas_write_authoring_workspace(path: Path, expected_identity: str, candidate: dict[str, Any]) -> str | None:
    """Persist application-validated source only if its content identity still matches."""
    try:
        _atomic_yaml_write(path, candidate, expected_identity)
    except FileExistsError:
        return None
    return content_identity(candidate)


def cas_write_authoring_aggregate(path: Path, expected_identity: str, candidates: Mapping[str, bytes]) -> str | None:
    """Publish application-validated bytes as one workspace aggregate switch.

    The workspace is written last, so a visible explicit source can never name a
    missing resource.  This function deliberately knows no authoring schema.
    """
    root = path.parent.resolve()
    workspace_name = path.name
    if workspace_name not in candidates or not all(isinstance(value, bytes) for value in candidates.values()):
        raise OperationalResourceError("E_AUTHORING_AGGREGATE_CANDIDATE")
    resources = [name for name in candidates if name != workspace_name]
    if not resources or any(not _relative(name) for name in candidates):
        raise OperationalResourceError("E_AUTHORING_AGGREGATE_PATH")
    top_levels = {Path(name).parts[0] for name in resources}
    if len(top_levels) != 1 or any(len(Path(name).parts) < 2 for name in resources):
        raise OperationalResourceError("E_AUTHORING_AGGREGATE_PATH")
    target = root / next(iter(top_levels))
    with _aggregate_lock(path):
        _recover_incomplete_aggregate(path)
        if target.exists():
            raise FileExistsError("E_AUTHORING_MATERIALIZE_COLLISION")
        if content_identity(_load_workspace(path)) != expected_identity:
            return None
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            staged = Path(temporary)
            for name, payload in candidates.items():
                destination = staged / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(payload)
            if content_identity(_load_workspace(path)) != expected_identity:
                return None
            marker = _transaction_marker(path)
            _write_marker(marker, expected_identity, target.name, {name: _bytes_identity(payload) for name, payload in candidates.items() if name != workspace_name})
            try:
                (staged / target.name).replace(target)
                if content_identity(_load_workspace(path)) != expected_identity:
                    _remove_published(target)
                    marker.unlink(missing_ok=True)
                    return None
                (staged / workspace_name).replace(path)
                marker.unlink(missing_ok=True)
            except Exception:
                _remove_published(target)
                marker.unlink(missing_ok=True)
                raise
    return content_identity(_load_workspace(path))


def _load_workspace(path: Path) -> dict[str, Any]:
    value = safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise OperationalResourceError("E_AUTHORING_WORKSPACE_SCHEMA")
    return value


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


def _relative(name: str) -> bool:
    candidate = Path(name)
    return bool(name) and not candidate.is_absolute() and all(part not in {"", ".", ".."} for part in candidate.parts)


@contextmanager
def _aggregate_lock(path: Path):
    lock = path.with_name(f".{path.name}.authoring.lock")
    with lock.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _transaction_marker(path: Path) -> Path:
    return path.with_name(f".{path.name}.authoring-transaction.json")


def _write_marker(marker: Path, expected_identity: str, directory: str, resources: Mapping[str, str]) -> None:
    payload = json.dumps({"workspaceIdentity": expected_identity, "directory": directory, "resources": dict(resources)}, sort_keys=True)
    with marker.open("x", encoding="utf-8") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _recover_incomplete_aggregate(path: Path) -> None:
    marker = _transaction_marker(path)
    if not marker.exists():
        return
    try:
        value = json.loads(marker.read_text(encoding="utf-8"))
        expected = value["workspaceIdentity"]
        directory = value["directory"]
        resources = value["resources"]
        if not isinstance(expected, str) or not isinstance(directory, str) or not _relative(directory) or "/" in directory or not isinstance(resources, dict):
            raise ValueError
        target = path.parent.resolve() / directory
        if content_identity(_load_workspace(path)) == expected and target.is_dir() and all(
            isinstance(name, str) and isinstance(identity, str) and _relative(name)
            and (target.parent / name).is_file() and _bytes_identity((target.parent / name).read_bytes()) == identity
            for name, identity in resources.items()
        ):
            _remove_published(target)
        marker.unlink(missing_ok=True)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        raise OperationalResourceError("E_AUTHORING_AGGREGATE_RECOVERY")


def _remove_published(target: Path) -> None:
    if target.is_dir():
        shutil.rmtree(target)


def _bytes_identity(payload: bytes) -> str:
    return "sha256:" + sha256(payload).hexdigest()
