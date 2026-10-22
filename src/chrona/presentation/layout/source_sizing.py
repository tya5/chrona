"""Bind immutable source facts to each candidate's completed inline allocation."""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Mapping

from chrona.presentation.layout.engine import (
    LayoutSizingContext, measure_required_normal_flow_inline, resolve_source_inline_budgets,
)
from chrona.presentation.layout.group_header_fit import GroupHeaderInlineDemand, GroupHeaderOwnerInlineDemand
from chrona.presentation.layout.group_tags import group_tag_column_size, vertical_group_tags
from chrona.presentation.layout.model import LayoutError, LayoutManifest, ResolvedLayoutProfile
from chrona.presentation.layout.slot_heading import reserve_slot_heading_blocks
from chrona.presentation.layout.sources import MeasuredSources, measure_sources
from chrona.presentation.layout.surface_quality import SurfaceLayoutRequest
from chrona.presentation.layout.table_measurement import measure_bounded_table
from chrona.presentation.model.theme_tokens import ThemeTokenView


def with_group_header_inline_demands(measured: MeasuredSources,
                                    demands: Mapping[str, GroupHeaderInlineDemand]) -> MeasuredSources:
    """Apply the monotone full-name floor to the table source and its measured demand."""
    if not demands:
        return measured
    table_input = measured.inputs.get("table")
    table_measurement = measured.measurements.get("table")
    if table_input is None or table_measurement is None:
        raise LayoutError("E_LAYOUT_MEASUREMENT_REQUIRED", "/sources/table",
                          detail="required group-header inline demand has no table source")
    floor = max(demand.minimum_source_inline for demand in demands.values())
    current = table_input.min_inline or Decimal(0)
    if floor <= current and floor <= table_measurement.min_inline:
        return measured
    table_input = replace(table_input, min_inline=max(current, floor))
    table_measurement = replace(
        table_measurement,
        min_inline=max(table_measurement.min_inline, floor),
        preferred_inline=max(table_measurement.preferred_inline, floor),
        max_inline=max(table_measurement.max_inline, floor),
    )
    return replace(measured,
                   inputs={**measured.inputs, "table": table_input},
                   measurements={**measured.measurements, "table": table_measurement})


