"""Typed, view-owned Plan/Actual review projection model."""
from __future__ import annotations

from copy import deepcopy
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date, timedelta
from enum import StrEnum
from itertools import chain
import re
from typing import Any

from chrona.core.completion import actual_occurrence_completed, rollup_completed
from chrona.core.hierarchy import HierarchyEntry, children_by_parent, normalize_hierarchy
from chrona.core.diagnostics import Diagnostic
from chrona.core.forecast import ForecastItem, ForecastOutcome
from chrona.core.observations import latest_observations
from chrona.core.relation_identity import relation_identities
from chrona.presentation.contracts.resources import ViewInput, _PrivateGroupingMode
from chrona.presentation.model.actual_observation import finish_variance
from chrona.presentation.model.date_basis import DisplayDateRange, ItemDateBasis, aggregate_date_ranges, endpoint_distance
from chrona.presentation.model.field_roles import FieldRoleBindings
from chrona.presentation.model.field_role_view import resolve_role_grouping
from chrona.presentation.model.wording_tables import WordingResolver, delta_unit_text, wording_resolver
from chrona.presentation.model.hierarchy_names import plot_name_selected
from chrona.presentation.review.lane_membership import (
    LaneItem, LaneMembership, LanePackingInput, PlannedPoint, PlannedSpan,
    SelectedFSRelation, derive_lane_membership,
)


_SHARED_TRACK_SOURCE_ORDER = {"snapshot": 0, "scenario": 1, "primary": 2, "actual": 3}


class ViewWindowError(ValueError):
    """A declared relative window cannot be resolved from its selected facts."""

    source_ref = "/body/window"

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


class NetworkLabelSourceError(ValueError):
    """A selected node's declared label field is present but is not text."""

    code = "E_VIEW_NETWORK_LABEL_SOURCE"
    source_ref = "/body/network/nodeLabel/source"

    def __init__(self, object_id: str, title: str, value_type: str) -> None:
        self.object_id = object_id
        self.title = title
        self.value_type = value_type
        self.detail = (f"Network node {object_id!r} label source must resolve to a string or null; "
                       f"found {value_type}. Select a text field, title or id.")
        super().__init__(f"{self.code}: {self.detail}")


class ObservationState(StrEnum):
    """One View-owned Actual availability fact at the declared as-of date."""

    RECORDED = "recorded"
    DUE_UNOBSERVED = "due-unobserved"
    NOT_YET_DUE = "not-yet-due"
    UNAVAILABLE = "unavailable"


class WindowMode(StrEnum):
    """Declared View window policy retained as projection provenance."""

    SELECTED_PLANNED = "selected-planned"
    SELECTED_COMPARISON = "selected-comparison"
    EXPLICIT = "explicit"
    RELATIVE = "relative"

    @property
    def is_bounded(self) -> bool:
        """Whether the View declared a positive bounded date window."""
        return self in {WindowMode.EXPLICIT, WindowMode.RELATIVE}


def shared_track_member_key(member: Any, source_index: int) -> tuple[int, int, int]:
    """Return the sole stable semantic traversal order for normalized track members."""
    if getattr(member, "track", "stacked") != "shared":
        return (1, source_index, source_index)
    return (0, _SHARED_TRACK_SOURCE_ORDER.get(getattr(member, "source_kind", ""), len(_SHARED_TRACK_SOURCE_ORDER)), source_index)


@dataclass(frozen=True)
class ForecastComparisonFact:
    schedule: ForecastItem
    # None for an object with no Snapshot counterpart: it is new, so there is no baseline distance (#1755).
    finish_delta: int | None


def active_placement(item: Any) -> Mapping[str, date]:
    """Displayed temporal geometry, never a replacement for source-plan queries."""
    forecast = getattr(item, "forecast", None)
    return forecast.schedule.placement if forecast is not None else item.planned


def display_finish_delta(item: Any) -> int | None:
    forecast = getattr(item, "forecast", None)
    return forecast.finish_delta if forecast is not None else item.finish_delta


def is_estimated_finish_delta(item: Any) -> bool:
    """Whether the selected finish-delta fact is forecast-estimated, not finalized."""
    forecast = getattr(item, "forecast", None)
    return (forecast is not None and forecast.finish_delta is not None
            and not forecast.schedule.completed)


def omit_zero_finish_delta(item: Any, enabled: bool) -> bool:
    """Whether the View removes this item's numeric-zero finish-delta label component (#1936)."""
    value = display_finish_delta(item)
    return bool(enabled and type(value) is int and value == 0)


NEW_MARKER = "new"  # the en-US default of ``marker.baselineNew``; localized text rides on ``ReviewItem.new_marker`` (#1781)


def is_new_against_baseline(item: Any) -> bool:
    """True for a primary object the supplied Snapshot does not contain (#1755)."""
    return bool(getattr(item, "new_vs_baseline", False))


def signed_delta_text(value: int, item: Any) -> str:
    """A signed day delta with the item's wording-resolved unit (#1790)."""
    return f"{value:+d}{getattr(item, 'delta_affix', 'd')}"


def finish_delta_text(item: Any) -> str | None:
    value = display_finish_delta(item)
    if value is None:
        return getattr(item, "new_marker", NEW_MARKER) if is_new_against_baseline(item) else None
    forecast = getattr(item, "forecast", None)
    return signed_delta_text(value, item) + ("*" if forecast is not None and not forecast.schedule.completed else "")


