"""On-demand repair keeps the exact preceding label inventory when attributing routes."""
from dataclasses import replace
from decimal import Decimal

import pytest

from chrona.presentation.layout import surface_member_labels as owner
from chrona.presentation.layout.labels import LabelPlacement, LabelRect, LabelRequest
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.surface_quality import CollisionDomain, TextPlacement


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


@pytest.mark.parametrize("selected", (None, LabelPlacement("start", LabelRect(0, 0, 10, 10))))
def test_route_only_probe_retains_preceding_text_and_rule_and_uses_exact_footprint(monkeypatch, selected):
    index = _index()
    before = index.all()

    def probe(context, requests, obstacles, *, reserve_only):
        assert reserve_only and requests == (_request(),)
        assert obstacles.has("prior-name") and obstacles.has("as-of")
        assert not obstacles.has("route")
        text = TextPlacement("name", "item", "Name", Rect(Decimal(15), Decimal(10), Decimal(10), Decimal(10)),
            "text", semantic_id="memberLabel", selected_rung="end")
        obstacles.add(SurfaceObstacle("label-footprint:name", "label-visual", "timeline",
                                      ObstacleRect(15, 10, 25, 20)))
        return owner.SurfaceMemberLabelsBatch((text,), (), (), (), (), (), (), frozenset())

    monkeypatch.setattr(owner, "place_member_labels", probe)
    reservation = owner._route_blocked_candidate(None, _request(), selected, index)
    assert reservation is not None and reservation.text.selected_rung == "end"
    assert not reservation.text.required
    assert [item.placement_id for item in reservation.obstacles] == ["label-footprint:name"]
    assert index.all() == before


@pytest.mark.parametrize("reason", ("mark-or-rule", "same-rung", "not-route", "first-choice", "required"))
def test_unrelated_or_nonimproving_obstruction_does_not_trigger_repair(monkeypatch, reason):
    request = replace(_request(), required_before_routes=reason == "required")
    selected = LabelPlacement("end" if reason == "first-choice" else "start", LabelRect(0, 0, 10, 10))
    index = _index()

    def probe(_context, _requests, obstacles, *, reserve_only):
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
    assert owner._route_blocked_candidate(None, request, selected, index) is None


@pytest.mark.parametrize("other_class", (None, "rule", "route-reserve", "text"))
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
    assert len(result.route_blocked_candidates) == (1 if other_class is None else 0)
    if result.route_blocked_candidates:
        assert result.route_blocked_candidates[0].text.selected_rung == "end"
