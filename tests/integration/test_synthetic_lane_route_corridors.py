"""#687: a lane member name is never the reason a dependency route disappears, proven on synthetic Projects.

No `examples/` input. Two small lane projects found by a seeded search and reduced to the spans that matter:

- ``wall``: the end-side names of two spans in the stacked lanes sit in the channel between the source's end and
  the target's start, one name beside the source's exit port; every route attempt is rejected for its bends;
- ``costly``: the only way to draw the relation suppresses a name that is shown today, so it is not repaired.
"""
from __future__ import annotations

import json
from datetime import date

import pytest

import chrona.presentation.layout.surface_composer as composer
import chrona.presentation.layout.surface_lane_route_plan as lane_plan
from tests.support import synthetic_review as sr

WALL = {"l0-t0": ("2026-01-20", "2026-02-09", "team-0"), "l1-t0": ("2026-01-23", "2026-02-07", "team-1"),
        "l2-t0": ("2026-01-20", "2026-02-02", "team-2"), "l3-t0": ("2026-01-06", "2026-01-20", "team-3"),
        "l3-t1": ("2026-02-12", "2026-03-07", "team-3"), "l3-t2": ("2026-04-02", "2026-04-21", "team-3")}
WALL_RELATION = ("l1-t0", "l3-t1")
COSTLY = {"l0-t0": ("2026-01-12", "2026-02-05", "team-0"), "l1-t0": ("2026-01-09", "2026-02-02", "team-1"),
          "l1-t1": ("2026-02-15", "2026-03-03", "team-1"), "l2-t0": ("2026-01-09", "2026-01-18", "team-2"),
          "l2-t1": ("2026-02-02", "2026-02-12", "team-2"), "l2-t3": ("2026-04-11", "2026-04-21", "team-2"),
          "l3-t0": ("2026-01-20", "2026-02-10", "team-3")}
COSTLY_RELATION = ("l3-t0", "l1-t1")


def _project(spans, relation):
    objects = {}
    for key, (start, end, owner) in spans.items():
        first = date.fromisoformat(start)
        objects[key] = sr.span(key, first, (date.fromisoformat(end) - first).days, owner=owner,
                               title=f"Task title {key[1]}.{key[-1]}")
    source, target = relation
    return sr.project(objects, [{"id": "r0", "type": "dependency", "lag": "0d",
                                 "from": {"object": source, "endpoint": "end"},
                                 "to": {"object": target, "endpoint": "start"}}])


def _parts():
    parts = sr.bundle()
    parts["view"] = sr.lane_view(parts["view"])
    return parts


def _render(tmp_path, source, monkeypatch, *, plan: bool):
    if not plan:
        monkeypatch.setattr(composer, "plan_lane_route_reservations", lambda context: lane_plan.LaneRoutePlan())
    return sr.render(tmp_path, source, presentation=_parts())


def _suppressed(rendered) -> list[str]:
    return [item for item in rendered.scene.diagnostics if item.startswith("W_LAYOUT_RELATION_SUPPRESSED:")]


def _routes(rendered):
    return [item for item in rendered.surface.primitives if item.scene_id.startswith("relation:")]


def _names(rendered):
    return {item.source_ref: item for item in rendered.surface.primitives if item.purpose == "member-label"}


def _marks(rendered):
    return [item for item in rendered.surface.primitives if item.purpose == "planned"]


def _segment_hits_box(start, end, box) -> bool:
    """Whether an orthogonal route segment passes through the interior of a box."""
    left, top, width, height = box
    right, bottom = left + width, top + height
    if start[0] == end[0]:
        return left < start[0] < right and min(start[1], end[1]) < bottom and max(start[1], end[1]) > top
    return top < start[1] < bottom and min(start[0], end[0]) < right and max(start[0], end[0]) > left


def test_the_wall_loses_its_route_to_member_names_today(tmp_path, monkeypatch):
    rendered = _render(tmp_path, _project(WALL, WALL_RELATION), monkeypatch, plan=False)

    assert len(_suppressed(rendered)) == 1 and _routes(rendered) == []
    cause = next(json.loads(item.split(":", 1)[1]) for item in rendered.scene.diagnostics
                 if item.startswith("I_LAYOUT_LANE_ROUTE_CAUSE:"))
    assert cause["primaryCause"] == "quality-rejected"
    assert {attempt["outcome"] for attempt in cause["attempts"]} == {"quality-rejected"}
    assert all(attempt["bends"] > attempt["maxBends"] or attempt["length"] > attempt["directLength"] * attempt["maxDetourRatio"]
               for attempt in cause["attempts"])
    assert len(_names(rendered)) == len(WALL)


