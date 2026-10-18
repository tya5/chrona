"""On-demand repair keeps the exact preceding label inventory when attributing routes."""
from dataclasses import replace
from decimal import Decimal

import pytest

from chrona.presentation.layout import surface_member_labels as owner
from chrona.presentation.layout.labels import LabelPlacement, LabelRect, LabelRequest
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.surface_quality import CollisionDomain, MarkPlacement, TextPlacement


def _request():
    return LabelRequest("name", "item", "Name", LabelRect(0, 0, 10, 10),
        ("end", "start"), "text", "plot-label", CollisionDomain("timeline", "overlay"),
        "suppress", semantic_id="memberLabel")


def _index():
    index = SurfaceObstacleIndex()
    index.extend((
        SurfaceObstacle("prior-name", "text", "timeline", ObstacleRect(50, 0, 60, 10)),
        SurfaceObstacle("as-of", "rule", "timeline", ObstacleSegment((70, 0), (70, 100), 1)),
        SurfaceObstacle("route", "dependency-route", "timeline", ObstacleSegment((20, 0), (20, 100), 1)),
    ))
    return index


def test_route_only_probe_retains_preceding_text_and_rule_and_uses_exact_footprint(monkeypatch):
    index = _index()
    before = index.all()

    def probe(context, requests, obstacles, *, reserve_only, _prepared=None):
        assert reserve_only and len(requests) == 1
        if requests[0].candidates == ("start",):
            return owner.SurfaceMemberLabelsBatch((), (), (), (), (), (), (), frozenset())
        assert requests[0].candidates == ("end",)
        assert obstacles.has("prior-name") and obstacles.has("as-of")
        assert not obstacles.has("route")
        text = TextPlacement("name", "item", "Name", Rect(Decimal(15), Decimal(10), Decimal(10), Decimal(10)),
            "text", semantic_id="memberLabel", selected_rung="end")
        obstacles.add(SurfaceObstacle("label-footprint:name", "label-visual", "timeline",
                                      ObstacleRect(15, 10, 25, 20)))
        return owner.SurfaceMemberLabelsBatch((text,), (), (), (), (), (), (), frozenset())

    monkeypatch.setattr(owner, "place_member_labels", probe)
    reservations = owner._route_blocked_candidate(None, _request(), None, index)
    assert len(reservations) == 1
    reservation = reservations[0]
    assert reservation.text.selected_rung == "end"
    assert not reservation.text.required
    assert [item.placement_id for item in reservation.obstacles] == ["label-footprint:name"]
    assert index.all() == before


def test_visible_later_rung_does_not_trigger_a_retry_probe(monkeypatch):
    def unexpected(*_args, **_kwargs):
        raise AssertionError("visible member labels are not retried")

    monkeypatch.setattr(owner, "place_member_labels", unexpected)
    assert owner._route_blocked_candidate(None, _request(),
        LabelPlacement("start", LabelRect(0, 0, 10, 10)), _index()) == ()


def _candidate_probe(monkeypatch, *, end=(10, 10, 20, 20), start=(40, 10, 50, 20)):
    boxes = {"end": ObstacleRect(*end), "start": ObstacleRect(*start)}

    def probe(_context, requests, obstacles, *, reserve_only, _prepared=None):
        assert reserve_only and len(requests) == 1
        request = requests[0]
        side = request.candidates[0]
        box = boxes[side]
        if obstacles.collisions(box, classes=("mark", "text", "label-visual", "route-reserve", "rule")):
            return owner.SurfaceMemberLabelsBatch((), (), (), (), (), (), (), frozenset())
        text = TextPlacement(request.placement_id, request.source_ref, request.content,
            Rect(Decimal(box.left), Decimal(box.top), Decimal(box.right - box.left), Decimal(box.bottom - box.top)),
            "text", semantic_id="memberLabel", selected_rung=side)
        # The visual footprint is deliberately larger than the text bounds, as with a chip.
        visual = ObstacleRect(box.left - 2, box.top - 2, box.right + 2, box.bottom + 2)
        obstacles.add(SurfaceObstacle(request.placement_id, "text", "timeline", box))
        obstacles.add(SurfaceObstacle(f"label-footprint:{request.placement_id}", "label-visual",
                                      "timeline", visual))
        return owner.SurfaceMemberLabelsBatch((text,), (), (), (), (), (), (), frozenset())

    monkeypatch.setattr(owner, "place_member_labels", probe)


