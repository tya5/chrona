"""Structural Layout pruning for explicitly absent presentation sources."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from decimal import Decimal
from typing import Any

from chrona.presentation.layout.model import ResolvedLayoutProfile


def omit_absent_sources(profile: Mapping[str, Any], absent_sources: frozenset[str]) -> Mapping[str, Any]:
    """Return an internal profile with absent-source leaves and empty ancestors removed.

    This is deliberately driven only by the caller's semantic absence set. Empty
    geometry, empty children already present in the profile, and other forms of
    missing content are not interpreted here.
    """
    if not absent_sources:
        return profile

    def prune(node: Any) -> Any:
        if not isinstance(node, Mapping):
            return node
        if node.get("kind") == "slot" and node.get("source") in absent_sources:
            return None

        children = node.get("children")
        if not isinstance(children, list):
            return node
        kept = []
        changed = False
        for child in children:
            result = prune(child)
            if result is None:
                changed = True
                continue
            kept.append(result)
            changed = changed or result is not child

        # Only a non-empty authored subtree that has become empty is removed.
        # A decorative container that was already empty remains untouched.
        if children and not kept:
            return None
        if not changed:
            return node
        copied = dict(node)
        copied["children"] = kept
        return copied

    root = profile.get("root")
    pruned_root = prune(root)
    if pruned_root is root:
        return profile

    if pruned_root is None:
        # The authored grammar requires a non-empty root subtree. Keep a small
        # engine-only shell so the all-absent case remains solvable without
        # fabricating any source geometry or a visible frame.
        root_id = root.get("id", "root") if isinstance(root, Mapping) else "root"
        pruned_root = {
            "id": root_id,
            "kind": "column",
            "inlineSize": root.get("inlineSize", "fill") if isinstance(root, Mapping) else "fill",
            "blockSize": root.get("blockSize", "fill") if isinstance(root, Mapping) else "fill",
            "gap": 0,
            "padding": 0,
            "alignItems": "stretch",
            "justifyContent": "start",
            "children": [],
        }
    copied_profile = dict(profile)
    copied_profile["root"] = pruned_root
    return copied_profile


def omit_absent_layout_sources(resolved: ResolvedLayoutProfile,
                               absent_sources: frozenset[str]) -> ResolvedLayoutProfile:
    """Prune absent sources from a resolved profile and remap node-owned paths.

    Node paths contain child indices, so pruning an earlier sibling moves the
    paths of later nodes. Distances and literal-path provenance are relocated
    by stable node id; authored content identity is intentionally unchanged.
    """
    if not absent_sources:
        return resolved
    profile = omit_absent_sources(resolved.profile, absent_sources)
    if profile is resolved.profile:
        return resolved

    def node_paths(root: Any) -> dict[str, str]:
        result: dict[str, str] = {}

        def visit(node: Any, path: str) -> None:
            if not isinstance(node, Mapping):
                return
            node_id = node.get("id")
            if isinstance(node_id, str):
                result[node_id] = path
            children = node.get("children")
            if isinstance(children, list):
                for index, child in enumerate(children):
                    visit(child, f"{path}/children/{index}")

        visit(root, "/root")
        return result

    old_paths = node_paths(resolved.profile.get("root"))
    new_paths = node_paths(profile.get("root"))
    new_path_by_id = {node_id: path for node_id, path in new_paths.items()}
    path_moves = {
        old_path: new_path_by_id.get(node_id)
        for node_id, old_path in old_paths.items()
    }
    ordered_old_paths = sorted(path_moves, key=len, reverse=True)

    def remap(path: str) -> str | None:
        for old in ordered_old_paths:
            if path == old or path.startswith(old + "/"):
                new = path_moves[old]
                if new is None:
                    return None
                return new + path[len(old):]
        return path

    distances: dict[str, Decimal] = {}
    for path, value in resolved.distances.items():
        mapped = remap(path)
        if mapped is not None:
            distances[mapped] = value
    literal_paths = tuple(sorted({mapped for path in resolved.literal_distance_paths
                                  if (mapped := remap(path)) is not None}))

    root = profile.get("root")
    if isinstance(root, Mapping) and root.get("kind") == "column" and not root.get("children"):
        distances["/root/gap"] = Decimal(0)
        distances["/root/padding"] = Decimal(0)

    return replace(resolved, profile=profile, distances=distances,
                   literal_distance_paths=literal_paths)
