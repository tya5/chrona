from decimal import Decimal as D

import pytest

from chrona.presentation.layout.engine import (
    LayoutSizingContext, measure_natural_normal_flow_block, resolve_content_block_extent,
    resolve_source_inline_budgets, solve_layout,
)
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.sources import SourceInput, measure_sources
from tests.unit.chrona.presentation.layout.test_bounded_table_measurement import Metrics
from tests.unit.chrona.presentation.layout.test_sources import theme
from tests.unit.chrona.presentation.layout.test_table_inline_budget import container, measurement, profile, slot


def heading(name="copy", **kwargs):
    return slot(name, share=None, source="title", **kwargs)


def closure(resolved, source, measurements):
    budgets = resolve_source_inline_budgets(resolved, viewport_inline=1000, viewport_block=5000,
                                            measurements=measurements, heading_slots=frozenset({"copy"}))
    closed = {}

    def measure(slot_id, width):
        assert slot_id == "copy"
        result = measure_sources({"title": source}, theme(), font_metrics=Metrics(), heading_inline={"title": width})
        closed[width] = result
        return result.measurements["title"]

    return budgets, LayoutSizingContext(budgets, measure), closed


@pytest.mark.parametrize("kind", ["row", "column", "overlay", "flow", "grid"])
def test_heading_uses_independent_parent_or_cell_budget_and_actual_width_before_height(kind):
    extra = dict(columnTracks=[{"fr": 1}, {"fr": 1}], rowTracks=["content"]) if kind == "grid" else {}
    selected = heading(inlineSize={"fr": 1}, **({"cell": {"row": 1, "column": 1}} if kind == "grid" else {}))
    other = slot("other", share=None, source="timeline", inlineSize={"fr": 1}, blockSize="content",
                 **({"cell": {"row": 1, "column": 2}} if kind == "grid" else {}))
    resolved = profile(container(kind, [selected, other], **extra))
    source = SourceInput(("heading words " * 100,), typography_role="heading", text_wrap="allow")
    original = measure_sources({"title": source}, theme(), font_metrics=Metrics())
    measurements = {"copy": original.measurements["title"], "other": measurement(30)}
    budgets, context, closed = closure(resolved, source, measurements)
    assert budgets["copy"].source_kind == "heading"
    assert budgets["copy"].failure_code == "E_LAYOUT_TEXT_OVERFLOW"
    assert budgets["copy"].ceiling == budgets["copy"].available_inline
    manifest = solve_layout(resolved, viewport_inline=1000, viewport_block=5000, measurements=measurements, sizing=context)
    placed = next(item.bounds for item in manifest.decisions if item.node_id == "copy")
    measured = closed[placed.inline_size]
    assert measured.measurements["title"].preferred_block == placed.block_size
    assert len(measured.run_measurements["title"][0].lines) > 1
    assert not manifest.fit_warnings


def test_table_and_heading_are_neutralized_together_without_changing_resources():
    resolved = profile(container("row", [slot(), heading()]))
    measurements = {"table": measurement(10000), "copy": measurement(20000)}
    budgets = resolve_source_inline_budgets(resolved, viewport_inline=1000, viewport_block=500,
                                            measurements=measurements, heading_slots=frozenset({"copy"}))
    assert budgets["table"].available_inline == budgets["copy"].available_inline == 960
    assert budgets["table"].ceiling == 384
    assert budgets["copy"].ceiling == 960
    assert "maxInlineShare" not in resolved.profile["root"]["children"][1]
    assert measurements["copy"].preferred_inline == 20000


@pytest.mark.parametrize("kind", ["row", "column", "overlay", "flow", "grid"])
def test_fitting_heading_sizing_preserves_complete_manifest(kind):
    extra = dict(columnTracks=[{"fixed": 400}], rowTracks=["content"]) if kind == "grid" else {}
    resolved = profile(container(kind, [heading(**({"cell": {"row": 1, "column": 1}} if kind == "grid" else {}))], **extra))
    source = SourceInput(("Short",), typography_role="heading", text_wrap="allow")
    original = measure_sources({"title": source}, theme(), font_metrics=Metrics())
    measurements = {"copy": original.measurements["title"]}
    _, context, _ = closure(resolved, source, measurements)
    ordinary = solve_layout(resolved, viewport_inline=1000, viewport_block=5000, measurements=measurements)
    assert solve_layout(resolved, viewport_inline=1000, viewport_block=5000, measurements=measurements, sizing=context) == ordinary


def test_heading_authored_minimum_above_budget_uses_text_diagnostic():
    resolved = profile(container("column", [heading(inlineSize={"fixed": 1200})]))
    source = SourceInput(("Short",), typography_role="heading", text_wrap="allow")
    measurements = {"copy": measure_sources({"title": source}, theme(), font_metrics=Metrics()).measurements["title"]}
    _, context, _ = closure(resolved, source, measurements)
    with pytest.raises(LayoutError, match="E_LAYOUT_TEXT_OVERFLOW"):
        solve_layout(resolved, viewport_inline=1000, viewport_block=5000, measurements=measurements, sizing=context)


@pytest.mark.parametrize("root", [heading(), slot()])
def test_schema_requires_container_root_so_slots_always_have_a_parent_budget(root):
    with pytest.raises(LayoutError, match="E_LAYOUT_SCHEMA"):
        profile(root)


def test_intrinsic_heading_cell_without_independent_width_fails_as_text():
    resolved = profile(container("grid", [heading(cell={"row": 1, "column": 1})],
                                 columnTracks=["content"], rowTracks=["content"]))
    with pytest.raises(LayoutError, match="E_LAYOUT_TEXT_OVERFLOW"):
        resolve_source_inline_budgets(resolved, viewport_inline=1000, viewport_block=500,
                                      measurements={"copy": measurement(2000)}, heading_slots=frozenset({"copy"}))


def test_natural_heading_height_and_auto_extent_use_allocated_width_closure():
    resolved = profile(container("column", [heading()]))
    source = SourceInput(("heading words " * 100,), typography_role="heading", text_wrap="allow")
    measurements = {"copy": measure_sources({"title": source}, theme(), font_metrics=Metrics()).measurements["title"]}
    _, context, closed = closure(resolved, source, measurements)
    natural = measure_natural_normal_flow_block(resolved, viewport_inline=1000, measurements=measurements, sizing=context)

    def required(manifest):
        width = next(item.bounds.inline_size for item in manifest.decisions if item.node_id == "copy")
        return {"title": closed[width].measurements["title"].preferred_block}

    extent = resolve_content_block_extent(resolved, viewport_inline=1000, minimum_block=50,
                                          measurements=measurements, required_blocks=required,
                                          content_sized=True, sizing=context)
    final = solve_layout(resolved, viewport_inline=1000, viewport_block=extent.extent,
                         measurements=measurements, content_sized=True, sizing=context)
    placed = next(item.bounds for item in final.decisions if item.node_id == "copy")
    assert natural == placed.block_size + 20
    assert extent.extent == int(natural.to_integral_value(rounding="ROUND_CEILING"))
    assert not extent.short_sources
    assert not final.fit_warnings
