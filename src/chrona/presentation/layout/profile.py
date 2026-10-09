"""Validation and immutable resolution for Layout Profile v0.2."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re
from typing import Any, Mapping

from chrona.presentation.layout.model import (
    SLOT_HEADING_ALIGNS, SLOT_HEADING_BLOCKS, LayoutError, ResolvedLayoutProfile,
)
from chrona.resources import schema_validator, validator_for_schema
from chrona.schema_diagnostics import explain_errors


LAYOUT_VERSION = "chrona/layout-profile/v0.10"
# v0.9 was retired once every committed and packaged profile was on v0.10 (#731); it is an unsupported version now.
LAYOUT_SCHEMAS = {
    LAYOUT_VERSION: "layout-profile-v0.10.schema.yaml",
}


@dataclass(frozen=True)
class LayoutBase:
    profile: Mapping[str, Any]
    revision: str
    content_identity: str


_FRAME_KEYS = frozenset({"inset", "paint"})
_ID = re.compile(r"^[A-Za-z][A-Za-z0-9._-]*$")
_FRAME_PAINT_VALIDATOR = validator_for_schema({"$ref": "urn:chrona:common-v0.1#/$defs/slug"})


def _check_frame_paint(paint: Any, pointer: str) -> None:
    errors = tuple(_FRAME_PAINT_VALIDATOR.iter_errors(paint))
    if errors:
        violation = explain_errors(errors)
        raise LayoutError("E_LAYOUT_SCHEMA", pointer, detail=violation.message)


def _check_frame(frame: Any, pointer: str) -> None:
    """Fail a malformed region frame (#889) at its exact pointer.

    The schema reports an error under a container union at the union's own pointer; a frame is a new
    declaration with its own contract, so its shape is checked first and named precisely. An override is not
    under that union, so the schema already names its frame's path exactly.
    """
    if not isinstance(frame, Mapping):
        raise LayoutError("E_LAYOUT_SCHEMA", pointer, detail="expected an object")
    for key in frame:
        if key not in _FRAME_KEYS:
            raise LayoutError("E_LAYOUT_SCHEMA", f"{pointer}/{key}", detail=f"unexpected property '{key}'")
    if "paint" in frame:
        _check_frame_paint(frame["paint"], f"{pointer}/paint")
    if "inset" not in frame:
        return
    inset = frame["inset"]
    number = isinstance(inset, (int, float)) and not isinstance(inset, bool) and 0 <= inset <= 1000000
    token = (isinstance(inset, Mapping) and set(inset) == {"token"} and isinstance(inset["token"], str)
             and bool(_ID.match(inset["token"])))
    if not (number or token):
        raise LayoutError("E_LAYOUT_SCHEMA", f"{pointer}/inset",
                          detail="expected a non-negative distance or a {token: id} reference")


_HEADING_KEYS = frozenset({"text", "align", "block"})


def _check_heading(heading: Any, pointer: str) -> None:
    """Fail a malformed slot heading (#1064) at its exact pointer, for the reason `_check_frame` gives."""
    if not isinstance(heading, Mapping):
        raise LayoutError("E_LAYOUT_SCHEMA", pointer, detail="expected an object")
    for key in heading:
        if key not in _HEADING_KEYS:
            raise LayoutError("E_LAYOUT_SCHEMA", f"{pointer}/{key}", detail=f"unexpected property '{key}'")
    text = heading.get("text")
    if text is None:
        raise LayoutError("E_LAYOUT_SCHEMA", pointer, detail="missing required property 'text'")
    if (not isinstance(text, str) or not 1 <= len(text) <= 80
            or any(ord(char) < 32 or ord(char) == 127 for char in text)):
        raise LayoutError("E_LAYOUT_SCHEMA", f"{pointer}/text",
                          detail="expected one to eighty characters with no control character")
    for key, allowed in (("align", SLOT_HEADING_ALIGNS), ("block", SLOT_HEADING_BLOCKS)):
        if key in heading and heading[key] not in allowed:
            raise LayoutError("E_LAYOUT_SCHEMA", f"{pointer}/{key}", detail=f"expected one of {list(allowed)}")


def _check_frames(profile: Mapping[str, Any]) -> None:
    def visit(node: Any, path: str) -> None:
        if not isinstance(node, Mapping):
            return
        if "frame" in node:
            _check_frame(node["frame"], f"{path}/frame")
        if "heading" in node:
            _check_heading(node["heading"], f"{path}/heading")
        children = node.get("children")
        for index, child in enumerate(children if isinstance(children, list) else ()):
            visit(child, f"{path}/children/{index}")

    visit(profile.get("root"), "/root")
    overrides = profile.get("overrides")
    if isinstance(overrides, Mapping):
        for node_id, override in overrides.items():
            frame = override.get("frame") if isinstance(override, Mapping) else None
            if isinstance(frame, Mapping) and "paint" in frame:
                _check_frame_paint(frame["paint"], f"/overrides/{node_id}/frame/paint")


def _validate_schema(profile: Mapping[str, Any]) -> None:
    schema = LAYOUT_SCHEMAS.get(profile.get("version"))
    if schema is None:
        raise LayoutError("E_LAYOUT_SCHEMA", "/version")
    _check_frames(profile)
    errors = tuple(schema_validator(schema).iter_errors(profile))
    if errors:
        identity = profile.get("id")
        violation = explain_errors(
            errors, resource_kind="layout-profile", resource_identity=identity if isinstance(identity, str) else None,
        )
        raise LayoutError("E_LAYOUT_SCHEMA", violation.pointer, detail=violation.message)


def _canonical_hash(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    return "sha256:" + sha256(encoded).hexdigest()


def _nodes(root: Mapping[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, str | None]]:
    found: dict[str, dict[str, Any]] = {}
    parents: dict[str, str | None] = {}

    def visit(node: Mapping[str, Any], parent: str | None) -> None:
        node_id = str(node["id"])
        if node_id in found:
            raise LayoutError("E_LAYOUT_NODE_DUPLICATE", node_id=node_id,
                              detail=f"node ID {node_id[:160]!r} is repeated in the Layout profile")
        found[node_id] = node  # type: ignore[assignment]
        parents[node_id] = parent
        for child in node.get("children", ()):
            visit(child, node_id)

    visit(root, None)
    return found, parents


def _merge_base(profile: Mapping[str, Any], bases: Mapping[str, LayoutBase], stack: tuple[str, ...]) -> dict[str, Any]:
    _validate_schema(profile)
    if "root" in profile:
        return deepcopy(dict(profile))
    reference = profile["extends"]
    base_id = str(reference["id"])
    if base_id in stack:
        raise LayoutError("E_LAYOUT_BASE_CYCLE", "/extends", base_id)
    base = bases.get(base_id)
    if base is None or base.revision != reference["revision"]["token"] or base.content_identity != reference["contentIdentity"]:
        raise LayoutError("E_LAYOUT_REFERENCE_UNKNOWN", "/extends", base_id)
    resolved = _merge_base(base.profile, bases, stack + (base_id,))
    index, _ = _nodes(resolved["root"])
    for node_id, override in profile["overrides"].items():
        target = index.get(node_id)
        if target is None:
            raise LayoutError("E_LAYOUT_OVERRIDE_UNKNOWN", f"/overrides/{node_id}", node_id)
        if "id" in override or "kind" in override:
            raise LayoutError("E_LAYOUT_OVERRIDE_KIND", f"/overrides/{node_id}", node_id)
        target.update(deepcopy(override))
    resolved["id"] = profile["id"]
    resolved["flowDirection"] = profile["flowDirection"]
    resolved["dependencyNetworkFlowDirection"] = profile["dependencyNetworkFlowDirection"]
    resolved["requiredThemeTokens"] = deepcopy(profile["requiredThemeTokens"])
    resolved["reviewSurface"] = deepcopy(profile["reviewSurface"])
    return resolved


def _distance(value: Any, theme_values: Mapping[str, Any], path: str, literals: list[str], used_tokens: set[str]) -> Decimal:
    if isinstance(value, bool):
        raise LayoutError("E_LAYOUT_TOKEN_TYPE", path)
    if isinstance(value, (int, float)):
        literals.append(path)
        try:
            result = Decimal(str(value))
        except InvalidOperation as error:
            raise LayoutError("E_LAYOUT_TOKEN_TYPE", path) from error
        if not result.is_finite() or result < 0:
            raise LayoutError("E_LAYOUT_TOKEN_TYPE", path)
        return result
    token = str(value["token"])
    used_tokens.add(token)
    declared = theme_values.get(token)
    if declared is None:
        raise LayoutError("E_LAYOUT_TOKEN_REQUIREMENT_UNAVAILABLE", path, token)
    if declared.get("type") != "number" or isinstance(declared.get("value"), bool):
        raise LayoutError("E_LAYOUT_TOKEN_REQUIREMENT_TYPE", path, token)
    try:
        result = Decimal(str(declared["value"]))
    except (InvalidOperation, KeyError) as error:
        raise LayoutError("E_LAYOUT_TOKEN_REQUIREMENT_TYPE", path, token) from error
    if not result.is_finite() or result < 0:
        raise LayoutError("E_LAYOUT_TOKEN_REQUIREMENT_TYPE", path, token)
    return result


def _semantic_validate(profile: dict[str, Any], available_sources: set[str], theme: Mapping[str, Any]) -> tuple[dict[str, Decimal], tuple[str, ...]]:
    index, parents = _nodes(profile["root"])
    theme_values = theme.get("body", {}).get("values", {})
    distances: dict[str, Decimal] = {}
    literals: list[str] = []
    used_tokens: set[str] = set()

    def collect_tokens(value: Any) -> None:
        if isinstance(value, dict):
            if set(value) == {"token"} and isinstance(value["token"], str):
                used_tokens.add(value["token"])
            for child in value.values():
                collect_tokens(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                collect_tokens(child)

    collect_tokens(profile["root"])
    declared = tuple(profile["requiredThemeTokens"])
    if tuple(sorted(declared)) != declared:
        raise LayoutError("E_LAYOUT_TOKEN_REQUIREMENTS", "/requiredThemeTokens")
    missing = sorted(used_tokens - set(declared))
    if missing:
        raise LayoutError("E_LAYOUT_TOKEN_REQUIREMENT_MISSING", "/requiredThemeTokens", missing[0])
    extraneous = sorted(set(declared) - used_tokens)
    if extraneous:
        raise LayoutError("E_LAYOUT_TOKEN_REQUIREMENT_EXTRANEOUS", "/requiredThemeTokens", extraneous[0])

    def size_distances(spec: Any, path: str) -> None:
        if not isinstance(spec, dict):
            return
        if "fixed" in spec:
            distances[path + "/fixed"] = _distance(spec["fixed"], theme_values, path + "/fixed", literals, used_tokens)
        elif "fitContent" in spec:
            distances[path + "/fitContent"] = _distance(spec["fitContent"], theme_values, path + "/fitContent", literals, used_tokens)
        elif "minmax" in spec:
            size_distances(spec["minmax"]["min"], path + "/minmax/min")
            size_distances(spec["minmax"]["max"], path + "/minmax/max")

    def visit(node: dict[str, Any], path: str) -> None:
        node_id, kind = node["id"], node["kind"]
        if isinstance(node["inlineSize"], dict) and "aspectRatio" in node["inlineSize"] and isinstance(node["blockSize"], dict) and "aspectRatio" in node["blockSize"]:
            raise LayoutError("E_LAYOUT_CONSTRAINT_CONTRADICTORY", path, node_id)
        size_distances(node["inlineSize"], path + "/inlineSize")
        size_distances(node["blockSize"], path + "/blockSize")
        if kind == "slot":
            source = node["source"]
            available_source = "title" if source == "heading" else source
            if available_source not in available_sources and node["priority"] == "required":
                raise LayoutError("E_LAYOUT_SOURCE_UNAVAILABLE", path + "/source", node_id)
            if node["priority"] == "required" and node["overflow"] == "clip-optional":
                raise LayoutError("E_LAYOUT_SCHEMA", path + "/overflow", node_id)
        if "anchor" in node:
            parent = index.get(parents[node_id] or "")
            if parent is None or parent["kind"] != "overlay":
                raise LayoutError("E_LAYOUT_REFERENCE_SCOPE", path + "/anchor", node_id)
        for name in ("gap", "padding", "itemMinInlineSize"):
            if name not in node:
                continue
            value = node[name]
            if name == "padding" and isinstance(value, dict) and "token" not in value:
                for side, side_value in value.items():
                    key = f"{path}/{name}/{side}"; distances[key] = _distance(side_value, theme_values, key, literals, used_tokens)
            else:
                key = f"{path}/{name}"; distances[key] = _distance(value, theme_values, key, literals, used_tokens)
        if "inset" in node.get("frame", {}):
            key = f"{path}/frame/inset"
            distances[key] = _distance(node["frame"]["inset"], theme_values, key, literals, used_tokens)
        if "anchor" in node and "gap" in node["anchor"]:
            anchor = node["anchor"]
            for axis, value in anchor["gap"].items():
                key = f"{path}/anchor/gap/{axis}"
                distances[key] = _distance(value, theme_values, key, literals, used_tokens)
                if anchor["self"][axis] == "center" and anchor["target"][axis]["point"] == "center":
                    raise LayoutError("E_LAYOUT_CONSTRAINT_CONTRADICTORY", key, node_id)
        if kind == "grid":
            if any(isinstance(track, dict) and "aspectRatio" in track for track in (*node["columnTracks"], *node["rowTracks"])):
                raise LayoutError("E_LAYOUT_CONSTRAINT_CONTRADICTORY", path, node_id)
            for offset, track in enumerate(node["columnTracks"]): size_distances(track, f"{path}/columnTracks/{offset}")
            for offset, track in enumerate(node["rowTracks"]): size_distances(track, f"{path}/rowTracks/{offset}")
            columns, rows = len(node["columnTracks"]), len(node["rowTracks"])
            for child in node["children"]:
                cell = child.get("cell")
                if not cell or cell["column"] > columns or cell["row"] > rows or cell.get("columnSpan", 1) + cell["column"] - 1 > columns or cell.get("rowSpan", 1) + cell["row"] - 1 > rows:
                    raise LayoutError("E_LAYOUT_CONSTRAINT_CONTRADICTORY", path + "/children", child["id"])
        if kind == "overlay":
            descendants = {child["id"] for child in node["children"]}
            guides, barriers = node.get("guides", {}), node.get("barriers", {})
            for barrier_id, barrier in barriers.items():
                if any(member not in descendants for member in barrier["members"]):
                    raise LayoutError("E_LAYOUT_REFERENCE_UNKNOWN", path + f"/barriers/{barrier_id}", barrier_id)
            for child in node["children"]:
                anchor = child.get("anchor")
                if not anchor:
                    continue
                for axis in ("inline", "block"):
                    reference = anchor["target"][axis]["ref"]
                    target_path = path + f"/children/{child['id']}/anchor/target/{axis}"
                    if reference.startswith("node:") and reference[5:] not in descendants:
                        raise LayoutError("E_LAYOUT_REFERENCE_UNKNOWN", target_path, child["id"])
                    if reference.startswith("guide:"):
                        guide = guides.get(reference[6:])
                        if guide is None:
                            raise LayoutError("E_LAYOUT_REFERENCE_UNKNOWN", target_path, child["id"])
                        if guide["axis"] != axis:
                            raise LayoutError("E_LAYOUT_REFERENCE_SCOPE", target_path, child["id"])
                    if reference.startswith("barrier:"):
                        barrier = barriers.get(reference[8:])
                        if barrier is None:
                            raise LayoutError("E_LAYOUT_REFERENCE_UNKNOWN", target_path, child["id"])
                        if barrier["axis"] != axis:
                            raise LayoutError("E_LAYOUT_REFERENCE_SCOPE", target_path, child["id"])

            dependencies: dict[str, set[str]] = {child["id"]: set() for child in node["children"]}
            for child in node["children"]:
                for target in child.get("anchor", {}).get("target", {}).values():
                    reference = target["ref"]
                    if reference.startswith("node:"):
                        dependencies[child["id"]].add(reference[5:])
                    elif reference.startswith("barrier:"):
                        dependencies[child["id"]].update(barriers[reference[8:]]["members"])

            visiting: set[str] = set()
            visited: set[str] = set()
            def check_cycle(node_name: str) -> None:
                if node_name in visiting:
                    raise LayoutError("E_LAYOUT_CONSTRAINT_CYCLE", path, node_name)
                if node_name in visited:
                    return
                visiting.add(node_name)
                for dependency in dependencies[node_name]:
                    check_cycle(dependency)
                visiting.remove(node_name)
                visited.add(node_name)
            for child_id in sorted(dependencies):
                check_cycle(child_id)
        for offset, child in enumerate(node.get("children", ())):
            visit(child, f"{path}/children/{offset}")

    visit(profile["root"], "/root")
    heading_claims: dict[str, tuple[str, str]] = {}
    heading_parts = {"heading.title": ("title",), "heading.kicker": ("kicker",),
                     "heading.subtitle": ("subtitle",)}

    def claim_heading(node: dict[str, Any], path: str) -> None:
        if node.get("kind") == "slot":
            source = node["source"]
            claimed = ("kicker", "title", "subtitle") if source in {"title", "heading"} else heading_parts.get(source, ())
            for part in claimed:
                previous = heading_claims.get(part)
                if previous is not None:
                    previous_source, previous_id = previous
                    raise LayoutError(
                        "E_LAYOUT_SCHEMA", path + "/source", str(node["id"]),
                        f"heading part {part!r} is already claimed by slot {previous_id!r} ({previous_source!r})",
                    )
                heading_claims[part] = (source, str(node["id"]))
        for offset, child in enumerate(node.get("children", ())):
            claim_heading(child, f"{path}/children/{offset}")

    claim_heading(profile["root"], "/root")
    return distances, tuple(sorted(literals))


def resolve_layout_profile(profile: Mapping[str, Any], *, available_sources: set[str], theme: Mapping[str, Any], bases: Mapping[str, LayoutBase] | None = None) -> ResolvedLayoutProfile:
    """Resolve and validate the one M24 authoring resource before geometry."""
    resolved = _merge_base(profile, bases or {}, (str(profile.get("id", "")),))
    _validate_schema(resolved)
    distances, literals = _semantic_validate(resolved, available_sources, theme)
    def canonicalize_heading_aliases(node: dict[str, Any]) -> None:
        if node.get("kind") == "slot" and node.get("source") == "heading":
            node["source"] = "title"
        for child in node.get("children", ()):
            canonicalize_heading_aliases(child)
    canonicalize_heading_aliases(resolved["root"])
    return ResolvedLayoutProfile(str(resolved["id"]), _canonical_hash(resolved), resolved, distances, literals)
