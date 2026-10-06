"""Pure, grouped summary measurement; Scene never arranges summary runs."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping, TYPE_CHECKING

from chrona.presentation.model.surface_content import SummaryContent

if TYPE_CHECKING:
    from chrona.presentation.layout.sources import MeasuredTextRun


@dataclass(frozen=True)
class MeasuredSummaryRun:
    placement_id: str
    inline: Decimal
    baseline: Decimal


@dataclass(frozen=True)
class MeasuredSummary:
    runs: tuple[MeasuredSummaryRun, ...]
    inline_size: Decimal
    block_size: Decimal


def measure_summary(content: SummaryContent, runs: Mapping[str, MeasuredTextRun],
                    gaps: Mapping[str, Decimal]) -> MeasuredSummary:
    """Close ordered panel origins and baselines using already measured runs."""
    placed: list[MeasuredSummaryRun] = []
    block, width = Decimal(0), Decimal(0)
    for panel in content.panels:
        measured = tuple(runs[run.placement_id] for run in panel.runs)
        if panel.arrangement == "inline":
            baseline = max((max(run.baseline, Decimal(str(run.font_size)))
                            for run in measured), default=Decimal(0))
            inline, height = Decimal(0), Decimal(0)
            for index, (source, run) in enumerate(zip(panel.runs, measured)):
                placed.append(MeasuredSummaryRun(source.placement_id, inline, block + baseline))
                height = max(height, baseline - Decimal(str(run.font_size)) + run.block_size)
                inline += run.inline_size
                if index + 1 < len(measured):
                    inline += gaps[source.typography_role]
            width = max(width, inline)
            block += height
        else:
            # A mixed panel source retains the existing stack line pitch.
            for source, run in zip(panel.runs, measured):
                placed.append(MeasuredSummaryRun(source.placement_id, Decimal(0),
                                                  block + Decimal(str(run.font_size))))
                width = max(width, run.inline_size)
                block += run.block_size
    return MeasuredSummary(tuple(placed), width, block)
