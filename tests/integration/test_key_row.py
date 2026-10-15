"""`rows.points: key-row` draws every selected point in one packed row under the axis (#1501)."""
from __future__ import annotations

from datetime import date

import pytest

from chrona.presentation.contracts.diagnostics import PresentationIngressRejected
from chrona.presentation.model.closure import ClosureError
from tests.support import synthetic_review as sr

TITLE = "Key milestones"
NEAR = {"p1": (date(2026, 1, 6), "Gate one long title"), "p2": (date(2026, 1, 8), "Gate two long title")}
FAR = {"p3": (date(2026, 8, 1), "Far")}
COLUMN = {"id": "name", "source": "title", "format": "text", "missing": "blank", "align": "start",
          "width": "content", "headerOrientation": "horizontal"}


def _parts(policy="key-row", grouping=None, table=True):
    parts = sr.bundle()
    body = parts["view"]["body"]
    body["rows"] = {"mode": "automatic", "points": policy}
    if policy == "key-row":
        body["rows"]["keyRow"] = {"title": TITLE}
    body["grouping"] = grouping or {"by": "none", "missing": "ungrouped"}
    if table:
        body["tableColumns"] = [dict(COLUMN), {**COLUMN, "id": "owner", "source": {"field": "owner"}}]
    return parts


def _render(tmp_path, points, *, parts=None, **kwargs):
    objects = {"span": sr.span("span", date(2026, 1, 5), 200), "span2": sr.span("span2", date(2026, 2, 5), 90, owner="b")}
    for key, (at, title) in points.items():
        objects[key] = sr.point(key, at, title=title)
    return sr.render(tmp_path, sr.project(objects), presentation=parts or _parts(**kwargs))


def _primitives(rendered, prefix):
    return {item.scene_id.split(":")[-1]: item for item in rendered.surface.primitives if item.scene_id.startswith(prefix)}


def _lane_blocks(rendered):
    return {key: item.bounds[1] for key, item in _primitives(rendered, "planned:key-row:").items()}


def test_every_selected_point_is_labelled_and_sits_in_the_first_row(tmp_path):
    rendered = _render(tmp_path, {**NEAR, **FAR})
    marks, labels = _primitives(rendered, "planned:key-row:"), _primitives(rendered, "member-label:key-row:")
    assert set(marks) == set(labels) == {"p1", "p2", "p3"}
    assert {key: item.text for key, item in labels.items()} == {key: value[1] for key, value in {**NEAR, **FAR}.items()}
    rule = next(item for item in rendered.surface.primitives if item.scene_id == "axis-rule").bounds
    band = next(item for item in rendered.surface.primitives if item.scene_id == "row-band:key-row").bounds
    assert band[1] == pytest.approx(rule[1])  # directly under the axis
    other = [item.bounds[1] for item in rendered.surface.primitives if item.scene_id.startswith("planned:span")]
    assert all(block >= band[1] + band[3] - 0.01 for block in other)  # every other row is below it
    assert not any(item.scene_id.startswith("planned:p") for item in rendered.surface.primitives)  # no row of their own


def test_colliding_points_take_separate_lanes_and_distant_points_share_one(tmp_path):
    blocks = _lane_blocks(_render(tmp_path, {**NEAR, **FAR}))
    assert blocks["p1"] == blocks["p3"]  # the far point reuses lane 0
    assert blocks["p2"] != blocks["p1"]  # the first label reaches the second mark
    assert len(set(blocks.values())) == 2  # minimal: the clique number of the extents is 2


def test_spread_points_need_one_lane_only(tmp_path):
    spread = {"p1": (date(2026, 1, 6), "One"), "p2": (date(2026, 5, 1), "Two"), "p3": (date(2026, 8, 1), "Three")}
    assert len(set(_lane_blocks(_render(tmp_path, spread)).values())) == 1


def test_labels_never_leave_their_lane_band(tmp_path):
    rendered = _render(tmp_path, {**NEAR, **FAR})
    marks, labels = _primitives(rendered, "planned:key-row:"), _primitives(rendered, "member-label:key-row:")
    for key, label in labels.items():
        mark = marks[key].bounds
        assert label.bounds[1] < mark[1] + mark[3] and label.bounds[1] + label.bounds[3] > mark[1]


def test_the_table_names_the_key_row_in_its_first_column(tmp_path):
    rendered = _render(tmp_path, {**NEAR, **FAR})
    cells = [item for item in rendered.surface.primitives if getattr(item, "text", None) == TITLE]
    assert len(cells) == 1
    assert cells[0].bounds[1] < next(item for item in rendered.surface.primitives
                                     if getattr(item, "text", None) == "Span").bounds[1]


@pytest.mark.parametrize("grouping", [None, {"by": "field", "field": "owner", "missing": "Other", "presentation": "header"}])
def test_it_works_with_any_grouping(tmp_path, grouping):
    rendered = _render(tmp_path, {**NEAR, **FAR}, grouping=grouping)
    assert set(_lane_blocks(rendered)) == {"p1", "p2", "p3"}
    texts = {getattr(item, "text", None) for item in rendered.surface.primitives}
    assert (grouping is None) == ("Team a" not in texts)  # headers keep their place below the key row


def test_without_a_table_the_row_still_draws(tmp_path):
    assert set(_lane_blocks(_render(tmp_path, {**NEAR, **FAR}, table=False))) == {"p1", "p2", "p3"}


def test_no_point_draws_no_key_row(tmp_path):
    rendered = _render(tmp_path, {})
    assert not _primitives(rendered, "row-band:key-row")


def test_other_policies_do_not_enter_the_key_row_path(tmp_path):
    rendered = _render(tmp_path, {**NEAR, **FAR}, parts=_parts("own-row"))
    assert not _primitives(rendered, "planned:key-row:")
    assert len(_primitives(rendered, "planned:p")) == 3


def test_render_is_deterministic(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    first, second = _render(tmp_path / "a", {**NEAR, **FAR}), _render(tmp_path / "b", {**NEAR, **FAR})
    assert first.surface == second.surface
    assert first.artifact.content == second.artifact.content


def test_typeset_targets_render(tmp_path):
    from chrona.presentation.renderers.v05_typeset import V05TikzRenderer, V05TypstRenderer

    rendered = _render(tmp_path, {**NEAR, **FAR})
    for renderer in (V05TypstRenderer(), V05TikzRenderer()):
        content = renderer.render(rendered.surface).content.decode()
        assert TITLE in content and "Gate one long title" in content


@pytest.mark.parametrize("mutate, code", [
    (lambda rows: rows.pop("keyRow"), "E_VIEW_KEY_ROW_TITLE_REQUIRED"),
    (lambda rows: rows.update(points="own-row"), "E_VIEW_KEY_ROW_UNUSED"),
    (lambda rows: rows.update(keyRow={"title": ""}), "E_RESOURCE_SCHEMA"),
])
def test_a_misdeclared_key_row_is_refused_with_its_code(tmp_path, mutate, code):
    parts = _parts()
    mutate(parts["view"]["body"]["rows"])
    with pytest.raises((ClosureError, PresentationIngressRejected)) as error:
        _render(tmp_path, NEAR, parts=parts)
    assert code in str(error.value) or code in repr(error.value.__dict__)



def test_key_row_needs_plot_titles(tmp_path):
    parts = _parts()
    parts["view"]["body"]["visibility"]["labels"] = {"placement": "plot", "content": ["finishDelta"], "side": "end", "overflow": "suppress"}
    with pytest.raises(ValueError, match="E_REVIEW_POINT_KEY_ROW_LABEL_REQUIRED"):
        _render(tmp_path, NEAR, parts=parts)
