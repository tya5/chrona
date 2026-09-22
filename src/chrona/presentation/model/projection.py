"""Typed, view-owned Plan/Actual review projection model."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import date
from typing import Any

from chrona.core.hierarchy import HierarchyEntry, normalize_hierarchy
from chrona.presentation.contracts.resources import ViewInput


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
    presentation: dict[str, Any] | None = None


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
                            view: ViewInput, actual_set: dict[str, Any] | None,
                            style: dict[str, Any] | None = None,
                            theme: dict[str, Any] | None = None,
                            snapshot_project: dict[str, Any] | None = None,
                            snapshot_placements: dict[str, dict[str, date]] | None = None) -> ReviewProjection:
    """Derive review facts; composition belongs to View, never Project."""
    if view.comparison.actual == "required" and actual_set is None:
        raise ValueError("E_ACTUAL_REQUIRED")
    if theme is not None and not theme.get("body", {}).get("roles"):
        raise ValueError("E_THEME_ROLES")
    latest, unmatched = _latest_observations(
        (actual_set or {}).get("body", actual_set or {}).get("observations", []), placements)
    explicit = view.rows.mode == "explicit"
    ids = set(view.selection.ids) if view.selection and view.selection.ids else set(placements)
    types = set(view.selection.types) if view.selection and view.selection.types else {"span", "point"}
    grouping = view.grouping
    selected: list[ReviewItem] = []
    hierarchy = grouping is not None and grouping.by == "hierarchy"
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
        selected = _expand_hierarchy_roots(selected, hierarchy_entries, hierarchy_root_ids, view)
    elif not explicit:
        _order(selected, view)
    snapshots = _snapshot_items(snapshot_project, snapshot_placements, style)
    rows = _compose_rows(view, selected, snapshots)
    dates = [v for row in rows for item in row.items for v in item.planned.values()]
    if view.window.mode == "selected-comparison":
        dates += [v for row in rows for item in row.items for v in (item.actual or {}).values() if isinstance(v, date)]
    start, end = min(dates), max(dates)
    margin = view.window.margin_days
    if view.window.mode == "explicit":
        start, end = (_date_or_number(value) for value in (view.window.start, view.window.end))
        margin = 0
        if start >= end:
            raise ValueError("E_REVIEW_WINDOW")
    return ReviewProjection(tuple(selected),
        (date.fromordinal(start.toordinal() - margin), date.fromordinal(end.toordinal() + margin)),
        tuple(sorted(unmatched)), tuple("E_ACTUAL_UNMATCHED" for _ in unmatched), rows,
        view.comparison.facets, hierarchy)


def _compose_rows(view: ViewInput, selected: list[ReviewItem],
                  snapshots: dict[str, ReviewItem]) -> tuple[ReviewRowProjection, ...]:
    if view.rows.mode != "explicit":
        return tuple(ReviewRowProjection(
            item.object_id, item.title, item.group_id, item.object_id,
            (replace(item, item_id=item.object_id, source_kind="combined"),),
            depth=item.hierarchy_depth if view.grouping is not None and view.grouping.by == "hierarchy" else 0,
            rollup_presentation=(view.grouping.rollup or "none"
                                 if item.is_rollup else "none"))
            for item in selected)
    available = {item.object_id: item for item in selected}
    output: list[ReviewRowProjection] = []
    seen_rows: set[str] = set()
    for row in view.rows.items:
        row_id = row.id
        if row_id in seen_rows:
            raise ValueError("E_REVIEW_ROW_ID_DUPLICATE")
        seen_rows.add(row_id)
        members, member_ids = [], set()
        for spec in row.items:
            item_id = spec.id
            if item_id in member_ids:
                raise ValueError("E_REVIEW_ITEM_ID_DUPLICATE")
            member_ids.add(item_id)
            object_id, kind = spec.source_object, spec.source_kind
            base = snapshots.get(object_id) if kind == "snapshot" else available.get(object_id)
            if kind not in {"primary", "actual", "snapshot"} or base is None:
                raise ValueError("E_REVIEW_ITEM_SOURCE_UNAVAILABLE")
            if kind == "actual" and base.actual is None:
                raise ValueError("E_REVIEW_ITEM_SOURCE_UNAVAILABLE")
            track = spec.track
            if track not in {"stacked", "shared"}:
                raise ValueError("E_REVIEW_ITEM_TRACK")
            intent = spec.presentation if spec.presentation is not None else row.presentation
            members.append(replace(base, item_id=item_id, source_kind=kind, track=track,
                                   presentation=dict(intent) if intent is not None else None))
        subject = row.table_subject or (members[0].item_id if members else "")
        if subject not in member_ids:
            raise ValueError("E_REVIEW_TABLE_SUBJECT")
        output.append(ReviewRowProjection(row_id, row.label or members[0].title,
            row.group or "", subject, tuple(members), depth=row.depth, parent_row_id=row.parent_row))
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


def _order(rows: list[ReviewItem], view: ViewInput) -> None:
    ordering = view.ordering
    def value(item: ReviewItem, field: str) -> Any:
        return {"id": item.object_id, "title": item.title, "plannedStart": item.planned.get("start", item.planned.get("at")), "plannedEnd": item.planned.get("end", item.planned.get("at")), "plannedFinish": item.planned.get("end", item.planned.get("at"))}[field]
    if ordering is None:
        ordering_by, tie_break, direction = "id", "id", "ascending"
    else:
        ordering_by, tie_break, direction = ordering.by, ordering.tie_break, ordering.direction
    rows.sort(key=lambda item: value(item, tie_break))
    rows.sort(key=lambda item: value(item, ordering_by), reverse=direction == "descending")
    group_order = view.grouping.order if view.grouping is not None else ()
    rows.sort(key=lambda item: (group_order.index(item.group_id) if item.group_id in group_order else len(group_order), item.group_id))


def _group_id(project: dict[str, Any], object_id: str, source_type: str, grouping: Any) -> str:
    if grouping is None or grouping.by == "none":
        return ""
    if grouping.by == "objectType":
        return source_type
    if grouping.by == "hierarchy":
        return ""
    return str(project["objects"][object_id].get("fields", {}).get(grouping.field or "", grouping.missing or "ungrouped"))


def _expand_hierarchy_roots(items: list[ReviewItem], entries: dict[str, HierarchyEntry],
                            candidate_ids: set[str], view: ViewInput) -> list[ReviewItem]:
    """Expand View-selected roots without giving View authority over tree truth."""
    item_by_id = {item.object_id: item for item in items}
    grouping = view.grouping
    predicate_omitted = view.selection is None or (not view.selection.ids and not view.selection.types)
    candidate_ids = candidate_ids if not predicate_omitted else {
        entry.object_id for entry in entries.values() if entry.parent_id is None and entry.object_id in item_by_id
    }
    roots = [object_id for object_id in candidate_ids
             if entries[object_id].parent_id not in candidate_ids]
    children: dict[str, list[str]] = {object_id: [] for object_id in entries}
    for entry in entries.values():
        if entry.parent_id in children:
            children[entry.parent_id].append(entry.object_id)
    limit = grouping.depth if grouping and grouping.depth is not None else 0
    output: list[ReviewItem] = []

    def visit(object_id: str, relative_depth: int) -> None:
        item = item_by_id.get(object_id)
        if item is not None:
            output.append(replace(item, hierarchy_depth=relative_depth))
        if relative_depth >= limit:
            return
        child_items = [item_by_id[child] for child in children.get(object_id, ()) if child in item_by_id]
        _order(child_items, view)
        for child in child_items:
            visit(child.object_id, relative_depth + 1)

    root_items = [item_by_id[root] for root in roots]
    _order(root_items, view)
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
