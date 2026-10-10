"""#1273: an inline legend is checked against the rows it really wraps into, not a stack of every entry.

Synthetic Project through the packaged `executive-light` bundle with a fixed-size inline legend slot and a Review
Detail Profile legend; no test reads `examples/`.
"""
from __future__ import annotations

from datetime import date

from tests.support import synthetic_review as sr

ROLES = ("planned", "milestone", "calendar-closed", "actual")
LABELS = {"planned": "Planned work", "milestone": "Gate review", "calendar-closed": "Non-working day", "actual": "Actual work"}


def _render(tmp_path, *, inline, block, item_min=None, direction="inline"):
    parts = sr.bundle("executive-light")
    legend = sr.find_node(parts["layout"], "legend")
    legend.update(direction=direction, overflow="ellipsize-with-source", inlineSize="content",
                  blockSize={"fixed": {"token": "legend-slot-block"}})
    tokens = {"legend-slot-block": block, "legend-side": inline}
    if item_min is not None:
        legend["itemMinInlineSize"] = {"token": "legend-item-min"}
        tokens["legend-item-min"] = item_min
    # The legend moves into a sidebar column of a fixed inline size: a content-sized slot there is as wide as the
    # sidebar leaves it, so a wide legend wraps there.
    footer_parent = next(item for item in parts["layout"]["root"]["children"]
                         if any(child.get("id") == "legend" for child in item.get("children", ())))
    footer_parent["children"] = [child for child in footer_parent["children"] if child.get("id") != "legend"]
    sidebar = {"id": "side", "kind": "column", "inlineSize": {"fixed": {"token": "legend-side"}},
               "blockSize": "content", "gap": {"token": "spacing.m"}, "padding": {"token": "spacing.none"},
               "alignItems": "start", "justifyContent": "start",
               "place": {"inline": "start", "block": "start", "safety": "safe"}, "children": [legend]}
    parts["layout"]["root"]["children"].insert(1, sidebar)
    parts["layout"]["requiredThemeTokens"] = sorted({*parts["layout"]["requiredThemeTokens"], *tokens})
    body = parts["theme"]["body"]
    for name, value in tokens.items():
        body["values"][name] = {"type": "number", "value": value}
    body["roles"].setdefault("milestone", {})
    body["colorBindings"].setdefault("milestone.fill", "text")
    source = sr.with_calendar(sr.project({"a": sr.span("a", date(2026, 2, 2), 30), "g": sr.point("g", date(2026, 3, 9))}))
    detail = {"version": "chrona/review-detail-profile/v0.1", "id": "legend-detail",
              "body": {"legend": [{"role": role, "label": LABELS[role]} for role in ROLES]}}
    return sr.render(tmp_path, source, presentation=parts, detail=detail)


def _track(rendered):
    return [item for item in rendered.surface.fit_warnings
            if item.failure_kind == "layout-track" and item.placement_id == "legend"]


def _rows(rendered):
    labels = [item for item in rendered.surface.primitives if item.scene_id.startswith("legend:")]
    return sorted({round(item.bounds[1], 3) for item in labels}), labels


def _sub(tmp_path, name):
    path = tmp_path / name
    path.mkdir()
    return path


def test_a_one_row_inline_legend_in_a_one_row_slot_reports_no_track_overflow(tmp_path):
    rendered = _render(_sub(tmp_path, "wide"), inline=1200, block=24, item_min=40)
    rows, labels = _rows(rendered)

    assert len(labels) == 4 and len(rows) == 1
    assert _track(rendered) == []


def test_an_inline_legend_too_wide_for_one_row_still_warns_with_the_block_its_rows_need(tmp_path):
    rendered = _render(_sub(tmp_path, "narrow"), inline=200, block=24, item_min=40)
    rows, labels = _rows(rendered)
    slot = next(item for item in rendered.surface.slots if item.source == "legend")
    warnings = _track(rendered)

    assert len(rows) > 1
    assert len(warnings) == 1 and warnings[0].behaviour == "visible-overflow"
    needed = max(item.bounds[1] + item.bounds[3] for item in labels) - slot.bounds[1]
    assert warnings[0].required_block >= needed - 1e-6
    assert warnings[0].required_block > warnings[0].available_block == 24


def test_a_stacked_legend_keeps_its_measured_stack(tmp_path):
    rendered = _render(_sub(tmp_path, "stack"), inline=300, block=24, direction="block")

    assert len(_track(rendered)) == 1  # four stacked entries in a one-row slot, as before
