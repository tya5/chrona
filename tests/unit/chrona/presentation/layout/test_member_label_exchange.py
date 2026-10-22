from dataclasses import replace
from decimal import Decimal

from chrona.presentation.layout.labels import CollisionDomain, LabelRect, LabelRequest
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.surface_member_labels import place_member_labels
from chrona.presentation.layout.surface_quality import MarkPlacement, VisualRequest
from chrona.presentation.model.closure import IconAsset
from chrona.presentation.model.semantic_registry import inside_member_label_semantic
from chrona.presentation.model.style_rules import OccurrenceStyleIndex, OccurrenceStyleIntent, StyleOccurrenceKey
from chrona.presentation.model.theme_tokens import ThemeTokenView
from tests.unit.chrona.presentation.layout.test_member_label_required_phase import _placement_context


def _mark(placement_id: str, x: int) -> MarkPlacement:
    bounds = Rect(Decimal(x), Decimal(40), Decimal(10), Decimal(10))
    return MarkPlacement(placement_id, placement_id, bounds, (x, 45), (x + 10, 45),
                         slot_id="timeline", semantic_id="planned", mark_shape="point")


def _request(placement_id: str, host_id: str, content: str,
             anchor_x: int, candidates: tuple[str, ...], *, required=False) -> LabelRequest:
    return LabelRequest(placement_id, placement_id, content,
        LabelRect(anchor_x, 40, 10, 10), candidates, "text", "plot-label",
        CollisionDomain("timeline", "overlay"), "suppress", semantic_id="memberLabel",
        bounds=LabelRect(0, 38, 200, 16), inside_host_obstacle_id=host_id,
        required_before_routes=required)


def _hosted_context_and_obstacles(*, first_x=50, second_x=110, icon_on=None):
    first = _mark("planned:first:first", first_x)
    second = _mark("planned:second:second", second_x)
    context = replace(_placement_context(), marks=(first, second))
    context.layout_manifest.member_names = {"search": "full-band"}
    if icon_on is not None:
        context.request.theme_tokens.icon_ratios = lambda _role: (0.8, 0.1)
        context.request.visual_requests = (VisualRequest("text", (("placementId", icon_on),),
            "icon:test", side="leading", source_ref="/test/visuals/0"),)
        context.request.icon_assets = {"icon:test": IconAsset("test-icon", "svg",
            "sha256:test-icon", (10, 10), "Test icon", b"<svg/>")}
    obstacles = SurfaceObstacleIndex()
    for mark in (first, second):
        x, y, width, height = (float(mark.bounds.inline), float(mark.bounds.block),
                               float(mark.bounds.inline_size), float(mark.bounds.block_size))
        obstacles.add(SurfaceObstacle(mark.placement_id, "mark", "timeline",
            ObstacleRect(x, y, x + width, y + height)))
    return context, obstacles


def test_hosted_names_exchange_end_for_start_as_one_visible_batch():
    context, obstacles = _hosted_context_and_obstacles(
        first_x=60, second_x=120, icon_on="member-label:second")
    first = _request("member-label:first", "planned:first:first", "AAAA", 60, ("end", "start"))
    second = _request("member-label:second", "planned:second:second", "BB", 120, ("start",))

    batch = place_member_labels(context, (first, second), obstacles)

    by_id = {item.placement_id: item for item in batch.text}
    assert set(by_id) == {first.placement_id, second.placement_id}
    assert by_id[first.placement_id].selected_rung == "start"
    assert by_id[second.placement_id].selected_rung == "start"
    assert all(item.overflow != "suppressed" for item in by_id.values())
    assert {item.host_placement_id for item in by_id.values()} == {
        "planned:first:first", "planned:second:second"}
    assert {item.source_ref for item in batch.shapes} == {first.placement_id, second.placement_id}
    icon, = batch.icons
    assert icon.placement_id == f"visual:{second.placement_id}:leading"
    assert icon.host_placement_id == second.placement_id

    all_placement_ids = ([item.placement_id for item in batch.text]
        + [item.placement_id for item in batch.shapes]
        + [item.placement_id for item in batch.icons])
    assert len(all_placement_ids) == len(set(all_placement_ids))
    for placement in batch.text:
        text_obstacle, = (item for item in obstacles.all()
            if item.placement_id == placement.placement_id and item.obstacle_class == "text")
        footprint, = (item for item in obstacles.all()
            if item.placement_id == f"label-footprint:{placement.placement_id}")
        assert text_obstacle.geometry == ObstacleRect(
            float(placement.bounds.inline), float(placement.bounds.block),
            float(placement.bounds.inline + placement.bounds.inline_size),
            float(placement.bounds.block + placement.bounds.block_size))
        shape, = (item for item in batch.shapes if item.source_ref == placement.placement_id)
        assert footprint.geometry == ObstacleRect(
            float(shape.bounds.inline), float(shape.bounds.block),
            float(shape.bounds.inline + shape.bounds.inline_size),
            float(shape.bounds.block + shape.bounds.block_size))


