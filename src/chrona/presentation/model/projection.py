"""Typed, view-owned Plan/Actual review projection model."""
from __future__ import annotations

from copy import deepcopy
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date
from enum import StrEnum
from typing import Any

from chrona.core.hierarchy import HierarchyEntry, normalize_hierarchy
from chrona.presentation.contracts.resources import ViewInput
from chrona.presentation.review.lane_membership import (
    LaneItem, LaneMembership, LanePackingInput, PlannedPoint, PlannedSpan,
    SelectedFSRelation, derive_lane_membership,
)


_SHARED_TRACK_SOURCE_ORDER = {"snapshot": 0, "scenario": 1, "primary": 2, "actual": 3}


class ObservationState(StrEnum):
    """One View-owned Actual availability fact at the declared as-of date."""

    RECORDED = "recorded"
    DUE_UNOBSERVED = "due-unobserved"
    NOT_YET_DUE = "not-yet-due"
    UNAVAILABLE = "unavailable"


def shared_track_member_key(member: Any, source_index: int) -> tuple[int, int, int]:
    """Return the sole stable semantic traversal order for normalized track members."""
    if getattr(member, "track", "stacked") != "shared":
        return (1, source_index, source_index)
    return (0, _SHARED_TRACK_SOURCE_ORDER.get(getattr(member, "source_kind", ""), len(_SHARED_TRACK_SOURCE_ORDER)), source_index)


@dataclass(frozen=True)
class ReviewItem:
    """One selected source object as displayed by a ReviewRow."""
    object_id: str
    title: str
    source_type: str
    planned: dict[str, date]
    actual: dict[str, date | float | str] | None
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
    planned_progress: float | None = None
    observation_state: ObservationState = ObservationState.UNAVAILABLE
    attached_to: str | None = None
    # How the missing-actual mark treats this item (#991): `due-end` at the planned finish of a due,
    # unobserved item (the default), `in-progress` as a span from the actual start to as-of, `none`.
    missing_actual_mark: str = "due-end"
    # Position of the object among the Project's `objects` as declared, for `ordering.by: source` (#991).
    source_index: int = 0

    @property
    def at_delta(self) -> int | None:
        """Point Actual minus planned point, in calendar days (Spec 06 §8)."""
        planned_at = self.planned.get("at")
        actual_at = self.actual.get("at") if self.actual is not None else None
        return ((actual_at - planned_at).days
                if isinstance(planned_at, date) and isinstance(actual_at, date) else None)


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
class ReviewLaneRowProjection:
    """One immutable View table/timeline row for a generated lane."""

    lane_id: str
    group_id: str
    items: tuple[ReviewItem, ...]
    member_item_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class FoldedPointProjection:
    """A selected point whose target is a real group header, never a table row."""

    item: ReviewItem
    group_id: str
    target_kind: str = "group-header"
    members: tuple[ReviewItem, ...] = ()

    @property
    def all_items(self) -> tuple[ReviewItem, ...]:
        """Keep comparison variants on the point's one header track."""
        return (self.item, *self.members)


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
class ReviewPeriod:
    """One View-selected Project period as dates; ``end`` is exclusive (#582)."""

    period_id: str
    title: str
    start: date
    end: date
    label_placement: str | None = None
    label_overflow: str = "visible-overflow"


