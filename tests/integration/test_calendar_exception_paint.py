"""A calendar-exception day is drawn in its own colour when the Theme declares a `calendar-exception` role (#991).

Exception days drew with the closed-day role, so only the legend swatch could be orange. Synthetic Project through the
packaged `executive-light` bundle; no test reads `examples/`.
"""
from __future__ import annotations

from datetime import date

import pytest

from tests.support import synthetic_review as sr

EXCEPTION = date(2026, 2, 11)  # a Wednesday the calendar closes by an exception


def _render(tmp_path, *, role: bool):
    source = sr.with_calendar(sr.project({"a": sr.span("a", date(2026, 2, 2), 28, title="Alpha")}))
    source["calendars"]["standard"]["exceptions"] = [{"date": EXCEPTION.isoformat(), "working": False}]
    parts = sr.bundle("executive-light")
    body = parts["theme"]["body"]
    if role:
        body["values"]["exception-opacity"] = {"type": "number", "value": 0.6}
        body["roles"]["calendar-exception"] = {"backgroundTreatment": "fill", "backgroundPaintOrder": 12, "opacity": "exception-opacity"}
        body["colorBindings"]["calendar-exception.fill"] = "warning"
    return sr.render(tmp_path, source, presentation=parts)


def _days(rendered, purpose: str) -> dict[str, tuple]:
    return {item.scene_id.split(":", 1)[1]: (item.visual_role, item.paint) for item in rendered.surface.primitives
            if item.purpose == purpose}


def _sub(tmp_path, name):
    path = tmp_path / name
    path.mkdir()
    return path


def test_without_the_role_an_exception_day_is_a_closed_day(tmp_path):
    rendered = _render(_sub(tmp_path, "a"), role=False)
    assert EXCEPTION.isoformat() in _days(rendered, "calendar-closed")
    assert not _days(rendered, "calendar-exception")


def test_with_the_role_the_exception_day_is_its_own_shape_and_other_closed_days_are_not(tmp_path):
    plain = _days(_render(_sub(tmp_path, "plain"), role=False), "calendar-closed")
    rendered = _render(_sub(tmp_path, "role"), role=True)
    exceptions, closed = _days(rendered, "calendar-exception"), _days(rendered, "calendar-closed")

    assert set(exceptions) == {EXCEPTION.isoformat()}
    assert EXCEPTION.isoformat() not in closed
    assert set(closed) == set(plain) - {EXCEPTION.isoformat()}  # weekends stay closed days, unchanged
    role, paint = exceptions[EXCEPTION.isoformat()]
    assert role == "calendar-exception" and paint.fill != next(iter(closed.values()))[1].fill
    assert paint.opacity == pytest.approx(0.6)
