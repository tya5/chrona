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
    total_float: int | None = None
    critical: bool = False
    link: dict[str, str] | None = None
    scenario_id: str | None = None


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
class DependencyNetworkNode:
    """View-selected graph fact; Layout alone assigns geometry."""

    object_id: str
    title: str
    order_key: tuple[Any, ...]
    critical: bool
    source_kind: str


@dataclass(frozen=True)
class DependencyNetworkEdge:
    """A selected dependency with stable endpoint provenance."""

    relation_id: str
    source_id: str
    target_id: str
    source_endpoint: str
    target_endpoint: str
    critical: bool


@dataclass(frozen=True)
class DependencyNetworkProjection:
    nodes: tuple[DependencyNetworkNode, ...]
    edges: tuple[DependencyNetworkEdge, ...]


@dataclass(frozen=True)
class ReviewProjection:
    items: tuple[ReviewItem, ...]
    window: tuple[date, date]
    unmatched_actual_ids: tuple[str, ...]
    diagnostics: tuple[str, ...]
    rows: tuple[ReviewRowProjection, ...] = ()
    comparison_facets: tuple[str, ...] = ()
    hierarchy_grouping: bool = False
    surface: str = "table-timeline"
    network: DependencyNetworkProjection | None = None
    driving_relations: frozenset[str] = frozenset()


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
                            snapshot_placements: dict[str, dict[str, date]] | None = None,
                            scenarios: dict[str, tuple[dict[str, Any], dict[str, dict[str, date]]]] | None = None,
                            analysis: Any | None = None,
                            snapshot_analysis: Any | None = None) -> ReviewProjection:
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
    object_types = set(view.selection.object_types) if view.selection else set()
    excluded_object_types = set(view.selection.excluded_object_types) if view.selection else set()
    grouping = view.grouping
    selected: list[ReviewItem] = []
    hierarchy = grouping is not None and grouping.by == "hierarchy"
    hierarchy_entries = {entry.object_id: entry for entry in normalize_hierarchy(project)}
    hierarchy_root_ids: set[str] = set()
    for object_id, planned in placements.items():
        source_type = "point" if "at" in planned else "span"
        project_type = str(project["objects"][object_id].get("type", ""))
        if not hierarchy and (object_id not in ids or source_type not in types
                              or (object_types and project_type not in object_types)
                              or project_type in excluded_object_types):
            continue
        if hierarchy and object_id in ids and source_type in types and (not object_types or project_type in object_types) and project_type not in excluded_object_types:
            hierarchy_root_ids.add(object_id)
        actual = _actual(latest.get(object_id))
        finish_delta = _finish_delta(planned, actual)
        total_float = analysis.total_float.get(object_id) if analysis is not None else None
        critical = object_id in analysis.critical if analysis is not None else False
        link = _object_link(project["objects"][object_id].get("link"))
        entry = hierarchy_entries.get(object_id)
        group_id = _group_id(project, object_id, source_type, grouping)
        selected.append(ReviewItem(
            object_id, str(project["objects"][object_id].get("title", object_id)), source_type,
            planned, actual, finish_delta, _roles(style, source_type, actual, finish_delta, critical),
            group_id, str(project.get("entities", {}).get(group_id, {}).get("title", group_id)),
            dict(project["objects"][object_id].get("fields", {})), object_id, "primary",
            parent_id=entry.parent_id if entry else None,
            hierarchy_depth=entry.depth if entry else 0,
            wbs_code=entry.display_wbs_code if entry else "",
            hierarchy_path=entry.path if entry else (),
            is_rollup=project["objects"][object_id].get("schedule", {}).get("mode") == "rollup",
            total_float=total_float, critical=critical, link=link))
    if not selected:
        raise ValueError("E_REVIEW_EMPTY")
    if hierarchy and not explicit:
        selected = _expand_hierarchy_roots(selected, hierarchy_entries, hierarchy_root_ids, view)
    elif not explicit:
        _order(selected, view)
    snapshots = _snapshot_items(snapshot_project, snapshot_placements, style, snapshot_analysis)
    scenario_items = {scenario_id: _snapshot_items(value[0], value[1], style, None, source_kind="scenario")
                      for scenario_id, value in (scenarios or {}).items()}
    rows = _compose_rows(view, selected, snapshots, scenario_items, project)
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
        view.comparison.facets, hierarchy, view.surface,
        _dependency_network_projection(project, selected, view),
        frozenset(getattr(analysis, "driving_relations", ())))


