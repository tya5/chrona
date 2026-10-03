"""The as-of chip's position and date form are declared on the marker (#991), end to end.

Synthetic Project through the packaged `executive-light` bundle; no test reads `examples/`.
"""
from __future__ import annotations

from datetime import date

import pytest

from tests.support import synthetic_review as sr

ACTUAL = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
          "body": {"asOf": "2026-02-20", "observations": []}}


def _render(tmp_path, **marker_edits):
    source = sr.project({"a": sr.span("a", date(2026, 2, 2), 40, title="Alpha"), "b": sr.span("b", date(2026, 3, 9), 20, title="Beta")})
    parts = sr.bundle("executive-light")
    marker = next(item for item in parts["view"]["body"]["markers"] if item["kind"] == "asOf")
    marker.update(marker_edits)
    return sr.render(tmp_path, source, presentation=parts, actual=ACTUAL)


def _chip(rendered):
    label = next(item for item in rendered.surface.primitives if item.scene_id == "as-of-label")
    rule = next(item for item in rendered.surface.primitives if item.scene_id == "as-of")
    return label, rule


def test_by_default_the_chip_sits_in_the_top_margin_and_reads_the_localized_date(tmp_path):
    label, rule = _chip(_render(tmp_path))
    assert label.text.endswith("Feb 20, 2026")
    top, bottom = rule.points[0][1], rule.points[-1][1]
    assert label.bounds[1] - top < (bottom - top) / 4  # near the top of the plot


def test_foot_placement_puts_the_chip_at_the_plot_foot_centred_on_the_rule(tmp_path):
    label, rule = _chip(_render(tmp_path, placement="foot", date={"form": "day-month"}))
    top, bottom = rule.points[0][1], rule.points[-1][1]
    assert label.text.endswith("20 Feb") and not label.text.endswith("2026")
    assert bottom - (label.bounds[1] + label.bounds[3]) < (bottom - top) / 4  # near the bottom of the plot
    rule_x = rule.points[0][0]
    assert label.bounds[0] <= rule_x <= label.bounds[0] + label.bounds[2]  # centred over the rule, not beside it


def test_the_day_month_year_form_adds_the_year(tmp_path):
    label, _ = _chip(_render(tmp_path, date={"form": "day-month-year"}))
    assert label.text.endswith("20 Feb 2026")