def finish_delta_semantic(item: Any) -> str:
    value = display_finish_delta(item)
    semantic = "varianceBehind" if value is not None and value > 0 else "varianceAhead" if value is not None and value < 0 else "finishDelta"
    return "forecast" + semantic[0].upper() + semantic[1:] if getattr(item, "forecast", None) is not None else semantic


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
    temporal_paint: bool = True
    # Lane of a key-row point, assigned by Layout from measured extents (#1501); None everywhere else.
    key_lane: int | None = None
    # Block pitch of that lane when a label is taller than the mark lane, so adjacent lanes' labels never meet (#1681).
    key_pitch: float | None = None
    # Project-declared link retained separately from lane-derived ``attached_to`` (#1373).
    declared_attaches_to: str | None = None
    field_bindings: FieldRoleBindings = FieldRoleBindings()
    date_basis: ItemDateBasis = ItemDateBasis()
    comparison_delta_unit: str = "calendar-days"
    # Locale text of the day unit that follows a signed delta (`d`, `日`, `営業日`); resolved from the
    # `delta.unit.*` wording keys at projection time, so Layout never carries a literal unit (#1790).
    delta_affix: str = "d"
    forecast: ForecastComparisonFact | None = None
    # View-owned content eligibility, independent of temporal mark visibility.
    member_label_eligible: bool = True
    # Source-local display titles aligned with ``hierarchy_path`` IDs.
    hierarchy_titles: tuple[str, ...] = ()
    # View's finite-depth row owner; never a Project parent or attachment.
    collapsed_row_id: str | None = None
    # The supplied Snapshot has no counterpart of this primary object: it is new, its baseline delta is empty (#1755).
    new_vs_baseline: bool = False
    # The localized ``marker.baselineNew`` text a new object shows in its empty Δ (#1781).
    new_marker: str = NEW_MARKER
    # Snapshot/current planned finish comparison, independent of Actual and forecast delta.
    snapshot_finish_delta: int | None = None
    # True when a role-bound field grouping sent this item to the `missing` group because it carries no value of the
    # role's field and nothing it is attached to supplies one (#1870 row 4). The group is then ordered last.
    group_unassigned: bool = False
    # The Project object's domain type (`task`, `gate`, ...), for count figures restricted by type (#1880).
    object_type: str = ""

    @property
    def at_delta(self) -> int | None:
        """Point Actual minus planned point on the declared comparison basis."""
        planned_at = self.planned.get("at")
        actual_at = self.actual.get("at") if self.actual is not None else None
        return (endpoint_distance(planned_at, actual_at, self.date_basis, self.comparison_delta_unit)
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
    # The one row of `points: key-row` (#1501): `label` is the declared title, every item is a point.
    key_row: bool = False


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
class NetworkDeadlineContent:
    """View-selected, already formatted deadline footer facts for a network node."""

    object_id: str
    label: str
    slipped: bool


@dataclass(frozen=True)
class DependencyNetworkNode:
    """View-selected graph fact; Layout alone assigns geometry."""

    object_id: str
    title: str
    order_key: tuple[Any, ...]
    critical: bool
    source_kind: str
    deadline: NetworkDeadlineContent | None = None
    is_container: bool = False
    container_id: str | None = None


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
    variant: str | None = None

    @property
    def band_role(self) -> str:
        return f"period-band:{self.variant}" if self.variant is not None else "period-band"

    @property
    def label_role(self) -> str:
        return f"period-label:{self.variant}" if self.variant is not None else "period-label"


@dataclass(frozen=True)
class ReviewDeadline:
    """One shown promise with completed Core calendar-day boundaries.

    ``slipped`` is the Core's verdict (the finish is strictly after the deadline); Layout never compares the dates.
    """

    object_id: str
    deadline: date
    deadline_boundary: int
    finish_boundary: int
    slipped: bool
    days_late: int
    caption: str | None = None


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
    unavailable_figures: tuple[Diagnostic, ...] = ()
    window_mode: WindowMode = WindowMode.SELECTED_PLANNED
    forecast_findings: tuple[Diagnostic, ...] = ()
    omitted_group_summary_count: int = 0
    # (id, title) of Snapshot objects with no current counterpart that no ghost row shows (#1755).
    removed_objects: tuple[tuple[str, str], ...] = ()
    forecast_warnings: tuple[Diagnostic, ...] = ()
    # True when View folding has resolved the ordinary row set, so an empty `rows` means "no ordinary rows" rather than
    # "no row input". Legacy projections that carry only `items` leave it False (#1660).
    rows_resolved: bool = False
    # Declared group containers in display order, including groups whose points were all folded into the header.
    group_order: tuple[str, ...] = ()
    # Comparison sources resolved by Render Context closure, independent of selected table rows.
    bound_comparison_sources: frozenset[str] = frozenset()
    window_outside: str = "keep"
    # Optional selected half-open temporal envelope before derived-window padding.
    # Explicit/relative windows and projections without this proof leave it unknown.
    unpadded_window: tuple[date, date] | None = None

    @property
    def has_rows(self) -> bool:
        """Whether Layout reads View-resolved rows instead of deriving one automatic row per item."""
        return self.rows_resolved or bool(self.rows)

    @property
    def group_ids(self) -> tuple[str, ...]:
        """Group containers in display order, including groups that hold only folded points."""
        return self.group_order or tuple(dict.fromkeys(row.group_id for row in self.rows if row.group_id))

    def group_member_items(self, group_id: str) -> tuple[ReviewItem, ...]:
        """Primary members of one group: its ordinary rows, or its folded points when it has none."""
        ordinary = tuple(item for row in self.rows if row.group_id == group_id for item in row.items)
        if ordinary:
            return ordinary
        return tuple(item for point in self.folded_points if point.group_id == group_id for item in point.all_items)

    def group_date_ranges(self, *, end_display: str) -> dict[str, DisplayDateRange]:
        """Complete display-only rollup ranges from the resolved View occurrences.

        Resolved rows are authoritative: neither omitted Project descendants nor
        comparison-only tracks may extend this range. Nested rollup ranges are
        resolved first, so their mixed endpoints are not closed a second time.
        """
        ordinary = (item for row in self.rows for item in row.items) if self.has_rows else iter(self.items)
        folded = (item for point in self.folded_points for item in point.all_items)
        members = tuple(item for item in chain(ordinary, folded) if item.source_kind in {"primary", "combined"})
        groups = {item.object_id: item for item in members if item.is_rollup and item.hierarchy_path}
        ranges: dict[str, DisplayDateRange] = {}
        # Close child rollups once before parents; never recursively expand the
        # same descendant subtree for every ancestor or table cell.
        for group in sorted(groups.values(), key=lambda item: len(item.hierarchy_path), reverse=True):
            path = group.hierarchy_path
            resolved = aggregate_date_ranges(
                ((ranges.get(item.object_id, item.planned), item.date_basis) for item in members
                 if len(item.hierarchy_path) > len(path) and item.hierarchy_path[:len(path)] == path),
                end_display=end_display)
            if resolved is not None:
                ranges[group.object_id] = resolved
        return ranges


def forecast_deadline_placements(projection: ReviewProjection) -> dict[str, dict[str, date]]:
    """Select completed View occurrences that may supply per-object forecast deadline finishes.

    This is source-fact selection only: it does not use window geometry or recompute dates.
    Repeated occurrences share the same Project object forecast and therefore one map entry.
    """
    occurrences = (item for row in projection.rows for item in row.items)
    folded_occurrences = (item for point in projection.folded_points for item in point.all_items)
    selected: dict[str, dict[str, date]] = {}
    for item in chain(occurrences, folded_occurrences):
        if (item.source_kind not in {"primary", "combined"} or not item.temporal_paint
                or item.forecast is None):
            continue
        selected.setdefault(item.object_id, dict(item.forecast.schedule.placement))
    return selected


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


_CIVIL_WINDOW_OFFSET = re.compile(r"(0|[1-9][0-9]*)(d|w)\Z")


def _civil_offset_days(value: str | None, *, default: int = 0) -> int:
    if value is None:
        return default
    match = _CIVIL_WINDOW_OFFSET.fullmatch(value)
    if match is None:
        raise ValueError(f"E_REVIEW_WINDOW: invalid relative offset {value!r}; expected non-negative civil d/w")
    amount = int(match.group(1))
    return amount * (7 if match.group(2) == "w" else 1)


def _actual_completion_states(project: Mapping[str, Any], placements: Mapping[str, Mapping[str, date]],
                              latest: Mapping[str, Mapping[str, Any]]) -> dict[str, bool]:
    """Close Core Actual completion over temporal objects and rollup children."""
    states: dict[str, bool] = {}
    objects = project.get("objects", {})
    for object_id, placement in placements.items():
        raw = objects.get(object_id, {})
        if raw.get("schedule", {}).get("mode") == "rollup":
            continue
        observation = latest.get(object_id)
        actual = observation.get("actual") if isinstance(observation, Mapping) else None
        kind = "point" if "at" in placement else "span"
        states[object_id] = actual_occurrence_completed(kind, actual)
    hierarchy = normalize_hierarchy(project)
    children = children_by_parent(hierarchy)
    for entry in reversed(hierarchy):
        raw = objects.get(entry.object_id, {})
        if raw.get("schedule", {}).get("mode") != "rollup":
            continue
        states[entry.object_id] = rollup_completed(
            states[child_id] for child_id in children.get(entry.object_id, ()) if child_id in states)
    return states


def build_review_projection(project: dict[str, Any], placements: dict[str, dict[str, date]],
                            view: ViewInput, actual_set: dict[str, Any] | None,
                            snapshot_project: dict[str, Any] | None = None,
                            snapshot_placements: dict[str, dict[str, date]] | None = None,
                            scenarios: dict[str, tuple[dict[str, Any], dict[str, dict[str, date]]]] | None = None,
                            analysis: Any | None = None,
                            snapshot_analysis: Any | None = None,
                            forecast: ForecastOutcome | None = None,
                            field_bindings: FieldRoleBindings | None = None,
                            snapshot_field_bindings: FieldRoleBindings | None = None,
                            scenario_field_bindings: Mapping[str, FieldRoleBindings] | None = None,
                            wording: WordingResolver | None = None) -> ReviewProjection:
    """Derive review facts; composition belongs to View, never Project."""
    if view.comparison.actual == "required" and actual_set is None:
        raise ValueError("E_ACTUAL_REQUIRED: the View compares against actuals (comparison.actual is required) but no actual "
                         "file was given; pass --actual FILE, or change the View so actuals are not required")
    if forecast is not None and not forecast.ok:
        raise ValueError("E_PRESENTATION_INPUT_INCOMPLETE: forecast outcome is unsuccessful")
    active_analysis = forecast.analysis if forecast is not None else analysis
    latest, unmatched = latest_observations(
        (actual_set or {}).get("body", actual_set or {}).get("observations", []), placements)
    as_of_value = (actual_set or {}).get("body", actual_set or {}).get("asOf")
    as_of = date.fromisoformat(as_of_value) if isinstance(as_of_value, str) else as_of_value
    if view.window.mode == "relative" and as_of is None:
        raise ViewWindowError("E_VIEW_WINDOW_AS_OF_REQUIRED",
                              "A relative View window requires Actual.asOf. Declare it in the Actual set, or use an explicit window.")
    if view.window.mode == "relative" and view.surface != "table-timeline":
        raise ValueError("E_VIEW_WINDOW_SURFACE: relative windows require a table-timeline surface at /body/window")
    resolver = wording if wording is not None else wording_resolver("en-US", view.wording)
    delta_affix = delta_unit_text(resolver, view.comparison.delta_unit or "calendar-days")
    explicit = view.rows.mode == "explicit"
    ids = set(view.selection.ids) if view.selection and view.selection.ids else set(placements)
    types = set(view.selection.types) if view.selection and view.selection.types else {"span", "point"}
    object_types = set(view.selection.object_types) if view.selection else set()
    excluded_object_types = set(view.selection.excluded_object_types) if view.selection else set()
    excluded_states = set(view.selection.excluded_states) if view.selection else set()
    completion_states = (_actual_completion_states(project, placements, latest)
                         if "finished" in excluded_states else {})
    bindings = field_bindings if field_bindings is not None else FieldRoleBindings.from_project(project)
    grouping = resolve_role_grouping(view.grouping, bindings)
    if grouping is not view.grouping:
        view = replace(view, grouping=grouping)
    selected: list[ReviewItem] = []
    hierarchy = grouping is not None and grouping.by == "hierarchy"
    root_grouping = (grouping is not None
                     and grouping.by is _PrivateGroupingMode.PROJECT_ROOT_GROUP)
    hierarchy_entries = {entry.object_id: entry for entry in normalize_hierarchy(project)}
    root_groups = {
        object_id for object_id, item in project.get("objects", {}).items()
        if item.get("type") == "group"
    }
    hierarchy_root_ids: set[str] = set()
    omitted_group_ids: list[str] = []
    role_bound = (grouping is not None and grouping.by == "field" and grouping.field_role is not None)
    declared = {object_id: index for index, object_id in enumerate(project["objects"])}
    for object_id, planned in placements.items():
        source_type = "point" if "at" in planned else "span"
        project_type = str(project["objects"][object_id].get("type", ""))
        # The role fallback presents top-level group objects as headers, not as
        # temporal rows, even when a group has a rollup placement.
        if root_grouping and project_type == "group":
            continue
        if "finished" in excluded_states and completion_states.get(object_id, False):
            continue
        if not hierarchy and (object_id not in ids or source_type not in types
                              or (object_types and project_type not in object_types)
                              or project_type in excluded_object_types):
            continue
        if (grouping is not None and grouping.by == "field" and grouping.field_role is not None
                and project_type == "group"):
            omitted_group_ids.append(object_id)
            continue
        if hierarchy and object_id in ids and source_type in types and (not object_types or project_type in object_types) and project_type not in excluded_object_types:
            hierarchy_root_ids.add(object_id)
        actual = _actual(latest.get(object_id))
        observation_state = _observation_state(planned, latest.get(object_id), as_of)
        date_basis = ItemDateBasis.from_project(project, object_id)
        finish_delta = _finish_delta(planned, actual, as_of, basis=date_basis,
                                     delta_unit=view.comparison.delta_unit or "calendar-days")
        snapshot_placement = (snapshot_placements.get(object_id)
                              if snapshot_project is not None and snapshot_placements is not None
                              and object_id in snapshot_project.get("objects", {}) else None)
        snapshot_finish_delta = _snapshot_finish_delta(
            planned, snapshot_placement, basis=date_basis,
            delta_unit=view.comparison.delta_unit or "calendar-days")
        float_value = active_analysis.total_float.get(object_id) if active_analysis is not None else None
        total_float = float_value.value if float_value is not None else None
        critical = object_id in active_analysis.critical if active_analysis is not None else False
        link = _object_link(project["objects"][object_id].get("link"))
        entry = hierarchy_entries.get(object_id)
        hierarchy_path = entry.path if entry else ()
        group_id = (_root_group_ancestor(hierarchy_entries.get(object_id), root_groups)
                    if root_grouping else _group_id(project, object_id, source_type, grouping))
        unassigned = False
        if role_bound and grouping.field not in project["objects"][object_id].get("fields", {}):
            donor = (_point_group_donor(project, object_id, entry, grouping.field)
                     if source_type == "point" and view.rows.points in _FOLDING_POINT_POLICIES else None)
            if donor is not None:
                group_id = donor
            else:
                unassigned = True
        selected.append(ReviewItem(
            object_id, str(project["objects"][object_id].get("title", object_id)), source_type,
            planned, actual, finish_delta, _roles(observation_state, finish_delta, critical),
            group_id, str(project.get("objects", {}).get(group_id, {}).get("title", group_id)
                          if root_grouping else project.get("entities", {}).get(group_id, {}).get("title", group_id)),
            dict(project["objects"][object_id].get("fields", {})), object_id, "primary",
            parent_id=entry.parent_id if entry else None,
            hierarchy_depth=entry.depth if entry else 0,
            wbs_code=entry.display_wbs_code if entry else "",
            hierarchy_path=hierarchy_path,
            hierarchy_titles=_hierarchy_titles(project, hierarchy_path),
            is_rollup=project["objects"][object_id].get("schedule", {}).get("mode") == "rollup",
            total_float=total_float, critical=critical, link=link,
            planned_progress=project["objects"][object_id].get("plannedProgress"),
            observation_state=observation_state, source_index=declared.get(object_id, 0),
            declared_attaches_to=project["objects"][object_id].get("attachesTo"), field_bindings=bindings,
            date_basis=date_basis, comparison_delta_unit=view.comparison.delta_unit or "calendar-days",
            delta_affix=delta_affix,
            new_vs_baseline=(snapshot_project is not None and snapshot_placements is not None
                             and object_id not in snapshot_placements),
            new_marker=resolver.text("marker.baselineNew"), group_unassigned=unassigned,
            snapshot_finish_delta=snapshot_finish_delta, object_type=project_type))
    if not selected:
        raise ValueError("E_REVIEW_EMPTY: the View selects no object of the Project; check its selection against the Project objects")
    if forecast is not None:
        baseline = snapshot_placements if snapshot_project is not None else placements
        displayed_ids = ({spec.source_object for row in view.rows.items for spec in row.items
                          if spec.source_kind == "primary"} if explicit else {item.object_id for item in selected})
        projected = []
        for item in selected:
            if item.object_id not in displayed_ids:
                projected.append(item)
                continue
            predicted = forecast.items.get(item.object_id)
            reference = (baseline or {}).get(item.object_id)
            endpoint = "at" if item.source_type == "point" else "end"
            if predicted is None or endpoint not in predicted.placement:
                raise ValueError(f"E_FORECAST_BASELINE_UNAVAILABLE: {item.object_id}: the forecast has no schedule for this "
                                 "displayed object; check that it is a schedulable span or point of the Project")
            if reference is None and item.new_vs_baseline:
                # New since the Snapshot: it draws normally and skips the baseline comparison (#1755).
                projected.append(replace(item, forecast=ForecastComparisonFact(predicted, None)))
                continue
            if reference is None or endpoint not in reference:
                raise ValueError(f"E_FORECAST_BASELINE_UNAVAILABLE: {item.object_id}: the baseline has no {endpoint!r} "
                                 "placement for this object (its kind changed); compare against a Snapshot of the same kind")
            delta = endpoint_distance(reference[endpoint], predicted.placement[endpoint],
                                      item.date_basis, item.comparison_delta_unit)
            projected.append(replace(item, forecast=ForecastComparisonFact(predicted, delta)))
        selected = projected
    if (grouping is not None and grouping.by == "field" and grouping.presentation == "header"
            and all(grouping.field not in (item.fields or {}) for item in selected)):
        # A header that distinguishes nothing is not drawn (Specification 45).
        selected = [replace(item, group_id="", group_label="", group_unassigned=False) for item in selected]
    omitted_group_summary_count = _unattributable_summaries(omitted_group_ids, selected, view)
    if hierarchy and not explicit:
        selected = _expand_hierarchy_roots(selected, hierarchy_entries, hierarchy_root_ids, view, project)
        selected = [replace(item, temporal_paint=not (
            item.is_rollup and grouping.rollup in {"header", "none"})) for item in selected]
    elif not explicit:
        _order(selected, view, project)
    snapshots = _snapshot_items(snapshot_project, snapshot_placements, snapshot_analysis,
                                field_bindings=snapshot_field_bindings)
    removed_ids = _removed_baseline_ids(snapshot_project, snapshots, placements, view, ids, types, object_types,
                                        excluded_object_types)
    ghosts_shown = bool(removed_ids) and not explicit and (
        forecast is not None or (view.comparison.baseline == "snapshot"
                                 and view.comparison.baseline_marks in {"ghost", "ghost-when-changed"}))
    removed_items = [_in_baseline_group(
        _removed_ghost(snapshots[object_id], resolver.text("marker.baselineRemoved")),
        snapshot_project, grouping, root_grouping, selected) for object_id in removed_ids] if ghosts_shown else []
    hidden_removed = tuple((object_id, snapshots[object_id].title) for object_id in removed_ids) if not ghosts_shown else ()
    # `ghost-when-changed` without a snapshot baseline draws no ghost and is not an error (#429); `ghost` still needs one.
    if forecast is None and view.comparison.baseline_marks == "ghost" and not explicit and (view.comparison.baseline != "snapshot" or not snapshots):
        raise ValueError("E_REVIEW_BASELINE_MARKS_SNAPSHOT: comparison.baselineMarks needs comparison.baseline snapshot "
                         "and a snapshot Project in the Render Context")
    scenario_items = {scenario_id: _snapshot_items(value[0], value[1], None, source_kind="scenario",
                                                  field_bindings=(scenario_field_bindings or {}).get(scenario_id))
                      for scenario_id, value in (scenarios or {}).items()}
    if view.comparison.missing_actual_scope == "in-progress":
        selected = [replace(item, missing_actual_mark=_missing_actual_scope_mark(item)) for item in selected]
    rows, folded_points = _compose_rows(view, selected, snapshots, scenario_items, project, removed_items)
    group_order = _group_order(selected, rows) if folded_points else ()
    if forecast is not None and explicit and snapshot_project is not None:
        for row in rows:
            for item in row.items:
                if item.forecast is not None and not any(
                    ghost.source_kind == "snapshot" and ghost.object_id == item.object_id for ghost in row.items
                ):
                    raise ValueError(f"E_FORECAST_PRESENTATION_REQUIRED: explicit row {row.row_id} needs a Snapshot track for {item.object_id}")
    lane_membership = _project_lane_membership(project, rows, view) if view.rows.mode == "lanes" else None
    lane_rows = _project_lane_rows(rows, lane_membership) if lane_membership is not None else ()
    if lane_membership is not None:
        lanes_by_id = {lane.lane_id: lane for lane in lane_membership.lanes}
        lane_membership = replace(lane_membership,
                                  lanes=tuple(lanes_by_id[row.lane_id] for row in lane_rows))
    unpadded_window = None
    if view.window.mode == "relative":
        if view.window.before is None and view.window.after is None:
            raise ValueError("E_REVIEW_WINDOW: relative window requires before or after at /body/window")
        before_days = _civil_offset_days(view.window.before)
        after_days = _civil_offset_days(view.window.after)
        if before_days == 0 and after_days == 0:
            raise ValueError("E_REVIEW_WINDOW: relative before and after cannot both be zero at /body/window")
        try:
            start = as_of - timedelta(days=before_days)
            end = as_of + timedelta(days=after_days)
        except (OverflowError, ValueError) as error:
            raise ViewWindowError("E_REVIEW_WINDOW",
                                  f"Relative bounds around Actual.asOf {as_of} exceed the Date domain. Reduce before/after.") from error
        margin = 0
    elif view.window.mode == "explicit":
        start, end = (_date_or_number(value) for value in (view.window.start, view.window.end))
        margin = 0
        if start >= end:
            raise ValueError(f"E_REVIEW_WINDOW: window.start {view.window.start} is not before window.end {view.window.end}")
    else:
        envelopes: list[tuple[date, date]] = []
        selected_dates = [item for row in rows for item in row.items]
        selected_dates.extend(point.item for point in folded_points)
        for item in selected_dates:
            placement = active_placement(item)
            if item.source_type == "point":
                point_date = placement["at"]
                try:
                    envelopes.append((point_date, point_date + timedelta(days=1)))
                except OverflowError as error:
                    raise ViewWindowError(
                        "E_REVIEW_WINDOW",
                        f"Point date {point_date} for selected object {item.object_id!r} has no following Date day in the Date domain",
                    ) from error
            else:
                envelopes.append((placement["start"], placement["end"]))
        if view.window.mode == "selected-comparison":
            for item in selected_dates:
                actual = item.actual or {}
                if "at" in actual and isinstance(actual["at"], date):
                    point_date = actual["at"]
                    try:
                        envelopes.append((point_date, point_date + timedelta(days=1)))
                    except OverflowError as error:
                        raise ViewWindowError(
                            "E_REVIEW_WINDOW",
                            f"Actual point date {point_date} for selected object {item.object_id!r} has no following Date day in the Date domain",
                        ) from error
                else:
                    actual_dates = [value for value in actual.values() if isinstance(value, date)]
                    if actual_dates:
                        envelopes.append((min(actual_dates), max(actual_dates)))
        start = min(bounds[0] for bounds in envelopes)
        end = max(bounds[1] for bounds in envelopes)
        unpadded_window = (start, end)
        margin = view.window.margin_days
        if margin is None:
            # Omitted policy: planned content receives proportional breathing room;
            # comparison content remains exactly at its completed envelope.
            margin = max(((end - start).days + 9) // 10, 1) if view.window.mode == "selected-planned" else 0
    try:
        window = (date.fromordinal(start.toordinal() - margin),
                  date.fromordinal(end.toordinal() + margin))
    except ValueError as error:
        ids = tuple(item.object_id for item in selected)
        raise ViewWindowError("E_REVIEW_WINDOW", f"cannot pad selected dates {start}..{end} "
                              f"by {margin} days within the Date domain; selected objects={ids!r}") from error
    return ReviewProjection(tuple(selected),
        window,
        tuple(sorted(unmatched)), tuple("E_ACTUAL_UNMATCHED" for _ in unmatched), rows,
        view.comparison.facets, hierarchy, view.surface,
        _dependency_network_projection(
            project, selected, view, hierarchy_entries,
            frozenset(getattr(active_analysis, "driving_relations", ()))),
        frozenset(getattr(active_analysis, "driving_relations", ()),), folded_points,
        lane_membership, lane_rows, window_mode=WindowMode(view.window.mode),
        window_outside=view.window.outside,
        forecast_findings=forecast.findings if forecast is not None else (),
        forecast_warnings=forecast.warnings if forecast is not None else (),
        omitted_group_summary_count=omitted_group_summary_count,
        removed_objects=hidden_removed,
        rows_resolved=True, group_order=group_order,
        bound_comparison_sources=frozenset(
            ("snapshot",) if snapshot_project is not None else ()
        ) | (frozenset({"scenario"}) if scenarios else frozenset()),
        unpadded_window=unpadded_window)


def _group_order(selected: list[ReviewItem], rows: tuple[ReviewRowProjection, ...]) -> tuple[str, ...]:
    """Group containers in declared display order, kept for groups whose points were all folded into the header."""
    order: list[str] = []
    for item in selected:
        if item.group_id and item.group_id not in order:
            order.append(item.group_id)
    known = set(order)
    order.extend(row.group_id for row in rows if row.group_id and row.group_id not in known)
    return tuple(order)


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
    row_ranks = {member_id: rank for rank, member_id in enumerate(source_rows)}
    group_ranks = {group_id: rank for rank, group_id in enumerate(dict.fromkeys(row.group_id for row in rows))}
    return tuple(sorted(output, key=lambda lane: (
        group_ranks[lane.group_id],
        min(row_ranks[member_id] for member_id in lane.member_item_ids), lane.lane_id)))


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
        placement = active_placement(item)
        planned = (PlannedPoint(placement["at"]) if item.source_type == "point" else
                   PlannedSpan(placement["start"], placement["end"]))
        host_id = item.declared_attaches_to
        selected_host = primary.get(host_id) if item.source_type == "point" else None
        if selected_host is not None and selected_host.source_type != "span":
            selected_host = None
        attached_host = selected_host.item_id if selected_host is not None else None
        # An attachment owns row placement independently of WBS or object fields.
        group_id = selected_host.group_id if selected_host is not None and "attached" in view.rows.packing else item.group_id
        key = by_object.get(item.object_id)
        if key is None and lane_keys is not None:
            source = ({"fieldRole": lane_keys.field_role} if lane_keys.field_role is not None
                      else {"field": lane_keys.field})
            key = item.field_bindings.read(item.fields, source)
        if key is not None and (not isinstance(key, str) or not key):
            raise ValueError(f"E_REVIEW_LANE_KEY: the lane key of object {item.object_id!r} must be a non-empty string, got {key!r}")
        items.append(LaneItem(item.item_id, item.object_id, group_id, planned, key, attached_host))
    project_relations = project.get("relations", ())
    relations = tuple(SelectedFSRelation(identity, str(relation["from"]["object"]),
                                         str(relation["to"]["object"]),
                                         relation.get("id") or identity)
                      for identity, relation in zip(relation_identities(project_relations), project_relations)
                      if relation.get("type") == "dependency"
                      and relation.get("from", {}).get("endpoint") == "end"
                      and relation.get("to", {}).get("endpoint") == "start"
                      and relation.get("from", {}).get("object") in primary
                      and relation.get("to", {}).get("object") in primary)
    return derive_lane_membership(LanePackingInput(tuple(items), view.rows.packing, relations))


def _dependency_network_projection(project: dict[str, Any], selected: list[ReviewItem],
                                   view: ViewInput,
                                   hierarchy_entries: Mapping[str, HierarchyEntry],
                                   driving_relations: frozenset[str] = frozenset()) -> DependencyNetworkProjection | None:
    """Close Project relation facts at the View boundary for a network surface."""
    if view.surface != "dependency-network":
        return None
    relation_visibility = view.visibility.relations
    relation_mode = (relation_visibility.get("mode", "none")
                     if isinstance(relation_visibility, Mapping) else relation_visibility)
    selected_ids = {item.object_id for item in selected}
    selected_containers = {item.object_id for item in selected
                           if project.get("objects", {}).get(item.object_id, {}).get("type") == "group"}
    critical_ids = {item.object_id for item in selected if item.critical}

    def selected_container_parent(item: ReviewItem) -> str | None:
        entry = hierarchy_entries.get(item.object_id)
        if entry is None:
            return None
        return next((ancestor for ancestor in reversed(entry.path[:-1])
                     if ancestor in selected_containers), None)

    # Explicit timeline rows do not order `selected`. A network still has the
    # same global ViewOrdering contract, without changing timeline row order.
    ordered = list(selected)
    _order(ordered, view, project)
    nodes = tuple(DependencyNetworkNode(item.object_id, _network_node_label(item, view),
                                        (ordinal,), item.critical, item.source_kind,
                                        is_container=item.object_id in selected_containers,
                                        container_id=selected_container_parent(item))
                  for ordinal, item in enumerate(ordered))
    edges = []
    project_relations = project.get("relations", ())
    for identity, relation in zip(relation_identities(project_relations), project_relations):
        if relation_mode == "none":
            continue
        source = relation.get("from", {})
        target = relation.get("to", {})
        source_id, target_id = source.get("object"), target.get("object")
        if source_id not in selected_ids or target_id not in selected_ids:
            continue
        critical = (identity in driving_relations
                    and source_id in critical_ids and target_id in critical_ids)
        if relation_mode == "critical" and not critical:
            continue
        edge = DependencyNetworkEdge(identity, str(source_id), str(target_id),
                                           str(source.get("endpoint", "end")), str(target.get("endpoint", "start")),
                                           critical)
        edges.append((relation.get("id") or identity, edge))
    return DependencyNetworkProjection(nodes, tuple(edge for _, edge in sorted(
        edges, key=lambda item: (item[0], item[1].relation_id))))


def _network_node_label(item: ReviewItem, view: ViewInput) -> str:
    source = view.network.node_label_source if view.network is not None else "title"
    if source is None or source == "title":
        return item.title
    if source == "id":
        return item.object_id
    value = item.field_bindings.read_result(item.fields, source, object_id=item.object_id).value
    if value is None:
        return item.title
    if not isinstance(value, str):
        raise NetworkLabelSourceError(item.object_id, item.title, type(value).__name__)
    return value


def _missing_actual_scope_mark(item: ReviewItem) -> str:
    """Select only missing-Actual marks; recorded open Actuals stay Actual (#1582)."""
    return "none" if item.observation_state == ObservationState.DUE_UNOBSERVED else "due-end"


def _compose_rows(view: ViewInput, selected: list[ReviewItem], snapshots: dict[str, ReviewItem],
                  scenarios: dict[str, dict[str, ReviewItem]], project: dict[str, Any],
                  removed: list[ReviewItem] | None = None) -> tuple[tuple[ReviewRowProjection, ...], tuple[FoldedPointProjection, ...]]:
    if view.rows.mode != "explicit":
        def scenario_ghost(item: ReviewItem) -> bool:
            return (view.comparison.baseline == "scenario" and view.comparison.scenario_id in scenarios
                    and item.object_id in scenarios[view.comparison.scenario_id])

        def snapshot_ghost(item: ReviewItem) -> bool:
            if item.forecast is not None:
                return item.object_id in snapshots
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
                         source_kind="scenario", scenario_id=view.comparison.scenario_id, track="shared",
                         temporal_paint=item.temporal_paint, collapsed_row_id=item.collapsed_row_id)
                 if scenario_ghost(item) else None),
                (replace(snapshots[item.object_id], item_id=f"snapshot:{item.object_id}",
                         source_kind="snapshot", track="shared", temporal_paint=item.temporal_paint,
                         collapsed_row_id=item.collapsed_row_id,
                         member_label_eligible=(snapshots[item.object_id].member_label_eligible
                                                and view.comparison.baseline_labels != "none"))
                 if snapshot_ghost(item) else None),
            ) if member is not None),
            depth=item.hierarchy_depth if view.grouping is not None and view.grouping.by == "hierarchy" else 0,
            rollup_presentation=(view.grouping.rollup or "none"
                                if item.is_rollup and view.grouping is not None else "none"))
            for item in selected)
        # A Snapshot object with no current counterpart is a removed baseline ghost row (#1755). It closes its own
        # baseline group, not the last group of the table (#1842): it sits after the last row of that group, or after
        # every row when the group has no current member.
        rows = _insert_removed_rows(rows, tuple(
            ReviewRowProjection(item.object_id, item.title, item.group_id, f"snapshot:{item.object_id}",
                                (replace(item, item_id=f"snapshot:{item.object_id}", source_kind="snapshot",
                                         track="shared"),))
            for item in (removed or ())))
        collapsed: dict[str, list[ReviewItem]] = {}
        for row in rows:
            target = row.items[0].collapsed_row_id
            if target is not None:
                collapsed.setdefault(target, []).extend(row.items)
        if collapsed:
            retained_ids = {row.row_id for row in rows if row.items[0].collapsed_row_id is None}
            missing = set(collapsed) - retained_ids
            if missing:
                raise ValueError(f"E_REVIEW_ROW_PARENT_UNAVAILABLE: collapsed points need retained rows {sorted(missing)}")
            rows = tuple(replace(row, items=row.items + tuple(collapsed.get(row.row_id, ())))
                         for row in rows if row.items[0].collapsed_row_id is None)
        rows = _forecast_member_label_ownership(rows)
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
                                   forecast=base.forecast if kind == "primary" else None,
                                   snapshot_finish_delta=(base.snapshot_finish_delta if kind == "primary" else None),
                                   presentation=dict(intent) if intent is not None else None))
        subject = row.table_subject or (members[0].item_id if members else "")
        if subject not in member_ids:
            raise ValueError(f"E_REVIEW_TABLE_SUBJECT: the table subject {subject!r} of row {row_id!r} is not one of its item ids {sorted(member_ids)}")
        output.append(ReviewRowProjection(row_id, row.label or members[0].title,
            row.group or "", subject, tuple(members), depth=row.depth, parent_row_id=row.parent_row))
    _validate_explicit_row_hierarchy(output)
    return _forecast_member_label_ownership(tuple(output)), ()


