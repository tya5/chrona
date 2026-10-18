from dataclasses import replace
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from chrona.presentation.layout.labels import CollisionDomain, LabelRect, LabelRequest
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.surface_member_labels import (
    SurfaceMemberLabelContext, SurfaceMemberLabelRequests, build_member_label_requests,
    place_member_labels,
)
from chrona.presentation.layout.surface_quality import MarkPlacement, ScalePlacement, SlotPlacement
from chrona.presentation.model.surface_content import SummaryContent, SurfaceContentInput
from tests.unit.chrona.presentation.layout.test_point_host_labels import _label_request_context
from chrona.core.forecast import ForecastItem
from chrona.presentation.model.projection import ForecastComparisonFact, WindowMode
import pytest


def _request(placement_id, semantic_id="memberLabel", *, required=False, rule_host=None):
    return LabelRequest(placement_id, placement_id, placement_id, LabelRect(20, 20, 10, 10),
        ("end", "start"), "text", "plot-label", CollisionDomain("timeline", "overlay"),
        "suppress", semantic_id=semantic_id, rule_host_obstacle_id=rule_host,
        required_before_routes=required)


def test_routing_phases_keep_required_rule_and_nonmember_labels_before_routes():
    optional_name = _request("optional")
    required_name = _request("required", required=True)
    rule_label = _request("rule-label", rule_host="as-of")
    nonmember = _request("as-of-label", "asOfLabel")
    delta = _request("delta", "finishDelta")
    later = _request("later", "relationLabel")

    before, after = SurfaceMemberLabelRequests(
        (optional_name, required_name, rule_label, nonmember, delta), (later,)
    ).routing_phases(first_fit=True)

    assert before == (required_name, rule_label, nonmember)
    assert after == (optional_name, delta, later)
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
    assert len(before) == 1 and len(after) == 1
    delta, name = before[0], after[0]
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
    attached_context.request.surface_content.attached_labels = (("gate", "Attached gate"),)
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
    assert before == (explicit, diagnosed)
    assert after == (optional,)


def test_best_keeps_the_existing_pre_route_lane_names_and_deltas():
    name = _request("lane-name")
    delta = _request("lane-delta", "finishDelta")
    later = _request("post-route")
    requests = SurfaceMemberLabelRequests((name, delta), (later,))
    assert requests.routing_phases(first_fit=False) == ((name, delta), (later,))
    assert requests.routing_phases(first_fit=True) == ((), (name, delta, later))


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


def test_reserve_only_uses_rule_obstacle_and_registers_full_candidate_footprint():
    context = _placement_context()
    request = LabelRequest("member-label:a", "a", "Owner", LabelRect(80, 40, 10, 10),
        ("end", "start"), "text", "plot-label", CollisionDomain("timeline", "overlay"),
        "suppress", semantic_id="memberLabel")
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("as-of", "rule", "timeline", ObstacleSegment((105, 0), (105, 100))))

    batch = place_member_labels(context, (request,), index, reserve_only=True)

    assert len(batch.text) == 1 and batch.text[0].selected_rung == "start"
    assert index.has("member-label:a")
    footprint = next(item for item in index.all() if item.placement_id == "label-footprint:member-label:a")
    assert footprint.obstacle_class == "label-visual"
    assert footprint.geometry.left < footprint.geometry.right
    assert not index.collisions(footprint.geometry, classes=("rule",))
    assert not batch.diagnostics


def test_generic_required_text_translates_diagnose_into_bounded_refusal_not_suppression():
    context = _placement_context()
    request = replace(_request("variance:a", "finishDelta"), content="+2d*", overflow="diagnose")
    placed = place_member_labels(context, (request,), SurfaceObstacleIndex())
    assert placed.text[0].required and placed.text[0].content == "+2d*"
    blocked = SurfaceObstacleIndex()
    blocked.add(SurfaceObstacle("block", "mark", "timeline", ObstacleRect(0, 0, 200, 100)))
    with pytest.raises(ValueError, match="E_PRESENTATION_LABEL_UNPLACEABLE"):
        place_member_labels(context, (request,), blocked)


def test_final_ordinary_member_label_avoids_asof_rule():
    context = _placement_context()
    request = LabelRequest("member-label:a", "a", "Owner", LabelRect(80, 40, 10, 10),
        ("end", "start"), "text", "plot-label", CollisionDomain("timeline", "overlay"),
        "suppress", semantic_id="memberLabel")
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("as-of", "rule", "timeline", ObstacleSegment((105, 0), (105, 100))))

    batch = place_member_labels(context, (request,), index)

    assert len(batch.text) == 1 and batch.text[0].selected_rung == "start"
    footprint = next(item for item in index.all() if item.placement_id == "label-footprint:member-label:a")
    assert not index.collisions(footprint.geometry, classes=("rule",))


def test_reserve_only_does_not_register_unavailable_or_out_of_slot_candidates():
    request = LabelRequest("member-label:a", "a", "Owner", LabelRect(80, 40, 10, 10),
        ("end",), "text", "plot-label", CollisionDomain("timeline", "overlay"),
        "visible-overflow", bounds=LabelRect(0, 0, 200, 100), semantic_id="memberLabel")
    # The measured candidate fits the placement bounds but escapes the actual viewport slot.
    index = SurfaceObstacleIndex()
    batch = place_member_labels(_placement_context(slot_width=90), (request,), index, reserve_only=True)
    assert not batch.text
    assert not index.all()
    assert not batch.diagnostics

    both_sides = replace(request, candidates=("end", "start"))
    index = SurfaceObstacleIndex()
    batch = place_member_labels(_placement_context(slot_width=90), (both_sides,), index, reserve_only=True)
    assert len(batch.text) == 1 and batch.text[0].selected_rung == "start"

    blocked = SurfaceObstacleIndex()
    blocked.add(SurfaceObstacle("as-of", "rule", "timeline", ObstacleRect(0, 0, 200, 100)))
    only_end = replace(request, candidates=("end",), bounds=None, overflow="visible-overflow")
    batch = place_member_labels(_placement_context(), (only_end,), blocked, reserve_only=True)
    assert not batch.text
    assert not any(item.placement_id.startswith("label-footprint:") for item in blocked.all())
    assert not batch.diagnostics


def test_unavailable_optional_associated_reservation_does_not_apply_final_visible_overflow_failure():
    context = _placement_context()
    host = MarkPlacement("planned:a", "a", Rect(Decimal(80), Decimal(40), Decimal(10), Decimal(10)),
                         (80, 45), (90, 45), semantic_id="planned")
    context = replace(context, marks=(host,))
    request = LabelRequest("member-label:a", "a", "Owner", LabelRect(80, 40, 10, 10),
        ("end", "start"), "text", "plot-label", CollisionDomain("timeline", "overlay"),
        "visible-overflow", semantic_id="memberLabel", inside_host_obstacle_id="planned:a")
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("as-of", "rule", "timeline", ObstacleRect(0, 0, 200, 100)))
    before = index.all()

    batch = place_member_labels(context, (request,), index, reserve_only=True)

    assert not batch.text and not batch.diagnostics
    assert index.all() == before
