"""Revision-bound View-local presentation annotation commands."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ViewCommandResult:
    status: str
    view: dict[str, Any] | None
    diagnostics: tuple[str, ...]
    result_revision: str | None = None


class MemoryViewStore:
    def __init__(self, view: dict[str, Any]):
        self._revision, self._view = 0, deepcopy(view)
        self._commands: dict[str, tuple[dict[str, Any], dict[str, Any], bool]] = {}

    def read(self) -> tuple[str, dict[str, Any]]:
        return f"view:{self._revision}", deepcopy(self._view)

    def write(self, expected_revision: str, view: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
        if expected_revision != f"view:{self._revision}":
            return None
        self._revision += 1
        self._view = deepcopy(view)
        return self.read()

    def record_command(self, command_id: str, before: dict[str, Any], after: dict[str, Any]) -> None:
        self._commands[command_id] = (deepcopy(before), deepcopy(after), False)

    def undo(self, expected_revision: str, command_id: str) -> tuple[str, dict[str, Any]] | None:
        entry = self._commands.get(command_id)
        if entry is None or entry[2] or expected_revision != f"view:{self._revision}" or self._view != entry[1]:
            return None
        self._revision += 1
        self._view = deepcopy(entry[0])
        self._commands[command_id] = (entry[0], entry[1], True)
        return self.read()

    def redo(self, expected_revision: str, command_id: str) -> tuple[str, dict[str, Any]] | None:
        entry = self._commands.get(command_id)
        if entry is None or not entry[2] or expected_revision != f"view:{self._revision}" or self._view != entry[0]:
            return None
        self._revision += 1
        self._view = deepcopy(entry[1])
        self._commands[command_id] = (entry[0], entry[1], False)
        return self.read()


def _validate(annotation: dict[str, Any]) -> bool:
    required = {"id", "purpose", "placement", "text"}
    return required <= set(annotation) and isinstance(annotation.get("id"), str) and bool(annotation["id"])


def _write(store: MemoryViewStore, base_revision: str, before: dict[str, Any], candidate: dict[str, Any], command_id: str) -> ViewCommandResult:
    persisted = store.write(base_revision, candidate)
    if persisted is None:
        return ViewCommandResult("rejected", None, ("E_CONFLICT",))
    result_revision, result = persisted
    store.record_command(command_id, before, result)
    return ViewCommandResult("accepted", result, (), result_revision)


def add_presentation_annotation(store: MemoryViewStore, base_revision: str, annotation: dict[str, Any], command_id: str = "add-presentation-annotation") -> ViewCommandResult:
    revision, view = store.read()
    if revision != base_revision:
        return ViewCommandResult("rejected", None, ("E_CONFLICT",))
    if not _validate(annotation):
        return ViewCommandResult("rejected", None, ("E_ANNOTATION",))
    candidate = deepcopy(view)
    annotations = candidate.setdefault("body", {}).setdefault("annotations", [])
    if any(item.get("id") == annotation["id"] for item in annotations):
        return ViewCommandResult("rejected", None, ("E_ANNOTATION",))
    annotations.append(deepcopy(annotation))
    return _write(store, base_revision, view, candidate, command_id)


def edit_presentation_annotation(store: MemoryViewStore, base_revision: str, annotation_id: str, annotation: dict[str, Any], command_id: str = "edit-presentation-annotation") -> ViewCommandResult:
    revision, view = store.read()
    if revision != base_revision:
        return ViewCommandResult("rejected", None, ("E_CONFLICT",))
    if annotation_id != annotation.get("id") or not _validate(annotation):
        return ViewCommandResult("rejected", None, ("E_ANNOTATION",))
    candidate = deepcopy(view)
    annotations = candidate.setdefault("body", {}).setdefault("annotations", [])
    index = next((i for i, item in enumerate(annotations) if item.get("id") == annotation_id), None)
    if index is None:
        return ViewCommandResult("rejected", None, ("E_REFERENCE",))
    annotations[index] = deepcopy(annotation)
    return _write(store, base_revision, view, candidate, command_id)


def delete_presentation_annotation(store: MemoryViewStore, base_revision: str, annotation_id: str, command_id: str = "delete-presentation-annotation") -> ViewCommandResult:
    revision, view = store.read()
    if revision != base_revision:
        return ViewCommandResult("rejected", None, ("E_CONFLICT",))
    candidate = deepcopy(view)
    annotations = candidate.setdefault("body", {}).setdefault("annotations", [])
    retained = [item for item in annotations if item.get("id") != annotation_id]
    if len(retained) == len(annotations):
        return ViewCommandResult("rejected", None, ("E_REFERENCE",))
    candidate["body"]["annotations"] = retained
    return _write(store, base_revision, view, candidate, command_id)


def undo_view_command(store: MemoryViewStore, base_revision: str, command_id: str) -> ViewCommandResult:
    persisted = store.undo(base_revision, command_id)
    return ViewCommandResult("accepted", persisted[1], (), persisted[0]) if persisted else ViewCommandResult("rejected", None, ("E_CONFLICT",))


def redo_view_command(store: MemoryViewStore, base_revision: str, command_id: str) -> ViewCommandResult:
    persisted = store.redo(base_revision, command_id)
    return ViewCommandResult("accepted", persisted[1], (), persisted[0]) if persisted else ViewCommandResult("rejected", None, ("E_CONFLICT",))