def _insert_removed_rows(rows: tuple[ReviewRowProjection, ...],
                         removed: tuple[ReviewRowProjection, ...]) -> tuple[ReviewRowProjection, ...]:
    """Place each removed-baseline row after the last row of its group, else at the end."""
    placed = list(rows)
    for row in removed:
        last = max((index for index, other in enumerate(placed) if row.group_id and other.group_id == row.group_id),
                   default=len(placed) - 1)
        placed.insert(last + 1, row)
    return tuple(placed)


def _in_baseline_group(item: ReviewItem, snapshot_project: dict[str, Any] | None, grouping: Any,
                       root_grouping: bool, selected: list[ReviewItem]) -> ReviewItem:
    """Give a removed ghost the group its Snapshot object had under the View's grouping (#1842).

    The group id comes from the Snapshot Project by the rule current items use, so a ghost of a `mobile` task
    belongs to the `mobile` group; a hierarchy or ungrouped View keeps the ghost ungrouped.
    """
    if snapshot_project is None or grouping is None:
        return item
    if root_grouping:
        entries = {entry.object_id: entry for entry in normalize_hierarchy(snapshot_project)}
        groups = {object_id for object_id, value in snapshot_project.get("objects", {}).items()
                  if value.get("type") == "group"}
        group_id = _root_group_ancestor(entries.get(item.object_id), groups)
        label = str(snapshot_project.get("objects", {}).get(group_id, {}).get("title", group_id))
    else:
        group_id = _group_id(snapshot_project, item.object_id, item.source_type, grouping)
        label = str(snapshot_project.get("entities", {}).get(group_id, {}).get("title", group_id))
    if not group_id:
        return item
    label = next((current.group_label for current in selected if current.group_id == group_id), label)
    unassigned = (not root_grouping and grouping.by == "field" and grouping.field_role is not None
                  and grouping.field not in snapshot_project["objects"][item.object_id].get("fields", {}))
    return replace(item, group_id=group_id, group_label=label, group_unassigned=unassigned)


