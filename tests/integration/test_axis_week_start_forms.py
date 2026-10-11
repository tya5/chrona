"""Week axis labels that name the week's first day (#1278).

A synthetic Project is rendered through a packaged preset bundle over a window that crosses a month and a year boundary and
starts mid-week, so the first (clipped) interval is named by its natural first day.
"""
from __future__ import annotations

from datetime import date

import pytest

from chrona.resources import schema_validator
from tests.support import synthetic_review as sr

WINDOW = {"mode": "explicit", "start": "2026-12-16", "end": "2027-01-25"}  # a Wednesday start
WEEKS = ["2026-12-14", "2026-12-21", "2026-12-28", "2027-01-04", "2027-01-11", "2027-01-18"]  # the Mondays


def _parts(form: str, table: str, secondary: str | None = None) -> dict:
    parts = sr.bundle("executive-light")
    parts["view"]["body"]["window"] = dict(WINDOW)
    label = {"form": form, "nameTable": table, "align": "start", "overflow": "visible-overflow", "orientation": "horizontal"}
    if secondary is not None:
        label["secondary"] = {"form": secondary, "nameTable": table, "typographyRole": "axisSecondary", "placement": "inline"}
        month = {key: value for key, value in parts["theme"]["body"]["roles"]["axisMonth"].items()
                 if key not in {"laneBlockSize", "labelInset"}}
        parts["theme"]["body"]["roles"]["axisSecondary"] = {**month}
    parts["view"]["body"]["axis"] = {"tiers": [{"unit": "week", "every": 1, "role": "labels", "label": label}]}
    return parts


def _labels(tmp_path, parts) -> list[str]:
    source = sr.project({"a": sr.span("a", date(2026, 12, 21), 20), "b": sr.span("b", date(2027, 1, 4), 12, owner="b")})
    rendered = sr.render(tmp_path, source, presentation=parts)
    items = [item for item in rendered.surface.primitives if item.scene_id.startswith("axis-label:")]
    return [item.text for item in sorted(items, key=lambda item: item.bounds[0])]


@pytest.mark.parametrize("form, table, expected", [
    ("start-day-month", "en-US", ["14 Dec", "21 Dec", "28 Dec", "4 Jan", "11 Jan", "18 Jan"]),
    ("start-numeric", "en-US", ["12/14", "12/21", "12/28", "01/04", "01/11", "01/18"]),
    ("iso-week", "en-US", ["2026-W51", "2026-W52", "2026-W53", "2027-W01", "2027-W02", "2027-W03"]),
])
def test_each_week_form_names_the_natural_first_day_across_a_month_and_year_boundary(tmp_path, form, table, expected):
    assert _labels(tmp_path, _parts(form, table)) == expected


@pytest.mark.parametrize("form, expected", [
    ("start-day-month", ["12月14日", "12月21日", "12月28日", "1月4日", "1月11日", "1月18日"]),
    ("start-numeric", ["12/14", "12/21", "12/28", "01/04", "01/11", "01/18"]),
])
def test_the_japanese_table_names_the_same_first_days(form, expected):
    """Formatted directly: the packaged test fonts carry no kanji, so a drawn ja-JP label is covered by the formatter."""
    from chrona.presentation.axis_intervals import axis_intervals
    from chrona.presentation.layout.axis import format_axis_tier_label
    from chrona.presentation.model.axis_names import axis_name_table

    intervals = axis_intervals(date(2026, 12, 16), date(2027, 1, 25), "week")
    assert [format_axis_tier_label(item, form, axis_name_table("ja-JP")) for item in intervals] == expected
    assert [item.natural_start.isoformat() for item in intervals] == WEEKS


def test_the_schema_accepts_the_new_forms_for_the_label_and_its_secondary_and_nothing_else():
    validator = schema_validator("view-v0.28.schema.yaml")

    def errors(form, secondary=None):
        view = _parts(form, "en-US", secondary)["view"]
        return [error.message for error in validator.iter_errors(view)]

    for form in ("iso-week", "start-day-month", "start-numeric"):
        assert errors("iso-week", form) == []
        assert errors(form) == []
    assert errors("iso-week", "start-numeric") == []
    assert errors("week-start") and errors("start-numeric", "short-month")
