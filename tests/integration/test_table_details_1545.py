"""Row-number suffix, lane-table textRole admission and the column-header rule (#1545).

Synthetic Project through the packaged `executive-light` bundle; every literal is ASCII.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date

import pytest

from tests.support import synthetic_review as sr

OWNERS = {"a": "Ana Maria Lopez", "b": "fw-team"}
RULE_ROLE = {"strokeWidth": "stroke-width"}


def _theme(parts, *, rule=False, mono=True):
    body = parts["theme"]["body"]
    if mono:
        body["values"]["cell-mono-family"] = {"type": "fontFamily", "value": "Noto Sans Mono, monospace"}
        body["roles"]["cell-mono"] = {key: value for key, value in body["roles"]["text"].items()
                                      if key not in {"iconScale", "iconGap"}} | {"fontFamily": "cell-mono-family"}
    if rule:
        body["values"]["rule-width"] = {"type": "number", "value": 1}
        body["roles"]["tableColumnRule"] = {"strokeWidth": "rule-width"}
        body["colorBindings"]["tableColumnRule.stroke"] = "text"


def _lane(tmp_path, columns, *, rule=False, mono=True):
    objects = {key: sr.span(key, date(2026, 2 + i, 2), 5, owner=owner, title=f"Task {key.upper()}")
               for i, (key, owner) in enumerate(OWNERS.items())}
    parts = sr.bundle("executive-light")
    parts["view"] = sr.lane_view(parts["view"])
    parts["view"]["body"]["rows"]["laneTable"] = {"label": "lane", "columns": deepcopy(columns)}
    _theme(parts, rule=rule, mono=mono)
    return sr.render(tmp_path, sr.project(objects), presentation=parts)


def _cells(review):
    table: dict[str, dict[str, str]] = {}
    for item in review.surface.primitives:
        if item.purpose == "table-cell":
            table.setdefault(item.table_column_id, {})[item.source_ref] = item.text
    return table


LANE = [{"id": "No", "source": "rowIndex"}, {"id": "Task", "source": "label"},
        {"id": "Owner", "source": {"field": "owner"}, "transform": "initials"}]


def test_lane_suffix_is_part_of_the_cell_text(tmp_path):
    columns = deepcopy(LANE)
    columns[0]["suffix"] = "."
    assert sorted(_cells(_lane(tmp_path, columns))["No"].values()) == ["1.", "2."]


def test_lane_suffix_on_another_source_is_rejected(tmp_path):
    columns = deepcopy(LANE)
    columns[1]["suffix"] = "."
    with pytest.raises(Exception) as caught:
        _lane(tmp_path, columns)
    assert "E_VIEW_LANE_TABLE_COLUMNS" in str(caught.value) or "suffix" in str(caught.value)


def test_lane_text_role_reaches_the_cell_and_unknown_role_is_rejected(tmp_path):
    columns = deepcopy(LANE)
    columns[2]["textRole"] = "cell-mono"
    review = _lane(tmp_path, columns)
    owner = [item for item in review.surface.primitives
             if item.purpose == "table-cell" and item.table_column_id == "Owner"]
    task = [item for item in review.surface.primitives
            if item.purpose == "table-cell" and item.table_column_id == "Lane"]
    assert owner and task
    assert {item.text_layout.family for item in owner} == {"Noto Sans Mono, monospace"}
    assert "Noto Sans Mono, monospace" not in {item.text_layout.family for item in task}
    (tmp_path / "b").mkdir()
    with pytest.raises(Exception) as caught:
        _lane(tmp_path / "b", columns, mono=False)
    assert "E_THEME_ROLE_REQUIRED" in str(caught.value)


def _bounds(review, scene_id):
    return next(item for item in review.surface.primitives if item.scene_id == scene_id).bounds


def test_header_rule_spans_the_table_only_and_is_absent_without_the_role(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    plain = _lane(tmp_path / "a", LANE)
    ruled = _lane(tmp_path / "b", LANE, rule=True)
    assert not [item for item in plain.surface.primitives if item.scene_id == "table-column-rule"]
    rule = next(item for item in ruled.surface.primitives if item.scene_id == "table-column-rule")
    columns = [item for item in ruled.surface.primitives if item.scene_id.startswith("column:")]
    plot = min(item.bounds[0] for item in ruled.surface.primitives if item.scene_id == "axis-rule")
    assert rule.bounds[0] <= min(item.bounds[0] for item in columns)
    assert rule.bounds[0] + rule.bounds[2] <= plot
    assert rule.bounds[2] > 0


def _flat(tmp_path, suffix_on):
    source = sr.project({"a": sr.span("a", date(2026, 2, 2), 30, title="Alpha"), "b": sr.span("b", date(2026, 3, 9), 20, title="Beta")})
    parts = sr.bundle("executive-light")
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    base = {"missing": "em-dash", "align": "start", "width": "content", "headerOrientation": "horizontal"}
    number = {"id": "No", "source": "rowIndex", **base} | ({"suffix": "."} if suffix_on == "rowIndex" else {})
    title = {"id": "Title", "source": "title", **base} | ({"suffix": "."} if suffix_on == "title" else {})
    parts["view"]["body"]["tableColumns"] = [number, title]
    return sr.render(tmp_path, source, presentation=parts)


def test_flat_table_suffix_and_rejection(tmp_path):
    assert sorted(_cells(_flat(tmp_path, "rowIndex"))["No"].values()) == ["1.", "2."]
    (tmp_path / "b").mkdir()
    with pytest.raises(Exception) as caught:
        _flat(tmp_path / "b", "title")
    assert "E_VIEW_COLUMN_SUFFIX" in str(caught.value)
