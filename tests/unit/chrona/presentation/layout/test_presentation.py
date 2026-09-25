from types import SimpleNamespace
from decimal import Decimal

import pytest

from chrona.presentation.layout.model import LayoutError, geometry_sum
from chrona.presentation.layout.presentation import RowPlacement, minimum_track_block_extent, place_mark_tracks, place_rows, place_table_columns, required_row_block_extents
from chrona.presentation.layout.text import ellipsize_text
from chrona.presentation.layout.surface_composer import _contains_block_interval
from chrona.presentation.model.surface_content import TableCellContent, TableColumnContent, TableColumnWidth


class FixedMetrics:
    def width(self, value: str, size: float) -> float:
        return len(value) * size


def fixed_measure(value: str, _role: str, orientation: str = "horizontal") -> float:
    return len(value) * 10 if orientation == "horizontal" else 10


def table_columns(*items: tuple[str, str]) -> tuple[TableColumnContent, ...]:
    return tuple(TableColumnContent(column_id, header, "start", TableColumnWidth("content", "content"))
                 for column_id, header in items)


def table_cells(*items: tuple[str, str, str]) -> tuple[TableCellContent, ...]:
    return tuple(TableCellContent(*item, "tableCell") for item in items)


def test_table_placements_are_ordered_and_non_overlapping() -> None:
    placements = place_table_columns(
        columns=table_columns(("owner", "Owner"), ("status", "Status")),
        cells=table_cells(("a", "owner", "Firmware"), ("a", "status", "In progress")),
        bounds=(10.0, 0.0, 240.0, 20.0),
        measure_text=fixed_measure, minimum_inline=10.0,
    )

    assert placements[0].inline < placements[1].inline
    assert placements[0].inline + placements[0].inline_size <= placements[1].inline


def test_geometry_sum_uses_the_cross_python_correctly_rounded_float_result() -> None:
    # Python 3.11's builtin sum returns 0.9999999999999999 here, while 3.12
    # compensates it.  Completed Layout placements use the invariant result.
    assert geometry_sum((0.1 for _ in range(10))) == 1.0


def test_table_placements_reserve_the_declared_positive_gutter() -> None:
    placements = place_table_columns(
        columns=table_columns(("owner", "Owner"), ("status", "Status")),
        cells=table_cells(("a", "owner", "Firmware"), ("a", "status", "In progress")),
        bounds=(10.0, 0.0, 260.0, 20.0), measure_text=fixed_measure, minimum_inline=10.0, gutter=12.0,
    )
    assert placements[1].inline - (placements[0].inline + placements[0].inline_size) == 12.0


def test_table_placement_diagnoses_when_required_text_cannot_fit() -> None:
    with pytest.raises(LayoutError, match="E_LAYOUT_TABLE_OVERFLOW"):
        place_table_columns(
            columns=table_columns(("owner", "Owner"), ("status", "Status")),
            cells=table_cells(("a", "owner", "Firmware"), ("a", "status", "In progress")),
            bounds=(0.0, 0.0, 20.0, 20.0),
            measure_text=fixed_measure, minimum_inline=10.0,
        )


def test_table_header_containment_ignores_only_sub_micro_point_float_residue() -> None:
    assert _contains_block_interval(
        container_start=Decimal("116.2"), container_end=Decimal("156.2"),
        item_start=Decimal("116.19999999999999"), item_end=Decimal("137.19999999999999"),
    )
    assert not _contains_block_interval(
        container_start=Decimal("116.2"), container_end=Decimal("156.2"),
        item_start=Decimal("116.199"), item_end=Decimal("137.199"),
    )


def test_ellipsize_allocation_preserves_a_minimum_for_each_column() -> None:
    placements = place_table_columns(
        columns=(TableColumnContent("first", "Long heading", "start", TableColumnWidth("ellipsis", "fr", 1)),
                 TableColumnContent("second", "Another heading", "start", TableColumnWidth("ellipsis", "fr", 1))),
        cells=table_cells(("a", "first", "a very long value"), ("a", "second", "another long value")),
        bounds=(0.0, 0.0, 60.0, 20.0), measure_text=fixed_measure, minimum_inline=10.0,
        overflow="ellipsize-with-source",
    )
    assert sum(item.inline_size for item in placements) == 60.0
    assert all(item.inline_size >= 20.0 for item in placements)
    assert all(item.inline_size <= item.natural_inline_size for item in placements)


