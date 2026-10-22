"""Typed intrinsic source-use facts emitted by completed Layout producers."""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Literal

from chrona.presentation.layout.model import Measurement
from chrona.presentation.layout.sources import (
    CompletedSourceMeasurement, MeasuredLegend, MeasuredTextRun, SourceInput, SourceTextRun,
)
from chrona.presentation.layout.surface_quality import TextPlacement, TextRunPlacement
from chrona.presentation.model.surface_content import SurfaceLegendEntry


def _run_finite_state(run: TextRunPlacement) -> tuple[object, ...]:
    """Keep selected fallback face and text partition, not measured advance."""
    return (run.text, run.font_size, run.family, run.weight, run.asset_identity)


def _legend_entry_finite_state(entry: SurfaceLegendEntry) -> SurfaceLegendEntry:
    """Normalize only geometry/diagnostic numbers derived from selected legend ink."""
    key = entry.realized_key
    if key is not None and key.glyph is not None:
        key = replace(key, glyph=replace(key.glyph, footprint=(0.0, 0.0)))
    collisions = tuple(replace(item, delta_e=0.0) for item in entry.scale_collisions)
    return replace(entry, realized_key=key, scale_collisions=collisions)


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
    geometry_witness: tuple[object, ...] = ()

    def finite_state(self) -> tuple[object, ...]:
        # Allocations and completed extents are dependent numeric results,
        # not new finite states. Keep them in exact dataclass equality only.
        return (self.consumer_id, self.disposition, self.treatment,
                tuple((item.placement_id, item.measurement.content,
                       item.measurement.typography_role, item.measurement.lines,
                       item.measurement.font_family, item.measurement.font_weight,
                       item.measurement.font_size, item.measurement.line_height,
                       item.measurement.font_asset_identity,
                       item.measurement.letter_spacing, item.measurement.text_transform,
                       item.measurement.numeric_spacing, item.measurement.horizontal_scale,
                       tuple(tuple(_run_finite_state(run) for run in line)
                             for line in item.measurement.fallback_runs)) for item in self.text))


@dataclass(frozen=True)
class CompletedSourceUse:
    """The actual legend selection and annotations-source consumers of a trial."""

    legend_entries: tuple[SurfaceLegendEntry, ...] = ()
    legend_layout: MeasuredLegend | None = None
    annotations: tuple[SourceConsumer, ...] = ()

    def finite_state(self) -> tuple[object, ...]:
        legend = self.legend_layout
        return (tuple(_legend_entry_finite_state(entry) for entry in self.legend_entries),
                (tuple((entry.source_text, entry.lines, entry.painted_lines,
                        entry.segment_lines,
                        tuple(tuple(_run_finite_state(run) for run in line)
                              for line in entry.segment_runs)) for entry in legend.entries)
                 if legend is not None else None),
                tuple(item.finite_state() for item in self.annotations))

    def annotation_input(self) -> SourceInput:
        if not self.annotations:
            return SourceInput(content_present=False)
        width = max(item.inline_size for item in self.annotations)
        height = sum((item.block_size for item in self.annotations), Decimal(0))
        # A record's fit against an earlier allocation is an outcome, not
        # intrinsic text demand. Its shown text/lines/font measurements remain
        # exact; the final composition retains its own overflow diagnostic.
        runs = tuple(replace(text.measurement, overflow="fit")
                     for item in self.annotations for text in item.text)
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
