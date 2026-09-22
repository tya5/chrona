from types import SimpleNamespace

import pytest

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.presentation import place_mark_tracks, place_rows, place_table_columns
from chrona.presentation.layout.text import ellipsize_text


class FixedMetrics:
    def width(self, value: str, size: float) -> float:
        return len(value) * size


def test_table_placements_are_ordered_and_non_overlapping() -> None:
    placements = place_table_columns(
        columns=(("owner", "Owner"), ("status", "Status")),
        cells=(("a", "owner", "Firmware"), ("a", "status", "In progress")),
        bounds=(10.0, 0.0, 240.0, 20.0),
        font_metrics=FixedMetrics(),
        font_size=10.0,
    )

    assert placements[0].inline < placements[1].inline
    assert placements[0].inline + placements[0].inline_size <= placements[1].inline


def test_table_placements_reserve_the_declared_positive_gutter() -> None:
    placements = place_table_columns(
        columns=(("owner", "Owner"), ("status", "Status")),
        cells=(("a", "owner", "Firmware"), ("a", "status", "In progress")),
        bounds=(10.0, 0.0, 260.0, 20.0), font_metrics=FixedMetrics(), font_size=10.0, gutter=12.0,
    )
    assert placements[1].inline - (placements[0].inline + placements[0].inline_size) == 12.0


def test_table_placement_diagnoses_when_required_text_cannot_fit() -> None:
    with pytest.raises(LayoutError, match="E_LAYOUT_TABLE_OVERFLOW"):
        place_table_columns(
            columns=(("owner", "Owner"), ("status", "Status")),
            cells=(("a", "owner", "Firmware"), ("a", "status", "In progress")),
            bounds=(0.0, 0.0, 20.0, 20.0),
            font_metrics=FixedMetrics(),
            font_size=10.0,
        )


def test_ellipsize_allocation_preserves_a_minimum_for_each_column() -> None:
    placements = place_table_columns(
        columns=(("first", "Long heading"), ("second", "Another heading")),
        cells=(("a", "first", "a very long value"), ("a", "second", "another long value")),
        bounds=(0.0, 0.0, 60.0, 20.0), font_metrics=FixedMetrics(), font_size=10.0,
        overflow="ellipsize-with-source",
    )
    assert sum(item.inline_size for item in placements) == 60.0
    assert all(item.inline_size >= 20.0 for item in placements)
    assert all(item.inline_size <= item.natural_inline_size for item in placements)


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
    )

    tracks = place_mark_tracks(
        review_rows=rows,
        row_placements=row_placements,
        mark_block_size=10.0,
    )

    assert tracks[0].block == tracks[1].block
    assert tracks[0].actual_block == tracks[1].actual_block
