from dataclasses import replace
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from chrona.presentation.layout.labels import CollisionDomain, LabelRect, LabelRequest
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex, obstacles_intersect,
)
from chrona.presentation.layout.surface_member_labels import (
    SurfaceMemberLabelContext, SurfaceMemberLabelRequests, build_member_label_requests,
    place_member_labels,
)
from chrona.presentation.layout.surface_quality import MarkPlacement, ScalePlacement, SlotPlacement
from chrona.presentation.model.surface_content import SummaryContent, SurfaceContentInput
from chrona.presentation.model.hierarchy_names import member_name_key
from tests.unit.chrona.presentation.layout.test_point_host_labels import _label_request_context
from chrona.core.forecast import ForecastItem
from chrona.presentation.model.projection import ForecastComparisonFact, WindowMode
import pytest


def _request(placement_id, semantic_id="memberLabel", *, required=False, rule_host=None):
    return LabelRequest(placement_id, placement_id, placement_id, LabelRect(20, 20, 10, 10),
        ("end", "start"), "text", "plot-label", CollisionDomain("timeline", "overlay"),
        "suppress", semantic_id=semantic_id, rule_host_obstacle_id=rule_host,
        required_before_routes=required)


def test_member_names_and_required_labels_precede_routes_for_both_policies():
    optional_name = _request("optional")
    required_name = _request("required", required=True)
    rule_label = _request("rule-label", "asOfLabel", rule_host="as-of")
    nonmember = _request("as-of-label", "asOfLabel")
    delta = _request("delta", "finishDelta")
    later = _request("later", "relationLabel")

    requests = SurfaceMemberLabelRequests(
        (optional_name, required_name, rule_label, nonmember, delta), (later,)
    )
    assert requests.routing_phases(first_fit=True) == (
        (rule_label, optional_name, required_name), (nonmember, delta, later))
    assert requests.routing_phases(first_fit=False) == (
        (rule_label, optional_name, required_name), (nonmember, delta, later))
    assert not _request("default").required_before_routes


def _forecast_context():
    context = _label_request_context()
    row = context.review_rows[0]
    row.items = (replace(row.items[0], forecast=ForecastComparisonFact(
        ForecastItem({"at": date(2026, 1, 12)}, False), 2)),)
    context.projection.rows = (row,)
    context.projection.lane_membership = None
    context.request.presentation_contract.labels.content = ("title", "finishDelta")
    return context


def test_forecast_delta_is_required_separate_from_optional_name_and_before_routes():
    context = _forecast_context()
    requests = build_member_label_requests(context)
    before, after = requests.routing_phases(first_fit=True)
    assert len(before) == 2 and not after
    delta, name = before
    assert delta.content == "+2d*" and delta.semantic_id == "forecastVarianceBehind"
    assert delta.overflow == "diagnose" and delta.required_before_routes
    assert name.content == "Review gate" and name.overflow == "suppress"
    assert delta.placement_id == "variance:child-row:gate"
    assert delta.lane_member_id is None  # No name preflight or suppression accounting.


def test_forecast_required_delta_outside_explicit_window_is_not_suppressed():
    context = _forecast_context()
    context.request.presentation_contract.labels.content = ("finishDelta",)
    context.projection.window_mode = WindowMode.EXPLICIT
    context.projection.window = (date(2026, 1, 1), date(2026, 1, 11))
    with pytest.raises(ValueError, match="E_PRESENTATION_LABEL_UNPLACEABLE"):
        build_member_label_requests(context)


def test_member_label_builder_marks_attached_and_key_row_names_required():
    attached_context = _label_request_context()
    attached_context.projection.lane_membership = None
    attached_row = attached_context.review_rows[0]
    attached_row.items = (replace(attached_row.items[0], attached_to="host"),)
    attached_context.request.surface_content.attached_labels = ((
        member_name_key(attached_row.items[0], attached_row.row_id), "Attached gate"),)
    attached, = build_member_label_requests(attached_context).pre_route
    assert attached.required_before_routes

    key_context = _label_request_context()
    key_context.projection.lane_membership = None
    key_context.review_rows[0].key_row = True
    key, = build_member_label_requests(key_context).pre_route
    assert key.required_before_routes


