"""Typed intrinsic source-use facts emitted by completed Layout producers."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from chrona.presentation.layout.model import Measurement
from chrona.presentation.layout.sources import (
    CompletedSourceMeasurement, MeasuredLegend, MeasuredTextRun, SourceInput, SourceTextRun,
)
from chrona.presentation.layout.surface_quality import TextPlacement
from chrona.presentation.model.surface_content import SurfaceLegendEntry


@dataclass(frozen=True)
class SourceTextUse:
    """Shown text and measurement identity, independent of its anchor position."""

    placement_id: str
    measurement: MeasuredTextRun
    available_inline: Decimal | None = None

    @classmethod
    def from_placement(cls, text: TextPlacement, *, available_inline: Decimal | None = None
                       ) -> SourceTextUse:
        return cls(text.placement_id, MeasuredTextRun(
            source_ref=text.source_ref, content=text.content,
            typography_role=text.typography_role,
            inline_size=text.bounds.inline_size, block_size=text.bounds.block_size,
            baseline=Decimal(str(text.font_size)),
            font_family=text.font_family, font_weight=text.font_weight,
            font_size=text.font_size, line_height=text.line_height,
            font_asset_identity=text.font_asset_identity,
            letter_spacing=text.letter_spacing, text_transform=text.text_transform,
            numeric_spacing=text.numeric_spacing, horizontal_scale=text.horizontal_scale,
            lines=text.lines, overflow=text.overflow, fallback_runs=text.runs),
            available_inline if available_inline is not None else
            Decimal(str(text.available_inline_size)) if text.available_inline_size is not None else None)


@dataclass(frozen=True)
class SourceConsumer:
    """One actual in-flow record, not a possible destination or narrative receipt."""

    consumer_id: str
    disposition: Literal["card", "list", "status", "summary"]
    inline_size: Decimal
    block_size: Decimal
    text: tuple[SourceTextUse, ...]
    treatment: tuple[object, ...] = ()

    def finite_state(self) -> tuple[object, ...]:
        # Block extent is the dependent numeric result, not a new finite
        # content state. Repeated content with drifting height must fail.
        return (self.consumer_id, self.disposition, self.treatment,
                tuple((item.placement_id, item.measurement.content,
                       item.measurement.typography_role, item.measurement.lines,
                       item.measurement.font_family, item.measurement.font_weight,
                       item.measurement.font_size, item.measurement.line_height,
                       item.measurement.font_asset_identity,
                       item.measurement.letter_spacing, item.measurement.text_transform,
                       item.measurement.numeric_spacing, item.measurement.horizontal_scale,
                       item.measurement.fallback_runs, item.available_inline) for item in self.text),
                self.inline_size)


@dataclass(frozen=True)
class CompletedSourceUse:
    """The actual legend selection and annotations-source consumers of a trial."""

    legend_entries: tuple[SurfaceLegendEntry, ...] = ()
    legend_layout: MeasuredLegend | None = None
    annotations: tuple[SourceConsumer, ...] = ()

    def finite_state(self) -> tuple[object, ...]:
        legend = self.legend_layout
        return (self.legend_entries,
                ((legend.available_inline, legend.slot_inline_size,
                  tuple((entry.source_text, entry.lines, entry.painted_lines,
                         entry.segment_lines, entry.segment_runs,
                         entry.label_available_inline) for entry in legend.entries))
                 if legend is not None else None),
                tuple(item.finite_state() for item in self.annotations))

    def annotation_input(self) -> SourceInput:
        if not self.annotations:
            return SourceInput(content_present=False)
        width = max(item.inline_size for item in self.annotations)
        height = sum((item.block_size for item in self.annotations), Decimal(0))
        runs = tuple(text.measurement for item in self.annotations for text in item.text)
        return SourceInput(
            typography_role="annotation", content_present=True,
            runs=tuple(SourceTextRun(run.content, run.typography_role, run.source_ref)
                       for run in runs),
            completed=CompletedSourceMeasurement(
                Measurement(width, width, width, height, height, height), runs))


class SourceDestinationActivation(Exception):
    """A selected candidate needs a declared source pruned by a prior trial."""

    def __init__(self, source: str, consumer_id: str, candidate_id: str):
        self.source, self.consumer_id, self.candidate_id = source, consumer_id, candidate_id
        super().__init__(f"{source}:{consumer_id}:{candidate_id}")