def _removed_ghost(item: ReviewItem, marker: str) -> ReviewItem:
    """The removed marker rides on the title and on the path title a `path` name source reads (#1755)."""
    marked = f"{item.title} ({marker})"
    titles = item.hierarchy_titles
    if item.hierarchy_path and item.hierarchy_path[-1] == item.object_id and len(titles) == len(item.hierarchy_path):
        titles = titles[:-1] + (marked,)
    return replace(item, title=marked, hierarchy_titles=titles)


def _removed_baseline_ids(snapshot_project: dict[str, Any] | None, snapshots: dict[str, ReviewItem],
                          placements: dict[str, dict[str, date]], view: ViewInput, ids: set[str], types: set[str],
                          object_types: set[str], excluded_object_types: set[str]) -> list[str]:
    """Snapshot objects the View would select but the current Project no longer has (#1755)."""
    if snapshot_project is None:
        return []
    result = []
    for object_id, item in snapshots.items():
        project_type = str(snapshot_project["objects"][object_id].get("type", ""))
        if (object_id in placements or project_type == "group" or object_id not in ids and view.selection and view.selection.ids
                or item.source_type not in types or (object_types and project_type not in object_types)
                or project_type in excluded_object_types):
            continue
        result.append(object_id)
    return result


def _forecast_member_label_ownership(rows: tuple[ReviewRowProjection, ...]) -> tuple[ReviewRowProjection, ...]:
    """A forecast primary owns its name; its paired baseline keeps paint only."""
    output = []
    for row in rows:
        primary_ids = {item.object_id for item in row.items if item.forecast is not None}
        if not primary_ids:
            output.append(row)
            continue
        items = tuple(replace(item, member_label_eligible=False)
                      if item.source_kind == "snapshot" and item.object_id in primary_ids
                      else item for item in row.items)
        output.append(replace(row, items=items))
    return tuple(output)


