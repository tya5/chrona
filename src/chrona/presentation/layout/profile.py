"""Validation and immutable resolution for Layout Profile v0.2."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from typing import Any, Mapping

import jsonschema
import yaml

from chrona.presentation.layout.model import LayoutError, ResolvedLayoutProfile
from chrona.resources import schema_resource


LAYOUT_VERSION = "chrona/layout-profile/v0.2"


@dataclass(frozen=True)
class LayoutBase:
    profile: Mapping[str, Any]
    revision: str
    content_identity: str


def _schema() -> dict[str, Any]:
    return yaml.safe_load(schema_resource("layout-profile-v0.2.schema.yaml").read_text(encoding="utf-8"))


def _validate_schema(profile: Mapping[str, Any]) -> None:
    if profile.get("version") != LAYOUT_VERSION:
        raise LayoutError("E_LAYOUT_SCHEMA", "/version")
    error = next(jsonschema.Draft202012Validator(_schema()).iter_errors(profile), None)
    if error is not None:
        path = "/" + "/".join(str(item) for item in error.absolute_path)
        raise LayoutError("E_LAYOUT_SCHEMA", path)


def _canonical_hash(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    return "sha256:" + sha256(encoded).hexdigest()


def _nodes(root: Mapping[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, str | None]]:
    found: dict[str, dict[str, Any]] = {}
    parents: dict[str, str | None] = {}

    def visit(node: Mapping[str, Any], parent: str | None) -> None:
        node_id = str(node["id"])
        if node_id in found:
            raise LayoutError("E_LAYOUT_NODE_DUPLICATE", node_id=node_id)
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
    resolved["writingMode"] = profile["writingMode"]
    return resolved


def _distance(value: Any, theme_values: Mapping[str, Any], path: str, literals: list[str]) -> Decimal:
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
    declared = theme_values.get(token)
    if declared is None:
        raise LayoutError("E_LAYOUT_TOKEN_UNKNOWN", path)
    if declared.get("type") != "number" or isinstance(declared.get("value"), bool):
        raise LayoutError("E_LAYOUT_TOKEN_TYPE", path)
    try:
        result = Decimal(str(declared["value"]))
    except (InvalidOperation, KeyError) as error:
        raise LayoutError("E_LAYOUT_TOKEN_TYPE", path) from error
    if not result.is_finite() or result < 0:
        raise LayoutError("E_LAYOUT_TOKEN_TYPE", path)
    return result


def _semantic_validate(profile: dict[str, Any], available_sources: set[str], theme: Mapping[str, Any]) -> tuple[dict[str, Decimal], tuple[str, ...]]:
    index, parents = _nodes(profile["root"])
    theme_values = theme.get("body", {}).get("values", {})
    distances: dict[str, Decimal] = {}
    literals: list[str] = []

    def visit(node: dict[str, Any], path: str) -> None:
        node_id, kind = node["id"], node["kind"]
        if kind == "slot":
            if node["source"] not in available_sources and node["priority"] == "required":
                raise LayoutError("E_LAYOUT_SOURCE_UNAVAILABLE", path + "/source", node_id)
            if node["priority"] == "required" and node["overflow"] == "clip-optional":
                raise LayoutError("E_LAYOUT_SCHEMA", path + "/overflow", node_id)
        if "anchor" in node:
            parent = index.get(parents[node_id] or "")
            if parent is None or parent["kind"] != "overlay":
                raise LayoutError("E_LAYOUT_REFERENCE_SCOPE", path + "/anchor", node_id)
            anchor = node["anchor"]
            if "gap" in anchor and anchor["self"] == {"inline": "center", "block": "center"} and anchor["target"]["inline"] == "center" and anchor["target"]["block"] == "center":
                raise LayoutError("E_LAYOUT_CONSTRAINT_CONTRADICTORY", path + "/anchor/gap", node_id)
        for name in ("gap", "padding", "itemMinInlineSize"):
            if name not in node:
                continue
            value = node[name]
            if name == "padding" and isinstance(value, dict) and "token" not in value:
                for side, side_value in value.items():
                    key = f"{path}/{name}/{side}"; distances[key] = _distance(side_value, theme_values, key, literals)
            else:
                key = f"{path}/{name}"; distances[key] = _distance(value, theme_values, key, literals)
        if "anchor" in node and "gap" in node["anchor"]:
            key = f"{path}/anchor/gap"; distances[key] = _distance(node["anchor"]["gap"], theme_values, key, literals)
        if kind == "grid":
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
                reference = anchor["target"]["ref"]
                if reference.startswith("node:") and reference[5:] not in descendants:
                    raise LayoutError("E_LAYOUT_REFERENCE_UNKNOWN", path + "/children", child["id"])
                if reference.startswith("guide:") and reference[6:] not in guides:
                    raise LayoutError("E_LAYOUT_REFERENCE_UNKNOWN", path + "/children", child["id"])
                if reference.startswith("barrier:") and reference[8:] not in barriers:
                    raise LayoutError("E_LAYOUT_REFERENCE_UNKNOWN", path + "/children", child["id"])
        for offset, child in enumerate(node.get("children", ())):
            visit(child, f"{path}/children/{offset}")

    visit(profile["root"], "/root")
    return distances, tuple(sorted(literals))


def resolve_layout_profile(profile: Mapping[str, Any], *, available_sources: set[str], theme: Mapping[str, Any], bases: Mapping[str, LayoutBase] | None = None) -> ResolvedLayoutProfile:
    """Resolve and validate the one M24 authoring resource before geometry."""
    resolved = _merge_base(profile, bases or {}, (str(profile.get("id", "")),))
    _validate_schema(resolved)
    distances, literals = _semantic_validate(resolved, available_sources, theme)
    return ResolvedLayoutProfile(str(resolved["id"]), _canonical_hash(resolved), resolved, distances, literals)

