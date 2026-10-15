"""Lane table columns (#1517): `rowIndex`, `{field}` and `transform: initials` on `rows.laneTable.columns`.

Every literal is ASCII or a \\u escape so the file and its console output are encoding-safe on Windows.
Synthetic Project through the packaged `executive-light` bundle (read only; no bundle is changed by #1517).
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date

import pytest

from tests.support import synthetic_review as sr

OWNERS = {"a": "Ana Maria Lopez", "b": "fw-team", "c": "(!)", "d": "zoe-ann ito"}


def _render(tmp_path, columns, *, label="lane", count=False):
    objects = {key: sr.span(key, date(2026, 2 + index, 2), 5, owner=owner, title=f"Task {key.upper()}")
               for index, (key, owner) in enumerate(OWNERS.items())}
    parts = sr.bundle("executive-light")
    parts["view"] = sr.lane_view(parts["view"])
    rows = parts["view"]["body"]["rows"]
    rows["laneTable"] = {"label": label, "count": count}
    if columns is not None:
        rows["laneTable"]["columns"] = deepcopy(columns)
    return sr.render(tmp_path, sr.project(objects), presentation=parts)


def _cells(review):
    table: dict[str, dict[str, str]] = {}
    for item in review.surface.primitives:
        if item.purpose == "table-cell":
            table.setdefault(item.table_column_id, {})[item.source_ref] = item.text
    return table


COLUMNS = [{"id": "No", "source": "rowIndex"},
           {"id": "Task", "source": "label"},
           {"id": "Owner", "source": {"field": "owner"}, "transform": "initials", "missing": {"text": "?"}}]


def test_row_index_label_and_initials_columns_are_cells_in_declared_order(tmp_path):
    table = _cells(_render(tmp_path, COLUMNS))

    assert sorted(table["No"].values()) == ["1", "2", "3", "4"]
    assert sorted(table["Owner"].values()) == ["?", "AML", "FT", "ZAI"]
    assert set(table) == {"No", "Lane", "Owner"}


def test_an_absent_columns_member_is_byte_identical(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    plain = _render(tmp_path / "a", None)
    single = _render(tmp_path / "b", [{"id": "Lane", "source": "label"}])

    assert _cells(plain) == _cells(single) and set(_cells(plain)) == {"Lane"}


def test_count_still_appends_the_items_column(tmp_path):
    table = _cells(_render(tmp_path, COLUMNS, count=True))

    assert set(table) == {"No", "Lane", "Owner", "Items"}


@pytest.mark.parametrize(("columns", "code"), [
    ([{"id": "No", "source": "rowIndex"}], "E_VIEW_LANE_TABLE_COLUMNS"),                      # no label column
    ([{"id": "A", "source": "label"}, {"id": "B", "source": "label"}], "E_VIEW_LANE_TABLE_COLUMNS"),
    ([{"id": "A", "source": "label"}, {"id": "A", "source": "rowIndex"}], "E_VIEW_LANE_TABLE_COLUMNS"),
    ([{"id": "A", "source": "label"}, {"id": "B", "source": "rowIndex", "transform": "initials"}], "E_VIEW_LANE_TABLE_COLUMNS"),
    ([{"id": "A", "source": "label"}, {"id": "Items", "source": "rowIndex"}], "E_VIEW_LANE_TABLE_COLUMNS"),
    ([{"id": "A", "source": "label", "transform": "upper"}], "E_VIEW_SCHEMA"),
    ([], "E_VIEW_SCHEMA"),
])
def test_misdeclared_columns_are_refused(tmp_path, columns, code):
    with pytest.raises(Exception) as caught:
        _render(tmp_path, columns)

    assert code in str(getattr(caught.value, "code", "")) + str(caught.value)
