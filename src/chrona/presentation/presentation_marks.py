"""Renderer-neutral projection of planned/actual comparison marks."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Mapping


@dataclass(frozen=True)
class ComparisonMark:
    """One immutable semantic mark; geometry is assigned later by Scene layout."""

    source_id: str
    facet: str
    source_type: str
    start: date | None = None
    end: date | None = None
    at: date | None = None
    variance_days: int | None = None


def _as_date(value: object) -> date | None:
    return value if isinstance(value, date) else None


def comparison_marks(items: Iterable[object], *, comparison_mode: str, show_zero: bool = True) -> tuple[ComparisonMark, ...]:
    """Project only observed facets; never infer an actual endpoint from plan data."""
    if comparison_mode not in {"stacked", "overlaid", "baseline-and-actual"}:
        raise ValueError("E_PRESENTATION_COMPARISON_MODE")
    result: list[ComparisonMark] = []
    for item in items:
        source_id = str(getattr(item, "object_id"))
        source_type = str(getattr(item, "source_type"))
        planned = getattr(item, "planned")
        actual = getattr(item, "actual") or {}
        if not isinstance(planned, Mapping) or not isinstance(actual, Mapping):
            raise ValueError("E_PRESENTATION_MARK_INPUT")
        if source_type == "span":
            start, end = _as_date(planned.get("start")), _as_date(planned.get("end"))
            if start is None or end is None or end <= start:
                raise ValueError("E_PRESENTATION_MARK_INPUT")
            planned_facet = "baseline" if comparison_mode == "baseline-and-actual" else "planned"
            result.append(ComparisonMark(source_id, planned_facet, source_type, start=start, end=end))
            actual_start, actual_finish = _as_date(actual.get("start")), _as_date(actual.get("finish"))
            if actual_start is not None and actual_finish is not None:
                if actual_finish <= actual_start:
                    raise ValueError("E_PRESENTATION_MARK_INPUT")
                delta = (actual_finish - end).days
                result.append(ComparisonMark(source_id, "actual", source_type, start=actual_start, end=actual_finish))
                if show_zero or delta != 0:
                    result.append(ComparisonMark(source_id, "finish-delta", source_type, at=actual_finish, variance_days=delta))
        elif source_type == "point":
            at = _as_date(planned.get("at"))
            if at is None:
                raise ValueError("E_PRESENTATION_MARK_INPUT")
            result.append(ComparisonMark(source_id, "planned", source_type, at=at))
            actual_at = _as_date(actual.get("at"))
            if actual_at is not None:
                result.append(ComparisonMark(source_id, "actual", source_type, at=actual_at))
        else:
            raise ValueError("E_PRESENTATION_MARK_INPUT")
    return tuple(result)
