from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

from chrona.presentation.layout import surface_table
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_base import SurfaceBaseGeometry
from chrona.presentation.layout.surface_quality import RowPlacement, ScalePlacement, SlotPlacement, SurfaceLayoutRequest
from chrona.presentation.layout.surface_table import TableRowIndentIntent
from chrona.presentation.model.surface_content import (
    TableCellContent, TableColumnContent, TableColumnWidth,
)
from chrona.presentation.model.theme_tokens import ThemeTokenView
from tests.unit.chrona.presentation.layout.test_sources import theme


class _Metrics:
    content_identity = "sha256:surface-table-seed"

    def width(self, text, size, **kwargs):
        return len(text) * size / 2

    def baseline(self, top, size, line_height):
        return top + size


def _request_and_content():
    resolved = theme()
    content = SimpleNamespace(
        table_columns=(
            TableColumnContent("work", "Work package", "start",
                               TableColumnWidth("content", "fill", 1), "rotate-cw"),
            TableColumnContent("owner", "Responsible", "end",
                               TableColumnWidth("content", "content"), "rotate-ccw"),
        ),
        table_cells=(
            TableCellContent("item-1", "work", "Alpha", "tableCell"),
            TableCellContent("item-1", "owner", "Team A", "tableCell"),
        ),
        table_hierarchy_column="work",
        table_indent_under_headers=False,
        slot_heading_text=(),
    )
    return SurfaceLayoutRequest(
        surface_content=content,
        theme_tokens=ThemeTokenView(resolved),
        font_metrics=_Metrics(),
    )


def _row_intents():
    return (TableRowIndentIntent("row-1", "item-1", "group-a", 2),)


def test_header_seed_closes_exact_rotated_header_extent_and_hierarchy_indent():
    request = _request_and_content()
    table = SlotPlacement("table", "table", Rect(Decimal(0), Decimal(0), Decimal(360), Decimal(200)),
                          overflow="ellipsize-with-source")
    rows = _row_intents()
    metrics = {"table.column.gutter.inlineSize": Decimal(8), "table.indent.inlineSize": Decimal(12)}
    seed = surface_table.prepare_table_header_seed(
        request=request, table=table, review_rows=rows, metric_values=metrics,
        group_tag_inline_size=16)
    assert dict(seed.cell_indents) == {"row-1": 38.0, "item-1": 38.0}
    assert seed.table_bounds[:2] == (16.0, 0.0)
    assert seed.header_end_block == max(
        item.bounds.block + item.bounds.block_size for item in seed.header_text)
    rotated = next(item for item in seed.header_text if item.placement_id == "column:owner")
    horizontal_extent = next(item for item in seed.header_text if item.placement_id == "column:work")
    assert seed.header_end_block == max(
        rotated.bounds.block + rotated.bounds.block_size,
        horizontal_extent.bounds.block + horizontal_extent.bounds.block_size)


def test_compose_table_reuses_a_prepared_content_slot_seed_and_places_cells_on_base_rows(monkeypatch):
    request = _request_and_content()
    full_table = SlotPlacement("table", "table", Rect(Decimal(0), Decimal(0), Decimal(360), Decimal(200)),
                               overflow="ellipsize-with-source")
    content_table = replace(full_table, bounds=Rect(Decimal(0), Decimal(18), Decimal(360), Decimal(182)))
    metrics = {"table.column.gutter.inlineSize": Decimal(8), "table.indent.inlineSize": Decimal(12)}
    seed = surface_table.prepare_table_header_seed(
        request=request, table=content_table, review_rows=_row_intents(), metric_values=metrics,
        group_tag_inline_size=16)
    row = RowPlacement("row-1", "item-1", "group-a", Rect(Decimal(0), Decimal(90), Decimal(200), Decimal(40)), depth=2)
    timeline = SlotPlacement("timeline", "timeline", Rect(Decimal(0), Decimal(40), Decimal(360), Decimal(160)))
    base = SurfaceBaseGeometry(
        request=request, projection=SimpleNamespace(), layout_manifest=SimpleNamespace(),
        measured_sources=SimpleNamespace(metric_values=metrics), metric_values=metrics,
        decisions={}, slots=(full_table, timeline), by_source={"table": full_table, "timeline": timeline},
        table=full_table, timeline=timeline, review_rows=_row_intents(), timeline_bounds=(0, 40, 360, 160),
        slot_ids=frozenset({"table", "timeline"}),
        scale=ScalePlacement("table-timeline", "primary", None, None, 0, 360, 0, 1),
        rows=(row,), raw_rows=(), groups=(), tracks=(), role_geometries={}, mark_block_size=0,
        lane_subtracks=None, group_header_size=0, row_padding=0, text_line_block=0,
        table_bounds=(0, 0, 360, 200), plot=Rect(Decimal(0), Decimal(40), Decimal(360), Decimal(160)),
        group_tag_inline_size=16)
    baseline = surface_table.compose_table(base)
    no_caption_seed = surface_table.prepare_table_header_seed(
        request=request, table=full_table, review_rows=_row_intents(), metric_values=metrics,
        group_tag_inline_size=16)
    seeded_baseline = surface_table.compose_table(base, seed=no_caption_seed)
    assert seeded_baseline == baseline

    def unexpected_rebuild(**kwargs):
        raise AssertionError("compose_table rebuilt the supplied native header seed")

    monkeypatch.setattr(surface_table, "prepare_table_header_seed", unexpected_rebuild)
    composed = surface_table.compose_table(base, seed=seed)

    assert composed.layout_columns == seed.layout_columns
    assert composed.columns == seed.columns
    assert composed.text[:len(seed.header_text)] == seed.header_text
    cell = next(item for item in composed.text if item.placement_id == "cell:item-1:work")
    assert cell.bounds.block >= row.bounds.block
    assert cell.bounds.block < row.bounds.block + row.bounds.block_size
    moved = surface_table.compose_table(
        replace(base, rows=(replace(row, bounds=Rect(Decimal(0), Decimal(500), Decimal(200), Decimal(40))),)),
        seed=seed)
    assert moved.layout_columns == composed.layout_columns
    assert moved.columns == composed.columns
    assert tuple(item for item in moved.text if item.placement_id.startswith("column:")) == seed.header_text
    assert tuple(item for item in composed.text if item.placement_id.startswith("column:")) == seed.header_text
    moved_cell = next(item for item in moved.text if item.placement_id == "cell:item-1:work")
    assert moved_cell.bounds.block > cell.bounds.block