def test_required_intent_is_closed_even_if_request_arrives_in_post_route_partition():
    explicit = _request("explicit", required=True)
    diagnosed = replace(_request("diagnosed"), overflow="diagnose")
    optional = _request("optional")
    before, after = SurfaceMemberLabelRequests((), (explicit, diagnosed, optional)).routing_phases(first_fit=True)
    assert before == (explicit, diagnosed, optional)
    assert not after


def test_ordinary_finish_delta_stays_post_route_unless_required():
    name = _request("lane-name")
    delta = _request("lane-delta", "finishDelta")
    later = _request("post-route", "relationLabel")
    requests = SurfaceMemberLabelRequests((name, delta), (later,))
    assert requests.routing_phases(first_fit=False) == ((name,), (delta, later))
    assert requests.routing_phases(first_fit=True) == ((name,), (delta, later))
    required_delta = replace(delta, required_before_routes=True)
    requests = SurfaceMemberLabelRequests((name, required_delta), (later,))
    assert requests.routing_phases(first_fit=True) == ((required_delta, name), (later,))


class _Metric:
    content_identity = "sha256:test-font"

    def width(self, value, size, **_kwargs):
        return len(value) * size

    def cap_height_at(self, size):
        return size * .7


class _Theme:
    def text_treatment(self, _role):
        return SimpleNamespace(family="Test", weight=400, font_size=10, line_height=1.2,
            letter_spacing=0, transform="none", numeric_spacing="proportional", horizontal_scale=1)

    def label_chip(self, _role):
        return (0.2, 0.1)

    def label_chip_min_block(self, _role):
        return None

    def label_chip_shape(self, _role):
        from chrona.presentation.model.theme_tokens import RectangleChipShape
        return RectangleChipShape()

    def optional_token(self, *_args):
        return None


def _placement_context(*, slot_width=200):
    slot = SlotPlacement("timeline", "timeline", Rect(Decimal(0), Decimal(0), Decimal(slot_width), Decimal(100)))
    surface_content = SurfaceContentInput(
        table_columns=(), table_cells=(), relations=(), annotations=(), show_member_labels=False,
        label_placement="none", label_content=(), label_side="auto", label_overflow="visible-overflow",
        relation_overflow="visible-overflow", group_presentation="band", axis_tiers=(),
        axis_fiscal_start_month=1, as_of=None, as_of_label="As of", annotation_numbered=False,
        calendar_closed=(), calendar_exceptions=(), notes=(), legend_entries=(), coverage_text="",
        summary=SummaryContent(()), template_values=(), group_details=(), milestones=(),
        observation_columns=(), observation_rows=(),
    )
    request = SimpleNamespace(theme_tokens=_Theme(), font_metrics=_Metric(), visual_requests=(), icon_assets={},
        fixed_lane_preflight=None, capacity_short_sources=(), surface_content=surface_content)
    return SurfaceMemberLabelContext(request, SimpleNamespace(lane_membership=None),
        SimpleNamespace(member_names={}, row_distribution="auto"), {"timeline": slot},
        lambda _text: "timeline", (), (), (), (),
        ScalePlacement("surface", "scale", date(2026, 1, 1), date(2026, 2, 1), 0, 200, 0, 1), (),
        (0, 0, 200, 100), None)


def test_member_name_avoids_intrinsic_endpoint_ink_without_reserving_a_route():
    context = _placement_context()
    request = LabelRequest("member-label:a", "a", "Owner", LabelRect(80, 40, 10, 10),
        ("end", "start"), "text", "plot-label", CollisionDomain("timeline", "overlay"),
        "suppress", semantic_id="memberLabel")
    original = place_member_labels(context, (request,), SurfaceObstacleIndex()).text[0]
    bounds = original.bounds
    footprint = SurfaceObstacle("intrinsic-endpoint:a:end", "mark", "timeline",
        ObstacleRect(float(bounds.inline), float(bounds.block),
                     float(bounds.inline + bounds.inline_size),
                     float(bounds.block + bounds.block_size)))
    context = replace(context, intrinsic_endpoint_footprints=(footprint,))
    index = SurfaceObstacleIndex()

    batch = place_member_labels(context, (request,), index)

    placed, = batch.text
    assert placed.overflow != "suppressed" and placed.bounds != original.bounds
    ink = next(item.geometry for item in index.all()
               if item.placement_id == f"label-footprint:{request.placement_id}")
    assert not obstacles_intersect(ink, footprint.geometry)
    assert not index.has(footprint.placement_id)