@dataclass(frozen=True)
class ReviewDeadline:
    """One Project deadline the View shows, with the finish the Core judged it against (#822).

    ``slipped`` is the Core's verdict (the finish is strictly after the deadline); Layout never compares the dates.
    """

    object_id: str
    deadline: date
    finish: date
    slipped: bool


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
    folded_points: tuple[FoldedPointProjection, ...] = ()
    lane_membership: LaneMembership | None = None
    lane_rows: tuple[ReviewLaneRowProjection, ...] = ()
    periods: tuple[ReviewPeriod, ...] = ()
    figures: tuple[tuple[str, int], ...] = ()  # (figure id, days) the Core resolved from the View's `figures` (#586)
    deadlines: tuple[ReviewDeadline, ...] = ()  # the Project deadlines the View's `deadlines` shows, in Project order (#822)
    group_figures: tuple[tuple[str, tuple[tuple[str, int], ...]], ...] = ()


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
                            snapshot_project: dict[str, Any] | None = None,
                            snapshot_placements: dict[str, dict[str, date]] | None = None,
                            scenarios: dict[str, tuple[dict[str, Any], dict[str, dict[str, date]]]] | None = None,
                            analysis: Any | None = None,
                            snapshot_analysis: Any | None = None) -> ReviewProjection:
    """Derive review facts; composition belongs to View, never Project."""
    if view.comparison.actual == "required" and actual_set is None:
        raise ValueError("E_ACTUAL_REQUIRED: the View compares against actuals (comparison.actual is required) but no actual "
                         "file was given; pass --actual FILE, or change the View so actuals are not required")
    latest, unmatched = _latest_observations(
        (actual_set or {}).get("body", actual_set or {}).get("observations", []), placements)
    as_of_value = (actual_set or {}).get("body", actual_set or {}).get("asOf")
    as_of = date.fromisoformat(as_of_value) if isinstance(as_of_value, str) else as_of_value
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
    declared = {object_id: index for index, object_id in enumerate(project["objects"])}
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
        observation_state = _observation_state(planned, latest.get(object_id), as_of)
        finish_delta = _finish_delta(planned, actual)
        total_float = analysis.total_float.get(object_id) if analysis is not None else None
        critical = object_id in analysis.critical if analysis is not None else False
        link = _object_link(project["objects"][object_id].get("link"))
        entry = hierarchy_entries.get(object_id)
        group_id = _group_id(project, object_id, source_type, grouping)
        selected.append(ReviewItem(
            object_id, str(project["objects"][object_id].get("title", object_id)), source_type,
            planned, actual, finish_delta, _roles(observation_state, finish_delta, critical),
            group_id, str(project.get("entities", {}).get(group_id, {}).get("title", group_id)),
            dict(project["objects"][object_id].get("fields", {})), object_id, "primary",
            parent_id=entry.parent_id if entry else None,
            hierarchy_depth=entry.depth if entry else 0,
            wbs_code=entry.display_wbs_code if entry else "",
            hierarchy_path=entry.path if entry else (),
            is_rollup=project["objects"][object_id].get("schedule", {}).get("mode") == "rollup",
            total_float=total_float, critical=critical, link=link,
            planned_progress=project["objects"][object_id].get("plannedProgress"),
            observation_state=observation_state, source_index=declared.get(object_id, 0)))
    if not selected:
        raise ValueError("E_REVIEW_EMPTY: the View selects no object of the Project; check its selection against the Project objects")
    if (grouping is not None and grouping.by == "field" and grouping.presentation == "header"
            and all(grouping.field not in (item.fields or {}) for item in selected)):
        # A header that distinguishes nothing is not drawn (Specification 45).
        selected = [replace(item, group_id="", group_label="") for item in selected]
    if hierarchy and not explicit:
        selected = _expand_hierarchy_roots(selected, hierarchy_entries, hierarchy_root_ids, view)
    elif not explicit:
        _order(selected, view)
    snapshots = _snapshot_items(snapshot_project, snapshot_placements, snapshot_analysis)
    if view.comparison.baseline_marks in {"ghost", "ghost-when-changed"} and not explicit and (view.comparison.baseline != "snapshot" or not snapshots):
        raise ValueError("E_REVIEW_BASELINE_MARKS_SNAPSHOT: comparison.baselineMarks needs comparison.baseline snapshot "
                         "and a snapshot Project in the Render Context")
    scenario_items = {scenario_id: _snapshot_items(value[0], value[1], None, source_kind="scenario")
                      for scenario_id, value in (scenarios or {}).items()}
    if view.comparison.missing_actual_scope == "in-progress":
        selected = [replace(item, missing_actual_mark=_in_progress_mark(item, as_of)) for item in selected]
    rows, folded_points = _compose_rows(view, selected, snapshots, scenario_items, project)
    lane_membership = _project_lane_membership(project, rows, view) if view.rows.mode == "lanes" else None
    lane_rows = _project_lane_rows(rows, lane_membership) if lane_membership is not None else ()
    dates = [v for row in rows for item in row.items for v in item.planned.values()]
    dates += [v for point in folded_points for v in point.item.planned.values()]
    if view.window.mode == "selected-comparison":
        dates += [v for row in rows for item in row.items for v in (item.actual or {}).values() if isinstance(v, date)]
    start, end = min(dates), max(dates)
    margin = view.window.margin_days
    if view.window.mode == "explicit":
        start, end = (_date_or_number(value) for value in (view.window.start, view.window.end))
        margin = 0
        if start >= end:
            raise ValueError(f"E_REVIEW_WINDOW: window.start {view.window.start} is not before window.end {view.window.end}")
    return ReviewProjection(tuple(selected),
        (date.fromordinal(start.toordinal() - margin), date.fromordinal(end.toordinal() + margin)),
        tuple(sorted(unmatched)), tuple("E_ACTUAL_UNMATCHED" for _ in unmatched), rows,
        view.comparison.facets, hierarchy, view.surface,
        _dependency_network_projection(project, selected, view),
        frozenset(getattr(analysis, "driving_relations", ()),), folded_points,
        lane_membership, lane_rows)


