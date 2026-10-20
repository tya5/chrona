"""Source-proven geometry-row admission for bounded View windows.

The Review projection and its visibility index remain complete and identity
bound.  This module derives a separate, immutable geometry mask from that
source closure; it never selects dates again or reads paint/label visibility.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Any, Mapping

from chrona.presentation.layout.lane_projection import (
    LaneProjectionInstance, close_lane_projection, lane_instance_owners,
)
from chrona.presentation.layout.mark_facet_visibility import (
    FacetDisposition, ItemMarkVisibility,
)
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_mark_visibility import (
    ItemMarkVisibilityIndex, MarkOccurrence, MarkOccurrenceKind,
    ensure_request_mark_visibility_index,
)
from chrona.presentation.model.projection import ReviewProjection, WindowMode


_NON_TEMPORAL_DERIVED_FACETS = frozenset({"missing-actual"})
_ROW_ADMISSION_SEAL = object()


@dataclass(frozen=True, slots=True)
class WindowRowOmissionProof:
    """Original source occurrence which did not retain its geometry row."""

    row_id: str
    occurrence: MarkOccurrence
    visibility: ItemMarkVisibility = field(repr=False, compare=False)
    projection: ReviewProjection = field(repr=False, compare=False)
    visibility_index: ItemMarkVisibilityIndex = field(repr=False, compare=False)
    reason: str

    def __post_init__(self) -> None:
        self.validate()

    @property
    def source_ref(self) -> str:
        return self.visibility.source_ref

    def validate(self) -> None:
        index = self.visibility_index
        valid = (isinstance(index, ItemMarkVisibilityIndex)
                 and isinstance(self.projection, ReviewProjection)
                 and isinstance(self.occurrence, MarkOccurrence)
                 and isinstance(self.row_id, str) and bool(self.row_id)
                 and index.projection is self.projection
                 and self.reason in {"outside-window", "no-selected-temporal-facet"})
        if valid:
            try:
                valid = (index.lookup(self.occurrence, projection=self.projection,
                                      as_of=index.as_of) is self.visibility)
            except KeyError:
                valid = False
        if valid:
            selected = tuple(facet for facet in self.visibility.selection.facets
                             if facet.facet not in _NON_TEMPORAL_DERIVED_FACETS)
            if self.reason == "no-selected-temporal-facet":
                valid = not selected
            else:
                valid = (bool(selected)
                         and all(facet.disposition == FacetDisposition.OMITTED
                                 for facet in self.visibility.facets
                                 if facet.source.facet not in _NON_TEMPORAL_DERIVED_FACETS))
        if not valid:
            raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/window/outside",
                              detail="stage=row-admission; reason=invalid-source-proof")


@dataclass(frozen=True)
class WindowRowAdmission:
    """One mask over geometry rows, retaining original source identities."""

    projection: ReviewProjection = field(repr=False, compare=False)
    visibility_index: ItemMarkVisibilityIndex = field(repr=False, compare=False)
    omit_outside: bool
    admitted_row_ids: frozenset[str]
    admitted_lane_ids: frozenset[str]
    admitted_auto_object_ids: frozenset[str]
    admitted_folded_group_ids: frozenset[str]
    admitted_group_ids: frozenset[str]
    omitted_row_reasons: Mapping[str, str] = field(default_factory=dict)
    omissions: Mapping[MarkOccurrence, WindowRowOmissionProof] = field(default_factory=dict)
    _seal: object | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "omitted_row_reasons",
                           MappingProxyType(dict(self.omitted_row_reasons)))
        object.__setattr__(self, "omissions", MappingProxyType(dict(self.omissions)))
        if not isinstance(self.projection, ReviewProjection):
            raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/window/outside",
                              detail="stage=row-admission; reason=invalid-projection")

    def require_match(self, projection: ReviewProjection,
                      visibility_index: ItemMarkVisibilityIndex) -> None:
        if (self._seal is not _ROW_ADMISSION_SEAL
                or projection is not self.projection or visibility_index is not self.visibility_index
                or visibility_index.projection is not projection):
            raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/window/outside",
                              detail="stage=row-admission; reason=request-mismatch")
        visibility_index.require_match(projection, visibility_index.as_of)

    def omission_for(self, occurrence: MarkOccurrence) -> WindowRowOmissionProof | None:
        """Return the exact original occurrence proof, without ID parsing."""
        proof = self.omissions.get(occurrence)
        if proof is not None:
            proof.validate()
        return proof


def _intersects(visibility: ItemMarkVisibility) -> bool:
    """Whether a selected temporal source facet survives the cached window."""
    return any(facet.source.facet not in _NON_TEMPORAL_DERIVED_FACETS
               and facet.disposition != FacetDisposition.OMITTED
               for facet in visibility.facets)


def _occurrence(kind: MarkOccurrenceKind, container_id: str, item: Any,
                source_kind: str | None = None) -> MarkOccurrence:
    item_id = item.item_id or item.object_id
    return MarkOccurrence(kind, container_id, item_id, item.object_id,
                          source_kind if source_kind is not None else item.source_kind)


def complete_window_row_admission(
    projection: ReviewProjection,
    visibility_index: ItemMarkVisibilityIndex,
) -> WindowRowAdmission:
    """Derive the sole geometry-row mask from the exact source visibility cache.

    A row is retained if any selected temporal source facet intersects the
    bounded window.  The original projection, lane membership and relations
    are never modified.  `keep` produces an all-admitted mask for callers that
    use the common geometry-row adapter.
    """
    if not isinstance(projection, ReviewProjection):
        raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/window/outside",
                          detail="stage=row-admission; reason=invalid-projection")
    if not isinstance(visibility_index, ItemMarkVisibilityIndex):
        raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/window/outside",
                          detail="stage=row-admission; reason=missing-visibility-index")
    visibility_index.require_match(projection, visibility_index.as_of)
    policy = getattr(projection, "window_outside", "keep")
    if policy not in {"keep", "omit"}:
        raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/window/outside",
                          detail="stage=row-admission; reason=invalid-policy")
    omit = policy == "omit"
    if omit and (projection.surface != "table-timeline"
                 or projection.window_mode not in {WindowMode.EXPLICIT, WindowMode.RELATIVE}):
        raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/window/outside",
                          detail="stage=row-admission; reason=unbounded-or-unsupported-surface")

    if not omit:
        # Do not traverse or revalidate legacy row/lane data on the default
        # path. The cache is a no-op there, preserving the established source
        # and geometry path byte-for-byte.
        row_ids = frozenset(row.row_id for row in projection.rows) if projection.has_rows else frozenset()
        lane_ids = frozenset(row.lane_id for row in projection.lane_rows)
        auto_ids = (frozenset(item.object_id for item in projection.items)
                    if not projection.has_rows and projection.lane_membership is None else frozenset())
        folded_groups = frozenset(point.group_id for point in projection.folded_points)
        groups = (frozenset(projection.group_order)
                  | frozenset(row.group_id for row in projection.rows if row.group_id)
                  | folded_groups)
        return _sealed_admission(
            projection, visibility_index, False, row_ids | auto_ids, lane_ids, auto_ids,
            folded_groups, groups, {}, {})

    omitted_row_reasons: dict[str, str] = {}
    omissions: dict[MarkOccurrence, WindowRowOmissionProof] = {}
    admitted_row_ids: set[str] = set()
    admitted_lane_ids: set[str] = set()
    admitted_auto_ids: set[str] = set()
    admitted_folded_groups: set[str] = set()
    admitted_groups: set[str] = set()

    def visibility_for(occurrence: MarkOccurrence) -> ItemMarkVisibility:
        try:
            return visibility_index.lookup(occurrence, projection=projection,
                                           as_of=visibility_index.as_of)
        except KeyError:
            raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/window/outside",
                              detail="stage=row-admission; reason=missing-source-occurrence") from None

    def occurrence_survives(occurrence: MarkOccurrence, row_id: str) -> bool:
        visibility = visibility_for(occurrence)
        if not omit or _intersects(visibility):
            return True
        selected = tuple(facet for facet in visibility.selection.facets
                         if facet.facet not in _NON_TEMPORAL_DERIVED_FACETS)
        reason = "outside-window" if selected else "no-selected-temporal-facet"
        omissions[occurrence] = WindowRowOmissionProof(
            row_id, occurrence, visibility, projection, visibility_index, reason)
        return False

    if projection.lane_membership is not None:
        closure = close_lane_projection(projection, as_of=visibility_index.as_of)
        owners = lane_instance_owners(projection, closure)
        by_lane: dict[str, list[tuple[MarkOccurrence, str]]] = {}
        row_groups = {row.row_id: row.group_id for row in projection.rows}
        for instance in closure.instances:
            lane_id, _ = owners[instance]
            occurrence = MarkOccurrence(
                MarkOccurrenceKind.LANE_SOURCE, instance.row_id, instance.item_id,
                instance.object_id, instance.source_kind)
            by_lane.setdefault(lane_id, []).append((occurrence, instance.row_id))
        lane_rows = {row.lane_id: row for row in projection.lane_rows}
        final_aliases = {
            (key.container_id, key.item_id, key.object_id, key.source_kind): key
            for key in visibility_index.entries
            if key.kind == MarkOccurrenceKind.LANE_FINAL
        }
        for lane_id, entries in by_lane.items():
            survive = [occurrence_survives(occurrence, lane_id)
                       for occurrence, _logical_row in entries]
            if not omit or any(survive):
                admitted_lane_ids.add(lane_id)
                admitted_row_ids.add(lane_id)
                for _occurrence_value, logical_row in entries:
                    if logical_row in row_groups:
                        admitted_groups.add(row_groups[logical_row])
            else:
                omitted_row_reasons[lane_id] = (
                    "outside-window" if any(
                        omission.reason == "outside-window"
                        for occurrence, _logical_row in entries
                        if (omission := omissions.get(occurrence)) is not None)
                    else "no-selected-temporal-facet")
            # Final lane aliases share the same immutable source visibility;
            # provide proof lookup for consumers that hold the final identity.
            for occurrence, _logical_row in entries:
                source = visibility_for(occurrence)
                final = final_aliases.get((lane_id, occurrence.item_id,
                                           occurrence.object_id, occurrence.source_kind))
                if final is None or visibility_index.entries[final] is not source:
                    raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/window/outside",
                                      detail="stage=row-admission; reason=missing-final-lane-alias") from None
                proof = omissions.get(occurrence)
                if proof is not None:
                    omissions[final] = proof
        # Validate that every declared physical lane received a source closure.
        if set(lane_rows) != set(by_lane):
            raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/laneRows",
                              detail="stage=row-admission; reason=lane-membership-mismatch")
    elif projection.has_rows:
        for row in projection.rows:
            occurrences = tuple(_occurrence(MarkOccurrenceKind.ROW, row.row_id, item)
                                for item in row.items)
            survives = [occurrence_survives(occurrence, row.row_id)
                        for occurrence in occurrences]
            if not omit or any(survives):
                admitted_row_ids.add(row.row_id)
                if row.group_id:
                    admitted_groups.add(row.group_id)
            else:
                reasons = {omissions[item].reason for item in occurrences if item in omissions}
                omitted_row_reasons[row.row_id] = (
                    "outside-window" if "outside-window" in reasons
                    else "no-selected-temporal-facet")
    else:
        for item in projection.items:
            occurrence = _occurrence(MarkOccurrenceKind.AUTO, item.object_id,
                                     item, "combined")
            if occurrence_survives(occurrence, item.object_id):
                admitted_auto_ids.add(item.object_id)
                admitted_row_ids.add(item.object_id)
                if item.group_id:
                    admitted_groups.add(item.group_id)
            else:
                omitted_row_reasons[item.object_id] = omissions[occurrence].reason

    for folded in projection.folded_points:
        occurrences = tuple(_occurrence(MarkOccurrenceKind.FOLDED, folded.group_id,
                                        item, item.source_kind)
                            for item in folded.all_items)
        survives = [occurrence_survives(occurrence, folded.group_id)
                    for occurrence in occurrences]
        if not omit or any(survives):
            admitted_folded_groups.add(folded.group_id)
            admitted_groups.add(folded.group_id)
        else:
            reasons = {omissions[item].reason for item in occurrences if item in omissions}
            omitted_row_reasons[f"group-header:{folded.group_id}"] = (
                "outside-window" if "outside-window" in reasons
                else "no-selected-temporal-facet")

    return _sealed_admission(
        projection, visibility_index, True, frozenset(admitted_row_ids),
        frozenset(admitted_lane_ids), frozenset(admitted_auto_ids),
        frozenset(admitted_folded_groups), frozenset(admitted_groups),
        omitted_row_reasons, omissions)


def _sealed_admission(
    projection: ReviewProjection,
    visibility_index: ItemMarkVisibilityIndex,
    omit: bool,
    row_ids: frozenset[str],
    lane_ids: frozenset[str],
    auto_ids: frozenset[str],
    folded_groups: frozenset[str],
    groups: frozenset[str],
    omitted_rows: Mapping[str, str],
    omissions: Mapping[MarkOccurrence, WindowRowOmissionProof],
) -> WindowRowAdmission:
    result = WindowRowAdmission(
        projection, visibility_index, omit, row_ids, lane_ids, auto_ids,
        folded_groups, groups, omitted_rows, omissions)
    object.__setattr__(result, "_seal", _ROW_ADMISSION_SEAL)
    result.require_match(projection, visibility_index)
    return result


def geometry_rows(rows: tuple[Any, ...],
                  admission: WindowRowAdmission | None) -> tuple[Any, ...]:
    """Apply the shared row mask; the keep path returns the identical tuple."""
    if admission is None or not admission.omit_outside:
        return rows
    return tuple(row for row in rows if row.row_id in admission.admitted_row_ids)


def geometry_folded_points(projection: ReviewProjection,
                           admission: WindowRowAdmission | None) -> tuple[Any, ...]:
    """Return only admitted folded headers while retaining source projection."""
    if admission is None or not admission.omit_outside:
        return projection.folded_points
    admission.require_match(projection, admission.visibility_index)
    return tuple(point for point in projection.folded_points
                 if point.group_id in admission.admitted_folded_group_ids)


def geometry_group_order(projection: ReviewProjection,
                         admission: WindowRowAdmission | None) -> tuple[str, ...]:
    """Limit declared headers to retained geometry only under explicit omission."""
    if admission is None or not admission.omit_outside:
        return projection.group_order
    admission.require_match(projection, admission.visibility_index)
    return tuple(group_id for group_id in projection.group_order
                 if group_id in admission.admitted_group_ids)


def geometry_table(table: Any, admission: WindowRowAdmission | None) -> Any:
    """Mask table geometry facts by canonical row identity, never source identity.

    Table columns and member-name/source indexes remain complete. Only cell
    facts, cell-object geometry bindings, and row-level geometry are filtered.
    The legacy/keep path returns the exact same TableContent object.
    """
    if admission is None or not admission.omit_outside:
        return table
    cells = tuple(cell for cell in table.cells
                  if cell.object_id in admission.admitted_row_ids)
    cell_objects = tuple(item for item in table.cell_objects
                         if item[0] in admission.admitted_row_ids)
    row_levels = tuple(level for level in table.row_levels
                       if level.keys and level.keys[0] in admission.admitted_row_ids)
    if (cells == table.cells and cell_objects == table.cell_objects
            and row_levels == table.row_levels):
        return table
    return replace(table, cells=cells, cell_objects=cell_objects, row_levels=row_levels)


def geometry_surface_content(content: Any, admission: WindowRowAdmission | None) -> Any:
    """Apply the same row mask to normalized Layout table facts, if present."""
    if admission is None or not admission.omit_outside:
        return content
    cells = tuple(cell for cell in content.table_cells
                  if cell.object_id in admission.admitted_row_ids)
    cell_objects = tuple(item for item in content.table_cell_objects
                         if item[0] in admission.admitted_row_ids)
    if cells == content.table_cells and cell_objects == content.table_cell_objects:
        return content
    return replace(content, table_cells=cells, table_cell_objects=cell_objects)


def ensure_request_window_row_admission(request: Any) -> Any:
    """Reuse or close one row-admission cache on the exact request projection."""
    projection = getattr(request, "projection", None)
    if not isinstance(projection, ReviewProjection):
        raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/window/outside",
                          detail="stage=row-admission; reason=invalid-projection")
    existing = getattr(request, "row_admission", None)
    if existing is not None:
        request = ensure_request_mark_visibility_index(request)
        index = request.mark_visibility_index
        if not isinstance(existing, WindowRowAdmission):
            raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/window/outside",
                              detail="stage=row-admission; reason=invalid-request-cache")
        existing.require_match(projection, index)
        if existing.omit_outside:
            content = geometry_surface_content(request.surface_content, existing)
            if content is not request.surface_content:
                request = replace(request, surface_content=content)
        return request
    # `keep` is the historical path: do not construct a new source index or
    # admission cache merely to prove that no omission was requested.
    if getattr(projection, "window_outside", "keep") == "keep":
        return request
    request = ensure_request_mark_visibility_index(request)
    index = request.mark_visibility_index
    admission = complete_window_row_admission(projection, index)
    request = replace(request, row_admission=admission)
    if admission.omit_outside:
        content = geometry_surface_content(request.surface_content, admission)
        if content is not request.surface_content:
            request = replace(request, surface_content=content)
    return request
