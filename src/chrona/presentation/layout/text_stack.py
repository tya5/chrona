"""Close an ordered text block's baselines and actual placement envelope."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from chrona.presentation.layout.sources import MeasuredTextRun


@dataclass(frozen=True)
class MeasuredTextStack:
    baselines: tuple[Decimal, ...]
    block_size: Decimal


def measure_text_stack(runs: Sequence[MeasuredTextRun], gaps: Sequence[Decimal]) -> MeasuredTextStack:
    """Measure the same baseline-minus-font-size boxes that place_text completes.

    Gaps are minimum box separation after each run, not a replacement for
    the role's line pitch. A negative first box top shifts the whole block.
    """
    if len(gaps) != len(runs):
        raise ValueError("text stack requires one following gap per run")
    baselines: list[Decimal] = []
    line_start = Decimal(0)
    minimum_top = Decimal(0)
    maximum_bottom = Decimal(0)
    previous_bottom = Decimal(0)
    for index, run in enumerate(runs):
        size = Decimal(str(run.font_size))
        baseline = line_start + run.baseline
        if index:
            baseline = max(baseline, previous_bottom + gaps[index - 1] + size)
        top = baseline - size
        previous_bottom = top + run.block_size
        minimum_top = min(minimum_top, top)
        maximum_bottom = max(maximum_bottom, previous_bottom)
        baselines.append(baseline)
        line_start += run.block_size + gaps[index]
    shift = -minimum_top
    return MeasuredTextStack(tuple(value + shift for value in baselines), maximum_bottom + shift)
