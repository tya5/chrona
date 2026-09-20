"""Common presentation Scene composed before any SVG adapter is invoked."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from .presentation_axis import AxisInterval, axis_intervals
from .presentation_marks import ComparisonMark, comparison_marks


@dataclass(frozen=True)
class PresentationScene:
    title: str
    window: tuple[date, date]
    axes: tuple[AxisInterval, ...]
    ticks: tuple[AxisInterval, ...]
    marks: tuple[ComparisonMark, ...]


def build_presentation_scene(title: str, items: Iterable[object], window: tuple[date, date], settings: dict) -> PresentationScene:
    """Build shared temporal primitives; adapters may only assign coordinates and emit output."""
    start, end = window
    axis = settings["layout"]["axis"]
    levels, heights = axis["levels"], axis["bandHeights"]
    order = {"quarter": 0, "month": 1, "week": 2, "day": 3}
    if len(levels) != len(heights) or len(set(levels)) != len(levels) or any(level not in order for level in levels) or levels != sorted(levels, key=order.__getitem__):
        raise ValueError("E_PRESENTATION_AXIS_INVALID")
    copied_items = tuple(items)
    axes = tuple(interval for level in levels for interval in axis_intervals(start, end, level))
    ticks = axis_intervals(start, end, axis["tickUnit"], tick_step=axis["tickStep"])
    marks = comparison_marks(copied_items, comparison_mode=settings["layout"]["bars"].get("comparisonMode", "stacked"), show_zero=settings["layout"]["variance"]["showZero"])
    return PresentationScene(str(title), (start, end), axes, ticks, marks)