def _fold_automatic_points(rows: tuple[ReviewRowProjection, ...], view: ViewInput,
                           project: dict[str, Any]) -> tuple[tuple[ReviewRowProjection, ...], tuple[FoldedPointProjection, ...]]:
    """Apply View-owned automatic point policy without exposing relation facts to Layout."""
    if view.rows.points == "own-row":
        return rows, ()
    if view.rows.points == "key-row":
        return _key_row(rows, view), ()
    if view.rows.points in {"attached", "predecessor"}:
        rows = _attach_points(rows, project)
    if view.rows.points == "attached":
        return rows, ()
    if view.rows.points == "group-header":
        if view.grouping is None or view.grouping.presentation != "header":
            raise ValueError("E_REVIEW_POINT_GROUP_HEADER_REQUIRED: rows.points group-header needs a grouping with presentation header")
        if not plot_name_selected(view):
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
            replace(item, track="shared", attached_to=candidates[0]) for item in row.items))
    return tuple(replacements.get(row.row_id, row) for row in rows if row.row_id not in folded), ()


KEY_ROW_ID = "key-row"


def _key_row(rows: tuple[ReviewRowProjection, ...], view: ViewInput) -> tuple[ReviewRowProjection, ...]:
    """Move every point row into one row placed first, under the axis (#1501); Layout packs it into lanes."""
    if not plot_name_selected(view):
        raise ValueError("E_REVIEW_POINT_KEY_ROW_LABEL_REQUIRED: rows.points key-row needs visibility.labels "
                         "to show titles on the plot")
    points = sorted((row for row in rows if row.items and row.items[0].source_type == "point"),
                    key=lambda row: (row.items[0].planned.get("at"), row.items[0].object_id))
    if not points:
        return rows
    if any(row.row_id == KEY_ROW_ID for row in rows):
        raise ValueError(f"E_REVIEW_ROW_ID_DUPLICATE: an object is named {KEY_ROW_ID!r}, the id of the key row")
    key = ReviewRowProjection(
        KEY_ROW_ID, view.rows.key_row_title or "", "", points[0].items[0].item_id or points[0].items[0].object_id,
        tuple(replace(item, attached_to=None) for row in points for item in row.items), key_row=True)
    return (key, *(row for row in rows if not row.items or row.items[0].source_type != "point"))


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
    """Validate the View-local parent graph without asserting Project containment."""
    by_id = {row.row_id: row for row in rows}
    parents: dict[str, str | None] = {}
    for row in rows:
        parent_id = row.parent_row_id
        if parent_id is not None and parent_id not in by_id:
            raise ValueError(f"E_REVIEW_ROW_PARENT_UNAVAILABLE: row {row.row_id!r} names parent row {row.parent_row_id!r}, which is not a row of the View")
        parents[row.row_id] = parent_id

    # Each row has at most one parent, so an iterative three-state walk checks
    # the whole functional graph in linear time and supports deep authored trees.
    state: dict[str, int] = {}
    for row in rows:
        start = row.row_id
        if state.get(start, 0) == 2:
            continue
        path: list[str] = []
        current: str | None = start
        while current is not None and state.get(current, 0) == 0:
            state[current] = 1
            path.append(current)
            current = parents[current]
        if current is not None and state.get(current) == 1:
            raise ValueError(f"E_REVIEW_ROW_PARENT_CYCLE: explicit row parent graph contains a cycle at row {current!r}")
        for row_id in path:
            state[row_id] = 2


