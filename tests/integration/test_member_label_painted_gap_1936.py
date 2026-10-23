"""Synthetic evidence for #1936's painted-mark to full-label footprint gap."""
from __future__ import annotations

from datetime import date

import pytest

from tests.support import synthetic_review as sr


def _render(tmp_path, *, label_gap=20, stroke_width=8, chip=False, point=False):
    parts = sr.bundle("executive-light")
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    parts["view"]["body"]["tableColumns"] = [{
        "id": "Work package", "source": "title", "missing": "em-dash",
        "align": "start", "width": "content", "headerOrientation": "horizontal",
    }]
    parts["view"]["body"]["visibility"]["labels"] = {
        "placement": "plot", "content": ["title"], "side": "end", "overflow": "suppress",
    }
    theme = parts["theme"]["body"]
    if label_gap is not None:
        theme["values"]["label-gap"] = {"type": "number", "value": label_gap}
        theme["metrics"]["timeline.mark.labelGap"] = "label-gap"
    theme["values"]["wide-stroke"] = {"type": "number", "value": stroke_width}
    theme["roles"]["planned"]["strokeWidth"] = "wide-stroke"
    if chip:
        theme["values"]["chip-padding"] = {"type": "number", "value": 0.1}
        theme["roles"]["member-label-chip"] = {
            "backgroundTreatment": "fill", "chipPadding": "chip-padding",
        }
        theme["colorBindings"]["member-label-chip.fill"] = "surfaceRaised"
    directory = tmp_path
    directory.mkdir(parents=True, exist_ok=True)
    item = (sr.point("a", date(2026, 2, 4), title="Painted gap target") if point else
            sr.span("a", date(2026, 2, 2), 5, title="Painted gap target"))
    rendered = sr.render(directory, sr.project({"a": item}), presentation=parts)
    return rendered, label_gap, stroke_width


def _gap_from_mark_to_full_label(rendered, stroke_width):
    primitives = {item.scene_id: item for item in rendered.surface.primitives}
    mark = next(item for item in primitives.values() if item.purpose == "planned" and item.source_ref == "a")
    label_group = [item for item in primitives.values()
                   if item.scene_id in {"member-label:a:a", "chip:member-label:a:a"}
                   or item.scene_id.startswith("visual:member-label:a:a:")]
    assert label_group
    mark_right = float(mark.bounds[0] + mark.bounds[2])
    label_left = min(float(item.bounds[0]) for item in label_group)
    # The span outline's actual stroke extends half its width past semantic bounds.
    painted_right = mark_right + stroke_width / 2
    return label_left - painted_right


def test_authored_gap_is_measured_from_painted_mark_to_full_label_footprint(tmp_path):
    rendered, label_gap, stroke_width = _render(tmp_path, chip=True)

    assert any(item.kind == "Rect" and item.visual_role == "member-label-chip"
               for item in rendered.surface.primitives)
    assert _gap_from_mark_to_full_label(rendered, stroke_width) == pytest.approx(label_gap)


def test_unbound_gap_keeps_existing_semantic_anchor_placement(tmp_path):
    rendered, _, stroke_width = _render(tmp_path, label_gap=None, chip=True)

    # Removing the authored binding must not switch the established fallback
    # anchor convention; its semantic-edge gap is four px, consumed by stroke.
    assert _gap_from_mark_to_full_label(rendered, stroke_width) == pytest.approx(0)


def test_authored_gap_uses_completed_point_glyph_footprint(tmp_path):
    rendered, label_gap, stroke_width = _render(tmp_path, chip=True, point=True)

    # The default point glyph is filled (not stroked), so its exact path bounds
    # are the painted envelope; the configured span stroke does not apply.
    assert _gap_from_mark_to_full_label(rendered, 0) == pytest.approx(label_gap)
