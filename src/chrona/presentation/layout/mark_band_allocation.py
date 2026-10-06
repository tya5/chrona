"""Complete track-local comparison bands without changing temporal facts."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import TYPE_CHECKING, Mapping

from chrona.presentation.layout.model import LayoutError, geometry_sum
from chrona.presentation.layout.presentation import MarkGeometry

if TYPE_CHECKING:
    from chrona.presentation.model.theme_tokens import MarkStackIntent


@dataclass(frozen=True)
class RoleBandBounds:
    role: str
    block: float
    block_size: float


@dataclass(frozen=True)
class MarkStackSlot:
    roles: tuple[str, ...]
    block: float
    block_size: float


@dataclass(frozen=True)
class MarkBandAllocation:
    """Immutable completed bounds; signed starts permit visible overflow."""

    track_size: float
    spans: tuple[RoleBandBounds, ...]
    symbols: tuple[RoleBandBounds, ...]
    slots: tuple[MarkStackSlot, ...] = ()
    frames: tuple[RoleBandBounds, ...] = ()
    outer_bounds: tuple[float, float] = (0.0, 0.0)
    diagnostics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (isinstance(self.track_size, bool) or not isfinite(self.track_size) or self.track_size <= 0
                or any(not isfinite(value) for value in self.outer_bounds)
                or self.outer_bounds[1] < self.outer_bounds[0]
                or any(not item.role or not isfinite(item.block)
                       or not isfinite(item.block_size) or item.block_size <= 0
                       for item in (*self.spans, *self.symbols, *self.frames))
                or len({item.role for item in self.spans}) != len(self.spans)
                or len({item.role for item in self.symbols}) != len(self.symbols)):
            raise LayoutError("E_LAYOUT_MARK_OVERFLOW", "/layout/markBandAllocation",
                              detail="invalid completed band bounds; require finite positive extents and unique roles")
        if (any(not slot.roles or not isfinite(slot.block) or not isfinite(slot.block_size)
                or slot.block_size <= 0 for slot in self.slots)
                or any(item.block < self.outer_bounds[0] - 1e-9
                       or item.block + item.block_size > self.outer_bounds[1] + 1e-9
                       for item in (*self.spans, *self.symbols))):
            raise LayoutError("E_LAYOUT_MARK_OVERFLOW", "/layout/markBandAllocation/outerBounds",
                              detail="completed outer bounds must contain all span/symbol extents and valid stack slots")

    def span_bounds(self, role: str) -> tuple[float, float]:
        item = next(item for item in self.spans if item.role == role)
        return item.block, item.block_size

    def symbol_bounds(self, role: str) -> tuple[float, float]:
        item = next(item for item in self.symbols if item.role == role)
        return item.block, item.block_size

    @property
    def outer_extent(self) -> float:
        return self.outer_bounds[1] - self.outer_bounds[0]


def compose_mark_band(*, track_size: float, role_geometries: Mapping[str, MarkGeometry],
                      stack: MarkStackIntent | None = None) -> MarkBandAllocation:
    """Close one nominal track once, independently of observed facet presence."""
    if isinstance(track_size, bool) or not isfinite(track_size) or track_size <= 0:
        raise LayoutError("E_LAYOUT_MARK_OVERFLOW", "/layout/markBandAllocation/trackSize",
                          detail=f"trackSize={track_size}; require a finite positive resolved track size")
    spans = {role: RoleBandBounds(role, track_size * geometry.offset, track_size * geometry.height)
             for role, geometry in role_geometries.items()}
    symbols = tuple(RoleBandBounds(role, track_size * geometry.symbol_extent[0],
                                  track_size * geometry.symbol_extent[1])
                    for role, geometry in role_geometries.items())
    slots: list[MarkStackSlot] = []
    frames: list[RoleBandBounds] = []
    if stack is not None:
        gap, padding = float(stack.gap), float(stack.frame_padding)
        heights = tuple(max(spans[role].block_size for role in members) for members in stack.members)
        stack_extent = geometry_sum(heights) + gap * (len(heights) - 1)
        start = (track_size - stack_extent) / 2
        cursor = start
        for members, height in zip(stack.members, heights, strict=True):
            slots.append(MarkStackSlot(members, cursor, height))
            for role in members:
                size = spans[role].block_size
                spans[role] = RoleBandBounds(role, cursor + (height - size) / 2, size)
            cursor += height + gap
        for role in stack.frame_roles:
            bounds = RoleBandBounds(role, start - padding, stack_extent + 2 * padding)
            frames.append(bounds)
            spans[role] = bounds
    outer_start = min(0.0, *(item.block for item in spans.values()))
    outer_end = max(track_size, *(item.block + item.block_size for item in spans.values()))
    diagnostics = ()
    if stack is not None and outer_end - outer_start > track_size + 1e-9:
        diagnostics = (f"W_LAYOUT_MARK_STACK_OVERFLOW:extent={outer_end - outer_start:g}; track={track_size:g}",)
    return MarkBandAllocation(track_size, tuple(spans.values()), symbols, tuple(slots), tuple(frames),
                              (outer_start, outer_end), diagnostics)
