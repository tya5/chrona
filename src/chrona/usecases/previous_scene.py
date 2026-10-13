"""Validate an explicit previous artifact before Layout sees route evidence."""
from __future__ import annotations

from dataclasses import dataclass
import json

from chrona.presentation.contracts.resources import FrozenDict, freeze
from chrona.presentation.scene.serialization import SceneSerializationError, validate_scene_document
from chrona.presentation.layout.relation_hint_model import (
    HintMark, HintMarker, HintRelation, HintSurface, PreviousRouteHints,
)


@dataclass(frozen=True)
class PreviousSceneInput:
    value: FrozenDict
    route_hints: PreviousRouteHints


def decode_previous_scene(payload: bytes, project_id: str, *,
                          current_theme_identity: str | None = None) -> PreviousSceneInput:
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
    themes = [item for item in value["provenance"]["resources"] if item["kind"] == "theme"]
    theme_identity = themes[0]["contentIdentity"] if len(themes) == 1 else None
    surfaces = []
    for surface in value["surfaces"]:
        marks, relations = [], []
        for primitive in surface["primitives"]:
            if primitive.get("purpose") == "dependency" and primitive.get("fromInstanceId") and primitive.get("toInstanceId"):
                relations.append(HintRelation(primitive["sourceRef"], primitive["fromInstanceId"],
                    primitive["toInstanceId"], tuple(tuple(point) for point in primitive.get("points", ())),
                    _hint_marker(primitive.get("markerStart")), _hint_marker(primitive.get("markerEnd"))))
            elif primitive.get("purpose") in {"planned", "actual", "baseline"}:
                bounds = primitive["bounds"]
                marks.append(HintMark(primitive["id"], primitive["sourceRef"], primitive["kind"],
                    primitive["purpose"], tuple(float(bounds[key])
                        for key in ("inline", "block", "inlineSize", "blockSize"))))
        surfaces.append(HintSurface(surface["id"], tuple(marks), tuple(relations)))
    hints = PreviousRouteHints(value["version"] == "chrona/scene/v0.7", tuple(surfaces),
                               theme_identity, theme_identity is not None and theme_identity == current_theme_identity)
    return PreviousSceneInput(freeze(value), hints)


def _hint_marker(value) -> HintMarker | None:
    if value is None:
        return None
    return HintMarker(tuple((item["kind"], tuple(tuple(point) for point in item["points"]))
                            for item in value["outline"]), float(value["headLength"]),
                      float(value["headWidth"]), float(value["attachmentOffset"]), value["paintMode"])
