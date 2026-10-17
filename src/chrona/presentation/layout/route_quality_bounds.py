"""Conservative completed-route quality proofs, independent of candidate history."""
from __future__ import annotations

from chrona.presentation.layout.obstacles import ObstacleRect


def rectangular_detour_lower_bound(
    start: tuple[float, float], end: tuple[float, float],
    barriers: tuple[ObstacleRect, ...],
) -> float:
    """Bound Manhattan length around certified required interiors.

    The caller certifies that every completed hard-safe path avoids these
    interiors, after all host exemptions and path transformations. Search
    envelopes alone cannot establish that promise. Each separating rectangle
    requires a side excursion; rectangles can share excursions, so take max,
    never sum. Shrinking the proof rectangles makes boundary/float tolerance
    conservative without relaxing the actual collision policy.
    """
    sx, sy = start
    tx, ty = end
    dx, dy = abs(tx - sx), abs(ty - sy)
    direct = dx + dy
    lower = direct
    # Completed terminal/clearance checks already allow this geometric margin.
    margin = 1e-6
    for rect in barriers:
        left, top = rect.left + margin, rect.top + margin
        right, bottom = rect.right - margin, rect.bottom - margin
        if left >= right or top >= bottom:
            continue
        if (min(sy, ty) < top < bottom < max(sy, ty)
                and left < sx < right and left < tx < right):
            lower = max(lower, dy + min(abs(sx - left) + abs(tx - left),
                                        abs(sx - right) + abs(tx - right)))
        if (min(sx, tx) < left < right < max(sx, tx)
                and top < sy < bottom and top < ty < bottom):
            lower = max(lower, dx + min(abs(sy - top) + abs(ty - top),
                                        abs(sy - bottom) + abs(ty - bottom)))
    return max(direct, lower - margin)
