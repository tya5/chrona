"""Revision-bound commands for independently stored Actual observations."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Protocol


class ActualStore(Protocol):
    def read(self) -> tuple[str, dict[str, Any]]: ...

    def write(self, expected_revision: str, actual_set: dict[str, Any]) -> tuple[str, dict[str, Any]] | None: ...


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

    def read(self) -> tuple[str, dict[str, Any]]:
        return f"actual:{self._revision}", deepcopy(self._actual_set)

    def write(self, expected_revision: str, actual_set: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
        if expected_revision != f"actual:{self._revision}":
            return None
        self._revision += 1
        self._actual_set = deepcopy(actual_set)
        return self.read()


def resolve_actual_observation(
    store: ActualStore,
    base_revision: str,
    observation_id: str,
    project_object_id: str,
    project_object_ids: set[str] | frozenset[str],
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
    return ActualCommandResult("accepted", result, (), result_revision, provenance)
