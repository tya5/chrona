"""Typed Plan/Actual projection model."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True)
class ReviewItem:
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


@dataclass(frozen=True)
class ReviewProjection:
    items: tuple[ReviewItem, ...]
    window: tuple[date, date]
    unmatched_actual_ids: tuple[str, ...]
    diagnostics: tuple[str, ...]


def build_review_projection(
    project: dict[str, Any],
    placements: dict[str, dict[str, date]],
    view: dict[str, Any],
    actual_set: dict[str, Any] | None,
    style: dict[str, Any] | None = None,
    theme: dict[str, Any] | None = None,
) -> ReviewProjection:
    """Derive review facts without modifying Project, schedule, or Actual inputs."""
    body = view["body"]
    comparison = body["comparison"]
    if comparison["actual"] == "required" and actual_set is None:
        raise ValueError("E_ACTUAL_REQUIRED")
    if theme is not None and not theme.get("body", {}).get("roles"):
        raise ValueError("E_THEME_ROLES")
    observations = (actual_set or {}).get("body", actual_set or {}).get("observations", [])
    latest: dict[str, dict[str, Any]] = {}
    unmatched: list[str] = []
    for observation in observations:
        object_id = observation.get("projectObjectId")
        if object_id not in placements:
            unmatched.append(observation["id"])
            continue
        if object_id not in latest or observation["sequence"] > latest[object_id]["sequence"]:
            latest[object_id] = observation
    include = body["selection"]["include"]
    ids = set(include.get("ids", placements))
    allowed_types = set(include.get("types", ("span", "point")))
    rows: list[ReviewItem] = []
    for object_id, planned in placements.items():
        source_type = "point" if "at" in planned else "span"
        if object_id not in ids or source_type not in allowed_types:
            continue
        raw_actual = latest.get(object_id, {}).get("actual")
        actual = {key: _date_or_number(value) for key, value in raw_actual.items()} if raw_actual else None
        finish_delta = None
        if actual and "finish" in actual and "end" in planned:
            finish_delta = (actual["finish"] - planned["end"]).days  # type: ignore[operator]
        roles = _roles(style, source_type, actual, finish_delta)
        grouping=body.get("grouping",{"by":"none","missing":"ungrouped"}); group_id=_group_id(project,object_id,source_type,grouping); group_label=str(project.get("entities",{}).get(group_id,{}).get("title",group_id))
        rows.append(ReviewItem(object_id, str(project["objects"][object_id].get("title", object_id)), source_type, planned, actual, finish_delta, roles, group_id, group_label, dict(project["objects"][object_id].get("fields", {}))))
    key = body["ordering"]["by"]
    def order_value(item, field):
        return {"id":item.object_id,"title":item.title,"plannedStart":item.planned.get("start",item.planned.get("at")),"plannedEnd":item.planned.get("end",item.planned.get("at")),"plannedFinish":item.planned.get("end",item.planned.get("at"))}[field]
    rows.sort(key=lambda item:order_value(item,body["ordering"].get("tieBreak","id")))
    rows.sort(key=lambda item:order_value(item,key),reverse=body["ordering"].get("direction")=="descending")
    group_order=body.get("grouping",{}).get("order",[])
    rows.sort(key=lambda item:(group_order.index(item.group_id) if item.group_id in group_order else len(group_order),item.group_id))
    dates = [value for item in rows for value in item.planned.values()]
    if body["window"].get("mode")=="selected-comparison":
        dates += [value for item in rows for value in (item.actual or {}).values() if isinstance(value,date)]
    if not dates: raise ValueError("E_REVIEW_EMPTY")
    margin = body["window"].get("marginDays", 0)
    start, end = min(dates), max(dates)
    if body["window"].get("mode")=="explicit":
        start,end=(_date_or_number(body["window"][part]) for part in ("start","end")); margin=0
        if start>=end: raise ValueError("E_REVIEW_WINDOW")
    return ReviewProjection(tuple(rows), (date.fromordinal(start.toordinal() - margin), date.fromordinal(end.toordinal() + margin)), tuple(sorted(unmatched)), tuple("E_ACTUAL_UNMATCHED" for _ in unmatched))

def _group_id(project:dict[str,Any], object_id:str, source_type:str, grouping:dict[str,Any])->str:
    if grouping["by"]=="none": return ""
    if grouping["by"]=="objectType": return source_type
    return str(project["objects"][object_id].get("fields",{}).get(grouping["field"],grouping["missing"]))


def _date_or_number(value: Any) -> date | float:
    if isinstance(value, date):
        return value
    return date.fromisoformat(value) if isinstance(value, str) else float(value)


def _roles(style: dict[str, Any] | None, source_type: str, actual: dict[str, Any] | None, finish_delta: int | None) -> tuple[str, ...]:
    facets = {"planned"}
    if actual: facets.add("actual")
    if finish_delta is not None: facets.add("finishDelta")
    if not actual: facets.add("missingActual")
    if style is None:
        roles = ["planned"]
        roles.append("actual" if actual else "missing-actual")
        if finish_delta is not None:
            roles.append("variance-behind" if finish_delta > 0 else "variance-ahead" if finish_delta < 0 else "variance-on-plan")
        return tuple(roles)
    roles: list[str] = []
    for rule in style.get("body", {}).get("rules", []):
        when = rule["when"]
        category = "behind" if (finish_delta or 0) > 0 else "on-track"
        if when.get("facet") in facets and ("sourceType" not in when or when["sourceType"] == source_type) and ("comparisonCategory" not in when or when["comparisonCategory"] == category):
            roles.extend(rule["addRoles"])
    return tuple(dict.fromkeys(roles))
