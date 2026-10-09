"""Renderer-neutral comparison-mark semantics consumed by surface layout."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Mapping


def _brief(value: object) -> str:
    if isinstance(value, str):
        clipped = value[:64]
        return repr(clipped + ("…" if len(value) > len(clipped) else ""))
    if value is None or isinstance(value, (bool, int, float, date)):
        return repr(value)
    return f"<{type(value).__name__}>"


@dataclass(frozen=True)
class ComparisonMark:
    """One immutable semantic mark; Layout assigns its geometry."""

    source_id: str
    facet: str
    source_type: str
    start: date | None = None
    end: date | None = None
    at: date | None = None
    variance_days: int | None = None


def _as_date(value: object) -> date | None:
    return value if isinstance(value, date) else None


def comparison_marks(items: Iterable[object], *, comparison_mode: str,
                     show_zero: bool = True) -> tuple[ComparisonMark, ...]:
    """Project only observed facets; never infer an actual endpoint from plan data."""
    if comparison_mode not in {"stacked", "overlaid", "baseline-and-actual"}:
        raise ValueError(f"E_PRESENTATION_COMPARISON_MODE: comparison_mode={_brief(comparison_mode)}; expected stacked, overlaid, or baseline-and-actual")
    result: list[ComparisonMark] = []
    for item in items:
        source_id = str(getattr(item, "object_id"))
        source_type = str(getattr(item, "source_type"))
        planned = getattr(item, "planned")
        actual = getattr(item, "actual") or {}
        if not isinstance(planned, Mapping) or not isinstance(actual, Mapping):
            raise ValueError(f"E_PRESENTATION_MARK_INPUT: object_id={_brief(source_id)} planned/actual must be mappings; received planned={type(planned).__name__}, actual={type(actual).__name__}")
        if source_type == "span":
            start, end = _as_date(planned.get("start")), _as_date(planned.get("end"))
            if start is None or end is None or end <= start:
                raise ValueError(f"E_PRESENTATION_MARK_INPUT: span object_id={_brief(source_id)} requires planned.start and planned.end dates with end>start; start={_brief(start)}, end={_brief(end)}")
            facet = "baseline" if comparison_mode == "baseline-and-actual" else "planned"
            result.append(ComparisonMark(source_id, facet, source_type, start=start, end=end))
            actual_start, actual_finish = _as_date(actual.get("start")), _as_date(actual.get("finish"))
            if actual_start is not None and actual_finish is not None:
                if actual_finish <= actual_start:
                    raise ValueError(f"E_PRESENTATION_MARK_INPUT: span object_id={_brief(source_id)} actual.finish={_brief(actual_finish)} must follow actual.start={_brief(actual_start)}")
                delta = (actual_finish - end).days
                result.append(ComparisonMark(source_id, "actual", source_type, start=actual_start, end=actual_finish))
                if show_zero or delta != 0:
                    result.append(ComparisonMark(source_id, "finish-delta", source_type, at=actual_finish, variance_days=delta))
        elif source_type == "point":
            at = _as_date(planned.get("at"))
            if at is None:
                raise ValueError(f"E_PRESENTATION_MARK_INPUT: point object_id={_brief(source_id)} requires planned.at date; received {_brief(planned.get('at'))}")
            result.append(ComparisonMark(source_id, "planned", source_type, at=at))
            actual_at = _as_date(actual.get("at"))
            if actual_at is not None:
                result.append(ComparisonMark(source_id, "actual", source_type, at=actual_at))
        else:
            raise ValueError(f"E_PRESENTATION_MARK_INPUT: object_id={_brief(source_id)} source_type={_brief(source_type)}; expected span or point")
    return tuple(result)
