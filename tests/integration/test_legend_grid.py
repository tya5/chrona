"""A legend slot can declare its entries as a grid, with its caption in the start column (#1290).

Synthetic Project through the packaged `executive-light` bundle with a Review Detail Profile legend; no test reads
`examples/`.
"""
from __future__ import annotations

from datetime import date

import pytest

from tests.support import synthetic_review as sr

ROLES = ("planned", "milestone", "calendar-closed", "actual")
LABELS = {"planned": "Planned work", "milestone": "Gate review", "calendar-closed": "Non-working day",
          "actual": "Actual work"}


def _render(tmp_path, *, columns=None, heading=None, direction=None, roles=ROLES):
    parts = sr.bundle("executive-light")
    legend = sr.find_node(parts["layout"], "legend")
    if columns is not None:
        legend["columns"] = columns
    if direction is not None:
        legend["direction"] = direction
    if heading is not None:
        legend["heading"] = heading
    body = parts["theme"]["body"]
    body["roles"].setdefault("milestone", {})
    body["colorBindings"].setdefault("milestone.fill", "text")
    source = sr.with_calendar(sr.project({"a": sr.span("a", date(2026, 2, 2), 30), "g": sr.point("g", date(2026, 3, 9))}))
    detail = {"version": "chrona/review-detail-profile/v0.1", "id": "legend-detail",
              "body": {"legend": [{"role": role, "label": LABELS[role]} for role in roles]}}
    return sr.render(tmp_path, source, presentation=parts, detail=detail)


def _sub(tmp_path, name):
    path = tmp_path / name
    path.mkdir()
    return path


def _entries(rendered, roles=ROLES):
    found = {}
    for role in roles:
        swatch = next(item for item in rendered.surface.primitives if item.scene_id.startswith(f"legend-swatch:{role}"))
        label = next(item for item in rendered.surface.primitives if item.scene_id == f"legend:{role}")
        found[role] = (swatch.bounds, label.bounds)
    return found


def test_entries_fill_ceil_count_over_columns_rows_in_reading_order(tmp_path):
    rendered = _render(tmp_path, columns=3)
    found = _entries(rendered)
    swatch_x = [found[role][0][0] for role in ROLES]
    swatch_y = [found[role][0][1] for role in ROLES]
    label_y = [found[role][1][1] for role in ROLES]

    assert len({round(value, 3) for value in label_y}) == 2  # ceil(4 / 3) rows
    assert round(label_y[0], 3) == round(label_y[1], 3) == round(label_y[2], 3) < round(label_y[3], 3)
    assert swatch_x[0] < swatch_x[1] < swatch_x[2] and swatch_x[3] == pytest.approx(swatch_x[0])  # entry 3 is column 0
    assert swatch_y[0] < swatch_y[3]


def test_each_column_is_as_wide_as_its_widest_entry(tmp_path):
    found = _entries(_render(tmp_path, columns=2))
    # Entries 0 and 2 share column 0, entries 1 and 3 share column 1.
    start_of_column_1 = found["milestone"][0][0]
    assert found["actual"][0][0] == pytest.approx(start_of_column_1)
    widest_in_column_0 = max(found[role][1][0] + found[role][1][2] for role in ("planned", "calendar-closed"))
    assert start_of_column_1 > widest_in_column_0  # a gap past the widest label of column 0


def test_a_single_column_stacks_every_entry(tmp_path):
    found = _entries(_render(tmp_path, columns=1))
    ys = [found[role][1][1] for role in ROLES]

    assert ys == sorted(ys) and len(set(round(y, 3) for y in ys)) == 4


def test_without_columns_the_legend_is_unchanged(tmp_path):
    plain = _render(_sub(tmp_path, "a"))
    block = _render(_sub(tmp_path, "b"), direction="block")

    assert plain.artifact.content == block.artifact.content


def test_a_grid_that_does_not_fit_its_slot_reports_the_track_overflow(tmp_path):
    rendered = _render(tmp_path, columns=3)
    legend = next(item for item in rendered.surface.slots if item.source == "legend")
    rows_end = max(entry[1][1] + entry[1][3] for entry in _entries(rendered).values())

    assert legend.bounds[1] + legend.bounds[3] >= rows_end - 1e-6  # the slot is allocated its measured rows


def test_a_start_column_heading_sits_beside_the_entries_within_their_block_extent(tmp_path):
    rendered = _render(tmp_path, columns=2, heading={"text": "The key", "block": "start-column"})
    heading = next(item for item in rendered.surface.primitives if item.scene_id.startswith("slot-heading:"))
    found = _entries(rendered)
    entries_top = min(min(swatch[1], label[1]) for swatch, label in found.values())
    entries_bottom = max(max(swatch[1] + swatch[3], label[1] + label[3]) for swatch, label in found.values())

    assert heading.bounds[1] >= entries_top - 1e-6 and heading.bounds[1] + heading.bounds[3] <= entries_bottom + 1e-6
    heading_end = heading.bounds[0] + heading.bounds[2]
    assert all(swatch[0] >= heading_end - 1e-6 for swatch, _ in found.values())  # no overlap with any entry


def test_a_start_column_heading_on_a_legend_without_columns_falls_back_to_the_top_with_a_record(tmp_path):
    rendered = _render(tmp_path, heading={"text": "The key", "block": "start-column"})

    assert any("I_LAYOUT_SLOT_HEADING_NO_START_COLUMN" in item for item in rendered.scene.diagnostics)