@pytest.mark.parametrize("semantic_id", ("finishDelta", "forecastVarianceBehind"))
def test_pre_route_delta_avoids_intrinsic_endpoint_ink_and_keeps_clear_end(semantic_id):
    context = _placement_context()
    request = replace(_request(f"delta:{semantic_id}", semantic_id),
        content="+2d*" if semantic_id.startswith("forecast") else "+2d",
        overflow="diagnose" if semantic_id.startswith("forecast") else "visible-overflow",
        required_before_routes=True)

    clear = place_member_labels(context, (request,), SurfaceObstacleIndex())
    assert clear.text[0].selected_rung == "end"
    assert not any(item.startswith("I_LAYOUT_FINISH_DELTA_ANCHOR_FALLBACK:")
                   for item in clear.diagnostics)

    clear_bounds = clear.text[0].bounds
    footprint = SurfaceObstacle("intrinsic-endpoint:delta:end", "mark", "timeline",
        ObstacleRect(float(clear_bounds.inline), float(clear_bounds.block),
                     float(clear_bounds.inline + clear_bounds.inline_size),
                     float(clear_bounds.block + clear_bounds.block_size)))
    context = replace(context, intrinsic_endpoint_footprints=(footprint,))
    obstacles = SurfaceObstacleIndex()

    placed = place_member_labels(context, (request,), obstacles)

    assert placed.text[0].bounds != clear_bounds
    assert placed.text[0].overflow != "suppressed"
    if semantic_id.startswith("forecast"):
        assert placed.text[0].required
    fallback, = (item for item in placed.diagnostics
                 if item.startswith("I_LAYOUT_FINISH_DELTA_ANCHOR_FALLBACK:"))
    assert '"blockerPlacementIds":["intrinsic-endpoint:delta:end"]' in fallback
    placed_ink, = (item.geometry for item in obstacles.all()
                   if item.placement_id == f"label-footprint:{request.placement_id}")
    assert not obstacles_intersect(placed_ink, footprint.geometry)
    assert not obstacles.has(footprint.placement_id)


def test_other_label_queries_share_intrinsic_inventory_without_publishing_it():
    context = _placement_context()
    request = _request("relation-label", "relationLabel")
    clear = place_member_labels(context, (request,), SurfaceObstacleIndex())
    bounds = clear.text[0].bounds
    footprint = SurfaceObstacle("intrinsic-endpoint:other:end", "mark", "timeline",
        ObstacleRect(float(bounds.inline), float(bounds.block),
                     float(bounds.inline + bounds.inline_size),
                     float(bounds.block + bounds.block_size)))
    context = replace(context, intrinsic_endpoint_footprints=(footprint,))
    obstacles = SurfaceObstacleIndex()

    placed = place_member_labels(context, (request,), obstacles)

    assert placed.text[0].bounds != bounds
    assert not obstacles.has(footprint.placement_id)


def test_generic_required_text_translates_diagnose_into_bounded_refusal_not_suppression():
    context = _placement_context()
    request = replace(_request("variance:a", "finishDelta"), content="+2d*", overflow="diagnose")
    placed = place_member_labels(context, (request,), SurfaceObstacleIndex())
    assert placed.text[0].required and placed.text[0].content == "+2d*"
    blocked = SurfaceObstacleIndex()
    blocked.add(SurfaceObstacle("block", "mark", "timeline", ObstacleRect(0, 0, 200, 100)))
    with pytest.raises(ValueError, match="E_PRESENTATION_LABEL_UNPLACEABLE"):
        place_member_labels(context, (request,), blocked)