def _dependency_network_projection(project: dict[str, Any], selected: list[ReviewItem],
                                   view: ViewInput) -> DependencyNetworkProjection | None:
    """Close Project relation facts at the View boundary for a network surface."""
    if view.surface != "dependency-network":
        return None
    selected_ids = {item.object_id for item in selected}
    nodes = tuple(DependencyNetworkNode(item.object_id, item.title,
                                        _network_order_key(item, view), item.critical, item.source_kind)
                  for item in selected)
    edges = []
    for relation in project.get("relations", ()):
        source = relation.get("from", {})
        target = relation.get("to", {})
        source_id, target_id = source.get("object"), target.get("object")
        if source_id not in selected_ids or target_id not in selected_ids:
            continue
        edges.append(DependencyNetworkEdge(str(relation["id"]), str(source_id), str(target_id),
                                           str(source.get("endpoint", "end")), str(target.get("endpoint", "start")),
                                           all(item.critical for item in selected if item.object_id in {source_id, target_id})))
    return DependencyNetworkProjection(nodes, tuple(sorted(edges, key=lambda item: item.relation_id)))


def _network_order_key(item: ReviewItem, view: ViewInput) -> tuple[Any, ...]:
    ordering = view.ordering
    if ordering is None or ordering.by == "id":
        value: Any = item.object_id
    elif ordering.by == "title":
        value = item.title
    elif ordering.by == "plannedEnd":
        value = item.planned.get("at", item.planned.get("end"))
    else:
        value = item.planned.get("start", item.planned.get("at"))
    return (value, item.object_id)


def _compose_rows(view: ViewInput, selected: list[ReviewItem], snapshots: dict[str, ReviewItem],
                  scenarios: dict[str, dict[str, ReviewItem]], project: dict[str, Any]) -> tuple[ReviewRowProjection, ...]:
    if view.rows.mode != "explicit":
        rows = tuple(ReviewRowProjection(
            item.object_id, item.title, item.group_id, item.object_id,
            tuple(member for member in (
                replace(item, item_id=item.object_id, source_kind="combined",
                        track=("shared" if view.comparison.baseline == "scenario"
                               and view.comparison.scenario_id in scenarios
                               and item.object_id in scenarios[view.comparison.scenario_id]
                               else item.track)),
                (replace(scenarios[view.comparison.scenario_id][item.object_id],
                         item_id=f"scenario:{view.comparison.scenario_id}:{item.object_id}",
                         source_kind="scenario", scenario_id=view.comparison.scenario_id, track="shared")
                 if view.comparison.baseline == "scenario"
                 and view.comparison.scenario_id in scenarios
                 and item.object_id in scenarios[view.comparison.scenario_id] else None),
            ) if member is not None),
            depth=item.hierarchy_depth if view.grouping is not None and view.grouping.by == "hierarchy" else 0,
            rollup_presentation=(view.grouping.rollup or "none"
                                 if item.is_rollup else "none"))
            for item in selected)
        return _fold_automatic_points(rows, view, project)
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
            base = (snapshots.get(object_id) if kind == "snapshot" else
                    scenarios.get(spec.scenario_id or "", {}).get(object_id) if kind == "scenario" else
                    available.get(object_id))
            if kind not in {"primary", "actual", "snapshot", "scenario"} or base is None:
                raise ValueError("E_REVIEW_ITEM_SOURCE_UNAVAILABLE")
            if kind == "actual" and base.actual is None:
                raise ValueError("E_REVIEW_ITEM_SOURCE_UNAVAILABLE")
            track = spec.track
            if track not in {"stacked", "shared"}:
                raise ValueError("E_REVIEW_ITEM_TRACK")
            intent = spec.presentation if spec.presentation is not None else row.presentation
            members.append(replace(base, item_id=item_id, source_kind=kind, track=track, scenario_id=spec.scenario_id,
                                   presentation=dict(intent) if intent is not None else None))
        subject = row.table_subject or (members[0].item_id if members else "")
        if subject not in member_ids:
            raise ValueError("E_REVIEW_TABLE_SUBJECT")
        output.append(ReviewRowProjection(row_id, row.label or members[0].title,
            row.group or "", subject, tuple(members), depth=row.depth, parent_row_id=row.parent_row))
    _validate_explicit_row_hierarchy(output)
    return tuple(output)


