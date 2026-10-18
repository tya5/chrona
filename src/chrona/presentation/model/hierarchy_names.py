"""Source-local member names, closed before text measurement or placement."""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from chrona.presentation.contracts.resources import _PrivateGroupingMode
from chrona.presentation.group_header_text import parse_template


NameKey = tuple[str, str, str, str, str]


def member_name_key(item: Any, container_id: str = "") -> NameKey:
    return (item.source_kind, item.scenario_id or "", item.item_id or item.object_id,
            item.object_id, container_id)


def path_name_selected(view: Any) -> bool:
    labels = view.visibility.labels
    return isinstance(labels, Mapping) and "path" in labels.get("content", ())


def source_path(item: Any) -> tuple[tuple[str, str], ...]:
    """Never look up a comparison ancestor in an unrelated primary Project."""
    ids = item.hierarchy_path
    titles = getattr(item, "hierarchy_titles", ())
    if not ids:
        return ((item.object_id, item.title or item.object_id),)
    return tuple((object_id, titles[index] if index < len(titles) and titles[index].strip()
                  else item.title if object_id == item.object_id and item.title.strip() else object_id)
                 for index, object_id in enumerate(ids))


def close_member_names(projection: Any, view: Any) -> Mapping[NameKey, str]:
    """Use typed enclosing rows/headers, never coincident title/entity text."""
    if not path_name_selected(view):
        return MappingProxyType({})
    names: dict[NameKey, str] = {}
    grouping = view.grouping
    root_headers = (grouping is not None
                    and grouping.by is _PrivateGroupingMode.PROJECT_ROOT_GROUP
                    and grouping.presentation == "header")
    group_ids = projection.group_ids or tuple(dict.fromkeys(
        row.group_id for row in projection.lane_rows if row.group_id))

    def header_names_object(group_id: str) -> bool:
        if not root_headers or not group_id:
            return False
        header = grouping.header
        if header is None:
            return True
        template = (header.first if group_ids and group_id == group_ids[0]
                    and header.first is not None else header.text)
        return "title" in parse_template(template, allow_roles=True).fields

    def remember(item: Any, container: str, group_id: str = "",
                 represented: frozenset[str] = frozenset()) -> None:
        covered = represented
        if (header_names_object(group_id) and item.source_kind in {"primary", "combined", "actual"}
                and group_id in item.hierarchy_path[:-1]):
            covered = covered | {group_id}
        segments = source_path(item)
        full = " / ".join(title for _, title in segments)
        names.setdefault(member_name_key(item), full)
        names[member_name_key(item, container)] = " / ".join(
            title for object_id, title in segments if object_id == item.object_id or object_id not in covered)

    rows = {row.row_id: row for row in projection.rows}
    for row in projection.rows:
        # Only typed enclosing hierarchy rows can cover ancestors. Merely
        # seeing an ancestor somewhere else on the slide is insufficient.
        ancestors: list[Any] = []
        parent = row.parent_row_id if projection.hierarchy_grouping else None
        seen: set[str] = set()
        while parent in rows and parent not in seen:
            seen.add(parent)
            ancestor = rows[parent]
            ancestors.extend(item for item in ancestor.items if item.item_id == ancestor.table_subject_id)
            parent = ancestor.parent_row_id
        for item in row.items:
            represented = frozenset(ancestor.object_id for ancestor in ancestors
                                    if _project_source(ancestor) == _project_source(item)
                                    and ancestor.scenario_id == item.scenario_id)
            remember(item, row.row_id, row.group_id, represented)
    for row in projection.lane_rows:
        for item in row.items:
            remember(item, row.lane_id, row.group_id)
    for folded in projection.folded_points:
        for item in folded.all_items:
            remember(item, folded.group_id, folded.group_id)
    if not projection.has_rows and projection.lane_membership is None:
        for item in projection.items:
            remember(item, item.object_id, item.group_id)
    return MappingProxyType(names)


def _project_source(item: Any) -> str:
    return "primary" if item.source_kind in {"primary", "combined", "actual"} else item.source_kind
