"""Direct tests for the hidden #467 lane preflight contract."""
from decimal import Decimal

import pytest

from chrona.presentation.layout.lane_allocation import LaneCandidate, LaneMark
from chrona.presentation.layout.lane_preflight import (
    LaneInlineFrame, LaneMeasurementIdentity, assert_lane_inline_stable, lane_table_measurement_content,
    preflight_surface_lanes,
)
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.sources import SourceInput, measure_sources


def _candidate(item_id, left, right, *, width=50, predecessors=()):
    return LaneCandidate(item_id, "systems", (left, right, item_id, item_id),
                         LaneMark(left, right), width, predecessors=predecessors)


def _frame(timeline_size="100"):
    return LaneInlineFrame(Decimal("0"), Decimal("30"), Decimal("30"),
                           Decimal(timeline_size), Decimal("1"))


def test_preflight_freezes_three_row_natural_extent_identity_chain_and_cells():
    candidates = (
        _candidate("structure", 10, 20),
        _candidate("avionics", 55, 65, predecessors=(("r1", "structure"),)),
        _candidate("bus-test", 70, 80, predecessors=(("r2", "avionics"),)),
    )
    plan = preflight_surface_lanes(
        candidates, seed_inline_frame=_frame(),
        measurement_identity=LaneMeasurementIdentity("theme:1", "font:1", "scale:1"),
        group_titles={"systems": "Systems"},
        candidate_titles={"structure": "Structure", "avionics": "Avionics", "bus-test": "Bus test"},
        lane_label="group", include_count=True, mark_row_height=10, label_row_height=10,
        group_header_block_size=Decimal("5"), canvas_left=0, canvas_right=100,
    )
    assert len(plan.allocation.lanes) == 1
    lane = plan.allocation.lanes[0]
    assert lane.lane_id == "lane:gsystems:structure"
    assert lane.members == ("structure", "avionics", "bus-test")
    assert lane.placements["bus-test"].level == "label-row-3-end"
    assert lane.block_extent == 40
    assert plan.natural_block_requirement == Decimal("45.0")
    assert plan.group_block_requirements == (("systems", Decimal("45.0")),)
    assert plan.table_cells[0].label == "Systems"
    assert plan.table_cells[0].count == 3


def test_lane_table_envelope_contains_all_candidate_names_and_count_bound():
    table = lane_table_measurement_content(
        lane_label="lane", include_count=True, group_titles={"systems": "Systems"},
        candidate_titles={"a": "Structure", "b": "Avionics"}, selected_item_count=26,
    )
    assert tuple(column.column_id for column in table.columns) == ("Lane", "Items")
    assert {cell.content for cell in table.cells if cell.column_id == "Lane"} == {
        "Avionics", "Structure", "Systems",
    }
    assert next(cell.content for cell in table.cells if cell.column_id == "Items") == "26"

    class Metrics:
        content_identity = "sha256:lane-test"
        def width(self, value, size): return len(value) * size / 2
        def baseline(self, top, size, line_height): return top + size

    # Exercise the same measured-column path as ordinary #487 table content.
    from tests.unit.chrona.presentation.layout.test_sources import theme
    measured = measure_sources({"table": SourceInput(table=table)}, theme(), font_metrics=Metrics())
    assert measured.measurements["table"].min_inline > Decimal("120")


def test_seed_and_final_lane_inline_frame_must_match_exactly():
    assert_lane_inline_stable(_frame(), _frame())
    with pytest.raises(LayoutError, match="E_LAYOUT_LANE_INLINE_UNSTABLE"):
        assert_lane_inline_stable(_frame(), _frame("99"))