def _fold_automatic_points(rows: tuple[ReviewRowProjection, ...], view: ViewInput,
                           project: dict[str, Any]) -> tuple[ReviewRowProjection, ...]:
    """Apply View-owned automatic point policy without exposing relation facts to Layout."""
    if view.rows.points == "own-row":
        return rows
    if view.rows.points == "group-header":
        # Header-target allocation is intentionally completed by the following Layout slice.
        return rows
    if view.rows.points != "predecessor":
        raise ValueError("E_REVIEW_POINT_POLICY")
    by_object = {row.table_subject_id: row for row in rows}
    incoming: dict[str, list[str]] = {}
    for relation in project.get("relations", ()):
        source, target = relation.get("from", {}).get("object"), relation.get("to", {}).get("object")
        if isinstance(source, str) and isinstance(target, str):
            incoming.setdefault(target, []).append(source)
    folded: set[str] = set()
    replacements: dict[str, ReviewRowProjection] = {}
    for row in rows:
        subject = row.items[0] if row.items else None
        if subject is None or subject.source_type != "point":
            continue
        candidates = [source for source in incoming.get(subject.object_id, ())
                      if source in by_object and by_object[source].items
                      and by_object[source].items[0].source_type == "span"]
        if len(candidates) != 1:
            continue
        target = replacements.get(candidates[0], by_object[candidates[0]])
        folded.add(row.row_id)
        replacements[candidates[0]] = replace(target, items=target.items + tuple(
            replace(item, track="shared") for item in row.items))
    return tuple(replacements.get(row.row_id, row) for row in rows if row.row_id not in folded)


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
                    style: dict[str, Any] | None, analysis: Any | None = None,
                    source_kind: str = "snapshot") -> dict[str, ReviewItem]:
    if project is None or placements is None:
        return {}
    result: dict[str, ReviewItem] = {}
    for object_id, planned in placements.items():
        source_type = "point" if "at" in planned else "span"
        total_float = analysis.total_float.get(object_id) if analysis is not None else None
        critical = object_id in analysis.critical if analysis is not None else False
        result[object_id] = ReviewItem(
            object_id, str(project["objects"][object_id].get("title", object_id)), source_type,
            planned, None, None, _roles(style, source_type, None, None, critical), "", "",
            dict(project["objects"][object_id].get("fields", {})), object_id, source_kind,
            total_float=total_float, critical=critical, link=_object_link(project["objects"][object_id].get("link")))
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


def _object_link(value: Any) -> dict[str, str] | None:
    if isinstance(value, str):
        return {"href": value}
    if isinstance(value, dict) and isinstance(value.get("href"), str):
        return {key: str(item) for key, item in value.items() if key in {"href", "title"}}
    return None


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
    predicate_omitted = view.selection is None or (not view.selection.ids and not view.selection.types
                                                   and not view.selection.object_types and not view.selection.excluded_object_types)
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


def _roles(style: dict[str, Any] | None, source_type: str, actual: dict[str, Any] | None,
           finish_delta: int | None, critical: bool = False) -> tuple[str, ...]:
    facets = {"planned"} | ({"actual"} if actual else {"missingActual"}) | ({"finishDelta"} if finish_delta is not None else set())
    if style is None:
        roles = ["planned", "actual" if actual else "missing-actual"]
        if finish_delta is not None:
            roles.append("variance-behind" if finish_delta > 0 else "variance-ahead" if finish_delta < 0 else "variance-on-plan")
        if critical:
            roles.append("critical")
        return tuple(roles)
    roles: list[str] = []
    for rule in style.get("body", {}).get("rules", []):
        when, category = rule["when"], "behind" if (finish_delta or 0) > 0 else "on-track"
        if when.get("facet") in facets and ("sourceType" not in when or when["sourceType"] == source_type) and ("comparisonCategory" not in when or when["comparisonCategory"] == category):
            roles.extend(rule["addRoles"])
    if critical:
        roles.append("critical")
    return tuple(dict.fromkeys(roles))
