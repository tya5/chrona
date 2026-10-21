"""A declared comparison column keeps its width until its data arrives when it asks to (#1869)."""
from __future__ import annotations

from datetime import date

import pytest

from tests.support import synthetic_review as sr

ACTUAL = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "synthetic-priority",
          "body": {"asOf": "2026-01-20", "observations": []}}


def _table_follows_its_content(node) -> None:
    if node.get("id") == "table":
        node["inlineSize"] = "content"
        node.pop("maxInlineShare", None)
    for child in node.get("children", ()):
        _table_follows_its_content(child)


def _render(tmp_path, *, priority: str | None, with_actual: bool):
    tmp_path.mkdir(parents=True, exist_ok=True)
    source = sr.project({"a": sr.span("a", date(2026, 1, 5), 28, title="Task a"),
                         "b": sr.span("b", date(2026, 2, 9), 28, title="Task b")})
    parts = sr.bundle()
    delta = {"id": "Delta", "source": {"facet": "finishDelta"}, "missing": "blank", "align": "end",
             "width": "content", "headerOrientation": "horizontal"}
    if priority is not None:
        delta["priority"] = priority
    _table_follows_its_content(parts["layout"]["root"])
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    parts["view"]["body"]["tableColumns"] = [
        {"id": "Task", "source": "path", "missing": "em-dash", "align": "start",
         "width": "content", "headerOrientation": "horizontal"}, delta]
    return sr.render(tmp_path, source, presentation=parts, actual=ACTUAL if with_actual else None)


def _facts(rendered):
    """The Delta header's bounds (None when the column is not drawn) and the plot's first planned bar."""
    primitives = list(rendered.surface.primitives)
    header = next((item.bounds for item in primitives if item.scene_id == "column:Delta"), None)
    bar = next(item for item in primitives if item.scene_id.startswith("planned:") and item.scene_id.endswith(":a"))
    return header, bar.bounds


def test_default_still_drops_an_unbound_comparison_column(tmp_path):
    before = _facts(_render(tmp_path / "w0", priority=None, with_actual=False))
    after = _facts(_render(tmp_path / "w1", priority=None, with_actual=True))

    assert before[0] is None and after[0] is not None
    assert _facts(_render(tmp_path / "w2", priority="optional", with_actual=False)) == before


@pytest.mark.parametrize("priority", ["preferred", "required"])
def test_preferred_or_required_column_keeps_its_header_width_and_the_time_scale(tmp_path, priority):
    before = _facts(_render(tmp_path / "w0", priority=priority, with_actual=False))
    after = _facts(_render(tmp_path / "w1", priority=priority, with_actual=True))

    assert before[0] is not None
    assert before[0] == pytest.approx(after[0]) and before[1] == pytest.approx(after[1])
