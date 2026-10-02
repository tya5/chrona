"""Named periods: a Project fact that names a date range and never schedules (#582).

A period is the half-open range ``[start, end)``, each side a calendar date or an endpoint of a Project
object. Like ``deadline`` and ``attachesTo`` it is metadata: it adds no relation, moves no object, and the
scheduler never reads it. This module owns its static validation.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
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