def _project_lane_rows(rows: tuple[ReviewRowProjection, ...], membership: LaneMembership
                       ) -> tuple[ReviewLaneRowProjection, ...]:
    """Project each countable membership exactly once while retaining its facets."""
    source_rows: dict[str, ReviewRowProjection] = {}
    for row in rows:
        if not row.items:
            continue
        member_id = row.items[0].item_id or row.items[0].object_id
        if member_id in source_rows:
            raise ValueError(f"E_REVIEW_LANE_ROW_DUPLICATE_MEMBER: member {member_id!r} appears in more than one row")
        source_rows[member_id] = row
    assigned = [assignment.item_id for assignment in membership.assignments]
    if len(assigned) != len(set(assigned)) or set(assigned) != set(source_rows):
        only_assigned = sorted(set(assigned) - set(source_rows))
        only_rows = sorted(set(source_rows) - set(assigned))
        raise ValueError(f"E_REVIEW_LANE_ROW_MEMBERSHIP_MISMATCH: lane assignments and rows disagree "
                         f"(assigned without a row: {only_assigned}; row without an assignment: {only_rows}; "
                         f"an item assigned twice: {len(assigned) != len(set(assigned))})")
    output = []
    for lane in membership.lanes:
        members = []
        member_item_ids = []
        for member_id in lane.member_item_ids:
            row = source_rows.get(member_id)
            if row is None:
                raise ValueError(f"E_REVIEW_LANE_ROW_MEMBERSHIP_MISMATCH: lane {lane.lane_id!r} lists member {member_id!r} that has no row")
            assignment = membership.assignment_for(member_id)
            for item in row.items:
                attached_to = (source_rows.get(assignment.source_id).items[0].object_id
                               if assignment.rule == "attached" and assignment.source_id in source_rows
                               else item.attached_to)
                members.append(replace(item, group_id=assignment.group_id,
                                       attached_to=attached_to))
                member_item_ids.append(member_id)
        output.append(ReviewLaneRowProjection(lane.lane_id, lane.group_id,
                                              tuple(members), tuple(member_item_ids)))
    return tuple(output)


