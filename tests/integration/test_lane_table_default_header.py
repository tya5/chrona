"""Default lane table header (#1633): `Task` for generated one-per-object lanes, `Lane` for declared lanes.

ASCII only. Synthetic Project through the packaged `executive-light` bundle (read only).
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date

from tests.support import synthetic_review as sr


def _render(tmp_path, *, lane_keys=None, columns=None, label="lane", packing=("explicit", "attached"), shared_owner=False):
    objects = {key: sr.span(key, date(2026, 2 + index, 2), 5, owner="a" if shared_owner else key, title=f"Task {key.upper()}")
               for index, key in enumerate("abcd")}
    parts = sr.bundle("executive-light")
    parts["view"] = sr.lane_view(parts["view"], packing=packing)
    rows = parts["view"]["body"]["rows"]
    rows["laneTable"] = {"label": label, "count": False}
    if columns is not None:
        rows["laneTable"]["columns"] = deepcopy(columns)
    if lane_keys is not None:
        rows["laneKeys"] = {"byObject": lane_keys}
    return sr.render(tmp_path, sr.project(objects), presentation=parts)


def _headers(review):
    column_ids = {item.table_column_id for item in review.surface.primitives
                  if item.purpose == "table-cell" and item.table_column_id}
    texts = {item.text for item in review.surface.primitives if getattr(item, "text", None)}
    return column_ids, texts


def test_generated_one_per_object_lanes_read_task(tmp_path):
    ids, texts = _headers(_render(tmp_path))

    assert ids == {"Lane"} and "Task" in texts and "Lane" not in texts


def test_declared_lane_keys_read_lane(tmp_path):
    ids, texts = _headers(_render(tmp_path, lane_keys={"a": "k1", "b": "k1"}))

    assert ids == {"Lane"} and "Lane" in texts and "Task" not in texts


def test_shared_generated_lanes_read_lane(tmp_path):
    parts = ("explicit", "attached", "dates")
    _, texts = _headers(_render(tmp_path, packing=parts, shared_owner=True))

    assert "Lane" in texts and "Task" not in texts


def test_explicit_columns_are_unchanged(tmp_path):
    _, texts = _headers(_render(tmp_path, columns=[{"id": "Name", "source": "label"}]))

    assert "Name" in texts and "Task" not in texts