def test_final_ordinary_member_label_crosses_asof_rule():
    context = _placement_context()
    request = LabelRequest("member-label:a", "a", "Owner", LabelRect(80, 40, 10, 10),
        ("end", "start"), "text", "plot-label", CollisionDomain("timeline", "overlay"),
        "suppress", semantic_id="memberLabel")
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("as-of", "rule", "timeline", ObstacleSegment((105, 0), (105, 100))))

    batch = place_member_labels(context, (request,), index)

    assert len(batch.text) == 1 and batch.text[0].selected_rung == "end"
    footprint = next(item for item in index.all() if item.placement_id == "label-footprint:member-label:a")
    assert [item.placement_id for item in index.collisions(footprint.geometry, classes=("rule",))] == ["as-of"]


@pytest.mark.parametrize("required", (False, True))
@pytest.mark.parametrize("route_blocks_end", (False, True))
def test_moving_only_asof_line_preserves_completed_member_label(required, route_blocks_end):
    context = _placement_context()
    request = replace(LabelRequest("member-label:a", "a", "Owner", LabelRect(80, 40, 10, 10),
        ("end", "start"), "text", "plot-label", CollisionDomain("timeline", "overlay"),
        "suppress", semantic_id="memberLabel"), required_before_routes=required)
    route = (ObstacleSegment((105, 0), (105, 100)) if route_blocks_end
             else ObstacleSegment((0, 85), (200, 85)))
    fixed = (
        SurfaceObstacle("a", "mark", "timeline", ObstacleRect(80, 40, 90, 50)),
        SurfaceObstacle("fixed-route", "dependency-route", "timeline", route,
                        route_owner_id="relation:fixed"),
        SurfaceObstacle("deadlineMark:fixed", "rule", "timeline", ObstacleSegment((180, 0), (180, 100))),
    )
    baseline_index = SurfaceObstacleIndex()
    baseline_index.extend(fixed)
    baseline = place_member_labels(context, (request,), baseline_index)
    assert len(baseline.text) == 1
    assert baseline.text[0].selected_rung == ("start" if route_blocks_end else "end")
    crossed = set()
    for position in (20, 60, 95, 105, 145, 190):
        line = SurfaceObstacle("as-of", "rule", "timeline",
                               ObstacleSegment((position, 0), (position, 100)))
        index = SurfaceObstacleIndex()
        index.extend((*fixed, line))
        actual = place_member_labels(context, (request,), index)
        assert actual == baseline  # Text, geometry, decisions and diagnostics.
        assert line in index.all()  # The exception never removes the shared route/annotation obstacle.
        assert tuple(item for item in index.all() if item.placement_id != "as-of") == baseline_index.all()
        footprint = next(item for item in index.all() if item.placement_id == "label-footprint:member-label:a")
        crossed.add(any(item.placement_id == "as-of"
                        for item in index.collisions(footprint.geometry, classes=("rule",))))
    assert crossed == {False, True}, "the control must move the line into and out of the actual footprint"


def test_member_name_still_avoids_deadline_rule_while_crossing_asof():
    context = _placement_context()
    request = LabelRequest("member-label:a", "a", "Owner", LabelRect(80, 40, 10, 10),
        ("end", "start"), "text", "plot-label", CollisionDomain("timeline", "overlay"),
        "suppress", semantic_id="memberLabel")
    index = SurfaceObstacleIndex()
    index.extend((
        SurfaceObstacle("as-of", "rule", "timeline", ObstacleSegment((105, 0), (105, 100))),
        SurfaceObstacle("deadlineMark:critical:segment:0", "rule", "timeline",
                        ObstacleSegment((95, 0), (95, 100))),
    ))

    batch = place_member_labels(context, (request,), index)

    assert len(batch.text) == 1 and batch.text[0].selected_rung == "start"
    assert index.has("as-of") and index.has("deadlineMark:critical:segment:0")


def test_required_member_name_also_crosses_asof_rule():
    context = _placement_context()
    request = replace(LabelRequest("member-label:a", "a", "Owner", LabelRect(80, 40, 10, 10),
        ("end", "start"), "text", "plot-label", CollisionDomain("timeline", "overlay"),
        "suppress", semantic_id="memberLabel"), required_before_routes=True)
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("as-of", "rule", "timeline", ObstacleSegment((105, 0), (105, 100))))

    batch = place_member_labels(context, (request,), index)

    assert len(batch.text) == 1 and batch.text[0].selected_rung == "end"
    assert index.has("as-of")