def _project_lane_membership(project: dict[str, Any], rows: tuple[ReviewRowProjection, ...],
                             view: ViewInput) -> LaneMembership:
    """Close View-selected lane membership before any Theme or geometry exists."""
    primary = {row.items[0].object_id: row.items[0] for row in rows if row.items}
    lane_keys = view.rows.lane_keys
    by_object = lane_keys.by_object if lane_keys is not None and lane_keys.by_object is not None else {}
    if set(by_object) - set(primary):
        raise ValueError("E_REVIEW_LANE_KEY_TARGET: rows.laneKeys.byObject names objects that are not selected rows: "
                         f"{sorted(set(by_object) - set(primary))}")
    items: list[LaneItem] = []
    for row in rows:
        if not row.items:
            continue
        item = row.items[0]
        planned = (PlannedPoint(item.planned["at"]) if item.source_type == "point" else
                   PlannedSpan(item.planned["start"], item.planned["end"]))
        host_id = project["objects"][item.object_id].get("attachesTo")
        selected_host = primary.get(host_id) if item.source_type == "point" else None
        if selected_host is not None and selected_host.source_type != "span":
            selected_host = None
        attached_host = selected_host.item_id if selected_host is not None else None
        # An attachment owns row placement independently of WBS or object fields.
        group_id = selected_host.group_id if selected_host is not None and "attached" in view.rows.packing else item.group_id
        key = by_object.get(item.object_id)
        if key is None and lane_keys is not None and lane_keys.field is not None:
            key = (item.fields or {}).get(lane_keys.field)
        if key is not None and (not isinstance(key, str) or not key):
            raise ValueError(f"E_REVIEW_LANE_KEY: the lane key of object {item.object_id!r} must be a non-empty string, got {key!r}")
        items.append(LaneItem(item.item_id, item.object_id, group_id, planned, key, attached_host))
    relations = tuple(SelectedFSRelation(str(relation["id"]), str(relation["from"]["object"]),
                                         str(relation["to"]["object"]))
                      for relation in project.get("relations", ())
                      if relation.get("type") == "dependency"
                      and relation.get("from", {}).get("endpoint") == "end"
                      and relation.get("to", {}).get("endpoint") == "start"
                      and relation.get("from", {}).get("object") in primary
                      and relation.get("to", {}).get("object") in primary)
    return derive_lane_membership(LanePackingInput(tuple(items), view.rows.packing, relations))


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
    elif ordering.by == "source":
        value = item.source_index
    else:
        value = item.planned.get("start", item.planned.get("at"))
    return (value, item.object_id)


def _in_progress_mark(item: ReviewItem, as_of: date | None) -> str:
    """`comparison.missingActualScope: in-progress`: a span in progress at as-of.

    The owner's rule (#991): an observed span is in progress when it has started (an actual `start` on or before
    as-of), has no actual finish, and its progress is below 1 or absent; `openUntil: asOf` stays a sufficient
    explicit signal. One that has not started, or sits at progress 1 without a finish and without `openUntil`, is not.
    """
    actual = item.actual or {}
    if item.observation_state == ObservationState.DUE_UNOBSERVED:
        return "none"
    start = actual.get("start")
    if (item.source_type != "span" or not isinstance(start, date) or as_of is None or start > as_of
            or actual.get("finish") is not None or actual.get("at") is not None):
        return "due-end"
    progress = actual.get("progress")
    below_one = progress is None or (isinstance(progress, (int, float)) and not isinstance(progress, bool) and progress < 1)
    return "in-progress" if actual.get("openUntil") == "asOf" or below_one else "due-end"


