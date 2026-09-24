"""Revision-bound commands for independently stored Actual observations."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from hashlib import sha256
from pathlib import Path
from typing import Any, Protocol
import yaml

from chrona.resources import safe_load


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


@dataclass(frozen=True)
class ActualIntakeCommandResult:
    status: str
    actual_set: dict[str, Any] | None
    diagnostics: tuple[str, ...]
    dispositions: tuple[str, ...]
    result_revision: str | None = None


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


class LocalActualStore:
    """Local immutable-token Actual Store with an adapter-private CAS pointer."""

    def __init__(self, root: Path, actual_set: dict[str, Any]):
        self.root, self.actual_set_id = root, str(actual_set.get("id", ""))
        self.tip = root / "actual-tips" / f"{self.actual_set_id}.json"
        self._commands: dict[str, tuple[dict[str, Any], dict[str, Any], bool]] = {}
        if self.tip.is_file():
            self._revision, self._actual_set = self._load_tip()
        else:
            self._revision, self._actual_set = self._persist(actual_set, 1)

    def read(self) -> tuple[str, dict[str, Any]]:
        return self._revision, deepcopy(self._actual_set)

    def write(self, expected_revision: str, actual_set: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
        if expected_revision != self._revision or actual_set.get("id") != self.actual_set_id:
            return None
        counter = int(json.loads(self.tip.read_text(encoding="utf-8"))["counter"]) + 1
        self._revision, self._actual_set = self._persist(actual_set, counter)
        return self.read()

    def record_command(self, command_id: str, before: dict[str, Any], after: dict[str, Any]) -> None:
        self._commands[command_id] = (deepcopy(before), deepcopy(after), False)

    def undo(self, expected_revision: str, command_id: str): return None
    def redo(self, expected_revision: str, command_id: str): return None

    def _persist(self, actual_set: dict[str, Any], counter: int) -> tuple[str, dict[str, Any]]:
        payload = yaml.safe_dump(actual_set, sort_keys=True).encode()
        digest = sha256(payload).hexdigest()
        token = f"actual:{counter}:{digest[:12]}"
        path = self.root / token / "actuals" / f"{self.actual_set_id}.yaml"
        path.parent.mkdir(parents=True, exist_ok=False)
        path.write_bytes(payload)
        self.tip.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.tip.with_name(self.tip.name + ".tmp")
        temporary.write_text(json.dumps({"token": token, "counter": counter}), encoding="utf-8")
        temporary.replace(self.tip)
        return token, deepcopy(actual_set)

    def _load_tip(self) -> tuple[str, dict[str, Any]]:
        pointer = json.loads(self.tip.read_text(encoding="utf-8"))
        token = pointer["token"]
        value = safe_load((self.root / token / "actuals" / f"{self.actual_set_id}.yaml").read_text(encoding="utf-8"))
        return token, value


def apply_actual_intake_batch(
    store: ActualStore,
    base_revision: str,
    batch: dict[str, Any],
    project_object_ids: set[str] | frozenset[str],
    command_id: str = "apply-actual-intake-batch",
) -> ActualIntakeCommandResult:
    """Atomically intake one normalized batch into an Actual-set v0.2.

    Replays with byte-equivalent observed facts and source provenance are no-ops.
    Different facts for the same external identity are rejected rather than overwritten.
    """
    source = batch.get("source", {}) if isinstance(batch, dict) else {}
    system = source.get("system")
    source_identity = source.get("contentIdentity")
    records = batch.get("records") if isinstance(batch, dict) else None
    if not isinstance(system, str) or not system or not isinstance(source_identity, str) or not source_identity or not isinstance(records, list):
        return ActualIntakeCommandResult("rejected", None, ("E_INTAKE_SCHEMA",), ())
    revision, current = store.read()
    if revision != base_revision:
        return ActualIntakeCommandResult("rejected", None, ("E_CONFLICT",), ())
    if current.get("version") != "chrona/actual-set/v0.2" or current.get("kind") != "actual-set":
        return ActualIntakeCommandResult("rejected", None, ("E_INTAKE_SCHEMA",), ())

    def identity(value: Any) -> tuple[str, str]:
        return (type(value).__name__, json.dumps(value, sort_keys=True, separators=(",", ":")))

    known_ids = frozenset(project_object_ids)
    seen: set[tuple[str, str]] = set()
    normalized: list[tuple[Any, dict[str, Any], tuple[str, str]]] = []
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("externalKey"), (str, int)) or isinstance(record.get("externalKey"), bool) or not isinstance(record.get("actual"), dict) or not record["actual"]:
            return ActualIntakeCommandResult("rejected", None, ("E_INTAKE_SCHEMA",), ())
        key = identity(record["externalKey"])
        if key in seen:
            return ActualIntakeCommandResult("rejected", None, ("E_INTAKE_DUPLICATE_KEY",), ())
        seen.add(key)
        normalized.append((record["externalKey"], deepcopy(record), key))

    candidate = deepcopy(current)
    observations = candidate["body"].setdefault("observations", [])
    existing: dict[tuple[str, str], dict[str, Any]] = {}
    for observation in observations:
        external = observation.get("externalIdentity")
        if isinstance(external, dict) and external.get("system") == system and "key" in external:
            key = identity(external["key"])
            if key in existing:
                return ActualIntakeCommandResult("rejected", None, ("E_INTAKE_DUPLICATE_KEY",), ())
            existing[key] = observation

    dispositions: list[str] = []
    next_sequence = max((int(item.get("sequence", 0)) for item in observations), default=0) + 1
    for external_key, record, key in normalized:
        prior = existing.get(key)
        if prior is not None:
            if prior.get("actual") == record["actual"] and prior.get("sourceContentIdentity") == source_identity:
                dispositions.append("alreadyPresent")
                continue
            return ActualIntakeCommandResult("rejected", None, ("E_ACTUAL_EXTERNAL_CONFLICT",), tuple(dispositions))
        observation_id = f"{system}:{external_key}"
        if any(item.get("id") == observation_id for item in observations):
            return ActualIntakeCommandResult("rejected", None, ("E_INTAKE_DUPLICATE_KEY",), tuple(dispositions))
        observation: dict[str, Any] = {
            "id": observation_id,
            "sequence": next_sequence,
            "externalIdentity": {"system": system, "key": external_key},
            "sourceContentIdentity": source_identity,
            "actual": record["actual"],
        }
        next_sequence += 1
        object_id = record.get("projectObjectId")
        if isinstance(object_id, str) and object_id in known_ids:
            observation["projectObjectId"] = object_id
        else:
            observation["alignment"] = "unmatched"
        observations.append(observation)
        dispositions.append("inserted")

    if not any(value == "inserted" for value in dispositions):
        return ActualIntakeCommandResult("accepted", current, (), tuple(dispositions), revision)
    persisted = store.write(base_revision, candidate)
    if persisted is None:
        return ActualIntakeCommandResult("rejected", None, ("E_CONFLICT",), tuple(dispositions))
    result_revision, result = persisted
    store.record_command(command_id, current, result)
    return ActualIntakeCommandResult("accepted", result, (), tuple(dispositions), result_revision)


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
    if candidate.get("version") != "chrona/actual-set/v0.2":
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
