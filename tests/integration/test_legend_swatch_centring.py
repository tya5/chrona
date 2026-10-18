"""A legend swatch is centred on its label's line box, in a horizontal legend as in a vertical one (#991).

The horizontal legend placed every swatch at the row top, so a thin key (the `actual` bar) and a gate hung
visibly above the label. Synthetic Project through the packaged `executive-light` bundle with the legend
slot declared `direction: inline`; no test reads `examples/`.
"""
from __future__ import annotations

from datetime import date

import pytest

from tests.support import synthetic_review as sr

DETAIL = {"version": "chrona/review-detail-profile/v0.1", "id": "legend-detail", "body": {"legend": [
    {"role": "planned", "label": "Planned"}, {"role": "actual", "label": "Actual"},
    {"role": "calendar-closed", "label": "Non-working"},
    {"role": "missing-actual", "label": "No actual"}, {"role": "snapshot", "label": "Baseline"}]}}


def _render(tmp_path, direction: str):
    parts = sr.bundle("executive-light")
    sr.find_node(parts["layout"], "legend")["direction"] = direction
    source = sr.with_calendar(sr.project({"a": sr.span("a", date(2026, 2, 2), 30),
                                          "g": sr.point("g", date(2026, 3, 9))}))
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
              "body": {"asOf": "2026-03-01", "observations": [
                  {"id": "a", "sequence": 1, "projectObjectId": "a",
                   "actual": {"start": "2026-02-02", "finish": "2026-02-27"}}]}}
    return sr.render(tmp_path, source, presentation=parts, detail=DETAIL, actual=actual)


def _pairs(rendered):
    by_id = {item.scene_id: item for item in rendered.surface.primitives}
    pairs = []
    for role in ("planned", "actual", "calendar-closed", "missing-actual", "snapshot"):
        swatch = by_id.get(f"legend-swatch:{role}") or next(
            (item for item in rendered.surface.primitives if item.scene_id.startswith(f"legend-swatch:{role}")), None)
        label = next((item for item in rendered.surface.primitives
                      if swatch is not None and item.purpose == "legend-label"
                      and item.source_ref == swatch.source_ref), None)
        if swatch is not None and label is not None:
            pairs.append((role, swatch.bounds, label.bounds))
    return pairs


@pytest.mark.parametrize("direction", ["inline", "block"])
def test_every_swatch_is_centred_on_its_label_line_box(tmp_path, direction):
    pairs = _pairs(_render(tmp_path, direction))

    assert {role for role, _, _ in pairs} == {"planned", "actual", "calendar-closed"}
    for role, swatch, label in pairs:
        swatch_centre = swatch[1] + swatch[3] / 2
        label_centre = label[1] + label[3] / 2
        assert swatch_centre == pytest.approx(label_centre, abs=0.05), (role, swatch, label)


def test_the_labels_of_one_horizontal_row_share_a_baseline(tmp_path):
    labels = [label for _, _, label in _pairs(_render(tmp_path, "inline"))]
    assert len({round(item[1], 2) for item in labels}) == 1
