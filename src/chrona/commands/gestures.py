"""Interactive gestures translated into explicit Command proposals."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GestureProposal:
    command_id: str
    base_revision: str
    object_id: str
    field: str
    value: Any


@dataclass(frozen=True)
class ActualResolutionProposal:
    command_id: str
    base_revision: str
    observation_id: str
    project_object_id: str


def propose_typed_field_gesture(
    command_id: str, base_revision: str, scene_id: str, field: str, value: Any
) -> GestureProposal:
    """Map a stable object scene ID to a Command proposal, never to a Project write."""
    prefix = "object:"
    if not scene_id.startswith(prefix) or not scene_id[len(prefix):]:
        raise ValueError("E_GESTURE_TARGET")
    return GestureProposal(command_id, base_revision, scene_id[len(prefix):], field, value)


def propose_actual_resolution(
    command_id: str, base_revision: str, observation_id: str, project_object_id: str
) -> ActualResolutionProposal:
    """Create a previewable reconciliation Command; it performs no store write."""
    if not observation_id or not project_object_id:
        raise ValueError("E_GESTURE_TARGET")
    return ActualResolutionProposal(command_id, base_revision, observation_id, project_object_id)