def _compose_rows(view: ViewInput, selected: list[ReviewItem], snapshots: dict[str, ReviewItem],
                  scenarios: dict[str, dict[str, ReviewItem]], project: dict[str, Any]) -> tuple[tuple[ReviewRowProjection, ...], tuple[FoldedPointProjection, ...]]:
    if view.rows.mode != "explicit":
        def scenario_ghost(item: ReviewItem) -> bool:
            return (view.comparison.baseline == "scenario" and view.comparison.scenario_id in scenarios
                    and item.object_id in scenarios[view.comparison.scenario_id])

        def snapshot_ghost(item: ReviewItem) -> bool:
            # `comparison.baselineMarks` (#991): a snapshot baseline draws one ghost per primary item (`ghost`), or
            # only for an item whose baseline placement differs from its current one (`ghost-when-changed`).
            if (view.comparison.baseline != "snapshot" or view.comparison.baseline_marks not in {"ghost", "ghost-when-changed"}
                    or item.object_id not in snapshots):
                return False
            return view.comparison.baseline_marks == "ghost" or snapshots[item.object_id].planned != item.planned

        rows = tuple(ReviewRowProjection(
            item.object_id, item.title, item.group_id, item.object_id,
            tuple(member for member in (
                replace(item, item_id=item.object_id, source_kind="combined",
                        track="shared" if scenario_ghost(item) or snapshot_ghost(item) else item.track),
                (replace(scenarios[view.comparison.scenario_id][item.object_id],
                         item_id=f"scenario:{view.comparison.scenario_id}:{item.object_id}",
                         source_kind="scenario", scenario_id=view.comparison.scenario_id, track="shared")
                 if scenario_ghost(item) else None),
                (replace(snapshots[item.object_id], item_id=f"snapshot:{item.object_id}",
                         source_kind="snapshot", track="shared")
                 if snapshot_ghost(item) else None),
            ) if member is not None),
            depth=item.hierarchy_depth if view.grouping is not None and view.grouping.by == "hierarchy" else 0,
            rollup_presentation=(view.grouping.rollup or "none"
                                 if item.is_rollup else "none"))
            for item in selected)
        if view.rows.mode == "lanes":
            # Lane packing decides attachment only when that rule is declared.
            return rows, ()
        return _fold_automatic_points(rows, view, project)
    available = {item.object_id: item for item in selected}
    output: list[ReviewRowProjection] = []
    seen_rows: set[str] = set()
    for row in view.rows.items:
        row_id = row.id
        if row_id in seen_rows:
            raise ValueError(f"E_REVIEW_ROW_ID_DUPLICATE: rows.items repeats the row id {row_id!r}")
        seen_rows.add(row_id)
        members, member_ids = [], set()
        for spec in row.items:
            item_id = spec.id
            if item_id in member_ids:
                raise ValueError(f"E_REVIEW_ITEM_ID_DUPLICATE: row {row_id!r} repeats the item id {item_id!r}")
            member_ids.add(item_id)
            object_id, kind = spec.source_object, spec.source_kind
            base = (snapshots.get(object_id) if kind == "snapshot" else
                    scenarios.get(spec.scenario_id or "", {}).get(object_id) if kind == "scenario" else
                    available.get(object_id))
            if kind not in {"primary", "actual", "snapshot", "scenario"}:
                raise ValueError(f"E_REVIEW_ITEM_SOURCE_UNAVAILABLE: item {item_id!r} of row {row_id!r} has source kind {kind!r}; "
                                 "use primary, actual, snapshot or scenario")
            if base is None:
                raise ValueError(f"E_REVIEW_ITEM_SOURCE_UNAVAILABLE: item {item_id!r} of row {row_id!r} reads the {kind} source of "
                                 f"object {object_id!r}, which that source does not contain")
            if kind == "actual" and base.actual is None:
                raise ValueError(f"E_REVIEW_ITEM_SOURCE_UNAVAILABLE: item {item_id!r} of row {row_id!r} reads the actual of "
                                 f"object {object_id!r}, which has no actual observation")
            track = spec.track
            if track not in {"stacked", "shared"}:
                raise ValueError(f"E_REVIEW_ITEM_TRACK: item {item_id!r} of row {row_id!r} has track {track!r}; use stacked or shared")
            intent = spec.presentation if spec.presentation is not None else row.presentation
            members.append(replace(base, item_id=item_id, source_kind=kind, track=track, scenario_id=spec.scenario_id,
                                   presentation=dict(intent) if intent is not None else None))
        subject = row.table_subject or (members[0].item_id if members else "")
        if subject not in member_ids:
            raise ValueError(f"E_REVIEW_TABLE_SUBJECT: the table subject {subject!r} of row {row_id!r} is not one of its item ids {sorted(member_ids)}")
        output.append(ReviewRowProjection(row_id, row.label or members[0].title,
            row.group or "", subject, tuple(members), depth=row.depth, parent_row_id=row.parent_row))
    _validate_explicit_row_hierarchy(output)
    return tuple(output), ()


