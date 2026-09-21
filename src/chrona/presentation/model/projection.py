"""Typed, view-owned Plan/Actual review projection model."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from typing import Any


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


@dataclass(frozen=True)
class ReviewRowProjection:
    """A View-owned row, with independently addressable ReviewItems."""
    row_id: str
    label: str
    group_id: str
    table_subject_id: str
    items: tuple[ReviewItem, ...]


@dataclass(frozen=True)
class ReviewProjection:
    items: tuple[ReviewItem, ...]
    window: tuple[date, date]
    unmatched_actual_ids: tuple[str, ...]
    diagnostics: tuple[str, ...]
    rows: tuple[ReviewRowProjection, ...] = ()
    comparison_facets: tuple[str, ...] = ()


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
    for object_id, planned in placements.items():
        source_type = "point" if "at" in planned else "span"
        if not explicit and (object_id not in ids or source_type not in types):
            continue
        actual = _actual(latest.get(object_id))
        finish_delta = _finish_delta(planned, actual)
        group_id = _group_id(project, object_id, source_type, grouping)
        selected.append(ReviewItem(
            object_id, str(project["objects"][object_id].get("title", object_id)), source_type,
            planned, actual, finish_delta, _roles(style, source_type, actual, finish_delta),
            group_id, str(project.get("entities", {}).get(group_id, {}).get("title", group_id)),
            dict(project["objects"][object_id].get("fields", {})), object_id, "primary"))
    if not selected:
        raise ValueError("E_REVIEW_EMPTY")
    if not explicit:
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
        tuple(body["comparison"].get("facets", ())))


def _compose_rows(body: dict[str, Any], selected: list[ReviewItem],
                  snapshots: dict[str, ReviewItem]) -> tuple[ReviewRowProjection, ...]:
    rows = body.get("rows", {})
    if rows.get("mode", "automatic") != "explicit":
        return tuple(ReviewRowProjection(
            item.object_id, item.title, item.group_id, item.object_id,
            (replace(item, item_id=item.object_id, source_kind="combined"),))
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
            members.append(replace(base, item_id=item_id, source_kind=kind))
        subject = str(row.get("tableSubject", members[0].item_id if members else ""))
        if subject not in member_ids:
            raise ValueError("E_REVIEW_TABLE_SUBJECT")
        output.append(ReviewRowProjection(row_id, str(row.get("label", members[0].title)),
            str(row.get("group", "")), subject, tuple(members)))
    return tuple(output)


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
    return str(project["objects"][object_id].get("fields", {}).get(grouping["field"], grouping["missing"]))


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
