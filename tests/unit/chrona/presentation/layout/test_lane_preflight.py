"""Direct tests for the hidden #467 lane preflight contract."""
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from chrona.presentation.layout.lane_allocation import (
    LaneCandidate, LaneMark, LaneMarkFacet, LaneMember,
)
from chrona.presentation.layout.obstacles import ObstacleRect
from chrona.presentation.layout.lane_preflight import (
    LaneInlineFrame, LaneMeasurementIdentity, assert_lane_inline_stable,
    assert_lane_plan_compatible, lane_table_measurement_content,
    preflight_surface_lanes,
)
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_composer import timeline_content_block_requirement
from chrona.presentation.layout.sources import SourceInput, measure_sources


def _candidate(item_id, left, right, *, width=50, predecessors=()):
    mark = LaneMark(left, right, (LaneMarkFacet(
        f"{item_id}:planned", f"row:{item_id}", item_id, f"project:{item_id}",
        "primary", "planned", f"planned:{item_id}", "Rect",
        (("rect", ((left, 0.0), (right, 10.0))),),
        (left, 0.0, right, 10.0), ObstacleRect(left, 0, right, 10),
    ),))
    return LaneCandidate(item_id, "systems", (left, right, item_id, item_id),
                         mark, width, predecessors=predecessors)


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


def test_plan_retains_exact_candidate_facet_closure_and_selected_cutoff():
    candidate = _candidate("task", 10, 20)
    selected_as_of = date(2026, 9, 27)
    identity = LaneMeasurementIdentity("theme:1", "font:1", "scale:1")
    plan = preflight_surface_lanes(
        [candidate], seed_inline_frame=_frame(), measurement_identity=identity,
        as_of=selected_as_of, group_titles={"systems": "Systems"},
        candidate_titles={"task": "Task"}, lane_label="group", include_count=False,
        mark_row_height=10, label_row_height=10,
    )
    assert plan.candidates == (candidate,)
    assert plan.candidates[0].mark.facets == candidate.mark.facets
    assert plan.as_of == selected_as_of
    assert_lane_plan_compatible(
        plan, final_inline_frame=_frame(), measurement_identity=identity, as_of=selected_as_of,
    )
    with pytest.raises(LayoutError, match="E_LAYOUT_LANE_PLAN_INVALID"):
        assert_lane_plan_compatible(
            plan, final_inline_frame=_frame(), measurement_identity=identity,
            as_of=date(2026, 9, 28),
        )
    assert timeline_content_block_requirement(
        projection=None, group_presentation="header", metric_values={},
        lane_plan=plan,
    ) == plan.natural_block_requirement


def test_plan_requires_bijection_between_closed_members_and_allocation():
    candidate = _candidate("task", 10, 20)
    plan = preflight_surface_lanes(
        [candidate], seed_inline_frame=_frame(),
        measurement_identity=LaneMeasurementIdentity("theme:1", "font:1", "scale:1"),
        group_titles={"systems": "Systems"}, candidate_titles={"task": "Task"},
        lane_label="group", include_count=False, mark_row_height=10, label_row_height=10,
    )
    broken_lane = replace(plan.allocation.lanes[0], members=())
    with pytest.raises(LayoutError, match="E_LAYOUT_LANE_PLAN_INVALID"):
        replace(plan, allocation=replace(plan.allocation, lanes=(broken_lane,)))


def test_lane_table_count_includes_attached_item_but_not_comparison_facet():
    host_plan = LaneMarkFacet(
        "host:planned", "row:host", "host", "project:host", "primary", "planned",
        "planned:row:host", "Rect", (("rect", ((0.0, 0.0), (10.0, 10.0))),),
        (0, 0, 10, 10), ObstacleRect(0, 0, 10, 10),
    )
    host_snapshot = LaneMarkFacet(
        "host:snapshot", "row:snapshot", "snapshot", "baseline:host", "snapshot", "snapshot",
        "snapshot:row:snapshot", "Rect", (("rect", ((0.0, 0.0), (10.0, 10.0))),),
        (0, 0, 10, 10), ObstacleRect(0, 0, 10, 10), overlay_with=("host:planned",),
    )
    attached_point = LaneMarkFacet(
        "gate:planned", "row:gate", "gate", "project:gate", "primary", "planned",
        "planned:row:gate", "Symbol", (("move", ((5.0, 0.0),)), ("line", ((6.0, 1.0),))),
        (5, 0, 6, 1), ObstacleRect(5, 0, 6, 1), overlay_with=("host:planned", "host:snapshot"),
    )
    host_mark = LaneMark(0, 10, (host_plan, host_snapshot))
    candidate = LaneCandidate(
        "host", "systems", (0,), host_mark, 5,
        bundle=(LaneMember("host", host_mark, 5),
                LaneMember("gate", LaneMark(5, 6, (attached_point,)), 5)),
    )
    plan = preflight_surface_lanes(
        [candidate], seed_inline_frame=_frame(),
        measurement_identity=LaneMeasurementIdentity("theme:1", "font:1", "scale:1"),
        group_titles={"systems": "Systems"}, candidate_titles={"host": "Host"},
        lane_label="group", include_count=True, mark_row_height=10, label_row_height=1,
        canvas_left=0, canvas_right=100,
    )
    assert plan.allocation.lanes[0].members == ("host", "gate")
    assert plan.table_cells[0].count == 2
