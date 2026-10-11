"""Shared renderer-neutral minimum/maximum/fractional track allocation."""
from __future__ import annotations

from decimal import Decimal


ZERO = Decimal(0)


def resolve_flexible_tracks(bases: list[tuple[Decimal, Decimal | None, Decimal]],
                            available: Decimal) -> list[Decimal]:
    """Freeze binding bounds and redistribute space, preserving mandatory floors.

    When lower and upper violations coexist, the clamped total identifies the
    direction of the feasible fr unit. Freeze only bounds that stay binding in
    that direction; freezing both prematurely can oversubscribe or lose space.
    An infeasible sum of minima is retained for the caller's typed disposition.
    """
    sizes: list[Decimal | None] = [None] * len(bases)
    flexible = [index for index, (_, _, weight) in enumerate(bases) if weight > ZERO]
    for index, (minimum, target, weight) in enumerate(bases):
        if weight == ZERO:
            sizes[index] = target if target is not None else minimum
    non_flex_total = sum((size for size in sizes if size is not None), ZERO)
    leftover = available - non_flex_total
    while flexible:
        total_weight = sum((bases[index][2] for index in flexible), ZERO)
        fr = leftover / total_weight if leftover > ZERO else ZERO
        violators = [index for index in flexible if bases[index][0] > fr * bases[index][2]]
        clamped = [index for index in flexible
                   if bases[index][1] is not None and bases[index][1] < fr * bases[index][2]]
        if violators and clamped:
            bounded = {index: max(bases[index][0], min(fr * bases[index][2], bases[index][1]))
                       if bases[index][1] is not None else max(bases[index][0], fr * bases[index][2])
                       for index in flexible}
            bounded_total = sum(bounded.values(), ZERO)
            if bounded_total == leftover:
                for index, size in bounded.items():
                    sizes[index] = size
                break
            if bounded_total < leftover:
                violators = []
        if violators:
            for index in violators:
                sizes[index] = bases[index][0]
                leftover -= bases[index][0]
            flexible = [index for index in flexible if index not in violators]
            continue
        if clamped:
            for index in clamped:
                sizes[index] = bases[index][1]
                leftover -= bases[index][1]
            flexible = [index for index in flexible if index not in clamped]
            continue
        for index in flexible:
            sizes[index] = fr * bases[index][2]
        break
    return sizes  # type: ignore[return-value]