def test_candidate_cost_counts_route_instances_not_segments_and_preserves_tie_order(monkeypatch):
    _candidate_probe(monkeypatch)
    index = SurfaceObstacleIndex()
    # Later declared `start` crosses two distinct route instances; `end` crosses
    # two segments from one instance and therefore has lower disruption cost.
    index.extend((
        SurfaceObstacle("end:a", "dependency-route", "timeline",
            ObstacleSegment((0, 15), (30, 15)), route_owner_id="route:a"),
        SurfaceObstacle("end:a:arc", "dependency-route", "timeline",
            ObstacleSegment((0, 16), (30, 16)), route_owner_id="route:a"),
        SurfaceObstacle("start:a", "dependency-route", "timeline",
            ObstacleSegment((30, 15), (60, 15)), route_owner_id="route:a"),
        SurfaceObstacle("start:b", "dependency-route", "timeline",
            ObstacleSegment((30, 16), (60, 16)), route_owner_id="route:b"),
    ))

    result = owner._route_blocked_candidate(None, _request(), None, index)

    assert tuple(item.text.selected_rung for item in result) == ("end", "start")
    assert {item.placement_id for item in result[0].obstacles} == {"name", "label-footprint:name"}


def test_declared_candidate_rank_breaks_equal_route_disruption_cost(monkeypatch):
    _candidate_probe(monkeypatch)
    index = SurfaceObstacleIndex()
    index.extend((
        SurfaceObstacle("end", "dependency-route", "timeline",
            ObstacleSegment((0, 15), (30, 15)), route_owner_id="route:end"),
        SurfaceObstacle("start", "dependency-route", "timeline",
            ObstacleSegment((30, 15), (60, 15)), route_owner_id="route:start"),
    ))

    result = owner._route_blocked_candidate(None, _request(), None, index)

    assert result[0].text.selected_rung == "end"


def test_ownerless_route_paint_counts_separately_and_full_visual_footprint_is_used(monkeypatch):
    # The end text box itself is clear; its wider label/chip footprint intersects
    # two independent ownerless paint obstacles. The start candidate hits one
    # completed logical route and should therefore win despite its later rung.
    _candidate_probe(monkeypatch)
    index = SurfaceObstacleIndex()
    index.extend((
        SurfaceObstacle("end:one", "dependency-route", "timeline",
            ObstacleSegment((8, 9), (22, 9))),
        SurfaceObstacle("end:two", "dependency-route", "timeline",
            ObstacleSegment((8, 21), (22, 21))),
        SurfaceObstacle("start:a", "dependency-route", "timeline",
            ObstacleSegment((30, 15), (60, 15)), route_owner_id="route:a"),
        SurfaceObstacle("start:a:arc", "dependency-route", "timeline",
            ObstacleSegment((30, 16), (60, 16)), route_owner_id="route:a"),
    ))

    result = owner._route_blocked_candidate(None, _request(), None, index)

    assert result[0].text.selected_rung == "start"


def test_ownerless_placement_id_cannot_alias_a_logical_route_owner(monkeypatch):
    _candidate_probe(monkeypatch)
    index = SurfaceObstacleIndex()
    index.extend((
        SurfaceObstacle("route-segment", "dependency-route", "timeline",
            ObstacleSegment((0, 15), (30, 15)), route_owner_id="shared"),
        SurfaceObstacle("shared", "dependency-route", "timeline",
            ObstacleSegment((0, 16), (30, 16))),
        SurfaceObstacle("start", "dependency-route", "timeline",
            ObstacleSegment((30, 15), (60, 15)), route_owner_id="route:start"),
    ))

    result = owner._route_blocked_candidate(None, _request(), None, index)

    # The end candidate intersects owner `shared` and ownerless paint `shared`;
    # tagging the two identity namespaces keeps its cost at two, so start wins.
    assert result[0].text.selected_rung == "start"


