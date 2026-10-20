"""Validate an explicit previous artifact before Layout sees route evidence."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from typing import Any

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
        primitives = surface["primitives"]
        by_id = {primitive["id"]: primitive for primitive in primitives}
        relations = []
        for primitive in primitives:
            if primitive.get("purpose") != "dependency" or not primitive.get("fromInstanceId") or not primitive.get("toInstanceId"):
                continue
            marker_end = primitive.get("markerEnd")
            fan_in = primitive.get("fanIn")
            if isinstance(fan_in, Mapping) and fan_in["terminalOwnerId"] != primitive["id"]:
                # Scene validation has proved that this exact owner is a
                # same-surface relation with the same target port. Its shared
                # end terminal is evidence for matching the configured mark;
                # it is not replayed into the preserved Scene or Layout.
                owner = by_id[fan_in["terminalOwnerId"]]
                marker_end = owner.get("markerEnd")
            relations.append(HintRelation(primitive["sourceRef"], primitive["fromInstanceId"],
                primitive["toInstanceId"], tuple(tuple(point) for point in primitive.get("points", ())),
                _hint_marker(primitive.get("markerStart")), _hint_marker(marker_end)))
        surfaces.append(HintSurface(surface["id"], _hint_marks(surface["primitives"]), tuple(relations)))
    hints = PreviousRouteHints(value["version"] == "chrona/scene/v0.7", tuple(surfaces),
                               theme_identity, theme_identity is not None and theme_identity == current_theme_identity)
    return PreviousSceneInput(freeze(value), hints)


_PRIMARY_MARK_PURPOSES = {"planned", "actual", "baseline", "forecast"}


def _part_parent(primitive_id: str) -> tuple[str, int] | None:
    base, separator, suffix = primitive_id.rpartition(":part")
    if not separator or not base or not suffix.isdigit():
        return None
    try:
        index = int(suffix)
    except ValueError:
        return None
    if suffix != str(index):
        return None
    return base, index


def _hint_marks(primitives: Sequence[Mapping[str, Any]]) -> tuple[HintMark, ...]:
    """Decode primary hosts, coalescing only exact completed Symbol siblings."""
    groups: dict[str, list[tuple[int, Mapping[str, Any]]]] = {}
    by_id = {item["id"]: item for item in primitives}
    for primitive in primitives:
        parsed = _part_parent(primitive["id"])
        if parsed is not None:
            groups.setdefault(parsed[0], []).append((parsed[1], primitive))

    coalesced: dict[str, Mapping[str, Any]] = {}
    collisions: set[str] = set()
    for base, indexed in groups.items():
        siblings = [item for _, item in indexed]
        sibling_ids = [item["id"] for item in siblings]
        if base in by_id or len(set(sibling_ids)) != len(sibling_ids):
            collisions.update((base, *sibling_ids))
            continue
        indices = sorted(index for index, _ in indexed)
        first = next((item for index, item in indexed if index == 0), siblings[0])
        same_metadata = all(
            item.get("kind") == "Symbol"
            and item.get("sourceRef") == first.get("sourceRef")
            and item.get("purpose") == first.get("purpose")
            and item.get("bounds") == first.get("bounds")
            for item in siblings
        )
        if (same_metadata and first.get("kind") == "Symbol"
                and first.get("purpose") in _PRIMARY_MARK_PURPOSES
                and indices == list(range(len(indices)))):
            coalesced[base] = first

    marks = []
    emitted_groups: set[str] = set()
    for primitive in primitives:
        purpose = primitive.get("purpose")
        if purpose not in _PRIMARY_MARK_PURPOSES or primitive["id"] in collisions:
            continue
        parsed = _part_parent(primitive["id"])
        if parsed is not None and parsed[0] in coalesced:
            base = parsed[0]
            if base in emitted_groups:
                continue
            primitive = coalesced[base]
            primitive_id = base
            emitted_groups.add(base)
        else:
            primitive_id = primitive["id"]
        bounds = primitive["bounds"]
        marks.append(HintMark(primitive_id, primitive["sourceRef"], primitive["kind"],
            purpose, tuple(float(bounds[key])
                for key in ("inline", "block", "inlineSize", "blockSize"))))
    return tuple(marks)


def _hint_marker(value) -> HintMarker | None:
    if value is None:
        return None
    return HintMarker(tuple((item["kind"], tuple(tuple(point) for point in item["points"]))
                            for item in value["outline"]), float(value["headLength"]),
                      float(value["headWidth"]), float(value["attachmentOffset"]), value["paintMode"])
