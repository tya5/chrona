"""Compare a completed canvas with its independently declared viewport."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_geometry import GEOMETRY_TOLERANCE


@dataclass(frozen=True)
class DeclaredViewport:
    """The positive, zero-origin inline and optional block declaration."""

    inline_size: Decimal
    block_size: Decimal | None

    def __post_init__(self) -> None:
        _require_positive_decimal(self.inline_size, "inline_size")
        if self.block_size is not None:
            _require_positive_decimal(self.block_size, "block_size")


@dataclass(frozen=True)
class ViewportOverrun:
    """Positive amount beyond each declared edge; zero means no overrun."""

    inline_start: Decimal = Decimal(0)
    inline_end: Decimal = Decimal(0)
    block_start: Decimal = Decimal(0)
    block_end: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        for name in ("inline_start", "inline_end", "block_start", "block_end"):
            value = getattr(self, name)
            if not _is_finite_decimal(value) or value < 0:
                raise ValueError(f"E_LAYOUT_VIEWPORT_FACT_INVALID: {name}={value!r}; expected finite non-negative Decimal")


@dataclass(frozen=True)
class CanvasContributor:
    """Union bounds and edge excess attributed to one native Layout slot."""

    slot_id: str
    bounds: Rect
    overrun: ViewportOverrun

    def __post_init__(self) -> None:
        if not isinstance(self.slot_id, str) or not self.slot_id:
            raise ValueError("E_LAYOUT_VIEWPORT_FACT_INVALID: slot_id must be a non-empty string")
        if not isinstance(self.bounds, Rect) or not isinstance(self.overrun, ViewportOverrun):
            raise ValueError("E_LAYOUT_VIEWPORT_FACT_INVALID: contributor requires Rect bounds and ViewportOverrun")
        _validate_rect(self.bounds, "contributor.bounds")


@dataclass(frozen=True)
class CanvasViewportWarning:
    """Immutable evidence that completed canvas bounds exceed a declaration."""

    surface_id: str
    declared: DeclaredViewport
    actual: Rect
    contributors: tuple[CanvasContributor, ...]
    contributor_count: int

    code = "W_LAYOUT_CANVAS_EXCEEDS_VIEWPORT"
    source_ref = "/body/environment/viewport"

    def __post_init__(self) -> None:
        if not isinstance(self.surface_id, str) or not self.surface_id:
            raise ValueError("E_LAYOUT_VIEWPORT_FACT_INVALID: surface_id must be a non-empty string")
        if not isinstance(self.declared, DeclaredViewport):
            raise ValueError("E_LAYOUT_VIEWPORT_FACT_INVALID: declared must be DeclaredViewport")
        _validate_rect(self.actual, "actual")
        if (not isinstance(self.contributors, tuple)
                or any(not isinstance(item, CanvasContributor) for item in self.contributors)
                or len(self.contributors) > 5
                or isinstance(self.contributor_count, bool)
                or not isinstance(self.contributor_count, int)
                or self.contributor_count < len(self.contributors)):
            raise ValueError("E_LAYOUT_VIEWPORT_FACT_INVALID: contributors must contain up to five records and a sufficient count")


def canvas_viewport_warning(
    *,
    surface_id: str,
    declared: DeclaredViewport | None,
    actual: Rect,
    contributors: Iterable[tuple[str, Rect]],
) -> CanvasViewportWarning | None:
    """Return deterministic overflow evidence without changing completed geometry.

    Contributors are first unioned by their native slot identity. The canvas
    itself and any canvas-derived treatments must not be supplied here.
    """
    _validate_rect(actual, "actual")
    if declared is None:
        return None
    if not isinstance(declared, DeclaredViewport):
        raise ValueError("E_LAYOUT_VIEWPORT_FACT_INVALID: declared must be DeclaredViewport or None")
    if not isinstance(surface_id, str) or not surface_id:
        raise ValueError("E_LAYOUT_VIEWPORT_FACT_INVALID: surface_id must be a non-empty string")

    actual_overrun = _overrun(actual, declared)
    if not _has_overrun(actual_overrun):
        return None

    grouped: dict[str, list[Rect]] = defaultdict(list)
    for index, value in enumerate(contributors):
        if (not isinstance(value, tuple) or len(value) != 2
                or not isinstance(value[0], str) or not value[0]
                or not isinstance(value[1], Rect)):
            raise ValueError(f"E_LAYOUT_VIEWPORT_FACT_INVALID: contributors[{index}] must be (non-empty slot id, Rect)")
        _validate_rect(value[1], f"contributors[{index}].bounds")
        grouped[value[0]].append(value[1])

    attributed: list[CanvasContributor] = []
    for slot_id, rects in grouped.items():
        bounds = _union(rects)
        overrun = _overrun(bounds, declared)
        if _has_overrun(overrun):
            attributed.append(CanvasContributor(slot_id, bounds, overrun))

    attributed.sort(key=lambda item: (-_maximum_overrun(item.overrun), item.slot_id))
    return CanvasViewportWarning(
        surface_id=surface_id,
        declared=declared,
        actual=actual,
        contributors=tuple(attributed[:5]),
        contributor_count=len(attributed),
    )


def _overrun(bounds: Rect, declared: DeclaredViewport) -> ViewportOverrun:
    inline_end = bounds.inline + bounds.inline_size
    block_end = bounds.block + bounds.block_size
    return ViewportOverrun(
        inline_start=max(Decimal(0), -bounds.inline)
        if bounds.inline < -GEOMETRY_TOLERANCE else Decimal(0),
        inline_end=max(Decimal(0), inline_end - declared.inline_size)
        if inline_end > declared.inline_size + GEOMETRY_TOLERANCE else Decimal(0),
        block_start=(max(Decimal(0), -bounds.block)
                     if declared.block_size is not None and bounds.block < -GEOMETRY_TOLERANCE else Decimal(0)),
        block_end=(max(Decimal(0), block_end - declared.block_size)
                   if declared.block_size is not None
                   and block_end > declared.block_size + GEOMETRY_TOLERANCE else Decimal(0)),
    )


def _has_overrun(value: ViewportOverrun) -> bool:
    return any(getattr(value, name) > 0 for name in ("inline_start", "inline_end", "block_start", "block_end"))


def _maximum_overrun(value: ViewportOverrun) -> Decimal:
    return max(value.inline_start, value.inline_end, value.block_start, value.block_end)


def _union(rects: list[Rect]) -> Rect:
    inline_start = min(item.inline for item in rects)
    block_start = min(item.block for item in rects)
    inline_end = max(item.inline + item.inline_size for item in rects)
    block_end = max(item.block + item.block_size for item in rects)
    return Rect(inline_start, block_start, inline_end - inline_start, block_end - block_start)


def _validate_rect(value: object, name: str) -> None:
    if not isinstance(value, Rect):
        raise ValueError(f"E_LAYOUT_VIEWPORT_FACT_INVALID: {name} must be Rect")
    for field_name in ("inline", "block", "inline_size", "block_size"):
        number = getattr(value, field_name)
        if not _is_finite_decimal(number):
            raise ValueError(f"E_LAYOUT_VIEWPORT_FACT_INVALID: {name}.{field_name}={number!r}; expected finite Decimal")
    if value.inline_size < 0 or value.block_size < 0:
        raise ValueError(f"E_LAYOUT_VIEWPORT_FACT_INVALID: {name} has negative extent")


def _require_positive_decimal(value: object, name: str) -> None:
    if not _is_finite_decimal(value) or value <= 0:
        raise ValueError(f"E_LAYOUT_VIEWPORT_DECLARATION_INVALID: {name}={value!r}; expected positive finite Decimal")


def _is_finite_decimal(value: object) -> bool:
    return isinstance(value, Decimal) and value.is_finite()
