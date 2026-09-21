from types import SimpleNamespace

from chrona.presentation.layout.presentation import place_rows, place_table_columns


class FixedMetrics:
    def width(self, value: str, size: float) -> float:
        return len(value) * size


def test_table_placements_are_ordered_and_non_overlapping() -> None:
    placements = place_table_columns(
        columns=(("owner", "Owner"), ("status", "Status")),
        cells=(("a", "owner", "Firmware"), ("a", "status", "In progress")),
        bounds=(10.0, 0.0, 200.0, 20.0),
        font_metrics=FixedMetrics(),
        font_size=10.0,
    )

    assert placements[0].inline < placements[1].inline
    assert placements[0].inline + placements[0].inline_size <= placements[1].inline


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
