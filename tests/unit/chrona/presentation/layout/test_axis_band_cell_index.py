"""Indexed axis-band host lookup preserves native exhaustive semantics."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from chrona.presentation.axis_intervals import AxisInterval
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_axis import AxisBandCellGeometry, AxisBandCellIndex


def _interval(index: int, *, start: int | None = None) -> AxisInterval:
    day = start if start is not None else index + 1
    first = date(2026, 1, 1) + timedelta(days=day - 1)
    last = first + timedelta(days=1)
    return AxisInterval(first, last, "day", str(index), index, first, last)


def _cell(tier: int, index: int, x: float, *, width: float = 10, y: float = 0,
          height: float = 10, paint: int = 1, interval: AxisInterval | None = None) -> AxisBandCellGeometry:
    return AxisBandCellGeometry(
        tier, interval or _interval(index), f"cell:{tier}:{index}",
        Rect(Decimal(str(x)), Decimal(str(y)), Decimal(str(width)), Decimal(str(height))), paint,
    )


def _exhaustive(bounds: Rect, cells: tuple[AxisBandCellGeometry, ...]) -> AxisBandCellGeometry | None:
    inline = bounds.inline + bounds.inline_size / 2
    block = bounds.block + bounds.block_size / 2
    candidates = [
        (cell.paint_order, order, cell)
        for order, cell in enumerate(cells)
        if cell.bounds.inline <= inline <= cell.bounds.inline + cell.bounds.inline_size
        and cell.bounds.block <= block <= cell.bounds.block + cell.bounds.block_size
    ]
    return max(candidates, key=lambda item: item[:2])[2] if candidates else None


@pytest.mark.parametrize(
    ("bounds", "expected"),
    [
        (Rect(Decimal("2"), Decimal("2"), Decimal("2"), Decimal("2")), "0"),  # interior
        (Rect(Decimal("8"), Decimal("2"), Decimal("0"), Decimal("2")), "0"),  # shared edge
        (Rect(Decimal("10"), Decimal("2"), Decimal("2"), Decimal("2")), None),  # gap
        (Rect(Decimal("-4"), Decimal("2"), Decimal("2"), Decimal("2")), None),  # before
        (Rect(Decimal("24"), Decimal("2"), Decimal("2"), Decimal("2")), None),  # after
        (Rect(Decimal("2"), Decimal("20"), Decimal("2"), Decimal("2")), None),  # wrong lane
    ],
)
def test_index_matches_exhaustive_host_at_interiors_edges_gaps_and_outside(bounds, expected):
    cells = (_cell(0, 0, 0, width=8), _cell(0, 1, 12, width=8))
    by_id = {cell.placement_id.rsplit(":", 1)[1]: cell for cell in cells}

    actual = AxisBandCellIndex.build(cells).host(bounds)

    assert actual == _exhaustive(bounds, cells)
    assert actual == (by_id[expected] if expected else None)


def test_index_matches_global_paint_order_for_overlapping_tiers_and_repeated_interval_key():
    shared = _interval(0)
    cells = (
        _cell(2, 0, 0, y=0, paint=9, interval=shared),
        _cell(0, 0, 0, y=0, paint=3, interval=shared),
        _cell(1, 0, 0, y=0, paint=9, interval=shared),
    )
    center = Rect(Decimal("4"), Decimal("4"), Decimal("2"), Decimal("2"))
    index = AxisBandCellIndex.build(cells)

    assert index.host(center) is cells[2]
    assert index.host(center) == _exhaustive(center, cells)
    assert index.by_interval[(shared.level, shared.start, shared.end)] is cells[2]


class _CountedBounds:
    """Rect-like bounds counting reads after index construction."""

    def __init__(self, x: int, y: int = 0):
        self._rect = Rect(Decimal(x), Decimal(y), Decimal(1), Decimal(10))
        self.reads = 0

    @property
    def inline(self):
        self.reads += 1
        return self._rect.inline

    @property
    def block(self):
        self.reads += 1
        return self._rect.block

    @property
    def inline_size(self):
        self.reads += 1
        return self._rect.inline_size

    @property
    def block_size(self):
        self.reads += 1
        return self._rect.block_size


def test_host_lookup_reads_only_adjacent_candidates_in_a_thousand_cell_tier():
    bounds = tuple(_CountedBounds(x) for x in range(1000))
    cells = tuple(
        AxisBandCellGeometry(0, _interval(index), f"cell:{index}", cell_bounds, 1)
        for index, cell_bounds in enumerate(bounds)
    )
    index = AxisBandCellIndex.build(cells)
    for item in bounds:
        item.reads = 0

    result = index.host(Rect(Decimal("500.25"), Decimal("2"), Decimal("0.5"), Decimal("2")))

    assert result is cells[500]
    assert sum(item.reads for item in bounds) <= 12
