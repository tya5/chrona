"""Renderer-neutral temporal facet selection for one projected review item.

This module decides which date-bearing facets exist. It deliberately has no
scale, Theme, frame, or coordinate inputs; Layout geometry consumes the
selected source dates later.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from chrona.presentation.model.actual_observation import in_progress_actual
from chrona.presentation.model.projection import ObservationState, active_placement


def mark_placement_facet(facet: str) -> str:
    """Physical primary slot naming; semantic purpose remains on the typed facet."""
    return "planned" if facet == "forecast" else facet


@dataclass(frozen=True)
class MarkFacetAbsence:
    """One deliberately unprojected facet and the semantic reason it is absent."""

    facet: str
    reason: str


@dataclass(frozen=True)
class LogicalMarkFacet:
    """One selected facet with its original temporal operands and paint intent."""

    facet: str
    semantic_id: str
    shape: Literal["point", "span", "open-span"]
    geometry: Literal["span", "open-span", "in-progress", "end-tick"] = "span"
    start: date | None = None
    finish: date | None = None
    at: date | None = None
    end_treatment: str = "closed"

    def placement_id(self, instance_id: str) -> str:
        return f"{mark_placement_facet(self.facet)}:{instance_id}"


@dataclass(frozen=True)
class ItemMarkFacetSelection:
    """Complete source-facet decision, including current omission evidence."""

    source_kind: str
    as_of: date | None
    missing_actual_eligible: bool
    facets: tuple[LogicalMarkFacet, ...]
    diagnostics: tuple[str, ...]
    absences: tuple[MarkFacetAbsence, ...]


def due_end_missing_actual_selected(item: Any, *, emit_missing_actual: bool) -> bool:
    """One View-selected due-end rule for source facets and lane inventory."""
    return (emit_missing_actual
            and item.observation_state == ObservationState.DUE_UNOBSERVED
            and getattr(item, "missing_actual_mark", "due-end") == "due-end")


def select_item_mark_facets(*, item: Any, source_kind: str,
                            as_of: date | None,
                            emit_missing_actual: bool = True,
                            emit_diagnostics: bool = True) -> ItemMarkFacetSelection:
    """Select planned/observed date facets without performing geometry work."""
    facets: list[LogicalMarkFacet] = []
    diagnostics: list[str] = []
    absences: list[MarkFacetAbsence] = []
    planned = active_placement(item)
    actual = item.actual or {}
    missing_eligible = bool(emit_missing_actual)

    planned_semantic = "snapshot" if source_kind in {"snapshot", "scenario"} else "planned"
    primary_facet = "forecast" if getattr(item, "forecast", None) is not None else "planned"
    if primary_facet == "forecast":
        planned_semantic = "forecast"
    if source_kind == "actual":
        absences.append(MarkFacetAbsence("planned", "actual-only-member"))
    elif item.source_type == "point":
        facets.append(LogicalMarkFacet(primary_facet, planned_semantic, "point", at=planned["at"]))
    else:
        facets.append(LogicalMarkFacet(primary_facet, planned_semantic, "span",
                                       start=planned["start"], finish=planned["end"]))

    open_actual = (in_progress_actual(actual, as_of)
                   if source_kind in {"actual", "combined"} and item.source_type == "span"
                   else None)
    if (source_kind in {"actual", "combined"} and item.source_type == "span"
            and isinstance(actual.get("start"), date) and isinstance(actual.get("finish"), date)):
        facets.append(LogicalMarkFacet("actual", "actual", "span",
                                       start=actual["start"], finish=actual["finish"]))
    elif open_actual is not None:
        start = open_actual.start
        if as_of is None:
            if emit_diagnostics:
                diagnostics.append(f"W_LAYOUT_OPEN_ACTUAL_AS_OF_REQUIRED:{item.object_id}")
            absences.append(MarkFacetAbsence("actual", "as-of-required"))
        elif as_of <= start:
            if emit_diagnostics:
                diagnostics.append(f"W_LAYOUT_OPEN_ACTUAL_INVALID:{item.object_id}")
            absences.append(MarkFacetAbsence("actual", "invalid-open-actual"))
        else:
            facets.append(LogicalMarkFacet("actual", "actual", "open-span",
                                           geometry="open-span", start=start, finish=as_of,
                                           end_treatment="open"))
    elif (source_kind in {"actual", "combined"} and item.source_type == "point"
          and isinstance(actual.get("at"), date)):
        facets.append(LogicalMarkFacet("actual", "actual", "point", at=actual["at"]))
    elif source_kind in {"actual", "combined", "primary"}:
        if source_kind == "primary" and item.observation_state == ObservationState.RECORDED:
            absences.append(MarkFacetAbsence("actual", "recorded-on-companion-member"))
        elif actual.get("openUntil") == "asOf" and isinstance(actual.get("start"), date) and as_of is None:
            if emit_diagnostics:
                diagnostics.append(f"W_LAYOUT_OPEN_ACTUAL_AS_OF_REQUIRED:{item.object_id}")
            absences.append(MarkFacetAbsence("actual", "as-of-required"))
        elif actual:
            if emit_diagnostics:
                diagnostics.append(f"W_LAYOUT_ACTUAL_INCOMPLETE:{item.object_id}")
            absences.append(MarkFacetAbsence("actual", "incomplete-observation"))
        elif due_end_missing_actual_selected(item, emit_missing_actual=emit_missing_actual):
            anchor = item.planned.get("end", item.planned.get("at"))
            if isinstance(anchor, date):
                facets.append(LogicalMarkFacet("missing-actual", "missing-actual", "span",
                                               geometry="end-tick", start=anchor, finish=anchor))
            else:
                absences.append(MarkFacetAbsence("missing-actual", "planned-anchor-unavailable"))
        else:
            absences.append(MarkFacetAbsence("actual", "no-selected-observation"))
    else:
        absences.append(MarkFacetAbsence("actual", "member-has-no-actual-facet"))

    return ItemMarkFacetSelection(source_kind, as_of, missing_eligible,
                                  tuple(facets), tuple(diagnostics), tuple(absences))
