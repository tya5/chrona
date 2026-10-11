"""Bind immutable source facts to each candidate's completed inline allocation."""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Mapping

from chrona.presentation.layout.engine import LayoutSizingContext, resolve_source_inline_budgets
from chrona.presentation.layout.group_tags import group_tag_column_size, vertical_group_tags
from chrona.presentation.layout.model import LayoutError, LayoutManifest, ResolvedLayoutProfile
from chrona.presentation.layout.slot_heading import reserve_slot_heading_blocks
from chrona.presentation.layout.sources import MeasuredSources, measure_sources
from chrona.presentation.layout.surface_quality import SurfaceLayoutRequest
from chrona.presentation.layout.table_measurement import measure_bounded_table
from chrona.presentation.model.theme_tokens import ThemeTokenView


class SourceSizingSession:
    """Render-local cache; no View parsing, resource mutation or peer allocation."""

    def __init__(self, profile: ResolvedLayoutProfile, measured: MeasuredSources, *,
                 theme: Mapping[str, Any], font_metrics: Any, content: Any):
        self.profile, self.measured = profile, measured
        self.theme, self.font_metrics, self.content = theme, font_metrics, content
        self.tokens = ThemeTokenView(theme)
        selected: dict[str, str] = {}
        headings: set[str] = set()

        def visit(node: Mapping[str, Any]) -> None:
            if node["kind"] == "slot":
                source, slot_id = str(node["source"]), str(node["id"])
                value = measured.inputs.get(source)
                if source == "table" and "maxInlineShare" in node:
                    selected[slot_id] = source
                elif (source in {"title", "heading.title", "heading.kicker", "heading.subtitle"}
                      and value is not None and value.content_present and value.text_wrap == "allow"):
                    selected[slot_id] = source
                    headings.add(slot_id)
            for child in node.get("children", ()):
                visit(child)

        visit(profile.profile["root"])
        self.slot_sources = MappingProxyType(selected)
        self.heading_slots = frozenset(headings)
        self._cache: dict[tuple[str, Decimal], MeasuredSources] = {}
        self.table_reserved_inline = (group_tag_column_size(self.tokens) if "table" in selected.values() and vertical_group_tags(
            SurfaceLayoutRequest(surface_content=content, theme_tokens=self.tokens)) else 0.0)

    @property
    def active(self) -> bool:
        return bool(self.slot_sources)

    def context(self, *, viewport_inline: int, viewport_block: int | Decimal,
                measurements: Mapping[str, Any], content_sized: bool = False) -> LayoutSizingContext:
        budgets = resolve_source_inline_budgets(
            self.profile, viewport_inline=viewport_inline, viewport_block=viewport_block,
            measurements=measurements, content_sized=content_sized, heading_slots=self.heading_slots)

        def measure(slot_id: str, width: Decimal):
            source = self.slot_sources[slot_id]
            return self._at_width(source, width).measurements[source]

        return LayoutSizingContext(budgets, measure)

    def _at_width(self, source: str, width: Decimal) -> MeasuredSources:
        key = source, width
        if key in self._cache:
            return self._cache[key]
        value = self.measured.inputs[source]
        if source == "table":
            if value.table is None:
                raise LayoutError("E_LAYOUT_MEASUREMENT_REQUIRED", "/sources/table")
            table = measure_bounded_table(value.table, available_inline=width, tokens=self.tokens,
                                          font_metrics=self.font_metrics, metric_values=self.measured.metric_values,
                                          original=self.measured.measurements[source],
                                          reserved_inline=self.table_reserved_inline)
            closed = replace(self.measured, measurements={source: table.measurement},
                             bounded_tables={source: table})
        else:
            closed = measure_sources({source: value}, self.theme, font_metrics=self.font_metrics,
                                      heading_inline={source: width})
            closed = reserve_slot_heading_blocks(closed, self.profile, self.tokens,
                                                 content=self.content, font_metrics=self.font_metrics)
        self._cache[key] = closed
        return closed

    def close_manifest(self, manifest: LayoutManifest) -> MeasuredSources:
        """Select final widths; never leak cap-width text into native placement."""
        if not self.active:
            return self.measured
        measurements = dict(self.measured.measurements)
        runs, stacks = dict(self.measured.run_measurements), dict(self.measured.block_stacks)
        tables = dict(self.measured.bounded_tables)
        for decision in manifest.decisions:
            source = self.slot_sources.get(decision.node_id)
            if source is None:
                continue
            closed = self._at_width(source, decision.bounds.inline_size)
            measurements[source] = closed.measurements[source]
            if source != "table":
                runs[source] = closed.run_measurements[source]
                if source in closed.block_stacks:
                    stacks[source] = closed.block_stacks[source]
            else:
                tables[source] = closed.bounded_tables[source]
        return replace(self.measured, measurements=measurements, run_measurements=runs,
                       block_stacks=stacks, bounded_tables=tables)
