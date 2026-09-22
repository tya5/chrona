"""Project-owned hierarchy normalization for the Date-only Project contract."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class HierarchyEntry:
    """One deterministic Project tree entry, independent of any View policy."""

    object_id: str
    parent_id: str | None
    depth: int
    path: tuple[str, ...]
    display_wbs_code: str


def normalize_hierarchy(project: Mapping[str, Any]) -> tuple[HierarchyEntry, ...]:
    """Return Project-order hierarchy facts after the caller has validated it.

    Mapping order is the authored root/sibling order.  Explicit WBS codes label
    only their own object; generated codes follow the containment path and do
    not create another hierarchy edge.
    """
    objects = project.get("objects", {})
    children: dict[str, list[str]] = {str(object_id): [] for object_id in objects}
    roots: list[str] = []
    for object_id, item in objects.items():
        object_id = str(object_id)
        parent = item.get("parent")
        if parent is None:
            roots.append(object_id)
        elif parent in children:
            children[parent].append(object_id)

    result: list[HierarchyEntry] = []

    def visit(object_id: str, parent_id: str | None, ancestors: tuple[str, ...], ordinal_path: tuple[int, ...]) -> None:
        item = objects[object_id]
        generated = ".".join(str(part) for part in ordinal_path)
        result.append(HierarchyEntry(
            object_id=object_id,
            parent_id=parent_id,
            depth=len(ancestors),
            path=ancestors + (object_id,),
            display_wbs_code=str(item.get("wbsCode", generated)),
        ))
        for ordinal, child_id in enumerate(children[object_id], start=1):
            visit(child_id, object_id, ancestors + (object_id,), ordinal_path + (ordinal,))

    for ordinal, object_id in enumerate(roots, start=1):
        visit(object_id, None, (), (ordinal,))
    return tuple(result)


def children_by_parent(entries: tuple[HierarchyEntry, ...]) -> dict[str, tuple[str, ...]]:
    """Return deterministic direct child order from normalized hierarchy facts."""
    values: dict[str, list[str]] = {entry.object_id: [] for entry in entries}
    for entry in entries:
        if entry.parent_id is not None:
            values[entry.parent_id].append(entry.object_id)
    return {object_id: tuple(children) for object_id, children in values.items()}
