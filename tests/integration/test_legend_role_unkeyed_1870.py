"""A drawn band or fill role the drawn legend does not key is named in a warning (#1870 row 2)."""
from __future__ import annotations

from datetime import date

from tests.support import synthetic_review as sr

CODE = "W_LEGEND_ROLE_UNKEYED"
ACTUAL = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "unkeyed-actual",
          "body": {"asOf": "2026-03-20", "observations": [
              {"id": "a-actual", "sequence": 1, "projectObjectId": "a",
               "actual": {"start": "2026-02-02", "finish": "2026-02-28"}}]}}


def _render(tmp_path, roles, *, legend=True):
    parts = sr.bundle("executive-light")
    detail = None if not legend else {"version": "chrona/review-detail-profile/v0.1", "id": "keys",
              "body": {"legend": [{"role": role, "label": role.title()} for role in roles]}}
    source = sr.with_calendar(sr.project({"a": sr.span("a", date(2026, 2, 2), 30)}))
    rendered = sr.render(tmp_path, source, presentation=parts, detail=detail, actual=ACTUAL)
    drawn = {item.purpose for item in rendered.surface.primitives}
    return rendered, drawn, [item.payload for item in rendered.warning_records if item.payload.get("code") == CODE]


def test_a_drawn_closed_day_band_without_a_key_is_named(tmp_path):
    rendered, drawn, warnings = _render(tmp_path, ("planned", "actual"))

    assert "calendar-closed" in drawn and "legend-label" in drawn
    assert [item["diagnostic"] for item in warnings] == [
        CODE + ':{"drawnAs":"calendar-closed","role":"calendar-closed"}']
    assert warnings[0]["severity"] == "warning"
    assert "calendar-closed (legend role calendar-closed)" in warnings[0]["message"]
    assert "no further detail" not in warnings[0]["message"]


def test_a_keyed_band_is_not_reported(tmp_path):
    _, drawn, warnings = _render(tmp_path, ("planned", "actual", "calendar-closed"))

    assert "calendar-closed" in drawn
    assert warnings == []


def test_a_surface_without_a_legend_has_nothing_to_key_against(tmp_path):
    _, drawn, warnings = _render(tmp_path, (), legend=False)

    assert "legend-label" not in drawn
    assert warnings == []
