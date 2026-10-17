"""View-folded points are not resurrected as ordinary rows when a group or the whole View holds only points (#1660)."""
from __future__ import annotations

from dataclasses import replace
from datetime import date

from chrona.presentation.model.projection import ReviewProjection
from tests.support import synthetic_review as sr


def _render(tmp_path, objects, *, relations=(), folding=True, window=True):
    source = sr.project(objects, relations)
    parts = sr.bundle()
    body = parts["view"]["body"]
    body["rows"] = {"mode": "automatic", **({"points": "group-header"} if folding else {})}
    if window:
        body["window"] = {"mode": "explicit", "start": "2026-01-01", "end": "2026-03-01"}
    return sr.render(tmp_path, source, presentation=parts)


def _planned(result):
    return [primitive.scene_id for primitive in result.surface.primitives if primitive.purpose == "planned"]


def _groups(result):
    return [group.group_id for group in result.surface.groups]


def test_all_point_twin_has_only_the_folded_occurrences(tmp_path):
    result = _render(tmp_path, {"one": sr.point("one", date(2026, 2, 12)), "two": sr.point("two", date(2026, 2, 16))})
    assert _planned(result) == ["planned:group-header:a:one", "planned:group-header:a:two"]
    assert _groups(result) == ["a"]
    assert result.surface.rows == ()
    header = next(item for item in result.surface.primitives if item.scene_id == "group-header:a")
    assert header.purpose == "group-header"
    assert any(item.purpose == "group-header" and "Team a" in repr(item) for item in result.surface.primitives)


def test_folded_occurrences_keep_project_provenance(tmp_path):
    result = _render(tmp_path, {"one": sr.point("one", date(2026, 2, 12)), "two": sr.point("two", date(2026, 2, 16))})
    refs = {item.scene_id: item.source_ref for item in result.surface.primitives if item.purpose == "planned"}
    assert refs == {"planned:group-header:a:one": "one", "planned:group-header:a:two": "two"}


def test_groups_without_ordinary_rows_keep_declared_order_beside_mixed_groups(tmp_path):
    result = _render(tmp_path, {
        "s1": sr.span("s1", date(2026, 1, 5), 20, owner="a"), "p1": sr.point("p1", date(2026, 1, 10), owner="a"),
        "s3": sr.span("s3", date(2026, 1, 20), 20, owner="c"),
        "q1": sr.point("q1", date(2026, 2, 2), owner="b"), "q2": sr.point("q2", date(2026, 2, 9), owner="b"),
        "r1": sr.point("r1", date(2026, 2, 20), owner="d"),
    })
    assert _planned(result) == [
        "planned:s1:s1", "planned:s3:s3", "planned:group-header:a:p1",
        "planned:group-header:b:q1", "planned:group-header:b:q2", "planned:group-header:d:r1"]
    assert _groups(result) == ["a", "c", "b", "d"]
    assert [row.row_id for row in result.surface.rows] == ["s1", "s3"]
    blocks = [group.header_bounds[1] for group in result.surface.groups]
    assert blocks == sorted(blocks)
    assert all(group.header_bounds is not None for group in result.surface.groups)


def test_a_leading_point_only_group_precedes_a_mixed_group(tmp_path):
    result = _render(tmp_path, {
        "q1": sr.point("q1", date(2026, 1, 3), owner="b"),
        "s1": sr.span("s1", date(2026, 1, 20), 20, owner="a"),
    })
    assert _groups(result) == ["b", "a"]
    assert _planned(result) == ["planned:s1:s1", "planned:group-header:b:q1"]


def test_folded_points_keep_their_routes(tmp_path):
    relations = [{"id": "one-two", "type": "dependency", "from": {"object": "one", "endpoint": "at"},
                  "to": {"object": "two", "endpoint": "at"}}]
    (tmp_path / "folded").mkdir()
    (tmp_path / "twin").mkdir()
    points = {"one": sr.point("one", date(2026, 2, 12)), "two": sr.point("two", date(2026, 2, 16))}
    folded = _render(tmp_path / "folded", points, relations=relations)
    twin = _render(tmp_path / "twin", {**points, "span": sr.span("span", date(2026, 1, 5), 10)}, relations=relations)
    def routes(result):
        return sorted(item.scene_id for item in result.surface.primitives if item.scene_id.startswith("relation"))

    assert routes(folded) and routes(folded) == routes(twin)


def test_no_folding_control_keeps_one_row_per_point(tmp_path):
    result = _render(tmp_path, {"one": sr.point("one", date(2026, 2, 12)), "two": sr.point("two", date(2026, 2, 16))},
                     folding=False)
    assert _planned(result) == ["planned:one:one", "planned:two:two"]
    assert [row.row_id for row in result.surface.rows] == ["one", "two"]


def test_mixed_group_keeps_header_only_points(tmp_path):
    result = _render(tmp_path, {"s1": sr.span("s1", date(2026, 1, 5), 20), "p1": sr.point("p1", date(2026, 1, 10))})
    assert _planned(result) == ["planned:s1:s1", "planned:group-header:a:p1"]


def test_projection_distinguishes_resolved_empty_rows_from_absent_rows():
    legacy = ReviewProjection((), (date(2026, 1, 1), date(2026, 2, 1)), (), ())
    assert legacy.has_rows is False and legacy.rows_resolved is False
    resolved = replace(legacy, rows_resolved=True)
    assert resolved.has_rows is True and resolved.rows == ()
