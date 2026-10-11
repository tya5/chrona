from dataclasses import replace
from decimal import Decimal as D
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.presentation import required_row_block_extents
from chrona.presentation.layout.surface_quality import RowPlacement, SlotPlacement, SurfaceLayoutRequest
from chrona.presentation.layout.surface_table import compose_table, prepare_table_header_seed, TableRowIndentIntent
from chrona.presentation.model.theme_tokens import ThemeTokenView
from tests.unit.chrona.presentation.layout.test_bounded_table_measurement import close, content, Metrics
from tests.unit.chrona.presentation.layout.test_sources import theme


def setup(table_content, width=300, reserved=0):
    bounded, measured = close(table_content, width, reserved_inline=reserved)
    surface = SimpleNamespace(table_columns=table_content.columns, table_cells=table_content.cells,
                              table_hierarchy_column=table_content.hierarchy_column,
                              table_indent_under_headers=table_content.indent_under_headers)
    request = SurfaceLayoutRequest(surface_content=surface, theme_tokens=ThemeTokenView(theme()),
                                   font_metrics=Metrics(),
                                   measured_sources=replace(measured, bounded_tables={"table": bounded}))
    slot = SlotPlacement("table", "table", Rect(D(50), D(20), D(width), D(3000)))
    intents = tuple(TableRowIndentIntent(key, key, "", 0) for key in ("a", "b"))
    seed = prepare_table_header_seed(request=request, table=slot, review_rows=intents,
                                     metric_values=measured.metric_values, group_tag_inline_size=reserved)
    rows = tuple(RowPlacement(key, key, "", Rect(D(50), D(1000), D(width), D(1000))) for key in ("a", "b"))
    base = SimpleNamespace(request=request, table=slot, rows=rows)
    return bounded, seed, base


def test_native_table_projects_closed_multiline_cells_at_translated_coordinates():
    bounded, seed, base = setup(content())
    placed = compose_table(base, seed=seed)
    cell = next(item for item in placed.text if item.placement_id == "cell:a:task")
    assert cell.lines == bounded.cells[0].fit.lines
    assert cell.source_content == bounded.cells[0].source_content
    assert cell.bounds.inline >= 50
    assert cell.bounds.inline + cell.bounds.inline_size <= 350
    assert cell.bounds.block + cell.bounds.block_size <= 2000
    assert placed.columns[-1].bounds.inline + placed.columns[-1].bounds.inline_size == 350
    assert cell.baseline[1] == pytest.approx(1000 + (1000 - float(bounded.cells[0].block_size)) / 2 + 14)


def test_reserved_group_chrome_is_translated_once():
    _, seed, base = setup(content(), reserved=16)
    assert seed.layout_columns[0].inline == 66
    assert compose_table(base, seed=seed).columns[-1].bounds.inline + seed.columns[-1].bounds.inline_size == 350


@pytest.mark.parametrize("orientation", ["horizontal", "rotate-cw", "rotate-ccw"])
def test_fitting_closed_table_keeps_all_native_placements_exact(orientation):
    _, bounded_seed, base = setup(content("Short", orientation=orientation), width=1000)
    ordinary_request = replace(base.request, measured_sources=replace(base.request.measured_sources, bounded_tables={}))
    ordinary_seed = prepare_table_header_seed(request=ordinary_request, table=base.table,
                                             review_rows=tuple(TableRowIndentIntent(key, key, "", 0) for key in ("a", "b")),
                                             metric_values=base.request.measured_sources.metric_values,
                                             group_tag_inline_size=0)
    assert compose_table(base, seed=bounded_seed) == compose_table(base, seed=ordinary_seed)


def test_ellipsis_keeps_full_source_in_completed_placement():
    bounded, seed, base = setup(content("X" * 1000))
    cell = next(item for item in compose_table(base, seed=seed).text if item.placement_id == "cell:a:task")
    assert cell.overflow == "ellipsized"
    assert cell.content == bounded.cells[0].fit.content
    assert cell.source_content == "X" * 1000


def test_stale_allocated_budget_is_rejected_before_native_placement():
    _, seed, base = setup(content())
    with pytest.raises(LayoutError, match="E_LAYOUT_TABLE_OVERFLOW"):
        prepare_table_header_seed(request=base.request, table=replace(base.table, bounds=replace(base.table.bounds, inline_size=D(299))),
                                  review_rows=(), metric_values=base.request.measured_sources.metric_values,
                                  group_tag_inline_size=0)


def test_each_rows_own_text_demand_is_combined_with_track_and_padding():
    rows = tuple(SimpleNamespace(row_id=f"row-{key}", table_subject_id=key, items=()) for key in ("a", "b"))
    kwargs = dict(review_rows=rows, row_minimum=40, row_padding=6, mark_block_size=10, text_line_block=19.6)
    assert required_row_block_extents(**kwargs, row_text_blocks={"a": D(120), "b": D("19.6")}) == (126, 40)
    assert required_row_block_extents(**kwargs, row_text_blocks={"row-a": D(80)}) == (86, 40)
    assert required_row_block_extents(**kwargs, row_text_blocks={}) == required_row_block_extents(**kwargs)


@pytest.mark.parametrize("lanes", [False, True])
def test_surface_inline_closes_cell_demand_before_row_allocation(lanes):
    from chrona.presentation.layout.surface_base import prepare_surface_inline
    from chrona.presentation.layout.surface_preparation import prepare_surface_candidate
    from chrona.presentation.model.projection import build_review_projection
    from tests.unit.chrona.presentation.layout.test_surface_slot_allocation import _request
    from tests.unit.chrona.presentation.scene.test_relation_ghost_endpoints import MODES, PLACED, PROJECT, SNAPSHOT

    request = _request()
    if lanes:
        projection = build_review_projection(PROJECT, PLACED, MODES["lanes"], None,
                                             snapshot_project=PROJECT, snapshot_placements=SNAPSHOT)
        request = replace(request, projection=projection,
                          measured_sources=replace(request.measured_sources, metric_values={
                              **request.measured_sources.metric_values,
                              "text.body.size": D(14), "text.body.lineHeight": D("1.4")}))
    original = prepare_surface_candidate(request).inline
    target = original.review_rows[0]
    bounded = SimpleNamespace(row_text_blocks=((target.table_subject_id, D(300)),))
    request = replace(original.request, measured_sources=replace(request.measured_sources, bounded_tables={"table": bounded}))
    actual = prepare_surface_inline(request)
    assert actual.row_requirements[0] == 308
    assert actual.natural_block_requirement == original.natural_block_requirement + D(str(308 - original.row_requirements[0]))
    assert actual.row_requirements[1:] == original.row_requirements[1:]