def test_declared_content_and_fractional_columns_allocate_from_measured_minima() -> None:
    columns = (
        TableColumnContent("fixed", "Fixed", "start", TableColumnWidth("content", "content")),
        TableColumnContent("one", "One", "start", TableColumnWidth("ellipsis", "fr", 1)),
        TableColumnContent("three", "Three", "start", TableColumnWidth("ellipsis", "fr", 3)),
    )
    placements = place_table_columns(columns=columns, cells=table_cells(("a", "fixed", "fixed value")),
                                     bounds=(0.0, 0.0, 300.0, 20.0), measure_text=fixed_measure, minimum_inline=10.0)
    assert placements[0].inline_size >= placements[0].natural_inline_size
    assert placements[2].inline_size - placements[2].natural_inline_size == pytest.approx(
        3 * (placements[1].inline_size - placements[1].natural_inline_size))


def test_table_allocator_measures_numeric_cells_with_their_completed_role() -> None:
    observed = []
    def measure(value: str, role: str, orientation: str) -> float:
        observed.append((value, role, orientation))
        return len(value) * 10
    place_table_columns(
        columns=table_columns(("delta", "Δ")),
        cells=(TableCellContent("a", "delta", "+12d", "tableCell", "numeric"),),
        bounds=(0.0, 0.0, 100.0, 20.0), measure_text=measure, minimum_inline=10.0,
    )
    assert ("+12d", "numeric", "horizontal") in observed


def test_table_allocator_uses_rotated_header_occupied_inline_measurement() -> None:
    observed = []
    def measure(value: str, role: str, orientation: str) -> float:
        observed.append((value, role, orientation))
        return 10 if orientation != "horizontal" else len(value) * 10
    place_table_columns(
        columns=(TableColumnContent("status", "Long status heading", "start",
                                    TableColumnWidth("content", "content"), "rotate-cw"),),
        cells=(), bounds=(0.0, 0.0, 100.0, 20.0), measure_text=measure, minimum_inline=10.0,
    )
    assert ("Long status heading", "text", "rotate-cw") in observed


def test_minmax_content_reserves_preferred_width_while_ellipsis_uses_only_flexible_columns() -> None:
    columns = (
        TableColumnContent("minimum", "Minimum", "start", TableColumnWidth("content", "fr", 1)),
        TableColumnContent("flex", "Flexible", "start", TableColumnWidth("ellipsis", "fill", 1)),
    )
    placements = place_table_columns(columns=columns,
                                     cells=table_cells(("a", "minimum", "a deliberately long fixed value"), ("a", "flex", "long")),
                                     bounds=(0.0, 0.0, 360.0, 20.0), measure_text=fixed_measure, minimum_inline=10.0,
                                     overflow="ellipsize-with-source")
    assert placements[0].inline_size >= placements[0].natural_inline_size
    assert placements[1].inline_size >= 20.0


def test_ellipsize_text_keeps_the_longest_measured_prefix() -> None:
    assert ellipsize_text("Firmware", available_inline=50.0, font_size=10.0, font_metrics=FixedMetrics()) == "Firm…"


def test_row_placements_reserve_declared_group_headers() -> None:
    rows = (
        SimpleNamespace(row_id="a", group_id="firmware"),
        SimpleNamespace(row_id="b", group_id="firmware"),
        SimpleNamespace(row_id="c", group_id="hardware"),
    )
    placements = place_rows(
        review_rows=rows,
        timeline_bounds=(0.0, 0.0, 100.0, 100.0),
        group_header_size=10.0,
        required_block_sizes=(20.0, 20.0, 20.0),
        distribution="pack",
    )

    assert placements[0].bounds[1] == 10.0
    assert placements[1].bounds[1] > placements[0].bounds[1]
    assert placements[2].bounds[1] > placements[1].bounds[1]


def test_track_placements_keep_shared_members_on_one_track() -> None:
    item = SimpleNamespace
    rows = (
        item(
            row_id="owner-a",
            group_id=None,
            items=(
                item(item_id="snapshot", object_id="schedule", track="shared", source_kind="snapshot"),
                item(item_id="actual", object_id="schedule", track="shared", source_kind="actual"),
            ),
        ),
    )
    row_placements = place_rows(
        review_rows=rows,
        timeline_bounds=(0.0, 0.0, 100.0, 40.0),
        group_header_size=0.0,
        required_block_sizes=(10.0,),
        distribution="pack",
    )

    tracks = place_mark_tracks(
        review_rows=rows,
        row_placements=row_placements,
        mark_block_size=10.0,
    )

    assert tracks[0].block == tracks[1].block
    assert tracks[0].actual_block == tracks[1].actual_block


