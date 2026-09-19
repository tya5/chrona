"""Initial standard Command family for resolved typed fields."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Protocol

from .profiles import validate_profiles
from .revision_store import ProjectSnapshot
from .scheduler import schedule


class RevisionStore(Protocol):
    """The minimal compare-and-set store contract used by Commands."""

    def read(self) -> ProjectSnapshot: ...

    def write(self, expected_revision: str, project: dict[str, Any]) -> ProjectSnapshot | None: ...


@dataclass(frozen=True)
class CommandResult:
    status: str
    project: dict[str, Any] | None
    diagnostics: tuple[str, ...]
    result_revision: str | None = None
    command_id: str | None = None
    invalidated: tuple[str, ...] = ()


def set_typed_field(project: dict[str, Any], package_manifests: dict[str, dict[str, Any]] | None, object_id: str, field: str, value: Any) -> CommandResult:
    if object_id not in project.get("objects", {}):
        return CommandResult("rejected", None, ("E_REFERENCE",))
    candidate = deepcopy(project)
    candidate["objects"][object_id].setdefault("fields", {})[field] = value
    diagnostics = validate_profiles(candidate, package_manifests)
    if diagnostics:
        return CommandResult("rejected", None, tuple(item.id for item in diagnostics))
    return CommandResult("accepted", candidate, ())


def execute_typed_field_batch(
    store: RevisionStore,
    base_revision: str,
    package_manifests: dict[str, dict[str, Any]],
    operations: list[tuple[str, str, Any]],
) -> CommandResult:
    """Apply all typed-field operations to one candidate, then write it once.

    A validation failure returns before the single Store write, so a batch is
    atomic with respect to both the Project content and its snapshot revision.
    """
    snapshot = store.read()
    if snapshot.revision != base_revision:
        return CommandResult("rejected", None, ("E_CONFLICT",))
    candidate_project = snapshot.project
    for object_id, field, value in operations:
        candidate = set_typed_field(candidate_project, package_manifests, object_id, field, value)
        if candidate.status == "rejected":
            return candidate
        assert candidate.project is not None
        candidate_project = candidate.project
    evaluation = schedule(candidate_project, package_manifests=package_manifests)
    if not evaluation.ok:
        return CommandResult("rejected", None, tuple(item.id for item in evaluation.diagnostics))
    persisted = store.write(base_revision, candidate_project)
    if persisted is None:
        return CommandResult("rejected", None, ("E_CONFLICT",))
    return CommandResult("accepted", persisted.project, (), persisted.revision, invalidated=("schedule", "scene"))


def execute_set_typed_field(
    store: RevisionStore,
    base_revision: str,
    package_manifests: dict[str, dict[str, Any]],
    object_id: str,
    field: str,
    value: Any,
    command_id: str = "set-typed-field",
) -> CommandResult:
    result = execute_typed_field_batch(store, base_revision, package_manifests, [(object_id, field, value)])
    if result.status == "accepted" and hasattr(store, "record_command"):
        store.record_command(command_id, base_revision, result.result_revision, [(object_id, field, value)])
    return CommandResult(result.status, result.project, result.diagnostics, result.result_revision, command_id)


def execute_undo(store: Any, base_revision: str, command_id: str) -> CommandResult:
    persisted = store.undo(base_revision, command_id)
    if persisted is None:
        return CommandResult("rejected", None, ("E_CONFLICT",))
    return CommandResult("accepted", persisted.project, (), persisted.revision)


def execute_redo(store: Any, base_revision: str, command_id: str) -> CommandResult:
    persisted = store.redo(base_revision, command_id)
    if persisted is None:
        return CommandResult("rejected", None, ("E_CONFLICT",))
    return CommandResult("accepted", persisted.project, (), persisted.revision)