def _snapshot_items(project: dict[str, Any] | None, placements: dict[str, dict[str, date]] | None,
                    analysis: Any | None = None,
                    source_kind: str = "snapshot", *,
                    field_bindings: FieldRoleBindings | None = None) -> dict[str, ReviewItem]:
    if project is None or placements is None:
        return {}
    result: dict[str, ReviewItem] = {}
    bindings = field_bindings if field_bindings is not None else FieldRoleBindings.from_project(project)
    hierarchy_entries = {entry.object_id: entry for entry in normalize_hierarchy(project)}
    for object_id, planned in placements.items():
        source_type = "point" if "at" in planned else "span"
        float_value = analysis.total_float.get(object_id) if analysis is not None else None
        total_float = float_value.value if float_value is not None else None
        critical = object_id in analysis.critical if analysis is not None else False
        entry = hierarchy_entries.get(object_id)
        hierarchy_path = entry.path if entry else ()
        result[object_id] = ReviewItem(
            object_id, str(project["objects"][object_id].get("title", object_id)), source_type,
            planned, None, None, _roles(ObservationState.UNAVAILABLE, None, critical), "", "",
            dict(project["objects"][object_id].get("fields", {})), object_id, source_kind,
            parent_id=entry.parent_id if entry else None,
            hierarchy_depth=entry.depth if entry else 0,
            wbs_code=entry.display_wbs_code if entry else "",
            hierarchy_path=hierarchy_path,
            hierarchy_titles=_hierarchy_titles(project, hierarchy_path),
            total_float=total_float, critical=critical, link=_object_link(project["objects"][object_id].get("link")),
            declared_attaches_to=project["objects"][object_id].get("attachesTo"), field_bindings=bindings,
            date_basis=ItemDateBasis.from_project(project, object_id))
    return result


