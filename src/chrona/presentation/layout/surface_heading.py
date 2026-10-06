"""Project measured heading runs into completed title-slot placements."""
from __future__ import annotations

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.sources import MeasuredSources
from chrona.presentation.layout.surface_quality import CollisionDomain, SlotPlacement, SurfaceLayoutRequest, TextPlacement
from chrona.presentation.layout.text import place_text


def place_heading(request: SurfaceLayoutRequest, slot: SlotPlacement, measured: MeasuredSources) -> tuple[TextPlacement, ...]:
    source = measured.inputs.get("title")
    measurement = measured.measurements.get("title")
    if measurement is None:
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources/measurements/title")

    def place(identifier: str, content: str, role: str, baseline: float,
              source_content: str | None = None) -> TextPlacement:
        return place_text(
            placement_id=identifier, source_ref="title", content=content,
            inline=float(slot.bounds.inline), baseline_block=baseline,
            typography_role=role, theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
            collision_region="title", collision_domain=CollisionDomain("title", "content"),
            source_content=source_content if source_content is not None else content,
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
                           float(slot.bounds.block) + float(baseline), source_content=run.content)
                     for run, closed, baseline in zip(runs, measured_runs, stack.baselines))

    # No kicker: retain the existing title/deck measurement and equations.
    title = source.lines[0] if source and source.lines else ""
    text = [place("title", title, "heading",
                  float(slot.bounds.block) + float(measurement.first_baseline or 0))]
    runs = measured.run_measurements.get("title", ())
    if source is not None and len(source.lines) > 1 and len(runs) > 1:
        text.append(place("subtitle", source.lines[1], runs[1].typography_role, max(
            float(slot.bounds.block) + float(runs[0].block_size) + float(runs[1].baseline),
            float(text[0].bounds.block + text[0].bounds.block_size) + runs[1].font_size)))
    return tuple(text)
