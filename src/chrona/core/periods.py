"""Named periods: a Project fact that names a date range and never schedules (#582).

A period is the half-open range ``[start, end)``, each side a calendar date or an endpoint of a Project
object. Like ``deadline`` and ``attachesTo`` it is metadata: it adds no relation, moves no object, and the
scheduler never reads it. This module owns its static validation.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from chrona.core.diagnostics import Diagnostic
from chrona.core.temporal import TemporalError, as_date

_SIDES = ("start", "end")
_ENDPOINTS = ("at", "start", "end")


def period_diagnostics(project: Mapping[str, Any],
                       endpoints_of: Callable[[Mapping[str, Any]], frozenset[str]]) -> list[Diagnostic]:
    """Reject a period whose references or literal dates cannot name one range.

    ``endpoints_of`` is the Project's one rule for which endpoints a schedule offers (a point has ``at``, a
    span has ``start`` and ``end``), the rule relations already apply, so it is not restated here. A range
    with a reference on either side cannot be ordered without placements and is checked after scheduling.
    """
    objects = project.get("objects", {})
    diagnostics: list[Diagnostic] = []
    for period_id, period in (project.get("periods") or {}).items():
        base = f"/periods/{period_id}"
        literals: dict[str, Any] = {}
        for side in _SIDES:
            boundary = period[side]
            if isinstance(boundary, Mapping):
                diagnostics.extend(_reference_diagnostics(period_id, side, boundary, objects, endpoints_of, base))
                continue
            try:
                literals[side] = as_date(boundary)
            except TemporalError as exc:
                diagnostics.append(Diagnostic("E_SCHEMA", str(exc), f"{base}/{side}"))
        if len(literals) == len(_SIDES) and literals["start"] >= literals["end"]:
            diagnostics.append(order_diagnostic(period_id, literals["start"], literals["end"]))
    return diagnostics


@dataclass(frozen=True)
class ResolvedPeriod:
    """One period with both sides turned into dates; ``end`` is exclusive."""

    period_id: str
    title: str
    start: date
    end: date


def resolve_periods(project: Mapping[str, Any], placements: Mapping[str, Mapping[str, date]]) -> tuple[ResolvedPeriod, ...]:
    """Every declared period as dates, in Project order, from the placements a scheduler returned.

    A reference names the completed date of an object endpoint, so a re-plan moves the period. The
    title falls back to the period identifier, as an object's does. Nothing here reorders, clips or
    rejects: an empty or inverted range is reported by ``period_range_diagnostics``.
    """
    return tuple(
        ResolvedPeriod(period_id, str(period.get("title") or period_id),
                       _boundary_date(period["start"], placements), _boundary_date(period["end"], placements))
        for period_id, period in (project.get("periods") or {}).items())


def period_range_diagnostics(project: Mapping[str, Any],
                             placements: Mapping[str, Mapping[str, date]]) -> tuple[Diagnostic, ...]:
    """Reject a period whose references resolve to an empty or inverted range.

    A range with two literal dates was already ordered by ``period_diagnostics``; only a reference needs
    placements. Like every post-placement finding of the reference scheduler it rejects the plan.
    """
    periods = project.get("periods") or {}
    return tuple(
        order_diagnostic(item.period_id, item.start, item.end)
        for item in resolve_periods(project, placements)
        if item.end <= item.start
        and any(isinstance(periods[item.period_id][side], Mapping) for side in _SIDES))


def _boundary_date(boundary: Any, placements: Mapping[str, Mapping[str, date]]) -> date:
    if isinstance(boundary, Mapping):
        return placements[boundary["object"]][boundary["endpoint"]]
    return as_date(boundary)


def order_diagnostic(period_id: str, start: Any, end: Any) -> Diagnostic:
    """The one ordering finding, whether found among literals or after a reference resolved."""
    return Diagnostic(
        "E_PROJECT_PERIOD_ORDER",
        f"Period {period_id} must start before it ends: start {start.isoformat()} is not before end "
        f"{end.isoformat()}, and end is exclusive, so write the day after the last day it covers",
        f"/periods/{period_id}",
        details={"period": period_id, "start": start.isoformat(), "end": end.isoformat()},
    )


def _reference_diagnostics(period_id: str, side: str, boundary: Mapping[str, Any], objects: Mapping[str, Any],
                           endpoints_of: Callable[[Mapping[str, Any]], frozenset[str]],
                           base: str) -> list[Diagnostic]:
    object_id, endpoint = boundary["object"], boundary["endpoint"]
    if object_id not in objects:
        return [Diagnostic("E_PROJECT_PERIOD_OBJECT_UNKNOWN",
                           f"Period {period_id} {side} names unknown object {object_id}", f"{base}/{side}/object")]
    available = endpoints_of(objects[object_id]["schedule"])
    if endpoint in available:
        return []
    return [Diagnostic(
        "E_PROJECT_PERIOD_ENDPOINT_UNAVAILABLE",
        f"Endpoint {endpoint} is unavailable on object {object_id}; its schedule offers "
        f"{', '.join(name for name in _ENDPOINTS if name in available)}",
        f"{base}/{side}/endpoint")]