def _hierarchy_titles(project: Mapping[str, Any], path: tuple[str, ...]) -> tuple[str, ...]:
    """Close path titles from the same Project that supplied the path IDs."""
    objects = project.get("objects", {})
    titles = []
    for object_id in path:
        item = objects.get(object_id, {}) if isinstance(objects, Mapping) else {}
        title = item.get("title") if isinstance(item, Mapping) else None
        titles.append(title if isinstance(title, str) and title.strip() else object_id)
    return tuple(titles)


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


def _finish_delta(planned: dict[str, date], actual: dict[str, date | float] | None,
                  as_of: date | None = None, *, basis: ItemDateBasis = ItemDateBasis(),
                  delta_unit: str = "calendar-days") -> int | None:
    """The canonical known finish variance, including a started open Actual at as-of."""
    return finish_variance(planned, actual, as_of, basis=basis, delta_unit=delta_unit)


def _snapshot_finish_delta(planned: Mapping[str, Any], snapshot: Mapping[str, Any] | None, *,
                           basis: ItemDateBasis, delta_unit: str) -> int | None:
    """Current planned finish minus a matching Snapshot finish, with no Actual/forecast policy."""
    if snapshot is None:
        return None
    endpoint = "at" if "at" in planned else "end"
    current_finish, snapshot_finish = planned.get(endpoint), snapshot.get(endpoint)
    if not isinstance(current_finish, date) or not isinstance(snapshot_finish, date):
        return None
    return endpoint_distance(snapshot_finish, current_finish, basis, delta_unit)