def test_exchange_repositions_earlier_icon_chip_and_host_group_together():
    first_id = "member-label:first"
    context, obstacles = _hosted_context_and_obstacles(
        first_x=60, second_x=120, icon_on=first_id)
    first = _request(first_id, "planned:first:first", "AA", 60, ("end", "start"))
    second = _request("member-label:second", "planned:second:second", "BBBB", 120, ("start",))

    baseline_context, baseline_obstacles = _hosted_context_and_obstacles(
        first_x=60, second_x=120, icon_on=first_id)
    start_only = replace(first, candidates=("start",))
    baseline = place_member_labels(baseline_context, (start_only,), baseline_obstacles)
    old_end_context, old_end_obstacles = _hosted_context_and_obstacles(
        first_x=60, second_x=120, icon_on=first_id)
    end_only = replace(first, candidates=("end",))
    old_end = place_member_labels(old_end_context, (end_only,), old_end_obstacles)

    batch = place_member_labels(context, (first, second), obstacles)

    moved, = (item for item in batch.text if item.placement_id == first_id)
    expected, = baseline.text
    assert moved.selected_rung == "start" and moved.host_placement_id == "planned:first:first"
    assert moved.bounds == expected.bounds and moved.baseline == expected.baseline
    moved_chip, = (item for item in batch.shapes if item.source_ref == first_id)
    expected_chip, = (item for item in baseline.shapes if item.source_ref == first_id)
    old_end_chip, = (item for item in old_end.shapes if item.source_ref == first_id)
    assert moved_chip.bounds == expected_chip.bounds
    assert moved_chip.bounds != old_end_chip.bounds
    moved_icon, = (item for item in batch.icons if item.host_placement_id == first_id)
    expected_icon, = (item for item in baseline.icons if item.host_placement_id == first_id)
    old_end_icon, = (item for item in old_end.icons if item.host_placement_id == first_id)
    assert moved_icon.bounds == expected_icon.bounds
    assert moved_icon.bounds != old_end_icon.bounds
    footprint, = (item for item in obstacles.all()
        if item.placement_id == f"label-footprint:{first_id}")
    assert footprint.geometry == ObstacleRect(
        float(moved_chip.bounds.inline), float(moved_chip.bounds.block),
        float(moved_chip.bounds.inline + moved_chip.bounds.inline_size),
        float(moved_chip.bounds.block + moved_chip.bounds.block_size))


def test_hard_mark_prevents_exchange_and_failed_attempt_leaves_no_alternate_group():
    context, obstacles = _hosted_context_and_obstacles(first_x=60, second_x=120)
    blocker = SurfaceObstacle("hard-mark:start", "mark", "timeline",
        ObstacleRect(10, 38, 58, 54))
    obstacles.add(blocker)
    first = _request("member-label:first", "planned:first:first", "AAAA", 60, ("end", "start"))
    second = _request("member-label:second", "planned:second:second", "BBBB", 120, ("start",))

    batch = place_member_labels(context, (first, second), obstacles)

    by_id = {item.placement_id: item for item in batch.text}
    assert by_id[first.placement_id].selected_rung == "end"
    assert by_id[second.placement_id].overflow == "suppressed"
    assert obstacles.has(blocker.placement_id)
    assert obstacles.has(f"label-footprint:{first.placement_id}")
    assert not obstacles.has(f"label-footprint:{second.placement_id}")
    assert len([item for item in batch.shapes if item.source_ref == first.placement_id]) == 1
    assert not any(item.source_ref == second.placement_id for item in (*batch.shapes, *batch.icons))


def test_required_before_routes_name_is_not_moved_to_make_room_for_later_name():
    context, obstacles = _hosted_context_and_obstacles(first_x=60, second_x=120)
    first = _request("member-label:first", "planned:first:first", "AAAA", 60,
                     ("end", "start"), required=True)
    second = _request("member-label:second", "planned:second:second", "BBBB", 120, ("start",))

    batch = place_member_labels(context, (first, second), obstacles)

    by_id = {item.placement_id: item for item in batch.text}
    assert by_id[first.placement_id].selected_rung == "end"
    assert by_id[first.placement_id].required
    assert by_id[second.placement_id].overflow == "suppressed"


