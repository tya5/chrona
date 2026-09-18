"""Initial standard Command family for resolved typed fields."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .profiles import validate_profiles
from .revision_store import MemoryRevisionStore


@dataclass(frozen=True)
class CommandResult:
    status: str
    project: dict[str, Any] | None
    diagnostics: tuple[str, ...]
    result_revision: str | None = None


def set_typed_field(project: dict[str, Any], package_manifests: dict[str, dict[str, Any]], object_id: str, field: str, value: Any) -> CommandResult:
    if object_id not in project.get("objects", {}):
        return CommandResult("rejected", None, ("E_REFERENCE",))
    candidate = deepcopy(project)
    candidate["objects"][object_id].setdefault("fields", {})[field] = value
    diagnostics = validate_profiles(candidate, package_manifests)
    if diagnostics:
        return CommandResult("rejected", None, tuple(item.id for item in diagnostics))
    return CommandResult("accepted", candidate, ())


def execute_set_typed_field(store: MemoryRevisionStore, base_revision: str, package_manifests: dict[str, dict[str, Any]], object_id: str, field: str, value: Any) -> CommandResult:
    snapshot = store.read()
    if snapshot.revision != base_revision:
        return CommandResult("rejected", None, ("E_CONFLICT",))
    candidate = set_typed_field(snapshot.project, package_manifests, object_id, field, value)
    if candidate.status == "rejected":
        return candidate
    persisted = store.write(base_revision, candidate.project)
    if persisted is None:
        return CommandResult("rejected", None, ("E_CONFLICT",))
    return CommandResult("accepted", persisted.project, (), persisted.revision)
