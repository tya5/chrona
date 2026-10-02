"""A Project with no declared calendar has no closed day to shade (#893).

The Specification defines no built-in default calendar: scheduling refuses working-day arithmetic without one
(`E_CALENDAR_REQUIRED`), so shading Saturday and Sunday (or every day) would show a calendar the schedule does
not use. Closed days come from the Project default calendar only, and the legend key for them is listed only when
a closed day is selected. Each rule is proven on a synthetic Project rendered through the packaged `editorial`
bundle and its Detail Profile (the starter's presentation), so no corpus edit can change what these tests prove.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from chrona.usecases.render_review import RenderRejected
from chrona.resources import builtin_preset_source_root, safe_load
from tests.support import synthetic_review as sr

WEEKDAYS = {"working_days": ["mon", "tue", "wed", "thu", "fri"]}


def _detail() -> dict:
    root = builtin_preset_source_root("presets/bundles/editorial")
    return safe_load(root.joinpath("detail.yaml").read_bytes())


def _source(calendars: dict | None = None, default: str | None = None) -> dict:
    source = sr.project({"a": sr.span("a", date(2026, 1, 5), 40), "g": sr.point("g", date(2026, 2, 20))})
    if calendars is not None:
        source["calendars"] = calendars
    if default is not None:
        source["project"]["calendar"] = default
    return source


def _render(tmp_path: Path, source: dict, *, closed_days: bool = True):
    parts = sr.bundle("editorial")
    parts["view"]["body"]["window"] = {"mode": "explicit", "start": "2026-01-01", "end": "2026-03-01"}
    if not closed_days:
        parts["view"]["body"]["shading"] = {"nonWorking": False, "exceptions": True}
    return sr.render(tmp_path, source, presentation=parts, detail=_detail())


def _closed(rendered) -> list[str]:
    return [item.scene_id for item in rendered.surface.primitives if item.purpose == "calendar-closed"]


def _key(rendered) -> list[str]:
    return [item.scene_id for item in rendered.surface.primitives if item.scene_id == "legend-swatch:calendar-closed"]


def test_a_project_without_a_calendar_draws_no_closed_day_and_no_closed_day_key(tmp_path):
    rendered = _render(tmp_path, _source())
    assert _closed(rendered) == []
    assert _key(rendered) == []
    # The other legend keys are still listed.
    assert {"legend-swatch:planned", "legend-swatch:milestone"} <= {item.scene_id for item in rendered.surface.primitives}


def test_a_default_calendar_naming_no_declared_calendar_is_rejected_before_presentation(tmp_path):
    with pytest.raises(RenderRejected):
        _render(tmp_path, _source({"standard": WEEKDAYS}, default="missing"))


def test_calendars_declared_without_a_default_shade_nothing(tmp_path):
    rendered = _render(tmp_path, _source({"standard": WEEKDAYS, "other": WEEKDAYS}))
    assert _closed(rendered) == [] and _key(rendered) == []


def test_a_declared_default_calendar_shades_its_closed_days_and_lists_the_key(tmp_path):
    rendered = _render(tmp_path, _source({"standard": WEEKDAYS}, default="standard"))
    ids = _closed(rendered)
    days = [date.fromisoformat(item.rsplit(":", 1)[1]) for item in ids]
    assert days and all(day.weekday() >= 5 for day in days)
    assert days == [day for day in (days[0] + timedelta(n) for n in range((days[-1] - days[0]).days + 1))
                    if day.weekday() >= 5], "every weekend day of the window, and no other day"
    assert "calendar-closed:2026-01-03" in ids and "calendar-closed:2026-01-05" not in ids
    assert _key(rendered) == ["legend-swatch:calendar-closed"]


def test_a_declared_exception_day_closes_without_a_default_weekend_rule(tmp_path):
    rendered = _render(tmp_path, _source({"all": {"working_days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
                                                   "exceptions": [{"date": "2026-01-01", "working": False}]}},
                                         default="all"), closed_days=False)
    assert _closed(rendered) == ["calendar-closed:2026-01-01"]


def test_the_key_is_dropped_with_the_band_when_the_view_selects_no_closed_day(tmp_path):
    rendered = _render(tmp_path, _source({"standard": WEEKDAYS}, default="standard"), closed_days=False)
    assert _closed(rendered) == [] and _key(rendered) == []


def _sidebar_parts() -> dict:
    """A content-sized legend slot in a sidebar, so the slot is as wide as its widest listed entry (#497)."""
    parts = sr.bundle("control-room-dark")
    legend = {"id": "legend", "kind": "slot", "source": "legend", "inlineSize": "content", "blockSize": "content",
              "place": {"inline": "start", "block": "start", "safety": "safe"}, "priority": "preferred",
              "overflow": "ellipsize-with-source"}
    sidebar = {"id": "side", "kind": "column", "inlineSize": {"fixed": {"token": "side-width"}},
               "blockSize": "content", "gap": {"token": "spacing.m"}, "padding": {"token": "spacing.none"},
               "alignItems": "start", "justifyContent": "start",
               "place": {"inline": "start", "block": "start", "safety": "safe"}, "children": [legend]}
    parts["layout"]["root"]["children"].insert(1, sidebar)
    parts["layout"]["requiredThemeTokens"] = sorted({*parts["layout"]["requiredThemeTokens"], "side-width"})
    parts["theme"]["body"]["values"]["side-width"] = {"type": "number", "value": 600}
    return parts


def test_the_legend_slot_is_measured_without_the_dropped_key(tmp_path):
    detail = {"version": "chrona/review-detail-profile/v0.1", "id": "closed-key", "body": {"legend": [
        {"role": "planned", "label": "Planned"},
        {"role": "calendar-closed", "label": "A closed day key with a deliberately long label"}]}}
    widths = {}
    for name, source in (("bare", _source()), ("keyed", _source({"standard": WEEKDAYS}, default="standard"))):
        (tmp_path / name).mkdir()
        rendered = sr.render(tmp_path / name, source, presentation=_sidebar_parts(), detail=detail)
        widths[name] = next(item for item in rendered.surface.slots if item.source == "legend").bounds[2]

    assert widths["bare"] < widths["keyed"] / 2