def test_separate_hard_mark_blocker_on_later_candidate_prevents_exchange():
    context, obstacles = _hosted_context_and_obstacles(first_x=60, second_x=120)
    # The final sliver intersects B's start footprint but lies beyond A's end footprint.
    blocker = SurfaceObstacle("later-only-hard-mark", "mark", "timeline",
        ObstacleRect(117, 38, 119, 52))
    obstacles.add(blocker)
    first = _request("member-label:first", "planned:first:first", "AAAA", 60, ("end", "start"))
    second = _request("member-label:second", "planned:second:second", "BBBB", 120, ("start",))

    batch = place_member_labels(context, (first, second), obstacles)

    by_id = {item.placement_id: item for item in batch.text}
    assert by_id[first.placement_id].selected_rung == "end"
    assert by_id[second.placement_id].overflow == "suppressed"
    assert obstacles.has(blocker.placement_id)
    assert obstacles.has(f"label-footprint:{first.placement_id}")
    assert not obstacles.has(f"label-footprint:{second.placement_id}")


def test_failed_exchange_with_no_alternative_keeps_accepted_group_unchanged():
    context, obstacles = _hosted_context_and_obstacles(first_x=60, second_x=120)
    first = _request("member-label:first", "planned:first:first", "AAAA", 60, ("end",))
    second = _request("member-label:second", "planned:second:second", "BBBB", 120, ("start",))
    baseline_obstacles = obstacles.copy()
    baseline = place_member_labels(context, (first,), baseline_obstacles)

    batch = place_member_labels(context, (first, second), obstacles)

    by_id = {item.placement_id: item for item in batch.text}
    assert by_id[first.placement_id] == baseline.text[0]
    assert by_id[second.placement_id].overflow == "suppressed"
    assert not obstacles.has(f"label-footprint:{second.placement_id}")
    assert obstacles.get(f"label-footprint:{first.placement_id}") == baseline_obstacles.get(
        f"label-footprint:{first.placement_id}")


def test_later_request_does_not_cascade_by_moving_an_already_exchanged_name():
    context, obstacles = _hosted_context_and_obstacles(first_x=60, second_x=120)
    third = _mark("planned:third:third", 155)
    context = replace(context, marks=(*context.marks, third))
    obstacles.add(SurfaceObstacle(third.placement_id, "mark", "timeline",
        ObstacleRect(155, 40, 165, 50)))
    first = _request("member-label:first", "planned:first:first", "AAAA", 60, ("end", "start"))
    second = _request("member-label:second", "planned:second:second", "BBBB", 120, ("start",))
    last = _request("member-label:third", third.placement_id, "CCCC", 155, ("start",))

    batch = place_member_labels(context, (first, second, last), obstacles)

    by_id = {item.placement_id: item for item in batch.text}
    assert by_id[first.placement_id].selected_rung == "start"
    assert by_id[second.placement_id].selected_rung == "start"
    assert by_id[last.placement_id].overflow == "suppressed"
    assert obstacles.has(f"label-footprint:{first.placement_id}")
    assert obstacles.has(f"label-footprint:{second.placement_id}")
    assert not obstacles.has(f"label-footprint:{last.placement_id}")


