"""#918: scale failures retain the View or Theme source that owns them."""
from __future__ import annotations

from datetime import date

import pytest

from chrona.usecases.render_review import RenderFailed
from chrona.usecases.failure_report import report_failure
from tests.support import synthetic_review as sr


def _project(owner: str = "bus"):
    key = "scale-task"
    source = sr.project({key: sr.span(key, date(2026, 1, 5), 12, owner=owner)})
    source["entities"].setdefault(owner, {"title": owner.title()})
    return source


def _parts():
    return sr.bundle("control-room-dark")


def test_group_tint_mapping_failure_points_to_escaped_theme_scale_slots(tmp_path):
    parts = _parts()
    parts["view"]["body"]["grouping"]["tint"] = {"scale": "missing/name~"}

    with pytest.raises(RenderFailed) as caught:
        sr.render(tmp_path, _project(), presentation=parts)

    error = caught.value
    assert error.code == "E_PRESENTATION_SCALE_MAPPING"
    assert error.source_ref == "/body/colorScales/missing~1name~0/slots"
    assert "Theme scale 'missing/name~'" in error.message


def test_late_view_value_failure_is_converted_by_outer_render_boundary(tmp_path):
    parts = _parts()
    parts["view"]["body"]["colorEncoding"] = {
        "scale": "series", "target": "planned", "source": {"field": "owner"}, "domain": ["bus"],
    }

    with pytest.raises(RenderFailed) as caught:
        sr.render(tmp_path, _project("other"), presentation=parts)

    error = caught.value
    assert error.code == "E_PRESENTATION_SCALE_VALUE"
    assert error.source_ref == "/body/colorEncoding"
    assert "object='scale-task'" in error.message
    assert "field='owner'" in error.message and "value='other'" in error.message


@pytest.mark.parametrize("caller", ("colorEncoding", "grouping.tint"))
def test_exact_mapping_mismatch_report_names_theme_keys_and_owner(caller, tmp_path):
    parts = _parts()
    scale_id = "bad/name~scale"
    parts["theme"]["body"]["colorScales"][scale_id] = {
        "slots": {"bus": "series-1", "extra-key": "series-2"},
    }
    if caller == "colorEncoding":
        parts["view"]["body"]["colorEncoding"] = {
            "scale": scale_id, "target": "planned", "source": {"field": "owner"},
            "domain": ["bus", "payload"],
        }
    else:
        parts["view"]["body"]["grouping"]["tint"] = {
            "scale": scale_id, "domain": ["bus", "payload"],
        }

    with pytest.raises(RenderFailed) as caught:
        sr.render(tmp_path, _project(), presentation=parts)

    error = caught.value
    assert error.code == "E_PRESENTATION_SCALE_MAPPING"
    report = report_failure(error)
    (row,) = report.diagnostics
    assert row["code"] == "E_PRESENTATION_SCALE_MAPPING"
    assert row["sourceRef"] == "/body/colorScales/bad~1name~0scale/slots"
    assert "missing keys=[\"'payload'\"]" in row["message"]
    assert "extra keys=[\"'extra-key'\"]" in row["message"]
