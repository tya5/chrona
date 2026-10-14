"""Group-header folded points pack into lanes by x-extent collision, and predecessor folds keep facts (#440)."""
from __future__ import annotations

from datetime import date

import pytest

from chrona.presentation.layout.surface_marks import pack_extent_lanes
from tests.support import synthetic_review as sr


def test_pack_extent_lanes_is_greedy_and_optimal():
    # Row 1 shape: the first and last two are far apart, so two lanes suffice and the first sits in lane 0.
    assert pack_extent_lanes([(1101, 1500), (1716, 1900), (1740, 1990)]) == [0, 0, 1]
    # Row 2: overlapping extents never share a lane; touching extents may.
    assert pack_extent_lanes([(0, 10), (5, 15)]) == [0, 1]
    assert pack_extent_lanes([(0, 10), (10, 15)]) == [0, 0]
    # Row 3: lane count equals the clique number (three mutually overlapping; freed lanes are reused lowest-first).
    lanes = pack_extent_lanes([(0, 10), (1, 11), (2, 12), (11, 20), (12, 30)])
    assert lanes == [0, 1, 2, 0, 1] and max(lanes) + 1 == 3
    assert pack_extent_lanes([]) == []


def _folded_render(tmp_path, points):
    objects = {"span": sr.span("span", date(2026, 1, 5), 200)}
    for key, (at, title) in points.items():
        objects[key] = sr.point(key, at, title=title)
    source = sr.project(objects)
    source["entities"]["a"]["title"] = "Group A"
    parts = sr.bundle()
    body = parts["view"]["body"]
    body["rows"] = {"mode": "automatic", "points": "group-header"}
    return sr.render(tmp_path, source, presentation=parts)


def _marks(rendered):
    return {item.scene_id.split(":")[-1]: item.bounds for item in rendered.surface.primitives
            if item.scene_id.startswith("planned:group-header:")}


def _overflow(rendered):
    return [item for item in rendered.warning_records if "GROUP_HEADER_OVERFLOW" in repr(item)]


NEAR = {"p1": (date(2026, 1, 6), "Gate one long title"), "p2": (date(2026, 1, 8), "Gate two long title")}
FAR = {"p3": (date(2026, 8, 1), "Far")}


def test_distant_points_share_a_lane_and_colliding_points_do_not(tmp_path):
    rendered = _folded_render(tmp_path, {**NEAR, **FAR})
    marks = _marks(rendered)
    assert marks["p1"][1] == marks["p3"][1]  # far point reuses lane 0
    assert marks["p2"][1] != marks["p1"][1]  # label of p1 reaches p2's mark
    assert len({bounds[1] for bounds in marks.values()}) == 2


def test_header_grows_and_warns_only_when_packing_exceeds_capacity(tmp_path):
    (tmp_path / "spread").mkdir()
    (tmp_path / "packed").mkdir()
    spread = _folded_render(tmp_path / "spread", {
        "p1": (date(2026, 1, 6), "One"), "p2": (date(2026, 5, 1), "Two"), "p3": (date(2026, 8, 1), "Three")})
    assert len({bounds[1] for bounds in _marks(spread).values()}) == 1
    assert _overflow(spread) == []
    packed = _folded_render(tmp_path / "packed", {**NEAR, **FAR})
    (warning,) = _overflow(packed)
    assert warning.payload["requiredBlock"] == 2 * 16.0 > warning.payload["availableBlock"]


@pytest.mark.parametrize("content", [["title"], ["finishDelta"]])
def test_predecessor_fold_carries_title_and_planned_date(tmp_path, content):
    objects = {"task": sr.span("task", date(2026, 3, 2), 14), "gate": sr.point("gate", date(2026, 3, 16), title="Design review")}
    source = sr.project(objects, [{"id": "task-gate", "type": "dependency", "from": {"object": "task", "endpoint": "end"},
                                            "to": {"object": "gate", "endpoint": "at"}}])
    parts = sr.bundle()
    parts["view"]["body"]["rows"] = {"mode": "automatic", "points": "predecessor"}
    parts["view"]["body"]["visibility"]["labels"]["content"] = content
    rendered = sr.render(tmp_path, source, presentation=parts)
    assert not any(row.scene_id.endswith(":gate") and row.scene_id.startswith("row") for row in rendered.surface.primitives)
    text = next(item.text for item in rendered.surface.primitives
                if item.scene_id.startswith("member-label:") and item.scene_id.endswith(":gate"))
    assert text.startswith("Design review") and "16" in text and "Mar" in text
