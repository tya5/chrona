"""Revision-bound commands for independently stored Actual observations."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Protocol


class ActualStore(Protocol):
    def read(self) -> tuple[str, dict[str, Any]]: ...

    def write(self, expected_revision: str, actual_set: dict[str, Any]) -> tuple[str, dict[str, Any]] | None: ...

    def record_command(self, command_id: str, before: dict[str, Any], after: dict[str, Any]) -> None: ...

    def undo(self, expected_revision: str, command_id: str) -> tuple[str, dict[str, Any]] | None: ...

    def redo(self, expected_revision: str, command_id: str) -> tuple[str, dict[str, Any]] | None: ...


@dataclass(frozen=True)
class ActualCommandResult:
    status: str
    actual_set: dict[str, Any] | None
    diagnostics: tuple[str, ...]
    result_revision: str | None = None
    provenance: dict[str, Any] | None = None


class MemoryActualStore:
    """A CAS test adapter for a separately versioned Actual set."""

    def __init__(self, actual_set: dict[str, Any]):
        self._revision = 0
        self._actual_set = deepcopy(actual_set)
        self._commands: dict[str, tuple[dict[str, Any], dict[str, Any], bool]] = {}

    def read(self) -> tuple[str, dict[str, Any]]:
        return f"actual:{self._revision}", deepcopy(self._actual_set)

    def write(self, expected_revision: str, actual_set: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
        if expected_revision != f"actual:{self._revision}":
            return None
        self._revision += 1
        self._actual_set = deepcopy(actual_set)
        return self.read()

    def record_command(self, command_id: str, before: dict[str, Any], after: dict[str, Any]) -> None:
        self._commands[command_id] = (deepcopy(before), deepcopy(after), False)

    def undo(self, expected_revision: str, command_id: str) -> tuple[str, dict[str, Any]] | None:
        entry = self._commands.get(command_id)
        if entry is None or entry[2] or expected_revision != f"actual:{self._revision}" or self._actual_set != entry[1]:
            return None
        self._revision += 1
        self._actual_set = deepcopy(entry[0])
        self._commands[command_id] = (entry[0], entry[1], True)
        return self.read()

    def redo(self, expected_revision: str, command_id: str) -> tuple[str, dict[str, Any]] | None:
        entry = self._commands.get(command_id)
        if entry is None or not entry[2] or expected_revision != f"actual:{self._revision}" or self._actual_set != entry[0]:
            return None
        self._revision += 1
        self._actual_set = deepcopy(entry[1])
        self._commands[command_id] = (entry[0], entry[1], False)
        return self.read()


def resolve_actual_observation(
    store: ActualStore,
    base_revision: str,
    observation_id: str,
    project_object_id: str,
    project_object_ids: set[str] | frozenset[str],
    command_id: str = "resolve-actual-observation",
) -> ActualCommandResult:
    """Explicitly align one imported observation without mutating planned data."""
    if project_object_id not in project_object_ids:
        return ActualCommandResult("rejected", None, ("E_REFERENCE",))
    revision, current = store.read()
    if revision != base_revision:
        return ActualCommandResult("rejected", None, ("E_CONFLICT",))
    candidate = deepcopy(current)
    observations = candidate.get("body", {}).get("observations", [])
    observation = next((item for item in observations if item.get("id") == observation_id), None)
    if observation is None:
        return ActualCommandResult("rejected", None, ("E_REFERENCE",))
    if observation.get("alignment") != "unmatched" or "externalIdentity" not in observation:
        return ActualCommandResult("rejected", None, ("E_ACTUAL_ALIGNMENT",))

    provenance = {"externalIdentity": deepcopy(observation["externalIdentity"])}
    observation.pop("alignment")
    observation.pop("externalIdentity")
    observation["projectObjectId"] = project_object_id
    persisted = store.write(base_revision, candidate)
    if persisted is None:
        return ActualCommandResult("rejected", None, ("E_CONFLICT",))
    result_revision, result = persisted
    store.record_command(command_id, current, result)
    return ActualCommandResult("accepted", result, (), result_revision, provenance)


def undo_actual_command(store: ActualStore, base_revision: str, command_id: str) -> ActualCommandResult:
    persisted = store.undo(base_revision, command_id)
    if persisted is None:
        return ActualCommandResult("rejected", None, ("E_CONFLICT",))
    revision, actual_set = persisted
    return ActualCommandResult("accepted", actual_set, (), revision)


def redo_actual_command(store: ActualStore, base_revision: str, command_id: str) -> ActualCommandResult:
    persisted = store.redo(base_revision, command_id)
    if persisted is None:
        return ActualCommandResult("rejected", None, ("E_CONFLICT",))
    revision, actual_set = persisted
    return ActualCommandResult("accepted", actual_set, (), revision)
