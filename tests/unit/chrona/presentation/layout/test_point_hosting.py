from dataclasses import replace
from datetime import date

import pytest

from chrona.presentation.layout.model import LayoutError, PointHostMode
from chrona.presentation.layout.point_hosting import resolve_point_host_plan
from chrona.presentation.model.projection import ReviewItem, ReviewProjection, ReviewRowProjection, WindowMode

MODE = PointHostMode.SPAN_WHEN_INSIDE


def _span(name="a", *, start=10, finish=20, **fields):
    return ReviewItem(name, name, "span", {"start": date(2026, 1, start),
        "end": date(2026, 1, finish)}, None, None, (), **fields)


def _point(*, at=15, **fields):
    return ReviewItem("p", "Point", "point", {"at": date(2026, 1, at)}, None, None, (), **fields)


def _projection(*items, rows=(), window=(date(2026, 1, 1), date(2026, 3, 1)), **fields):
    return ReviewProjection(items, window, (), (), rows=rows, **fields)


def _row(name, *items):
    return ReviewRowProjection(name, name, "", items[0].object_id, items)


def _plan(projection):
    return resolve_point_host_plan(projection, as_of=None, mode=MODE)


def test_default_off_does_not_inspect_projection_or_select_source_facets():
    # Off is an actual fast path, not a second interpretation of legacy input.
    assert resolve_point_host_plan(object(), as_of=None, mode=None).relations == ()


@pytest.mark.parametrize("at", [10, 15, 20])
def test_original_semantic_interval_is_inclusive_and_row_membership_unchanged(at):
    projection = _projection(_span(), _point(at=at, parent_id="a"))
    plan = _plan(projection)
    assert len(plan.relations) == 1
    relation = plan.relations[0]
    assert relation.point.row_id == "p" and relation.span.row_id == "a"
    assert relation.point.final_mark_id("planned") == "planned:p"
    assert relation.point.source_mark_id("planned") == "planned:p"
    assert projection.items[1].parent_id == "a"


def test_declared_attachment_wins_and_ineligible_attachment_allows_direct_parent():
    point = _point(parent_id="a", declared_attaches_to="b")
    projection = _projection(_span(), _span("b"), point)
    assert _plan(projection).relations[0].span.item.object_id == "b"
    outside = replace(projection, items=(_span(), _span("b", start=1, finish=5), point))
    assert _plan(outside).relations[0].span.item.object_id == "a"


def test_derived_row_attachment_does_not_become_an_author_host_link():
    assert not _plan(_projection(_span(), _point(attached_to="a"))).relations


@pytest.mark.parametrize("host", [None, _span(start=1, finish=5), _span(temporal_paint=False)])
def test_absent_outside_and_unpainted_host_preserve_the_point(host):
    items = (host,) if host is not None else ()
    assert not _plan(_projection(*items, _point(parent_id="a"))).relations


def test_window_admission_is_independent_of_inclusive_host_interval():
    projection = _projection(_span(), _point(at=20, parent_id="a"),
        window=(date(2026, 1, 10), date(2026, 1, 20)), window_mode=WindowMode.EXPLICIT)
    assert not _plan(projection).relations  # window end is still exclusive
    assert len(_plan(replace(projection, items=(_span(), _point(at=10, parent_id="a")))).relations) == 1


def test_same_facet_is_required_for_actual_and_planned_hosts():
    span = replace(_span(), actual={"start": date(2026, 2, 1), "finish": date(2026, 2, 20)})
    point = replace(_point(parent_id="a"), actual={"at": date(2026, 2, 10)})
    assert {r.facet for r in _plan(_projection(span, point)).relations} == {"planned", "actual"}
    point = replace(point, actual={"at": date(2026, 1, 15)})
    assert [r.facet for r in _plan(_projection(span, point)).relations] == ["planned"]


@pytest.mark.parametrize("span_kind,point_kind,span_scenario,point_scenario", [
    ("snapshot", "primary", None, None), ("scenario", "scenario", "one", "two"),
])
def test_source_and_scenario_boundaries_are_not_crossed(span_kind, point_kind, span_scenario, point_scenario):
    span = _span(source_kind=span_kind, scenario_id=span_scenario)
    point = _point(parent_id="a", source_kind=point_kind, scenario_id=point_scenario)
    projection = _projection(span, point, rows=(_row("s", span), _row("p", point)))
    assert not _plan(projection).relations


@pytest.mark.parametrize("kind,scenario", [("snapshot", None), ("scenario", "one")])
def test_snapshot_and_scenario_points_can_use_their_own_source_host(kind, scenario):
    span = _span(source_kind=kind, scenario_id=scenario)
    point = _point(parent_id="a", source_kind=kind, scenario_id=scenario)
    plan = _plan(_projection(span, point, rows=(_row("s", span), _row("p", point))))
    assert len(plan.relations) == 1
    assert plan.relations[0].facet == "planned"
    assert plan.relations[0].point.instance.source_kind == kind
    assert plan.relations[0].span.item.scenario_id == scenario


def test_multiple_occurrences_require_a_unique_host_or_prefer_the_child_row():
    span, other = _span(item_id="first"), _span(item_id="second")
    point = _point(parent_id="a", item_id="point")
    ambiguous = _projection(span, other, point,
        rows=(_row("first", span), _row("second", other), _row("point", point)))
    with pytest.raises(LayoutError, match="E_LAYOUT_POINT_HOST_AMBIGUOUS"):
        _plan(ambiguous)
    same_row = replace(ambiguous, rows=(_row("first", span, point), _row("second", other)))
    assert _plan(same_row).relations[0].span.row_id == "first"


def test_parent_is_not_followed_transitively():
    # Direct parent is a point, not a drawable span; grandparent never qualifies.
    parent = replace(_point(), object_id="middle", parent_id="a")
    point = _point(parent_id="middle")
    projection = _projection(_span(), parent, point)
    assert all(r.point.item.object_id != "p" for r in _plan(projection).relations)