def test_required_and_nonroute_blockers_are_not_released_for_a_route_candidate(monkeypatch):
    _candidate_probe(monkeypatch)
    index = SurfaceObstacleIndex()
    index.extend((
        SurfaceObstacle("required-name", "text", "timeline", ObstacleRect(7, 7, 23, 23)),
        SurfaceObstacle("as-of", "rule", "timeline", ObstacleSegment((0, 15), (60, 15))),
        SurfaceObstacle("route", "dependency-route", "timeline",
            ObstacleSegment((0, 16), (60, 16)), route_owner_id="route:one"),
    ))
    required_request = replace(_request(), required_before_routes=True)

    assert owner._route_blocked_candidate(None, required_request, None, index) == ()
    # With an optional name, the rule blocks both candidate footprints in the
    # route-free inventory; route paint cannot turn that into eligibility.
    assert owner._route_blocked_candidate(None, _request(), None, index) == ()


def test_real_owner_selects_a_route_blocked_candidate_only_after_suppression():
    from tests.unit.chrona.presentation.layout.test_member_label_required_phase import _placement_context

    context = _placement_context()
    request = replace(_request(), anchor=LabelRect(80, 40, 10, 10), content="Owner")
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("route:all", "dependency-route", "timeline",
        ObstacleRect(0, 0, 200, 100), route_owner_id="relation:one"))

    result = owner.place_member_labels(context, (request,), index)

    assert result.text[0].overflow == "suppressed"
    assert tuple(item.text.selected_rung for item in result.route_blocked_candidates) == ("end", "start")
    assert {item.obstacle_class for item in result.route_blocked_candidates[0].obstacles} == {"text", "label-visual"}


def test_top_level_reuses_admitted_span_footprints_only_within_its_probe_family(monkeypatch):
    from tests.unit.chrona.presentation.layout.test_member_label_required_phase import _placement_context

    context = _placement_context()
    context.request.theme_tokens.optional_number = lambda *_args: None
    admitted = MarkPlacement("planned:admitted", "a", Rect(Decimal(0), Decimal(0), Decimal(8), Decimal(8)),
        (0, 4), (8, 4), mark_shape="span")
    absent = MarkPlacement("planned:absent", "b", Rect(Decimal(10), Decimal(0), Decimal(8), Decimal(8)),
        (10, 4), (18, 4), mark_shape="span")
    context = replace(context, marks=(admitted, absent))
    request = replace(_request(), anchor=LabelRect(80, 40, 10, 10), content="Owner")
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle(admitted.placement_id, "mark", "timeline",
                              ObstacleRect(0, 0, 8, 8)))
    index.add(SurfaceObstacle("route:all", "dependency-route", "timeline",
                              ObstacleRect(0, 0, 200, 100), route_owner_id="relation:one"))

    footprint_calls = []
    original_footprint = owner.span_mark_footprint

    def count_footprint(mark, theme):
        footprint_calls.append(mark.placement_id)
        return original_footprint(mark, theme)

    membership_checks = []
    original_has = SurfaceObstacleIndex.has

    def record_membership(obstacles, identifier):
        result = original_has(obstacles, identifier)
        if identifier in {admitted.placement_id, absent.placement_id}:
            membership_checks.append((obstacles, identifier, result))
        return result

    monkeypatch.setattr(owner, "span_mark_footprint", count_footprint)
    monkeypatch.setattr(SurfaceObstacleIndex, "has", record_membership)

    first = owner.place_member_labels(context, (request,), index)

    assert first.text[0].overflow == "suppressed"
    assert footprint_calls == [admitted.placement_id]
    assert len({item[0] for item in membership_checks if item[1] == admitted.placement_id}) >= 3
    assert any(item[1] == absent.placement_id and not item[2] for item in membership_checks)

    owner.place_member_labels(context, (request,), index)

    assert footprint_calls == [admitted.placement_id, admitted.placement_id]


