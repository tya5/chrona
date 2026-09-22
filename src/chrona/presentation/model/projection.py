"""Typed, view-owned Plan/Actual review projection model."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import date
from typing import Any

from chrona.core.hierarchy import HierarchyEntry, normalize_hierarchy


@dataclass(frozen=True)
class ReviewItem:
    """One selected source object as displayed by a ReviewRow."""
    object_id: str
    title: str
    source_type: str
    planned: dict[str, date]
    actual: dict[str, date | float] | None
    finish_delta: int | None
    roles: tuple[str, ...]
    group_id: str = ""
    group_label: str = ""
    fields: dict[str, Any] | None = None
    item_id: str = ""
    source_kind: str = "primary"
    track: str = "stacked"
    parent_id: str | None = None
    hierarchy_depth: int = 0
    wbs_code: str = ""
    hierarchy_path: tuple[str, ...] = ()
    is_rollup: bool = False


@dataclass(frozen=True)
class ReviewRowProjection:
    """A View-owned row, with independently addressable ReviewItems."""
    row_id: str
    label: str
    group_id: str
    table_subject_id: str
    items: tuple[ReviewItem, ...]
    depth: int = 0
    parent_row_id: str | None = None
    rollup_presentation: str = "none"


@dataclass(frozen=True)
class ReviewProjection:
    items: tuple[ReviewItem, ...]
    window: tuple[date, date]
    unmatched_actual_ids: tuple[str, ...]
    diagnostics: tuple[str, ...]
    rows: tuple[ReviewRowProjection, ...] = ()
    comparison_facets: tuple[str, ...] = ()
    hierarchy_grouping: bool = False


@dataclass(frozen=True)
class FederatedSceneInput:
    """Display-only child summary data, kept outside the canonical Project."""

    nodes: dict[str, dict[str, Any]]


def federated_scene_input(plan: dict[str, Any], resolved_exports: dict[str, dict[str, Any]]) -> FederatedSceneInput:
    """Namespace published child objects for presentation consumption only."""
    nodes: dict[str, dict[str, Any]] = {}
    for entry in plan.get("exports", []):
        federation_id = entry["id"]
        namespace = entry["presentation"]["namespace"]
        export = resolved_exports.get(federation_id)
        if export is None:
            continue
        for item in export.get("objects", []):
            node_id = f"{namespace}:{item['id']}"
            nodes[node_id] = {
                "sceneId": f"federation:{federation_id}:{item['id']}",
                "title": item.get("title", item["id"]),
                "schedule": deepcopy(item.get("schedule", {})),
                "progress": item.get("progress"),
                "aggregation": deepcopy(export.get("progressAggregation", {})),
            }
    return FederatedSceneInput(nodes)


def build_review_projection(project: dict[str, Any], placements: dict[str, dict[str, date]],
                            view: dict[str, Any], actual_set: dict[str, Any] | None,
                            style: dict[str, Any] | None = None,
                            theme: dict[str, Any] | None = None,
                            snapshot_project: dict[str, Any] | None = None,
                            snapshot_placements: dict[str, dict[str, date]] | None = None) -> ReviewProjection:
    """Derive review facts; composition belongs to View, never Project."""
    body = view["body"]
    if body["comparison"]["actual"] == "required" and actual_set is None:
        raise ValueError("E_ACTUAL_REQUIRED")
    if theme is not None and not theme.get("body", {}).get("roles"):
        raise ValueError("E_THEME_ROLES")
    latest, unmatched = _latest_observations(
        (actual_set or {}).get("body", actual_set or {}).get("observations", []), placements)
    explicit = body.get("rows", {}).get("mode") == "explicit"
    include = body.get("selection", {}).get("include", {})
    ids, types = set(include.get("ids", placements)), set(include.get("types", ("span", "point")))
    grouping = body.get("grouping", {"by": "none", "missing": "ungrouped"})
    selected: list[ReviewItem] = []
    hierarchy = grouping.get("by") == "hierarchy"
    hierarchy_entries = {entry.object_id: entry for entry in normalize_hierarchy(project)}
    hierarchy_root_ids: set[str] = set()
    for object_id, planned in placements.items():
        source_type = "point" if "at" in planned else "span"
        if not explicit and not hierarchy and (object_id not in ids or source_type not in types):
            continue
        if hierarchy and object_id in ids and source_type in types:
            hierarchy_root_ids.add(object_id)
        actual = _actual(latest.get(object_id))
        finish_delta = _finish_delta(planned, actual)
        entry = hierarchy_entries.get(object_id)
        group_id = _group_id(project, object_id, source_type, grouping)
        selected.append(ReviewItem(
            object_id, str(project["objects"][object_id].get("title", object_id)), source_type,
            planned, actual, finish_delta, _roles(style, source_type, actual, finish_delta),
            group_id, str(project.get("entities", {}).get(group_id, {}).get("title", group_id)),
            dict(project["objects"][object_id].get("fields", {})), object_id, "primary",
            parent_id=entry.parent_id if entry else None,
            hierarchy_depth=entry.depth if entry else 0,
            wbs_code=entry.display_wbs_code if entry else "",
            hierarchy_path=entry.path if entry else (),
            is_rollup=project["objects"][object_id].get("schedule", {}).get("mode") == "rollup"))
    if not selected:
        raise ValueError("E_REVIEW_EMPTY")
    if hierarchy and not explicit:
        selected = _expand_hierarchy_roots(selected, hierarchy_entries, hierarchy_root_ids, body)
    elif not explicit:
        _order(selected, body)
    snapshots = _snapshot_items(snapshot_project, snapshot_placements, style)
    rows = _compose_rows(body, selected, snapshots)
    dates = [v for row in rows for item in row.items for v in item.planned.values()]
    if body["window"].get("mode") == "selected-comparison":
        dates += [v for row in rows for item in row.items for v in (item.actual or {}).values() if isinstance(v, date)]
    start, end = min(dates), max(dates)
    margin = body["window"].get("marginDays", 0)
    if body["window"].get("mode") == "explicit":
        start, end = (_date_or_number(body["window"][part]) for part in ("start", "end"))
        margin = 0
        if start >= end:
            raise ValueError("E_REVIEW_WINDOW")
    return ReviewProjection(tuple(selected),
        (date.fromordinal(start.toordinal() - margin), date.fromordinal(end.toordinal() + margin)),
        tuple(sorted(unmatched)), tuple("E_ACTUAL_UNMATCHED" for _ in unmatched), rows,
        tuple(body["comparison"].get("facets", ())), hierarchy)


def _compose_rows(body: dict[str, Any], selected: list[ReviewItem],
                  snapshots: dict[str, ReviewItem]) -> tuple[ReviewRowProjection, ...]:
    rows = body.get("rows", {})
    if rows.get("mode", "automatic") != "explicit":
        return tuple(ReviewRowProjection(
            item.object_id, item.title, item.group_id, item.object_id,
            (replace(item, item_id=item.object_id, source_kind="combined"),),
            depth=item.hierarchy_depth if body.get("grouping", {}).get("by") == "hierarchy" else 0,
            rollup_presentation=(str(body.get("grouping", {}).get("rollup", "none"))
                                 if item.is_rollup else "none"))
            for item in selected)
    available = {item.object_id: item for item in selected}
    output: list[ReviewRowProjection] = []
    seen_rows: set[str] = set()
    for row in rows.get("items", ()):
        row_id = str(row["id"])
        if row_id in seen_rows:
            raise ValueError("E_REVIEW_ROW_ID_DUPLICATE")
        seen_rows.add(row_id)
        members, member_ids = [], set()
        for spec in row["items"]:
            item_id, source = str(spec["id"]), spec["source"]
            if item_id in member_ids:
                raise ValueError("E_REVIEW_ITEM_ID_DUPLICATE")
            member_ids.add(item_id)
            object_id, kind = str(source["object"]), source["kind"]
            base = snapshots.get(object_id) if kind == "snapshot" else available.get(object_id)
            if kind not in {"primary", "actual", "snapshot"} or base is None:
                raise ValueError("E_REVIEW_ITEM_SOURCE_UNAVAILABLE")
            if kind == "actual" and base.actual is None:
                raise ValueError("E_REVIEW_ITEM_SOURCE_UNAVAILABLE")
            track = str(spec.get("track", "stacked"))
            if track not in {"stacked", "shared"}:
                raise ValueError("E_REVIEW_ITEM_TRACK")
            members.append(replace(base, item_id=item_id, source_kind=kind, track=track))
        subject = str(row.get("tableSubject", members[0].item_id if members else ""))
        if subject not in member_ids:
            raise ValueError("E_REVIEW_TABLE_SUBJECT")
        output.append(ReviewRowProjection(row_id, str(row.get("label", members[0].title)),
            str(row.get("group", "")), subject, tuple(members), depth=int(row["depth"]),
            parent_row_id=str(row["parentRow"]) if "parentRow" in row else None))
    _validate_explicit_row_hierarchy(output)
    return tuple(output)


def _validate_explicit_row_hierarchy(rows: list[ReviewRowProjection]) -> None:
    """Validate only asserted View row edges against the Project-owned hierarchy."""
    by_id = {row.row_id: row for row in rows}
    for row in rows:
        if row.parent_row_id is None:
            continue
        parent = by_id.get(row.parent_row_id)
        if parent is None:
            raise ValueError("E_REVIEW_ROW_PARENT_UNAVAILABLE")
        subject = next((item for item in row.items if item.item_id == row.table_subject_id), None)
        parent_subject = next((item for item in parent.items if item.item_id == parent.table_subject_id), None)
        if subject is None or parent_subject is None or subject.source_kind != "primary" or parent_subject.source_kind != "primary":
            raise ValueError("E_REVIEW_ROW_PARENT_SOURCE")
        if subject.parent_id is None:
            raise ValueError("E_REVIEW_ROW_PARENT_ROOT")
        if subject.parent_id != parent_subject.object_id:
            raise ValueError("E_REVIEW_ROW_PARENT_MISMATCH")


def _snapshot_items(project: dict[str, Any] | None, placements: dict[str, dict[str, date]] | None,
                    style: dict[str, Any] | None) -> dict[str, ReviewItem]:
    if project is None or placements is None:
        return {}
    result: dict[str, ReviewItem] = {}
    for object_id, planned in placements.items():
        source_type = "point" if "at" in planned else "span"
        result[object_id] = ReviewItem(
            object_id, str(project["objects"][object_id].get("title", object_id)), source_type,
            planned, None, None, _roles(style, source_type, None, None), "", "",
            dict(project["objects"][object_id].get("fields", {})), object_id, "snapshot")
    return result


def _latest_observations(observations: list[dict[str, Any]], placements: dict[str, dict[str, date]]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    latest, unmatched = {}, []
    for observation in observations:
        object_id = observation.get("projectObjectId")
        if object_id not in placements:
            unmatched.append(observation["id"])
        elif object_id not in latest or observation["sequence"] > latest[object_id]["sequence"]:
            latest[object_id] = observation
    return latest, unmatched


def _actual(observation: dict[str, Any] | None) -> dict[str, date | float] | None:
    raw = (observation or {}).get("actual")
    return {key: _date_or_number(value) for key, value in raw.items()} if raw else None


def _finish_delta(planned: dict[str, date], actual: dict[str, date | float] | None) -> int | None:
    return (actual["finish"] - planned["end"]).days if actual and "finish" in actual and "end" in planned else None  # type: ignore[operator]


def _order(rows: list[ReviewItem], body: dict[str, Any]) -> None:
    ordering = body.get("ordering", {"by": "id", "tieBreak": "id"})
    def value(item: ReviewItem, field: str) -> Any:
        return {"id": item.object_id, "title": item.title, "plannedStart": item.planned.get("start", item.planned.get("at")), "plannedEnd": item.planned.get("end", item.planned.get("at")), "plannedFinish": item.planned.get("end", item.planned.get("at"))}[field]
    rows.sort(key=lambda item: value(item, ordering.get("tieBreak", "id")))
    rows.sort(key=lambda item: value(item, ordering["by"]), reverse=ordering.get("direction") == "descending")
    group_order = body.get("grouping", {}).get("order", [])
    rows.sort(key=lambda item: (group_order.index(item.group_id) if item.group_id in group_order else len(group_order), item.group_id))


def _group_id(project: dict[str, Any], object_id: str, source_type: str, grouping: dict[str, Any]) -> str:
    if grouping["by"] == "none":
        return ""
    if grouping["by"] == "objectType":
        return source_type
    if grouping["by"] == "hierarchy":
        return ""
    return str(project["objects"][object_id].get("fields", {}).get(grouping["field"], grouping["missing"]))


def _expand_hierarchy_roots(items: list[ReviewItem], entries: dict[str, HierarchyEntry],
                            candidate_ids: set[str], body: dict[str, Any]) -> list[ReviewItem]:
    """Expand View-selected roots without giving View authority over tree truth."""
    item_by_id = {item.object_id: item for item in items}
    grouping = body.get("grouping", {})
    include = body.get("selection", {}).get("include", {})
    predicate_omitted = not any(key in include for key in ("ids", "types"))
    candidate_ids = candidate_ids if not predicate_omitted else {
        entry.object_id for entry in entries.values() if entry.parent_id is None and entry.object_id in item_by_id
    }
    roots = [object_id for object_id in candidate_ids
             if entries[object_id].parent_id not in candidate_ids]
    children: dict[str, list[str]] = {object_id: [] for object_id in entries}
    for entry in entries.values():
        if entry.parent_id in children:
            children[entry.parent_id].append(entry.object_id)
    limit = int(grouping.get("depth", 0))
    output: list[ReviewItem] = []

    def visit(object_id: str, relative_depth: int) -> None:
        item = item_by_id.get(object_id)
        if item is not None:
            output.append(replace(item, hierarchy_depth=relative_depth))
        if relative_depth >= limit:
            return
        child_items = [item_by_id[child] for child in children.get(object_id, ()) if child in item_by_id]
        _order(child_items, body)
        for child in child_items:
            visit(child.object_id, relative_depth + 1)

    root_items = [item_by_id[root] for root in roots]
    _order(root_items, body)
    for root in root_items:
        visit(root.object_id, 0)
    return output


def _date_or_number(value: Any) -> date | float:
    return value if isinstance(value, date) else date.fromisoformat(value) if isinstance(value, str) else float(value)


def _roles(style: dict[str, Any] | None, source_type: str, actual: dict[str, Any] | None, finish_delta: int | None) -> tuple[str, ...]:
    facets = {"planned"} | ({"actual"} if actual else {"missingActual"}) | ({"finishDelta"} if finish_delta is not None else set())
    if style is None:
        roles = ["planned", "actual" if actual else "missing-actual"]
        if finish_delta is not None:
            roles.append("variance-behind" if finish_delta > 0 else "variance-ahead" if finish_delta < 0 else "variance-on-plan")
        return tuple(roles)
    roles: list[str] = []
    for rule in style.get("body", {}).get("rules", []):
        when, category = rule["when"], "behind" if (finish_delta or 0) > 0 else "on-track"
        if when.get("facet") in facets and ("sourceType" not in when or when["sourceType"] == source_type) and ("comparisonCategory" not in when or when["comparisonCategory"] == category):
            roles.extend(rule["addRoles"])
    return tuple(dict.fromkeys(roles))