def test_exchange_selects_prepared_inside_role_and_replaces_complete_group():
    first_id = "member-label:first"
    first_host = MarkPlacement("planned:first:first", "planned:first:first",
        Rect(Decimal(20), Decimal(40), Decimal(60), Decimal(10)), (20, 45), (80, 45),
        slot_id="timeline", semantic_id="planned", mark_shape="span")
    second_host = _mark("planned:second:second", 140)
    context = replace(_placement_context(), marks=(first_host, second_host))
    context.layout_manifest.member_names = {"search": "full-band"}

    values = {
        "family": {"type": "fontFamily", "value": "sans"},
        "weight": {"type": "fontWeight", "value": 400},
        "line": {"type": "number", "value": 1.2},
        "spacing": {"type": "number", "value": 0},
        "transform": {"type": "textTransform", "value": "none"},
        "numeric": {"type": "numericSpacing", "value": "proportional"},
        "ink": {"type": "color", "value": "#202020"},
        "large-size": {"type": "number", "value": 10},
        "small-size": {"type": "number", "value": 6},
        "icon-scale": {"type": "number", "value": 0.8},
        "icon-gap": {"type": "number", "value": 0.1},
        "chip-padding": {"type": "number", "value": 0.1},
    }
    role_bindings = {}
    for role, size in (("member-end", "large-size"), ("member-inside", "small-size")):
        role_bindings[role] = {
            "fontFamily": "family", "fontWeight": "weight", "fontSize": size,
            "lineHeight": "line", "letterSpacing": "spacing", "textTransform": "transform",
            "numericSpacing": "numeric", "fill": "ink", "iconScale": "icon-scale",
            "iconGap": "icon-gap", "backgroundTreatment": "fill", "chipPadding": "chip-padding",
        }
    role_bindings["text"] = dict(role_bindings["member-end"])
    role_bindings["member-label-chip"] = {
        "fill": "ink", "backgroundTreatment": "fill", "chipPadding": "chip-padding",
    }
    context.request.theme_tokens = ThemeTokenView({
        "version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
        "body": {"values": values, "roles": role_bindings},
    })
    key = StyleOccurrenceKey("first", "primary", "memberLabel", "row", "first")
    inside_key = replace(key, semantic_id=inside_member_label_semantic("primary"))
    context.request.surface_content = replace(context.request.surface_content, style_intents=OccurrenceStyleIndex((
        OccurrenceStyleIntent(key, "member-end", None, ("rule:end",), ("rule:end",), ()),
        OccurrenceStyleIntent(inside_key, "member-inside", None,
                              ("rule:inside",), ("rule:inside",), ()),
    )))
    icon_request = VisualRequest("text", (("placementId", first_id),), "icon:test",
        side="leading", source_ref="/test/visuals/0")
    context.request.visual_requests = (icon_request,)
    context.request.icon_assets = {"icon:test": IconAsset(
        "test-icon", "svg", "sha256:test-icon", (10, 10), "Test icon", b"<svg/>")}

    first = replace(_request(first_id, "planned:first:first", "AAAA", 20, ("end", "inside")),
        anchor=LabelRect(20, 40, 60, 10), style_occurrence_key=key)
    second = _request("member-label:second", "planned:second:second", "BBBB", 140, ("start",))

    baseline_context = replace(context, marks=(first_host,))
    baseline_obstacles = SurfaceObstacleIndex()
    baseline_obstacles.add(SurfaceObstacle(first_host.placement_id, "mark", "timeline",
        ObstacleRect(20, 40, 80, 50)))
    baseline = place_member_labels(baseline_context, (replace(first, candidates=("inside",)),), baseline_obstacles)
    end_context = replace(context, marks=(first_host,))
    end_obstacles = SurfaceObstacleIndex()
    end_obstacles.add(SurfaceObstacle(first_host.placement_id, "mark", "timeline",
        ObstacleRect(20, 40, 80, 50)))
    end_only = place_member_labels(end_context, (replace(first, candidates=("end",)),), end_obstacles)
    obstacles = SurfaceObstacleIndex()
    for mark in (first_host, second_host):
        x, y, width, height = (float(mark.bounds.inline), float(mark.bounds.block),
                               float(mark.bounds.inline_size), float(mark.bounds.block_size))
        obstacles.add(SurfaceObstacle(mark.placement_id, "mark", "timeline",
            ObstacleRect(x, y, x + width, y + height)))

    batch = place_member_labels(context, (first, second), obstacles)

    moved, = (item for item in batch.text if item.placement_id == first_id)
    expected, = baseline.text
    original, = end_only.text
    assert original.selected_rung == "end" and original.theme_role == "member-end"
    assert original.bounds.inline_size > expected.bounds.inline_size
    assert moved.selected_rung == "inside"
    assert moved.theme_role == "member-inside"
    assert moved.font_size == expected.font_size == 6
    assert moved.host_placement_id == first_host.placement_id
    assert moved.style_occurrence_key == inside_key
    assert all(item.overflow != "suppressed" for item in batch.text)
    assert moved.bounds == expected.bounds and moved.baseline == expected.baseline
    assert moved.bounds.inline_size < 4 * 10
    moved_chip, = (item for item in batch.shapes if item.source_ref == first_id)
    expected_chip, = (item for item in baseline.shapes if item.source_ref == first_id)
    original_chip, = (item for item in end_only.shapes if item.source_ref == first_id)
    assert moved_chip.bounds == expected_chip.bounds
    assert moved_chip.bounds != original_chip.bounds
    moved_icon, = (item for item in batch.icons if item.host_placement_id == first_id)
    expected_icon, = (item for item in baseline.icons if item.host_placement_id == first_id)
    original_icon, = (item for item in end_only.icons if item.host_placement_id == first_id)
    assert moved_icon.bounds == expected_icon.bounds
    assert moved_icon.bounds != original_icon.bounds
    assert sum(item.source_ref == first_id for item in batch.shapes) == 1
    assert obstacles.get(f"label-footprint:{first_id}").geometry == (
        baseline_obstacles.get(f"label-footprint:{first_id}").geometry)