def _fold_automatic_points(rows: tuple[ReviewRowProjection, ...], view: ViewInput,
                           project: dict[str, Any]) -> tuple[tuple[ReviewRowProjection, ...], tuple[FoldedPointProjection, ...]]:
    """Apply View-owned automatic point policy without exposing relation facts to Layout."""
    if view.rows.points == "own-row":
        return rows, ()
    if view.rows.points in {"attached", "predecessor"}:
        rows = _attach_points(rows, project)
    if view.rows.points == "attached":
        return rows, ()
    if view.rows.points == "group-header":
        if view.grouping is None or view.grouping.presentation != "header":
            raise ValueError("E_REVIEW_POINT_GROUP_HEADER_REQUIRED: rows.points group-header needs a grouping with presentation header")
        labels = view.visibility.labels
        has_title_label = (labels is True or
                           (isinstance(labels, Mapping) and labels.get("placement") in {"plot", "both"}
                            and "title" in labels.get("content", ())))
        if not has_title_label:
            raise ValueError("E_REVIEW_POINT_GROUP_HEADER_LABEL_REQUIRED: rows.points group-header needs visibility.labels "
                             "to show titles on the plot")
        folded = tuple(FoldedPointProjection(row.items[0], row.group_id, members=row.items[1:])
                       for row in rows if row.items and row.items[0].source_type == "point")
        if any(not point.group_id for point in folded):
            raise ValueError("E_REVIEW_POINT_GROUP_HEADER_UNAVAILABLE: these points belong to no group, so no header can hold them: "
                             f"{[point.item.object_id for point in folded if not point.group_id]}")
        return tuple(row for row in rows if not row.items or row.items[0].source_type != "point"), folded
    if view.rows.points != "predecessor":
        raise ValueError(f"E_REVIEW_POINT_POLICY: rows.points {view.rows.points!r} is not one of own-row, attached, predecessor, group-header")
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
    return tuple(replacements.get(row.row_id, row) for row in rows if row.row_id not in folded), ()


def _attach_points(rows: tuple[ReviewRowProjection, ...], project: dict[str, Any]) -> tuple[ReviewRowProjection, ...]:
    """Move each point that attachesTo a selected span onto that span's row (#486)."""
    objects = project.get("objects", {})
    by_object = {row.table_subject_id: row for row in rows}
    moved: set[str] = set()
    replacements: dict[str, ReviewRowProjection] = {}
    for row in rows:
        subject = row.items[0] if row.items else None
        host = objects.get(subject.object_id, {}).get("attachesTo") if subject is not None else None
        if subject is None or subject.source_type != "point" or host not in by_object:
            continue
        target = replacements.get(host, by_object[host])
        if not target.items or target.items[0].source_type != "span":
            continue
        moved.add(row.row_id)
        replacements[host] = replace(target, items=target.items + tuple(
            replace(item, track="shared", attached_to=host) for item in row.items))
    return tuple(replacements.get(row.row_id, row) for row in rows if row.row_id not in moved)