def test_prepared_span_footprint_is_not_substituted_when_current_index_lacks_mark(monkeypatch):
    from tests.unit.chrona.presentation.layout.test_member_label_required_phase import _placement_context

    context = _placement_context()
    context.request.theme_tokens.optional_number = lambda *_args: None
    mark = MarkPlacement("planned:cached", "cached", Rect(Decimal(0), Decimal(0), Decimal(8), Decimal(8)),
        (0, 4), (8, 4), mark_shape="span")
    context = replace(context, marks=(mark,))
    source_index = SurfaceObstacleIndex()
    source_index.add(SurfaceObstacle(mark.placement_id, "mark", "timeline", ObstacleRect(0, 0, 8, 8)))
    prepared = owner._prepare_member_label_facts(context, source_index)
    assert mark.placement_id in prepared.span_paint_footprints

    copies = []
    original_copy = SurfaceObstacleIndex.copy

    def capture_overrides(obstacles, *, geometry_overrides=None):
        copies.append(dict(geometry_overrides or {}))
        return original_copy(obstacles, geometry_overrides=geometry_overrides)

    monkeypatch.setattr(SurfaceObstacleIndex, "copy", capture_overrides)
    request = replace(_request(), anchor=LabelRect(80, 40, 10, 10), content="Owner")

    owner.place_member_labels(context, (request,), SurfaceObstacleIndex(), _prepared=prepared)

    assert copies
    assert all(mark.placement_id not in item for item in copies)


@pytest.mark.parametrize("reason", ("mark-or-rule", "same-rung", "not-route", "first-choice", "required"))
def test_unrelated_or_nonimproving_obstruction_does_not_trigger_repair(monkeypatch, reason):
    request = replace(_request(), required_before_routes=reason == "required")
    selected = LabelPlacement("end" if reason == "first-choice" else "start", LabelRect(0, 0, 10, 10))
    index = _index()

    def probe(_context, _requests, obstacles, *, reserve_only, _prepared=None):
        assert reason not in {"first-choice", "required"}
        if reason == "mark-or-rule":
            return owner.SurfaceMemberLabelsBatch((), (), (), (), (), (), (), frozenset())
        x = 30 if reason == "not-route" else 15
        text = TextPlacement("name", "item", "Name", Rect(Decimal(x), Decimal(10), Decimal(10), Decimal(10)),
            "text", semantic_id="memberLabel", selected_rung="start" if reason == "same-rung" else "end")
        obstacles.add(SurfaceObstacle("label-footprint:name", "label-visual", "timeline",
                                      ObstacleRect(x, 10, x + 10, 20)))
        return owner.SurfaceMemberLabelsBatch((text,), (), (), (), (), (), (), frozenset())

    monkeypatch.setattr(owner, "place_member_labels", probe)
    assert owner._route_blocked_candidate(None, request, selected, index) == ()


@pytest.mark.parametrize("other_class", (None, "mark", "rule", "route-reserve", "text"))
def test_real_label_owner_requires_route_ink_to_be_the_only_blocker(other_class):
    from tests.unit.chrona.presentation.layout.test_member_label_required_phase import _placement_context
    context = _placement_context()
    request = replace(_request(), anchor=LabelRect(80, 40, 10, 10), content="Owner")
    index = SurfaceObstacleIndex()
    geometry = ObstacleSegment((105, 0), (105, 100), 1)
    index.add(SurfaceObstacle("route", "dependency-route", "timeline", geometry))
    if other_class is not None:
        index.add(SurfaceObstacle("other", other_class, "timeline", geometry))
    result = owner.place_member_labels(context, (request,), index)
    assert result.text[0].selected_rung == "start"
    # A route-blocked earlier rung is not a retry qualification while the name
    # already has a visible later rung.
    assert not result.route_blocked_candidates