class SourceSizingSession:
    """Render-local cache; no View parsing, resource mutation or peer allocation."""

    def __init__(self, profile: ResolvedLayoutProfile, measured: MeasuredSources, *,
                 theme: Mapping[str, Any], font_metrics: Any, content: Any):
        self.profile, self.measured = profile, measured
        self.theme, self.font_metrics, self.content = theme, font_metrics, content
        self.tokens = ThemeTokenView(theme)
        self.group_header_demands: dict[str, GroupHeaderInlineDemand] = {}
        self.group_header_owner_demands: dict[str, GroupHeaderOwnerInlineDemand] = {}
        self.owner_inline_minima: dict[str, Decimal] = {}
        selected: dict[str, str] = {}
        headings: set[str] = set()
        wrapping_tables: set[str] = set()

        def visit(node: Mapping[str, Any]) -> None:
            if node["kind"] == "slot":
                source, slot_id = str(node["source"]), str(node["id"])
                value = measured.inputs.get(source)
                table_wrap = (source == "table" and value is not None and value.table is not None
                              and any(column.text_wrap == "allow" for column in value.table.columns))
                if source == "table" and ("maxInlineShare" in node or table_wrap):
                    selected[slot_id] = source
                    if table_wrap:
                        wrapping_tables.add(slot_id)
                elif (source in {"title", "heading.title", "heading.kicker", "heading.subtitle"}
                      and value is not None and value.content_present and value.text_wrap == "allow"):
                    selected[slot_id] = source
                    headings.add(slot_id)
            for child in node.get("children", ()):
                visit(child)

        visit(profile.profile["root"])
        self.group_header_inline_owner = self._common_owner_for_sources(profile.profile["root"], {"table", "timeline"})
        self.slot_sources = MappingProxyType(selected)
        self.heading_slots = frozenset(headings)
        self.wrapping_table_slots = frozenset(wrapping_tables)
        self._cache: dict[tuple[str, Decimal], MeasuredSources] = {}
        self.table_reserved_inline = (group_tag_column_size(self.tokens) if "table" in selected.values() and vertical_group_tags(
            SurfaceLayoutRequest(surface_content=content, theme_tokens=self.tokens)) else 0.0)

    @staticmethod
    def _common_owner_for_sources(root: Mapping[str, Any], sources: set[str]) -> str | None:
        """Return the smallest shared Layout owner for the table and timeline slots."""
        paths: dict[str, tuple[str, ...]] = {}

        def visit(node: Mapping[str, Any], ancestors: tuple[str, ...]) -> None:
            node_id = str(node["id"])
            if node.get("kind") == "slot" and node.get("source") in sources:
                paths[str(node["source"])] = (*ancestors, node_id)
            for child in node.get("children", ()):
                visit(child, (*ancestors, node_id))

        visit(root, ())
        if set(paths) != sources:
            return None
        shared = []
        for values in zip(*(paths[source] for source in sorted(sources))):
            if len(set(values)) != 1:
                break
            shared.append(values[0])
        return shared[-1] if shared else None

    def add_group_header_demand(self, demand: GroupHeaderInlineDemand) -> MeasuredSources:
        """Admit one newly measured group minimum, or reject a non-progressing reclosure."""
        previous = self.group_header_demands.get(demand.group_id)
        if previous is not None or demand.group_id in self.group_header_owner_demands:
            raise self._group_header_overflow(
                demand, demand.available_source_inline,
                detail="group-name demand repeated after its source minimum was admitted")
        self.group_header_demands[demand.group_id] = demand
        self.measured = with_group_header_inline_demands(self.measured, self.group_header_demands)
        self._cache.clear()
        return self.measured

    def add_group_header_owner_demand(self, demand: GroupHeaderOwnerInlineDemand) -> None:
        """Admit one exact full-header minimum on its shared Layout owner."""
        if demand.group_id in self.group_header_demands or demand.group_id in self.group_header_owner_demands:
            raise LayoutError("E_LAYOUT_TABLE_OVERFLOW", f"/layout/groupHeaders/{demand.group_id}", "table",
                              f"group {demand.group_id!r} repeated its owner inline demand")
        self.group_header_owner_demands[demand.group_id] = demand
        self.owner_inline_minima[demand.owner_node_id] = max(
            demand.minimum_owner_inline, self.owner_inline_minima.get(demand.owner_node_id, Decimal(0)))
        self._cache.clear()

    @property
    def group_header_growth_demands(self) -> tuple[GroupHeaderInlineDemand | GroupHeaderOwnerInlineDemand, ...]:
        return (*self.group_header_demands.values(), *self.group_header_owner_demands.values())

    def with_group_header_demands(self, measured: MeasuredSources) -> MeasuredSources:
        """Apply the session's accumulated table floor to a parallel measurement view."""
        return with_group_header_inline_demands(measured, self.group_header_demands)

    def refresh(self, measured: MeasuredSources) -> MeasuredSources:
        """Replace completed source facts while retaining all admitted group floors."""
        self.measured = self.with_group_header_demands(measured)
        self._cache.clear()
        return self.measured

    @staticmethod
    def _group_header_overflow(demand: GroupHeaderInlineDemand, available: Decimal,
                               *, detail: str = "") -> LayoutError:
        cause = (f"group {demand.group_id!r} requires complete horizontal name at "
                 f"{demand.minimum_source_inline}px; available table source width is {available}px")
        return LayoutError("E_LAYOUT_TABLE_OVERFLOW", f"/layout/groupHeaders/{demand.group_id}", "table",
                           f"{cause}; {detail}" if detail else cause)

    def _check_group_header_width(self, width: Decimal, slot_id: str) -> None:
        blocked = max((demand for demand in self.group_header_demands.values()
                       if demand.minimum_source_inline > width),
                      key=lambda demand: demand.minimum_source_inline, default=None)
        if blocked is not None:
            raise self._group_header_overflow(blocked, width,
                                              detail=f"bounded table slot {slot_id!r} cannot honor its source minimum")

    @property
    def active(self) -> bool:
        return bool(self.slot_sources or self.owner_inline_minima)

    def context(self, *, viewport_inline: int, viewport_block: int | Decimal,
                measurements: Mapping[str, Any], content_sized: bool = False) -> LayoutSizingContext:
        budgets = resolve_source_inline_budgets(
            self.profile, viewport_inline=viewport_inline, viewport_block=viewport_block,
            measurements=measurements, content_sized=content_sized, heading_slots=self.heading_slots,
            wrapping_table_slots=self.wrapping_table_slots,
            owner_inline_minima=self.owner_inline_minima)

        def measure(slot_id: str, width: Decimal):
            source = self.slot_sources[slot_id]
            return self._at_width(source, width).measurements[source]

        return LayoutSizingContext(budgets, measure, self.owner_inline_minima)

    def required_normal_flow_inline(self, measurements: Mapping[str, Any]) -> Decimal:
        """Return the exact root minimum after all admitted named source/owner floors."""
        return measure_required_normal_flow_inline(
            self.profile, measurements, owner_inline_minima=self.owner_inline_minima)

    def _at_width(self, source: str, width: Decimal) -> MeasuredSources:
        key = source, width
        if key in self._cache:
            return self._cache[key]
        value = self.measured.inputs[source]
        if source == "table":
            self._check_group_header_width(width, "table")
            if value.table is None:
                raise LayoutError("E_LAYOUT_MEASUREMENT_REQUIRED", "/sources/table")
            table = measure_bounded_table(value.table, available_inline=width, tokens=self.tokens,
                                          font_metrics=self.font_metrics, metric_values=self.measured.metric_values,
                                          original=self.measured.measurements[source],
                                          reserved_inline=self.table_reserved_inline)
            if self.group_header_demands:
                floor = max(item.minimum_source_inline for item in self.group_header_demands.values())
                measurement = table.measurement
                table = replace(table, measurement=replace(
                    measurement, min_inline=max(measurement.min_inline, floor),
                    preferred_inline=max(measurement.preferred_inline, floor),
                    max_inline=max(measurement.max_inline, floor)))
            closed = replace(self.measured, measurements={source: table.measurement},
                             bounded_tables={source: table})
        else:
            closed = measure_sources({source: value}, self.theme, font_metrics=self.font_metrics,
                                      heading_inline={source: width}, resolved_metrics=self.measured.metric_values)
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