def _validate_explicit_row_hierarchy(rows: list[ReviewRowProjection]) -> None:
    """Validate only asserted View row edges against the Project-owned hierarchy."""
    by_id = {row.row_id: row for row in rows}
    for row in rows:
        if row.parent_row_id is None:
            continue
        parent = by_id.get(row.parent_row_id)
        if parent is None:
            raise ValueError(f"E_REVIEW_ROW_PARENT_UNAVAILABLE: row {row.row_id!r} names parent row {row.parent_row_id!r}, which is not a row of the View")
        subject = next((item for item in row.items if item.item_id == row.table_subject_id), None)
        parent_subject = next((item for item in parent.items if item.item_id == parent.table_subject_id), None)
        if subject is None or parent_subject is None or subject.source_kind != "primary" or parent_subject.source_kind != "primary":
            raise ValueError(f"E_REVIEW_ROW_PARENT_SOURCE: row {row.row_id!r} and its parent row {parent.row_id!r} must both "
                             "have a primary table subject")
        if subject.parent_id is None:
            raise ValueError(f"E_REVIEW_ROW_PARENT_ROOT: row {row.row_id!r} names a parent row but its subject "
                             f"{subject.object_id!r} is a hierarchy root")
        if subject.parent_id != parent_subject.object_id:
            raise ValueError(f"E_REVIEW_ROW_PARENT_MISMATCH: the Project parent of {subject.object_id!r} (row {row.row_id!r}) is "
                             f"{subject.parent_id!r}, not {parent_subject.object_id!r}, the subject of parent row {parent.row_id!r}")


def _snapshot_items(project: dict[str, Any] | None, placements: dict[str, dict[str, date]] | None,
                    analysis: Any | None = None,
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
            planned, None, None, _roles(ObservationState.UNAVAILABLE, None, critical), "", "",
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


def _actual(observation: dict[str, Any] | None) -> dict[str, date | float | str] | None:
    raw = (observation or {}).get("actual")
    if not raw:
        return None
    # ``openUntil`` is an explicit observation policy, not a date and never a
    # fabricated ``finish``.  Preserve it through View projection so Layout can
    # resolve its shared Actual Set cutoff.
    return {key: (value if key == "openUntil" else _date_or_number(value)) for key, value in raw.items()}


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
        return {"id": item.object_id, "title": item.title, "plannedStart": item.planned.get("start", item.planned.get("at")), "plannedEnd": item.planned.get("end", item.planned.get("at")), "plannedFinish": item.planned.get("end", item.planned.get("at")), "source": item.source_index}[field]
    if ordering is None:
        ordering_by, tie_break, direction = "id", "id", "ascending"
    else:
        ordering_by, tie_break, direction = ordering.by, ordering.tie_break, ordering.direction
    rows.sort(key=lambda item: value(item, tie_break))
    rows.sort(key=lambda item: value(item, ordering_by), reverse=direction == "descending")
    if view.grouping is not None and view.grouping.order_by == "earliestPlannedStart":
        earliest: dict[str, Any] = {}
        for item in rows:
            start = item.planned.get("start", item.planned.get("at"))
            if start is not None and (item.group_id not in earliest or start < earliest[item.group_id]):
                earliest[item.group_id] = start
        rows.sort(key=lambda item: (item.group_id not in earliest, earliest.get(item.group_id, date.min), item.group_id))
        return
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


def _observation_state(planned: dict[str, date], observation: dict[str, Any] | None,
                       as_of: date | None) -> ObservationState:
    """Classify one selected observation without reading the local clock."""
    if observation is not None:
        return ObservationState.RECORDED
    if as_of is None:
        return ObservationState.UNAVAILABLE
    due = planned.get("end", planned.get("at"))
    if due is None:
        return ObservationState.UNAVAILABLE
    return ObservationState.DUE_UNOBSERVED if due <= as_of else ObservationState.NOT_YET_DUE


def _roles(observation_state: ObservationState, finish_delta: int | None,
           critical: bool = False) -> tuple[str, ...]:
    """Map selected facts to the closed semantic-role vocabulary."""
    roles = ["planned"]
    if observation_state == ObservationState.RECORDED:
        roles.append("actual")
    elif observation_state == ObservationState.DUE_UNOBSERVED:
        roles.append("missing-actual")
    if finish_delta is not None:
        roles.append("variance-behind" if finish_delta > 0 else "variance-ahead" if finish_delta < 0 else "variance-on-plan")
    if critical:
        roles.append("critical")
    return tuple(roles)
