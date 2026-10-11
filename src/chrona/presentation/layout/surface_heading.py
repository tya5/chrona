"""Owns measured heading projection; reads closed sources, title slot and Theme typography."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.sources import MeasuredSources, MeasuredTextRun
from chrona.presentation.layout.surface_quality import CollisionDomain, SlotPlacement, SurfaceLayoutRequest, TextPlacement
from chrona.presentation.layout.text import measured_text_bounds, place_text


HEADING_PARTS = (("kicker", "kicker"), ("title", "heading"), ("subtitle", "subtitle"))


@dataclass(frozen=True)
class HeadingPlacementBatch:
    """Completed heading text and explicit notices for real unallocated copy."""

    text: tuple[TextPlacement, ...]
    diagnostics: tuple[str, ...] = ()


def place_surface_headings(request: SurfaceLayoutRequest,
                           slots: Mapping[str, SlotPlacement],
                           measured: MeasuredSources) -> HeadingPlacementBatch:
    """Compose either the existing whole heading or independently sourced parts.

    The profile's claim validation guarantees one owner per canonical text identity.
    No geometry or source selection is left for Scene to infer.
    """
    if "title" in slots:
        return HeadingPlacementBatch(place_heading(request, slots["title"], measured))
    text: list[TextPlacement] = []
    diagnostics: list[str] = []
    for part, role in HEADING_PARTS:
        source_id = f"heading.{part}"
        source = measured.inputs.get(source_id)
        runs = measured.run_measurements.get(source_id, ())
        if source is None or not source.text_runs():
            continue
        slot = slots.get(source_id)
        if slot is None:
            diagnostics.append(f"I_LAYOUT_HEADING_PART_OMITTED:{part}")
            continue
        if len(runs) != 1:
            raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED",
                              f"/measuredSources/runMeasurements/{source_id}",
                              "a heading part requires exactly one closed text run")
        run = runs[0]
        stack = measured.block_stacks.get(source_id)
        if stack is None or len(stack.baselines) != 1:
            raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED",
                              f"/measuredSources/blockStacks/{source_id}",
                              "a heading part requires one closed block baseline")
        baseline = float(slot.bounds.block + stack.baselines[0])
        text.append(TextPlacement(
            part, "title", run.content,
            measured_text_bounds(inline=float(slot.bounds.inline), baseline_block=baseline,
                                 width=float(run.inline_size), height=float(run.block_size),
                                 font_size=run.font_size, rotation=0), role,
            baseline=(float(slot.bounds.inline), baseline),
            lines=run.lines or (run.content,), overflow=run.overflow,
            font_family=run.font_family, font_weight=run.font_weight,
            font_size=run.font_size, line_height=run.line_height,
            letter_spacing=run.letter_spacing, text_transform=run.text_transform,
            numeric_spacing=run.numeric_spacing, horizontal_scale=run.horizontal_scale,
            font_asset_identity=run.font_asset_identity, collision_region=slot.slot_id,
            slot_id=slot.slot_id,
            collision_domain=CollisionDomain(slot.slot_id, "content"),
            source_content=source.text_runs()[0].content,
            available_inline_start=float(slot.bounds.inline),
            available_inline_size=float(slot.bounds.inline_size)))
    return HeadingPlacementBatch(tuple(text), tuple(diagnostics))


def place_heading(request: SurfaceLayoutRequest, slot: SlotPlacement, measured: MeasuredSources) -> tuple[TextPlacement, ...]:
    source = measured.inputs.get("title")
    measurement = measured.measurements.get("title")
    if measurement is None:
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources/measurements/title")

    def place(identifier: str, content: str, role: str, baseline: float,
              source_content: str | None = None, closed: MeasuredTextRun | None = None) -> TextPlacement:
        return place_text(
            placement_id=identifier, source_ref="title", content=content,
            inline=float(slot.bounds.inline), baseline_block=baseline,
            typography_role=role, theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
            collision_region="title", collision_domain=CollisionDomain("title", "content"),
            source_content=source_content if source_content is not None else content,
            lines=closed.lines or None if closed is not None else None,
            overflow=closed.overflow if closed is not None else "fit",
            available_inline_start=float(slot.bounds.inline),
            available_inline_size=float(slot.bounds.inline_size))

    if source is not None and source.run_flow == "block":
        stack = measured.block_stacks.get("title")
        runs = source.text_runs()
        measured_runs = measured.run_measurements.get("title", ())
        if (stack is None or len(stack.baselines) != len(runs) or len(measured_runs) != len(runs)
                or any(run.source_ref is None for run in runs)):
            raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources/blockStacks/title")
        return tuple(place(run.source_ref, closed.content, run.typography_role,
                           float(slot.bounds.block) + float(baseline), source_content=run.content, closed=closed)
                     for run, closed, baseline in zip(runs, measured_runs, stack.baselines))

    # No kicker: retain the existing title/deck measurement and equations.
    title = source.lines[0] if source and source.lines else ""
    runs = measured.run_measurements.get("title", ())
    # The selected title slot may have been measured with a caption reservation.
    # Its run measurements remain the native title geometry; use those here so
    # passing the reduced content viewport does not apply the caption offset twice.
    baseline = (float(slot.bounds.block) + float(runs[0].baseline) if runs
                else float(slot.bounds.block) + float(measurement.first_baseline or 0))
    text = [place("title", runs[0].content if runs and runs[0].lines else title, "heading", baseline,
                  source_content=title, closed=runs[0] if runs else None)]
    if source is not None and len(source.lines) > 1 and len(runs) > 1:
        text.append(place("subtitle", runs[1].content if runs[1].lines else source.lines[1], runs[1].typography_role, max(
            float(slot.bounds.block) + float(runs[0].block_size) + float(runs[1].baseline),
            float(text[0].bounds.block + text[0].bounds.block_size) + runs[1].font_size),
            source_content=source.lines[1], closed=runs[1]))
    return tuple(text)
