"""Only the forecast primary owns its member name; paired ghost ink and required deltas remain."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from chrona.usecases.draft_render import render_draft
from tests.integration.test_forecast_occurrence_coverage import (
    _forecast_deltas, _forecast_marks, _request, _write,
)


def _member_labels(rendered):
    return [item for item in rendered.surface.primitives if item.purpose == "member-label"]


@pytest.mark.parametrize("case, expected", [
    ("automatic", {"a", "b"}),
    ("explicit", {"a", "b"}),
    ("folded", {"a", "gate"}),
    ("lanes", {"a", "b"}),
])
def test_forecast_labels_are_owned_by_primary_across_row_compositions(tmp_path, case, expected):
    request = _request(tmp_path, placement="plot", explicit=case == "explicit", folded=case == "folded")
    if case == "lanes":
        view_path = Path(request.view)
        view = yaml.safe_load(view_path.read_text(encoding="utf-8"))
        body = view["body"]
        body.pop("tableColumns", None)
        body["rows"] = {"mode": "lanes", "packing": ["explicit", "attached"],
                         "laneTable": {"label": "group", "count": True}}
        _write(view_path, view)

    rendered = render_draft(request).rendered
    labels = _member_labels(rendered)
    assert {item.source_ref for item in labels} == expected
    assert len(labels) == len(expected)
    assert all(item.source_kind != "snapshot" for item in labels)
    assert {item.source_ref for item in _forecast_marks(rendered)} == expected
    assert {item.source_ref for item in _forecast_deltas(rendered)} == expected


def test_nonforecast_snapshot_label_eligibility_is_unchanged(tmp_path):
    request = _request(tmp_path, placement="plot")
    ordinary = render_draft(replace(request, forecast=False)).rendered
    labels = _member_labels(ordinary)
    assert {item.source_ref for item in labels} == {"a", "b"}
    assert not any(item.purpose == "forecast" for item in ordinary.surface.primitives)

