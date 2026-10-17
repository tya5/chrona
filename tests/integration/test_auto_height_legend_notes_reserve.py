"""#1649: a Draft `auto` canvas reserves the rows an inline legend wraps to and nothing for an empty notes source.

Synthetic Project through the packaged `executive-light` bundle; no test reads `examples/`.
"""
from __future__ import annotations

from datetime import date

from tests.support import synthetic_review as sr

ROLES = ("planned", "milestone", "calendar-closed", "actual")
LABELS = {"planned": "Planned work", "milestone": "Gate review", "calendar-closed": "Non-working day", "actual": "Actual work"}


def _render(tmp_path, *, inline_width, item_min=None, notes=False, height: int | None = None, name="r"):
    parts = sr.bundle("executive-light")
    legend = sr.find_node(parts["layout"], "legend")
    legend.update(direction="inline", overflow="ellipsize-with-source", inlineSize="fill", blockSize="content")
    tokens = {}
    if item_min is not None:
        legend["itemMinInlineSize"] = {"token": "legend-item-min"}
        tokens["legend-item-min"] = item_min
    parts["layout"]["requiredThemeTokens"] = sorted({*parts["layout"]["requiredThemeTokens"], *tokens})
    body = parts["theme"]["body"]
    for key, value in tokens.items():
        body["values"][key] = {"type": "number", "value": value}
    body["roles"].setdefault("milestone", {})
    body["colorBindings"].setdefault("milestone.fill", "text")
    source = sr.with_calendar(sr.project({"a": sr.span("a", date(2026, 2, 2), 30), "g": sr.point("g", date(2026, 3, 9))}))
    if notes:
        source["annotations"] = {"n1": {"kind": "note", "text": "A synthetic note.", "anchor": {"object": "a"}}}
    detail = {"version": "chrona/review-detail-profile/v0.1", "id": "legend-detail",
              "body": {"legend": [{"role": role, "label": LABELS[role]} for role in ROLES]}}
    path = tmp_path / name
    path.mkdir()
    return sr.render(path, source, presentation=parts, detail=detail, viewport=(inline_width, height))


def _legend(rendered):
    slot = next(item for item in rendered.surface.slots if item.source == "legend")
    labels = [item for item in rendered.surface.primitives if item.scene_id.startswith("legend:")]
    rows = sorted({round(item.bounds[1], 3) for item in labels})
    return slot, rows


def _height(rendered):
    return rendered.surface.canvas_bounds[3]


def test_a_wrapping_inline_legend_reserves_the_rows_it_wraps_to_not_every_entry(tmp_path):
    rendered = _render(tmp_path, inline_width=700, item_min=300)
    slot, rows = _legend(rendered)

    assert 1 < len(rows) < len(ROLES)
    step = rows[1] - rows[0]
    assert slot.bounds[3] < len(ROLES) * step
    assert slot.bounds[3] >= rows[-1] - rows[0] + 1  # holds every drawn row


def test_a_legend_that_fits_one_row_reserves_one_row(tmp_path):
    rendered = _render(tmp_path, inline_width=1600, item_min=40)
    slot, rows = _legend(rendered)

    assert len(rows) == 1
    assert slot.bounds[3] < 40


def test_an_inline_legend_without_a_wrap_rule_is_one_row_not_a_stack(tmp_path):
    rendered = _render(tmp_path, inline_width=1600)
    slot, rows = _legend(rendered)

    assert len(rows) == 1 and slot.bounds[3] < 40


def test_a_fixed_height_canvas_is_unchanged_by_the_narrowing(tmp_path):
    fixed = _render(tmp_path, inline_width=700, item_min=300, height=900, name="fixed")

    assert _height(fixed) == 900


def test_an_empty_notes_source_reserves_nothing_and_a_non_empty_one_keeps_its_slot(tmp_path):
    empty = _render(tmp_path, inline_width=1600, name="empty")
    noted = _render(tmp_path, inline_width=1600, notes=True, name="noted")

    assert not any(item.source == "notes" for item in empty.surface.slots)
    assert any(item.source == "notes" and item.bounds[3] > 0 for item in noted.surface.slots)
