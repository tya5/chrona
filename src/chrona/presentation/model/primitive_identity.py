"""Renderer-neutral identities for completed multi-part Symbols."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def completed_symbol_primitive_ids(placement_id: str, parts: tuple[Any, ...]) -> tuple[str, ...]:
    """Return the canonical Scene identity for each explicitly painted Symbol part."""
    return tuple(f"{placement_id}:part{index}" if part.paint_mode is not None else placement_id
                 for index, part in enumerate(parts))


def parse_symbol_part_id(primitive_id: object) -> tuple[str, int] | None:
    """Parse only the canonical ``<placement>:partN`` component identity."""
    if not isinstance(primitive_id, str):
        return None
    base, separator, suffix = primitive_id.rpartition(":part")
    if (not separator or not base or not suffix or not suffix.isascii()
            or not suffix.isdecimal()):
        return None
    index = int(suffix)
    if suffix != str(index):
        return None
    return base, index


def completed_symbol_part_group(primitives: Sequence[Mapping[str, Any]], placement_id: str
                                ) -> tuple[Mapping[str, Any], ...] | None:
    """Resolve one exact completed sibling group, or fail closed.

    The group is identity evidence only. It requires canonical IDs, contiguous
    part numbering, and matching Symbol source, purpose, and full completed
    bounds. It never combines geometry or guesses a placement from a prefix.
    """
    if not placement_id:
        return None
    component_prefix = placement_id + ":part"
    candidates = [item for item in primitives
                  if isinstance(item.get("id"), str) and item["id"].startswith(component_prefix)]
    if not candidates:
        return None
    parsed = [(parse_symbol_part_id(item.get("id")), item) for item in candidates]
    if any(identity is None or identity[0] != placement_id for identity, _ in parsed):
        return None
    indexed = [(identity[1], item) for identity, item in parsed if identity is not None]
    indexes = [index for index, _ in indexed]
    if len(indexes) != len(set(indexes)) or sorted(indexes) != list(range(len(indexes))):
        return None
    ordered = tuple(item for _, item in sorted(indexed, key=lambda value: value[0]))
    first = ordered[0]
    source_ref, purpose, bounds = first.get("sourceRef"), first.get("purpose"), first.get("bounds")
    if (first.get("kind") != "Symbol" or not isinstance(source_ref, str) or not source_ref
            or not isinstance(purpose, str) or not purpose or not isinstance(bounds, Mapping)):
        return None
    if any(item.get("kind") != "Symbol" or item.get("sourceRef") != source_ref
           or item.get("purpose") != purpose or item.get("bounds") != bounds for item in ordered[1:]):
        return None
    if any(item.get("id") == placement_id for item in primitives):
        return None
    return ordered


def completed_symbol_part_groups(primitives: Sequence[Mapping[str, Any]]) -> tuple[
        dict[str, tuple[Mapping[str, Any], ...]], frozenset[str]]:
    """Resolve all valid canonical sibling groups and report base-ID collisions."""
    by_id: dict[str, list[Mapping[str, Any]]] = {}
    for item in primitives:
        primitive_id = item.get("id")
        if isinstance(primitive_id, str):
            by_id.setdefault(primitive_id, []).append(item)
    bases = {base for primitive_id in by_id
             if (parsed := parse_symbol_part_id(primitive_id)) is not None
             for base in (parsed[0],)}
    groups: dict[str, tuple[Mapping[str, Any], ...]] = {}
    collisions: set[str] = set()
    for base in bases:
        sibling_ids = [primitive_id for primitive_id in by_id
                       if primitive_id.startswith(base + ":part")]
        duplicate_ids = any(len(by_id[primitive_id]) != 1 for primitive_id in sibling_ids)
        if base in by_id or duplicate_ids:
            collisions.add(base)
            collisions.update(sibling_ids)
            continue
        group = completed_symbol_part_group(primitives, base)
        if group is not None:
            groups[base] = group
    return groups, frozenset(collisions)
