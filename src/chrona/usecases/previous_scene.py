"""Validate an explicit previous artifact before Layout sees route evidence."""
from __future__ import annotations

from dataclasses import dataclass
import json

from chrona.presentation.contracts.resources import FrozenDict, freeze
from chrona.presentation.scene.serialization import SceneSerializationError, validate_scene_document


@dataclass(frozen=True)
class PreviousSceneInput:
    value: FrozenDict


def decode_previous_scene(payload: bytes, project_id: str) -> PreviousSceneInput:
    """Schema and project identity are ingress rules, never routing heuristics."""
    try:
        value = json.loads(payload)
    except (ValueError, UnicodeError) as error:
        raise SceneSerializationError("E_SCENE_SERIALIZATION: previous Scene must be valid JSON") from error
    if not isinstance(value, dict):
        raise SceneSerializationError("E_SCENE_SERIALIZATION: previous Scene must be an object")
    validate_scene_document(value)
    projects = [item for item in value["provenance"]["resources"] if item["kind"] == "project"]
    if len(projects) != 1 or projects[0]["id"] != project_id:
        raise SceneSerializationError(
            "E_SCENE_SERIALIZATION: previous Scene must identify exactly the current primary Project")
    return PreviousSceneInput(freeze(value))
