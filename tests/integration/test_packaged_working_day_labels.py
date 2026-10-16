"""Packaged comparison policy reaches plot labels through canonical facts."""
import pytest

from tests.support import synthetic_review as sr


def _project():
    return {
        "version": "timeline/v0.7", "project": {"id": "working-label", "calendar": "office"},
        "calendars": {"office": {"working_days": ["mon", "tue", "wed", "thu", "fri"]}},
        "objects": {"test-plan": {"type": "task", "title": "Test plan", "schedule": {
            "mode": "scheduled", "amount": "5wd", "anchor": {"start": "2026-10-05"}}}},
        "relations": [],
    }


def _actual():
    return {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observations",
            "body": {"asOf": "2026-10-12", "observations": [{"id": "done", "sequence": 1,
                "projectObjectId": "test-plan", "actual": {
                    "start": "2026-10-05", "finish": "2026-10-10", "progress": 1}}]}}


@pytest.mark.parametrize("declared_unit,expected", [(None, "0d"), ("working-days", "0d"), ("calendar-days", "-2d")])
@pytest.mark.parametrize("row_mode", ["lanes", "automatic"])
def test_executive_plot_label_uses_shared_declared_comparison(tmp_path, declared_unit, expected, row_mode):
    parts = sr.bundle("executive-light")
    if declared_unit is not None:
        parts["view"]["body"]["comparison"]["deltaUnit"] = declared_unit
    parts["view"]["body"]["rows"]["mode"] = row_mode
    if row_mode == "automatic":
        parts["view"]["body"]["rows"] = {"mode": "automatic"}
    rendered = sr.render(tmp_path, _project(), presentation=parts, actual=_actual())
    labels = [item.text for item in rendered.surface.primitives if item.kind == "Text"
              and "Test plan" in (item.text or "")]
    assert any(expected in label for label in labels), labels
    if expected == "0d":
        assert all("-2d" not in label for label in labels)
