"""Client-side Command result state; never a canonical mutation path."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EditorState:
    revision: str
    model: dict[str, Any]
    status: str = "ready"
    diagnostics: tuple[str, ...] = ()


def apply_command_result(state: EditorState, result: Any) -> EditorState:
    """Accept an issued Command result or preserve state for rollback/resync."""
    diagnostics = tuple(getattr(result, "diagnostics", ()))
    if getattr(result, "status", None) == "accepted":
        model = getattr(result, "project", None) or getattr(result, "actual_set", None) or getattr(result, "view", None)
        revision = getattr(result, "result_revision", None)
        if model is not None and revision is not None:
            return EditorState(revision, model, "applied", diagnostics)
    if "E_CONFLICT" in diagnostics:
        return EditorState(state.revision, state.model, "resync-required", diagnostics)
    return EditorState(state.revision, state.model, "rejected", diagnostics)