def _order(rows: list[ReviewItem], view: ViewInput, project: Mapping[str, Any]) -> None:
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
        rows.sort(key=lambda item: (item.group_unassigned, item.group_id not in earliest,
                                    earliest.get(item.group_id, date.min), item.group_id))
        return
    group_order = view.grouping.order if view.grouping is not None else ()
    if group_order:
        rows.sort(key=lambda item: (group_order.index(item.group_id) if item.group_id in group_order else len(group_order), item.group_id))
    elif (view.grouping is not None
          and view.grouping.by is _PrivateGroupingMode.PROJECT_ROOT_GROUP):
        declared_group_order = {
            object_id: index for index, (object_id, obj) in enumerate(
                (entry for entry in project.get("objects", {}).items() if entry[1].get("type") == "group"))
        }
        rows.sort(key=lambda item: (
            0 if not item.group_id else 1,
            declared_group_order.get(item.group_id, len(declared_group_order)),
            item.group_id))
    elif view.grouping is not None and view.grouping.by == "field" and view.grouping.field_role is not None:
        # Role-bound grouping (#1870 row 4, Spec 06 §6.3): headers in first appearance in the Project's declared
        # object order among the selected rows, the `missing` group last. A direct field key stays alphabetical.
        first_seen: dict[str, int] = {}
        for item in rows:
            first_seen[item.group_id] = min(item.source_index, first_seen.get(item.group_id, item.source_index))
        rows.sort(key=lambda item: (item.group_unassigned, first_seen[item.group_id], item.group_id))
    else:
        rows.sort(key=lambda item: (len(group_order), item.group_id))


# Point policies that fold a point into another row or a header; a point without the role value follows them (#1870).
_FOLDING_POINT_POLICIES = frozenset({"attached", "predecessor", "group-header"})


def _point_group_donor(project: Mapping[str, Any], object_id: str, entry: HierarchyEntry | None,
                       field: str) -> str | None:
    """The group a point lacking the role's value is attached to: its `attachesTo` host, else its nearest container."""
    objects = project.get("objects", {})
    host = objects[object_id].get("attachesTo")
    candidates = [host] if isinstance(host, str) else []
    candidates += reversed(entry.path[:-1]) if entry is not None else []
    for candidate in candidates:
        value = objects.get(candidate, {}).get("fields", {}).get(field)
        if value is not None:
            return str(value)
    return None


def _unattributable_summaries(group_ids: list[str], selected: list[ReviewItem], view: ViewInput) -> int:
    """Parent groups whose selected descendants span more than one header (#1870 row 4, R4).

    A role-bound grouping drops `type: group` summary rows. A parent whose descendants all sit under one header loses
    nothing, since its span is that header's members' union. Only a parent spread over several headers has a summary no
    header can carry. A point the key row takes out of the headers belongs to none.
    """
    counted = 0
    key_row = view.rows.points == "key-row"
    for group_id in group_ids:
        headers = {item.group_id for item in selected
                   if group_id in item.hierarchy_path[:-1]
                   and not (key_row and item.group_unassigned and item.source_type == "point")}
        counted += len(headers) > 1
    return counted


def _group_id(project: dict[str, Any], object_id: str, source_type: str, grouping: Any) -> str:
    if grouping is None or grouping.by == "none":
        return ""
    if grouping.by == "objectType":
        return source_type
    if grouping.by == "hierarchy":
        return ""
    return str(project["objects"][object_id].get("fields", {}).get(grouping.field or "", grouping.missing or "ungrouped"))


def _root_group_ancestor(entry: HierarchyEntry | None, group_ids: set[str]) -> str:
    """Return the rootmost group ancestor, or an empty ungrouped identity."""
    if entry is None:
        return ""
    return next((ancestor for ancestor in entry.path[:-1] if ancestor in group_ids), "")


def _expand_hierarchy_roots(items: list[ReviewItem], entries: dict[str, HierarchyEntry],
                            candidate_ids: set[str], view: ViewInput,
                            project: Mapping[str, Any]) -> list[ReviewItem]:
    """Expand View-selected roots without giving View authority over tree truth."""
    item_by_id = {item.object_id: item for item in items}
    grouping = view.grouping
    predicate_omitted = view.selection is None or (not view.selection.ids and not view.selection.types
                                                   and not view.selection.object_types and not view.selection.excluded_object_types
                                                   and not view.selection.excluded_states)
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

    root_items = [item_by_id[root] for root in roots]
    _order(root_items, view, project)
    pending = [(item, 0, None) for item in reversed(root_items)]
    while pending:
        item, relative_depth, collapsed_row_id = pending.pop()
        if collapsed_row_id is None or item.source_type == "point":
            output.append(replace(item, hierarchy_depth=relative_depth,
                                  collapsed_row_id=collapsed_row_id))
        if limit != "all" and relative_depth >= limit:
            collapsed_row_id = collapsed_row_id or item.object_id
        child_items = [item_by_id[child] for child in children.get(item.object_id, ()) if child in item_by_id]
        _order(child_items, view, project)
        pending.extend((child, relative_depth + 1, collapsed_row_id) for child in reversed(child_items))
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
        roles.append("variance-behind" if finish_delta > 0 else "variance-ahead" if finish_delta < 0 else "variance-on-track")
    if critical:
        roles.append("critical")
    return tuple(roles)