@pytest.mark.parametrize("track, source_kind, actual", [
    ("shared", "primary", None),
    ("stacked", "combined", {"start": "2026-01-01", "finish": "2026-01-02"}),
    ("stacked", "combined", None),
])
def test_track_placements_reject_completed_mark_extent_outside_its_row(track, source_kind, actual) -> None:
    item = SimpleNamespace
    rows = (item(row_id="row", group_id=None, items=(item(
        item_id="member", object_id="member", track=track, source_kind=source_kind, actual=actual,
    ),)),)
    row_placements = place_rows(review_rows=rows, timeline_bounds=(0.0, 0.0, 100.0, 9.0), group_header_size=0.0,
                                required_block_sizes=(9.0,), distribution="pack")

    with pytest.raises(LayoutError, match="E_LAYOUT_MARK_OVERFLOW") as error:
        place_mark_tracks(review_rows=rows, row_placements=row_placements, mark_block_size=10.0)

    assert error.value.path == "/measuredSources/metricValues/timeline.mark.blockSize"


def test_track_placements_accept_mark_extents_at_the_row_boundary() -> None:
    item = SimpleNamespace
    rows = (item(row_id="row", group_id=None, items=(item(
        item_id="member", object_id="member", track="stacked", source_kind="combined", actual=None,
    ),)),)
    row_placements = place_rows(review_rows=rows, timeline_bounds=(0.0, 0.0, 100.0, 30.0), group_header_size=0.0,
                                required_block_sizes=(30.0,), distribution="pack")

    tracks = place_mark_tracks(review_rows=rows, row_placements=row_placements, mark_block_size=10.0)

    assert tracks[0].block == tracks[0].actual_block == 10.0
    assert tracks[0].block_size == 10.0


def test_track_minimum_uses_the_completed_multi_lane_milestone_placement() -> None:
    item = SimpleNamespace
    row = item(row_id="milestone-lanes", group_id=None, items=(
        item(item_id="gate-a", object_id="gate-a", track="stacked", source_kind="combined", actual=None),
        item(item_id="gate-b", object_id="gate-b", track="stacked", source_kind="combined", actual=None),
    ))
    assert minimum_track_block_extent(review_row=row, mark_block_size=10.0) == 20.0
    with pytest.raises(LayoutError, match="E_LAYOUT_MARK_OVERFLOW"):
        place_mark_tracks(review_rows=(row,), row_placements=(
            RowPlacement("milestone-lanes", None, (0.0, 0.0, 100.0, 19.0)),
        ), mark_block_size=10.0)


def test_row_requirements_are_per_row_and_fill_only_distributes_surplus() -> None:
    item = SimpleNamespace
    rows = (
        item(row_id="one-lane", group_id=None, items=(item(item_id="one", object_id="one", track="stacked", source_kind="primary"),)),
        item(row_id="two-lane", group_id=None, items=(
            item(item_id="two-a", object_id="two-a", track="stacked", source_kind="primary"),
            item(item_id="two-b", object_id="two-b", track="stacked", source_kind="primary"),
        )),
    )
    required = required_row_block_extents(review_rows=rows, row_minimum=12.0, row_padding=4.0, mark_block_size=10.0)
    assert required == (14.0, 24.0)
    packed = place_rows(review_rows=rows, timeline_bounds=(0.0, 0.0, 100.0, 60.0), group_header_size=0.0,
                        required_block_sizes=required, distribution="pack")
    filled = place_rows(review_rows=rows, timeline_bounds=(0.0, 0.0, 100.0, 60.0), group_header_size=0.0,
                        required_block_sizes=required, distribution="fill")
    assert tuple(row.bounds[3] for row in packed) == required
    assert tuple(row.bounds[3] for row in filled) == (25.0, 35.0)


def test_row_allocation_rejects_infeasible_requirements_before_track_projection() -> None:
    rows = (SimpleNamespace(row_id="r", group_id=None),)
    with pytest.raises(LayoutError, match="E_LAYOUT_REQUIRED_OVERFLOW"):
        place_rows(review_rows=rows, timeline_bounds=(0.0, 0.0, 100.0, 19.0), group_header_size=0.0,
                   required_block_sizes=(20.0,), distribution="pack")
