"""Direct tests for the hidden #467 lane preflight contract."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.lane_allocation import (
    LaneCandidate, LaneMark, LaneMarkFacet, LaneMember,
)
from chrona.presentation.layout.obstacles import ObstacleRect
from chrona.presentation.layout.lane_preflight import (
    LaneInlineFrame, LaneMeasurementIdentity, assert_lane_inline_stable,
    assert_lane_plan_compatible, lane_inline_frame_for_manifest, lane_table_measurement_content,
    preflight_surface_lanes,
)
from chrona.presentation.layout.model import LayoutDecision, LayoutError, LayoutManifest, Rect
from chrona.presentation.layout.surface_composer import compose_surface_layout, timeline_content_block_requirement
from chrona.presentation.layout.surface_quality import SurfaceLayoutRequest
from chrona.presentation.layout.sources import MeasuredSources
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


def test_lane_inline_frame_reads_actual_solved_table_and_timeline_bounds():
    manifest = LayoutManifest(
        "profile", "sha256:test", "block", "inline",
        Rect(Decimal(0), Decimal(0), Decimal(200), Decimal(100)),
        (LayoutDecision("table", "slot", Rect(Decimal(0), Decimal(0), Decimal(30), Decimal(40)), source="table"),
         LayoutDecision("timeline", "slot", Rect(Decimal(30), Decimal(0), Decimal(100), Decimal(40)), source="timeline")),
    )
    frame = lane_inline_frame_for_manifest(manifest, window=(date(2026, 1, 1), date(2026, 1, 11)))
    assert frame == LaneInlineFrame(Decimal(0), Decimal(30), Decimal(30), Decimal(100), Decimal(10))
    with pytest.raises(LayoutError, match="E_LAYOUT_LANE_SEED_INVALID"):
        lane_inline_frame_for_manifest(replace(manifest, decisions=()),
                                       window=(date(2026, 1, 1), date(2026, 1, 11)))


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


def test_final_composer_checks_seed_frame_identity_and_cutoff_before_geometry():
    identity = LaneMeasurementIdentity("theme:1", "font:1", "scale:1")
    plan = preflight_surface_lanes(
        [_candidate("task", 10, 20)], seed_inline_frame=_frame(),
        measurement_identity=identity, as_of=date(2026, 1, 5),
        group_titles={"systems": "Systems"}, candidate_titles={"task": "Task"},
        lane_label="group", include_count=False, mark_row_height=10, label_row_height=10,
    )
    window = (date(2026, 1, 1), date(2026, 4, 11))
    decisions = tuple(LayoutDecision(name, "slot", bounds, source=name) for name, bounds in (
        ("title", Rect(Decimal(0), Decimal(0), Decimal(130), Decimal(10))),
        ("table", Rect(Decimal(0), Decimal(10), Decimal(30), Decimal(40))),
        ("timeline", Rect(Decimal(30), Decimal(10), Decimal(100), Decimal(40))),
        ("timeline-axis", Rect(Decimal(30), Decimal(50), Decimal(100), Decimal(10))),
    ))
    manifest = LayoutManifest("profile", "sha256:test", "block", "inline",
                              Rect(Decimal(0), Decimal(0), Decimal(130), Decimal(60)), decisions)
    request = SurfaceLayoutRequest(
        projection=SimpleNamespace(window=window),
        layout_manifest=manifest, measured_sources=MeasuredSources({}, {}, {}),
        surface_content=SimpleNamespace(as_of=date(2026, 1, 6)),
        lane_plan=plan, lane_measurement_identity=identity,
    )
    with pytest.raises(LayoutError, match="E_LAYOUT_LANE_PLAN_INVALID"):
        compose_surface_layout(request)
    with pytest.raises(LayoutError, match="E_LAYOUT_LANE_INLINE_UNSTABLE"):
        compose_surface_layout(replace(request, surface_content=SimpleNamespace(as_of=plan.as_of),
                                       layout_manifest=replace(manifest, decisions=decisions[:2] + (
                                           replace(decisions[2], bounds=Rect(Decimal(30), Decimal(10), Decimal(99), Decimal(40))),
                                           decisions[3]))))


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