def test_the_planned_corridor_draws_the_route_and_keeps_every_name_associated(tmp_path, monkeypatch):
    rendered = _render(tmp_path, _project(WALL, WALL_RELATION), monkeypatch, plan=True)

    assert _suppressed(rendered) == [] and len(_routes(rendered)) == 1
    assert not [item for item in rendered.scene.diagnostics if item.startswith("I_LAYOUT_LANE_ROUTE_CAUSE:")]
    names, marks = _names(rendered), {item.scene_id: item for item in _marks(rendered)}
    assert set(names) == set(WALL), "no name may be suppressed"
    for key, name in names.items():
        host = marks[name.host_placement_id]
        assert host.source_ref == key, f"{key}: hosted by a foreign mark"
        box = tuple(name.text_layout.bounds)
        reach = 2.0 * name.text_layout.font_size
        inline = max(0.0, box[0] - (host.bounds[0] + host.bounds[2]), host.bounds[0] - (box[0] + box[2]))
        block = max(0.0, box[1] - (host.bounds[1] + host.bounds[3]), host.bounds[1] - (box[1] + box[3]))
        assert (inline * inline + block * block) ** 0.5 <= reach + 0.01, f"{key}: beyond the 2 em reach"
    points = _routes(rendered)[0].points
    for start, end in zip(points, points[1:]):
        for name in names.values():
            assert not _segment_hits_box(start, end, tuple(name.text_layout.bounds)), name.scene_id
        for mark in marks.values():
            if mark.source_ref in WALL_RELATION:
                continue
            assert not _segment_hits_box(start, end, mark.bounds), mark.scene_id


def test_the_plan_moves_only_names_in_its_way(tmp_path, monkeypatch):
    (tmp_path / "off").mkdir()
    (tmp_path / "on").mkdir()
    off = _render(tmp_path / "off", _project(WALL, WALL_RELATION), monkeypatch, plan=False)
    monkeypatch.undo()
    on = _render(tmp_path / "on", _project(WALL, WALL_RELATION), monkeypatch, plan=True)

    before, after = _names(off), _names(on)
    moved = {key for key in before if before[key].bounds != after[key].bounds}
    assert "l0-t0" in moved  # the name in the channel yields (end side to start side)
    assert moved < set(before), "a name that is not in the way keeps its position"
    for key in set(before) - moved:
        assert before[key].bounds == after[key].bounds and before[key].host_placement_id == after[key].host_placement_id


def test_without_the_corridor_the_wall_fixture_fails_the_rule(tmp_path, monkeypatch):
    # Mutation check: a planner that reserves nothing is today's order, and the rule above is violated.
    rendered = _render(tmp_path, _project(WALL, WALL_RELATION), monkeypatch, plan=False)
    assert _suppressed(rendered) and not _routes(rendered)


def test_a_project_with_no_conflict_is_placed_exactly_as_before(tmp_path, monkeypatch):
    (tmp_path / "off").mkdir()
    (tmp_path / "on").mkdir()
    source = sr.chain_project()
    off = _render(tmp_path / "off", source, monkeypatch, plan=False)
    monkeypatch.undo()
    calls: list[int] = []
    real = lane_plan.plan_lane_route_reservations

    def spy(context):
        plan = real(context)
        calls.append(len(plan.reservations))
        return plan

    monkeypatch.setattr(composer, "plan_lane_route_reservations", spy)
    on = sr.render(tmp_path / "on", source, presentation=_parts())

    assert calls == [0], "the planner ran and reserved nothing"
    assert _suppressed(off) == [] and _routes(off), "the fixture draws every relation today"
    assert [(item.scene_id, item.bounds, getattr(item, "points", None), item.host_placement_id) for item in off.surface.primitives] == \
           [(item.scene_id, item.bounds, getattr(item, "points", None), item.host_placement_id) for item in on.surface.primitives]
    assert off.scene.diagnostics == on.scene.diagnostics


def test_a_repair_that_would_suppress_a_shown_name_is_refused(tmp_path, monkeypatch):
    (tmp_path / "off").mkdir()
    (tmp_path / "on").mkdir()
    source = _project(COSTLY, COSTLY_RELATION)
    off = _render(tmp_path / "off", source, monkeypatch, plan=False)
    monkeypatch.undo()
    on = _render(tmp_path / "on", source, monkeypatch, plan=True)

    assert len(_suppressed(off)) == 1 and _routes(off) == []
    assert len(_names(off)) == len(COSTLY)
    # The only way to draw the relation suppresses a name that is shown today, so the plan is empty:
    assert [(item.scene_id, item.bounds) for item in off.surface.primitives] == \
           [(item.scene_id, item.bounds) for item in on.surface.primitives]
    assert off.scene.diagnostics == on.scene.diagnostics


def test_a_project_without_relations_never_rehearses(tmp_path, monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("a project without relations must not run a rehearsal")

    monkeypatch.setattr(lane_plan, "_rehearse", refuse)
    source = sr.chain_project()
    source["relations"] = []
    rendered = sr.render(tmp_path, source, presentation=_parts())
    assert _names(rendered)


@pytest.mark.parametrize("plan", [False, True])
def test_the_rehearsal_leaves_the_shared_index_alone(plan, tmp_path, monkeypatch):
    # The index the composer hands to the phases holds the pre-name obstacles plus the corridors, nothing from a rehearsal.
    seen: list[tuple[int, int]] = []
    real = lane_plan.plan_lane_route_reservations

    def spy(context):
        before = len(context.obstacles.all())
        result = real(context)
        seen.append((before, len(context.obstacles.all())))
        return result if plan else lane_plan.LaneRoutePlan()

    monkeypatch.setattr(composer, "plan_lane_route_reservations", spy)
    sr.render(tmp_path, _project(WALL, WALL_RELATION), presentation=_parts())
    assert seen and all(before == after for before, after in seen)
